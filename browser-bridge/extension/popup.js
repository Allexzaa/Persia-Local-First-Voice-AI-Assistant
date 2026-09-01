const BRIDGE = "http://127.0.0.1:8765";

async function refresh() {
  let data = null;
  try {
    const r = await fetch(`${BRIDGE}/health`);
    data = await r.json();
  } catch {
    // bridge server unreachable
  }

  const extConn = data?.extension_connected ?? false;
  const bridgeUp = data !== null;

  // Connection status
  const connected = bridgeUp && extConn;
  document.getElementById("dot").className = "dot" + (connected ? " on" : "");
  document.getElementById("conn-label").textContent = !bridgeUp
    ? "Bridge offline"
    : extConn ? "Connected" : "Extension disconnected";
  document.getElementById("conn-label").className = "conn-label " + (connected ? "on" : "off");

  // Stats
  document.getElementById("last-action").textContent = data?.last_action || "—";
  document.getElementById("last-site").textContent = data?.last_site || "—";
  document.getElementById("queue").textContent = data?.queue_depth ?? "—";

  const cd = data?.cooldown_remaining_sec ?? 0;
  const cdEl = document.getElementById("cooldown");
  if (cd > 0) {
    cdEl.textContent = `${cd}s`;
    cdEl.className = "stat-value warn";
  } else {
    cdEl.textContent = "—";
    cdEl.className = "stat-value";
  }

  document.getElementById("hint").textContent = !bridgeUp
    ? "Start: python3 server.py"
    : !extConn
    ? "Reload extension in chrome://extensions"
    : "Ready";
}

refresh();
// Refresh every 2s while popup is open
setInterval(refresh, 2000);
