const BRIDGE_URL = "ws://127.0.0.1:8765/ws";
const RECONNECT_DELAY_MS = [1000, 2000, 4000, 8000, 15000];
const PING_INTERVAL_MS = 20000;

const LINKEDIN_ACTIONS = ["search_jobs", "get_profile", "get_feed", "get_notifications", "search_people", "get_job_details", "get_inbox"];

let ws = null;
let reconnectAttempt = 0;
let connected = false;

// Alarm-based keepalive — chrome.alarms persists even when Chrome force-terminates the SW.
// When the alarm fires, Chrome wakes the SW; the script runs from scratch and connect() is called.
chrome.alarms.create("keepalive", { periodInMinutes: 1 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name !== "keepalive") return;
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "ping" }));
  }
});

// While-alive keepalive — accessing a Chrome API prevents Chrome from marking SW as idle.
function keepAlive() {
  chrome.storage.local.get(null);
  setTimeout(keepAlive, PING_INTERVAL_MS);
}
keepAlive();

function connect() {
  ws = new WebSocket(BRIDGE_URL);

  ws.onopen = () => {
    connected = true;
    reconnectAttempt = 0;
    console.log("[Persia Bridge] Connected to bridge server");
    updateBadge(true);
  };

  ws.onmessage = async (event) => {
    try {
      let cmd;
      try {
        cmd = JSON.parse(event.data);
      } catch {
        console.error("[Persia Bridge] Bad JSON from server:", event.data);
        return;
      }

      // Ignore server-side pings or messages without an action
      if (!cmd.action) return;

      console.log("[Persia Bridge] Command received:", cmd.action, cmd.command_id);

      // For LinkedIn actions and LinkedIn navigate_to: prefer any open LinkedIn tab
      // so the user doesn't need LinkedIn to be the active/frontmost window.
      const isLinkedInAction =
        LINKEDIN_ACTIONS.includes(cmd.action) ||
        (cmd.action === "navigate_to" && (cmd.params?.url || "").includes("linkedin.com"));

      let tab = null;
      if (isLinkedInAction) {
        const linkedinTabs = await chrome.tabs.query({ url: "*://*.linkedin.com/*" });
        if (linkedinTabs.length > 0) tab = linkedinTabs[0];
      }
      if (!tab) {
        const activeTabs = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!activeTabs.length) {
          sendResult(cmd.command_id, cmd.action, null, "No active tab");
          return;
        }
        tab = activeTabs[0];
      }

      const tabId = tab.id;

      // navigate_to: use tab API directly, then wait for page + SPA render
      if (cmd.action === "navigate_to") {
        const url = cmd.params && cmd.params.url;
        if (!url) { sendResult(cmd.command_id, cmd.action, null, "Missing url param"); return; }
        try {
          await chrome.tabs.update(tabId, { url });
          // Wait for the tab to reach "complete" status (HTML loaded)
          await new Promise((resolve) => {
            const timeout = setTimeout(() => {
              chrome.tabs.onUpdated.removeListener(listener);
              resolve();
            }, 15000);
            function listener(updatedTabId, changeInfo) {
              if (updatedTabId === tabId && changeInfo.status === "complete") {
                chrome.tabs.onUpdated.removeListener(listener);
                clearTimeout(timeout);
                resolve();
              }
            }
            chrome.tabs.onUpdated.addListener(listener);
          });
          // Extra delay for JavaScript-rendered content (React/SPA like LinkedIn)
          await new Promise(r => setTimeout(r, 3000));
          sendResult(cmd.command_id, cmd.action, { navigated: true, url }, null);
        } catch (err) {
          sendResult(cmd.command_id, cmd.action, null, err.message);
        }
        return;
      }

      // debug: dump first job card HTML
      if (cmd.action === "dump_card_html") {
        try {
          const results = await chrome.scripting.executeScript({
            target: { tabId },
            func: () => {
              const card = document.querySelector(".job-card-container") ||
                           document.querySelector(".jobs-search-results__list-item") ||
                           document.querySelector("[data-job-id]");
              return card ? card.innerHTML : "NO CARD FOUND";
            },
          });
          sendResult(cmd.command_id, cmd.action, { html: results[0].result }, null);
        } catch (err) {
          sendResult(cmd.command_id, cmd.action, null, err.message);
        }
        return;
      }

      // LinkedIn actions: check for CAPTCHA first, then inject extractor
      if (LINKEDIN_ACTIONS.includes(cmd.action)) {
        try {
          // CAPTCHA / challenge page detection
          const captchaCheck = await chrome.scripting.executeScript({
            target: { tabId },
            func: () => {
              const url = window.location.href;
              const body = document.body?.innerText || "";
              const title = document.title || "";
              return (
                url.includes("/checkpoint/") ||
                url.includes("/authwall") ||
                title.toLowerCase().includes("security verification") ||
                body.includes("unusual activity") ||
                body.includes("Let's do a quick security check") ||
                body.includes("verify you're a human") ||
                document.querySelector("[data-test-id='captcha']") !== null
              );
            },
          });

          if (captchaCheck[0].result) {
            sendResult(cmd.command_id, cmd.action, { captcha_detected: true }, null);
            return;
          }

          await chrome.scripting.executeScript({
            target: { tabId },
            files: ["extractors/linkedin.js"],
          });

          const results = await chrome.scripting.executeScript({
            target: { tabId },
            func: async (action, params) => {
              const extractor = window.__linkedinExtractors && window.__linkedinExtractors[action];
              if (!extractor) return { error: `No extractor for: ${action}` };
              try { return await extractor(params); }
              catch (e) { return { error: e.message }; }
            },
            args: [cmd.action, cmd.params || {}],
          });

          sendResult(cmd.command_id, cmd.action, results[0].result, null);
        } catch (err) {
          sendResult(cmd.command_id, cmd.action, null, err.message);
        }
        return;
      }

      // get_page_text and any other actions: use content script messaging
      try {
        const result = await chrome.tabs.sendMessage(tabId, cmd);
        sendResult(cmd.command_id, cmd.action, result, null);
      } catch (err) {
        sendResult(cmd.command_id, cmd.action, null, err.message);
      }
    } catch (err) {
      console.warn("[Persia Bridge] Uncaught error in message handler:", err.message);
    }
  };

  ws.onerror = (err) => {
    console.warn("[Persia Bridge] WebSocket error:", err);
  };

  ws.onclose = () => {
    connected = false;
    updateBadge(false);
    const delay = RECONNECT_DELAY_MS[Math.min(reconnectAttempt, RECONNECT_DELAY_MS.length - 1)];
    reconnectAttempt++;
    console.log(`[Persia Bridge] Disconnected — reconnecting in ${delay}ms`);
    setTimeout(connect, delay);
  };
}

function sendResult(command_id, action, data, error) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ command_id, action, data, error }));
  }
}

function updateBadge(isConnected) {
  chrome.action.setBadgeText({ text: isConnected ? "ON" : "OFF" });
  chrome.action.setBadgeBackgroundColor({ color: isConnected ? "#22c55e" : "#ef4444" });
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "GET_STATUS") {
    sendResponse({ connected });
  }
});

connect();
