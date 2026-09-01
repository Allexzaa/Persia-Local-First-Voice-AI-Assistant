// Inject linkedin extractor script into page context so it has full DOM access
function injectExtractors() {
  return new Promise((resolve) => {
    if (window.__linkedinExtractors) { resolve(); return; }
    const s = document.createElement("script");
    s.src = chrome.runtime.getURL("extractors/linkedin.js");
    s.onload = () => { s.remove(); resolve(); };
    (document.head || document.documentElement).appendChild(s);
  });
}

chrome.runtime.onMessage.addListener((cmd, sender, sendResponse) => {
  handleCommand(cmd).then(sendResponse).catch((err) => {
    sendResponse({ error: err.message });
  });
  return true;
});

async function handleCommand(cmd) {
  const linkedinActions = ["search_jobs", "get_profile", "get_feed", "get_notifications", "search_people"];

  if (linkedinActions.includes(cmd.action)) {
    await injectExtractors();
    return await runInPageContext(cmd.action, cmd.params || {});
  }

  switch (cmd.action) {
    case "get_page_text":
      return getPageText();
    default:
      return { error: `Unknown action: ${cmd.action}` };
  }
}

// Run extractor in page context via postMessage (avoids CSP issues)
function runInPageContext(action, params) {
  return new Promise((resolve, reject) => {
    const id = Math.random().toString(36).slice(2);

    window.addEventListener("message", function handler(event) {
      if (event.source !== window || !event.data || event.data.__persiaId !== id) return;
      window.removeEventListener("message", handler);
      if (event.data.error) reject(new Error(event.data.error));
      else resolve(event.data.result);
    });

    window.postMessage({ __persiaAction: action, __persiaParams: params, __persiaId: id }, "*");

    setTimeout(() => reject(new Error("Extractor timed out")), 10000);
  });
}

function getPageText() {
  const clone = document.body.cloneNode(true);
  for (const tag of ["script", "style", "nav", "footer", "header", "code", "template", "noscript"]) {
    clone.querySelectorAll(tag).forEach((el) => el.remove());
  }
  const text = clone.innerText
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.length > 0)
    .join("\n");

  return {
    url: window.location.href,
    title: document.title,
    text: text.slice(0, 50000),
  };
}
