// LinkedIn DOM extractors — targets specific elements, not raw innerText

function text(el, selector) {
  const found = el.querySelector(selector);
  return found ? found.innerText.trim() : "";
}

function attr(el, selector, attribute) {
  const found = el.querySelector(selector);
  return found ? (found.getAttribute(attribute) || "").trim() : "";
}

// --- search_jobs ---
function extractJobs() {
  const selectors = [
    ".job-card-container",
    ".jobs-search-results__list-item",
    "[data-job-id]",
  ];

  let cards = [];
  for (const sel of selectors) {
    cards = Array.from(document.querySelectorAll(sel));
    if (cards.length) break;
  }

  if (!cards.length) return { error: "No job cards found on page", jobs: [] };

  const jobs = cards.slice(0, 10).map((card) => {
    const titleEl =
      card.querySelector("a.job-card-list__title--link") ||
      card.querySelector(".job-card-list__title") ||
      card.querySelector("a[class*='job-card']");

    // <strong> inside aria-hidden span holds the clean title without "with verification"
    const title = titleEl
      ? (text(titleEl, "span[aria-hidden='true'] strong") ||
         text(titleEl, "span[aria-hidden='true']").split("\n")[0].trim())
      : "";

    const url = titleEl ? titleEl.href : "";

    const company = text(card, ".artdeco-entity-lockup__subtitle span");

    const location = text(card, ".artdeco-entity-lockup__caption li span");

    const jobId = card.getAttribute("data-job-id") ||
      card.querySelector("[data-job-id]")?.getAttribute("data-job-id") || "";

    return { title, company, location, url, job_id: jobId };
  }).filter(j => j.title);

  return { jobs, total_on_page: cards.length };
}

// --- get_profile ---
function extractProfile() {
  const name =
    text(document, "h1.text-heading-xlarge") ||
    text(document, ".pv-text-details__left-panel h1");

  const headline =
    text(document, ".text-body-medium.break-words") ||
    text(document, ".pv-text-details__left-panel .text-body-medium");

  const location = text(document, ".pv-text-details__left-panel .text-body-small.inline");

  const about = text(document, ".pv-shared-text-with-see-more span[aria-hidden='true']") ||
    text(document, "#about ~ * .pv-shared-text-with-see-more span");

  const roles = Array.from(
    document.querySelectorAll(".pvs-list__paged-list-item .mr1.t-bold span[aria-hidden='true']")
  ).slice(0, 3).map(el => el.innerText.trim());

  return { name, headline, location, about, recent_roles: roles };
}

// --- get_feed ---
function extractFeed() {
  const posts = Array.from(
    document.querySelectorAll(".feed-shared-update-v2, [data-urn*='activity']")
  ).slice(0, 10).map((post) => {
    const author =
      text(post, ".update-components-actor__name span[aria-hidden='true']") ||
      text(post, ".feed-shared-actor__name");

    const content =
      text(post, ".feed-shared-update-v2__description span[aria-hidden='true']") ||
      text(post, ".feed-shared-text span[aria-hidden='true']");

    const timestamp =
      text(post, ".update-components-actor__sub-description span[aria-hidden='true']") ||
      text(post, ".feed-shared-actor__sub-description");

    return { author, content: content.slice(0, 500), timestamp };
  }).filter(p => p.author || p.content);

  return { posts, total_on_page: posts.length };
}

// --- get_notifications ---
function extractNotifications() {
  const items = Array.from(
    document.querySelectorAll(".nt-card-list__item, [data-notification-card]")
  ).slice(0, 15).map((item) => {
    const text_content = item.innerText.trim().split("\n").filter(l => l.trim()).join(" ");
    return { text: text_content.slice(0, 200) };
  }).filter(n => n.text);

  return { notifications: items, total_on_page: items.length };
}

// --- search_people ---
function extractPeople() {
  const cards = Array.from(
    document.querySelectorAll(".reusable-search__result-container, .entity-result")
  ).slice(0, 10).map((card) => {
    const name =
      text(card, ".entity-result__title-text a span[aria-hidden='true']") ||
      text(card, ".app-aware-link span[aria-hidden='true']");

    const headline =
      text(card, ".entity-result__primary-subtitle") ||
      text(card, ".entity-result__summary");

    const location = text(card, ".entity-result__secondary-subtitle");

    const profileUrl = attr(card, ".app-aware-link", "href").split("?")[0];

    return { name, headline, location, profile_url: profileUrl };
  }).filter(p => p.name);

  return { people: cards, total_on_page: cards.length };
}

