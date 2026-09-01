import asyncio
import logging
import random
import time
import uuid
from typing import Optional
from urllib.parse import urlparse

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(title="Browser Agent Bridge")

# --- Config ---
MIN_DELAY_SEC = 2.0       # minimum seconds between commands to the same site
MAX_DELAY_SEC = 4.0       # maximum random jitter ceiling
COMMAND_TIMEOUT = 30.0    # seconds before a command times out (navigate_to waits for page load)

# --- State ---
extension_ws: Optional[WebSocket] = None
pending: dict[str, asyncio.Event] = {}
results: dict[str, dict] = {}

# Per-site last-used timestamps: domain -> float (epoch)
site_last_used: dict[str, float] = {}

# Serialise all commands — only 1 in-flight at a time
command_lock = asyncio.Lock()

# Stats exposed to popup
stats = {
    "last_action": None,
    "queue_depth": 0,
    "last_site": None,
    "cooldown_until": 0.0,
}


def _domain(action: str, params: dict) -> str:
    """Derive a site key from the action or navigate_to URL."""
    url = params.get("url", "")
    if url:
        try:
            return urlparse(url).netloc
        except Exception:
            pass
    # LinkedIn actions default to linkedin.com
    linkedin = {"search_jobs", "get_job_details", "get_profile", "get_feed",
                "get_notifications", "search_people", "get_inbox"}
    if action in linkedin:
        return "www.linkedin.com"
    return "unknown"


async def _enforce_cooldown(domain: str):
    """Wait if we hit this domain too recently."""
    last = site_last_used.get(domain, 0.0)
    elapsed = time.monotonic() - last
    if elapsed < MIN_DELAY_SEC:
        delay = MIN_DELAY_SEC - elapsed + random.uniform(0, MAX_DELAY_SEC - MIN_DELAY_SEC)
        stats["cooldown_until"] = time.time() + delay
        log.info(f"Rate limit: waiting {delay:.1f}s before hitting {domain}")
        await asyncio.sleep(delay)
    site_last_used[domain] = time.monotonic()
    stats["cooldown_until"] = 0.0


class Command(BaseModel):
    action: str
    params: dict = {}


@app.get("/health")
async def health():
    now = time.time()
    cooldown_remaining = max(0.0, stats["cooldown_until"] - now)
    return {
        "status": "ok",
        "extension_connected": extension_ws is not None,
        "last_action": stats["last_action"],
        "last_site": stats["last_site"],
        "queue_depth": stats["queue_depth"],
        "cooldown_remaining_sec": round(cooldown_remaining, 1),
    }


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    global extension_ws
    await ws.accept()
    extension_ws = ws
    log.info("Extension connected")
    try:
        while True:
            data = await ws.receive_json()
            command_id = data.get("command_id")
            if command_id and command_id in pending:
                results[command_id] = data
                pending[command_id].set()
                log.info(f"Result received for {command_id}: action={data.get('action')}")
    except WebSocketDisconnect:
        log.warning("Extension disconnected")
        extension_ws = None


@app.post("/command")
async def send_command(cmd: Command):
    if extension_ws is None:
        raise HTTPException(status_code=503, detail="Extension not connected")

    stats["queue_depth"] += 1
    domain = _domain(cmd.action, cmd.params)

    try:
        async with command_lock:
            await _enforce_cooldown(domain)

            command_id = str(uuid.uuid4())
            event = asyncio.Event()
            pending[command_id] = event

            stats["last_action"] = cmd.action
            stats["last_site"] = domain

            payload = {"command_id": command_id, "action": cmd.action, "params": cmd.params}
            await extension_ws.send_json(payload)
            log.info(f"Command sent: {command_id} action={cmd.action} site={domain}")

            try:
                await asyncio.wait_for(event.wait(), timeout=COMMAND_TIMEOUT)
            except asyncio.TimeoutError:
                pending.pop(command_id, None)
                results.pop(command_id, None)
                raise HTTPException(status_code=504, detail="Extension did not respond in time")

            result = results.pop(command_id, {})
            pending.pop(command_id, None)

            # Surface CAPTCHA warning from extension
            # Use `or {}` because data may be explicitly null (key present, value None)
            # — dict.get(key, default) only uses default when the key is missing.
            if (result.get("data") or {}).get("captcha_detected"):
                log.warning("CAPTCHA detected by extension!")
                raise HTTPException(
                    status_code=429,
                    detail="LinkedIn showed a CAPTCHA or unusual activity warning. Please solve it manually in Chromium."
                )

            return JSONResponse(content=result)
    finally:
        stats["queue_depth"] = max(0, stats["queue_depth"] - 1)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8765, reload=False)
