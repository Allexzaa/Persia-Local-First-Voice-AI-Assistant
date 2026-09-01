"""
Dumps the innerHTML of the first LinkedIn job card to find correct CSS selectors.
Run while LinkedIn jobs search page is open in Chromium.
"""
import httpx, time

BRIDGE = "http://127.0.0.1:8765"
JOBS_URL = "https://www.linkedin.com/jobs/search/?keywords=cloud+engineering&location=Oregon%2C+United+States"

def command(action, params={}):
    r = httpx.post(f"{BRIDGE}/command", json={"action": action, "params": params}, timeout=30)
    r.raise_for_status()
    return r.json()

print("Navigating...")
command("navigate_to", {"url": JOBS_URL})
time.sleep(6)

print("Dumping first job card HTML...\n")
result = command("dump_card_html")
html = result.get("data", {}).get("html", "")

# Print first 6000 chars — enough to see the structure
print(html[:6000])