// --- get_job_details ---
async function extractJobDetails(params) {
  const jobId = params && params.job_id;
  if (!jobId) return { error: "Missing job_id param" };

  // Click the card with this job_id to load the description panel
  const card =
    document.querySelector(`[data-job-id="${jobId}"]`) ||
    document.querySelector(`.job-card-container a[href*="${jobId}"]`);

  if (card) {
    (card.closest(".job-card-container") || card).click();
    // Wait for description panel to load
    await new Promise(r => setTimeout(r, 2000));
  }

  // Extract description from the side panel
  const panel =
    document.querySelector(".jobs-search__job-details--container") ||
    document.querySelector(".job-details-jobs-unified-top-card__container--two-pane") ||
    document.querySelector("[class*='job-details']");

  if (!panel) return { error: "Description panel not found", job_id: jobId };

  const titleEl = panel.querySelector(
    ".job-details-jobs-unified-top-card__job-title h1, " +
    ".jobs-unified-top-card__job-title h1, " +
    "h1"
  );
  const companyEl = panel.querySelector(
    ".job-details-jobs-unified-top-card__company-name a, " +
    ".jobs-unified-top-card__company-name a, " +
    "[class*='company-name'] a"
  );
  const locationEl = panel.querySelector(
    ".job-details-jobs-unified-top-card__bullet, " +
    ".jobs-unified-top-card__bullet, " +
    "[class*='workplace-type'], " +
    "[class*='bullet']"
  );

  const descEl =
    panel.querySelector(".jobs-description__content .jobs-description-content__text") ||
    panel.querySelector(".jobs-description__content") ||
    panel.querySelector("[class*='description-content']") ||
    panel.querySelector(".jobs-box__html-content");

  // Clean description — strip HTML tags, collapse whitespace
  const rawDesc = descEl ? descEl.innerText : "";
  const description = rawDesc
    .split("\n").map(l => l.trim()).filter(l => l).join("\n")
    .slice(0, 8000);

  return {
    job_id: jobId,
    title: titleEl ? titleEl.innerText.trim() : "",
    company: companyEl ? companyEl.innerText.trim() : "",
    location: locationEl ? locationEl.innerText.trim() : "",
    description,
  };
}

// --- get_inbox ---
async function extractInbox(params) {
  if (!window.location.href.includes("linkedin.com/messaging")) {
    return { error: "Not on LinkedIn Messaging page. Navigating there now — please try again in a moment." };
  }

  // Wait for the conversation list to render
  await new Promise(r => setTimeout(r, 1500));

  const listSelectors = [
    ".msg-conversations-container__conversations-list li",
    ".msg-conversation-card",
    ".msg-conversation-listitem",
    "[data-control-name='conversation_card']",
  ];

  let items = [];
  for (const sel of listSelectors) {
    items = Array.from(document.querySelectorAll(sel));
    if (items.length) break;
  }

  if (!items.length) {
    const container = document.querySelector(".msg-conversations-container") ||
                      document.querySelector(".scaffold-layout__main");
    return {
      conversations: [],
      raw_text: container ? container.innerText.slice(0, 2000) : "No conversations found",
    };
  }

  const limit = params && params.limit ? parseInt(params.limit) : 10;
  const conversations = items.slice(0, limit).map(item => {
    const nameEl =
      item.querySelector(".msg-conversation-listitem__participant-names .truncate") ||
      item.querySelector(".msg-conversation-card__participant-names span[aria-hidden='true']") ||
      item.querySelector("[class*='participant-names'] span") ||
      item.querySelector("[class*='participant-names']");

    const previewEl =
      item.querySelector(".msg-conversation-listitem__message-snippet-body") ||
      item.querySelector("[class*='message-snippet-body']") ||
      item.querySelector("[class*='message-snippet']");

    const timeEl =
      item.querySelector(".msg-conversation-listitem__time-stamp") ||
      item.querySelector("[class*='time-stamp']") ||
      item.querySelector("time");

    const isUnread = !!(
      item.querySelector(".msg-conversation-card__unread-count") ||
      item.querySelector("[class*='unread-count']")
    );

    const linkEl = item.querySelector("a");

    return {
      name: nameEl ? nameEl.innerText.trim() : "",
      preview: previewEl ? previewEl.innerText.trim().slice(0, 200) : "",
      timestamp: timeEl ? (timeEl.getAttribute("datetime") || timeEl.innerText.trim()) : "",
      unread: isUnread,
      url: linkEl ? linkEl.href : "",
    };
  }).filter(c => c.name || c.preview);

  return { conversations, total_visible: items.length };
}

window.__linkedinExtractors = {
  search_jobs: extractJobs,
  get_profile: extractProfile,
  get_feed: extractFeed,
  get_notifications: extractNotifications,
  search_people: extractPeople,
  get_job_details: extractJobDetails,
  get_inbox: extractInbox,
};

// Listen for commands from content_script via postMessage
window.addEventListener("message", (event) => {
  if (event.source !== window || !event.data || !event.data.__persiaAction) return;
  const { __persiaAction, __persiaId } = event.data;
  const extractor = window.__linkedinExtractors[__persiaAction];
  if (!extractor) {
    window.postMessage({ __persiaId, error: `No extractor for: ${__persiaAction}` }, "*");
    return;
  }
  try {
    const result = extractor();
    window.postMessage({ __persiaId, result }, "*");
  } catch (err) {
    window.postMessage({ __persiaId, error: err.message }, "*");
  }
});
