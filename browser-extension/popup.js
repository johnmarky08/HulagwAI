const backendInput = document.querySelector("#backend-url");
const siteForm = document.querySelector("#site-form");
const pairForm = document.querySelector("#pair-form");
const pairInput = document.querySelector("#pair-code");
const status = document.querySelector("#connection-status");
const tokenStatus = document.querySelector("#token-status");
const disconnectButton = document.querySelector("#disconnect");
const enabledInput = document.querySelector("#enabled");
const logList = document.querySelector("#log-list");
const clearButton = document.querySelector("#clear-log");
const showHistoryButton = document.querySelector("#show-history");
const historyView = document.querySelector("#history-view");
const historyList = document.querySelector("#history-list");
const historyCount = document.querySelector("#history-count");
const historyBack = document.querySelector("#history-back");
const historyClear = document.querySelector("#history-clear");
const openSiteHistoryButton = document.querySelector("#open-site-history");
const historySiteStatus = document.querySelector("#history-site-status");
const listPanel = document.querySelector("#history-list-panel");
const analysisPanel = document.querySelector("#analysis-panel");
const analysisBack = document.querySelector("#analysis-back");
const analysisOpen = document.querySelector("#analysis-open");
const adImage = document.querySelector("#analysis-image");
const adFile = document.querySelector("#analysis-file");
const adLabel = document.querySelector("#analysis-label");
const adConfidence = document.querySelector("#analysis-confidence");
const adAi = document.querySelector("#analysis-ai");
const adDate = document.querySelector("#analysis-date");
const adId = document.querySelector("#analysis-id");
const adStatus = document.querySelector("#analysis-status");
const thumbCache = new Map();
let currentLogs = [];
let historyRenderId = 0;
let analysisRequestId = 0;
let currentAnalysisId = "";
const LOG_KEY = "scanLog";
const PREVIEW_LOG_LIMIT = 5;
const SCAN_REVIEW_KEY = "scanReviewRequestId";
const PENDING_PREFIX = "pendingScan:";
const REVIEW_TTL_MS = 10 * 60 * 1000;
const settingsView = document.querySelector("#settings-view");
const reviewView = document.querySelector("#review-view");
const reviewHost = document.querySelector("#review-host");
const reviewPairState = document.querySelector("#review-pair-state");
const reviewStatus = document.querySelector("#review-status");
const permissionBox = document.querySelector("#permission-box");
const permissionCopy = document.querySelector("#permission-copy");
const preview = document.querySelector("#selected-preview");
const previewPlaceholder = document.querySelector("#preview-placeholder");
const grantButton = document.querySelector("#grant-access");
const confirmButton = document.querySelector("#confirm");
const cancelButton = document.querySelector("#cancel");
let review = null;

function showStatus(message, kind = "") {
  status.textContent = message;
  status.className = `status ${kind}`.trim();
}

function normalizeBaseUrl(value) {
  const parsed = new URL(value);
  if (!["http:", "https:"].includes(parsed.protocol) || parsed.username || parsed.password) {
    throw new Error("Use a valid HTTP or HTTPS site address.");
  }
  if (parsed.protocol !== "https:" && !["localhost", "127.0.0.1"].includes(parsed.hostname)) {
    throw new Error("Use HTTPS for a non-local HulagwAI site.");
  }
  return parsed.origin;
}

// Settings shows the latest few attempts; the history view shows everything stored.
function renderLogs(logs = []) {
  currentLogs = logs;
  renderLogList(logList, logs.slice(0, PREVIEW_LOG_LIMIT));
  void renderHistory(logs);
  historyCount.textContent = logs.length === 1 ? "1 attempt" : `${logs.length} attempts`;
}

function entryParts(entry) {
  const time = document.createElement("time");
  time.textContent = entry.time || "";
  const message = document.createElement("span");
  const stage = document.createElement("b");
  stage.textContent = (entry.stage || "event").replaceAll("_", " ");
  message.append(stage, document.createTextNode(` · ${entry.message || ""}`));
  if (entry.analysisId) message.append(document.createElement("br"), document.createTextNode(`Analysis ${entry.analysisId}`));
  return { time, message };
}

function renderEmpty(list) {
  const empty = document.createElement("li");
  empty.className = "empty";
  empty.textContent = "No scan attempts yet.";
  list.append(empty);
}

function renderLogList(list, logs) {
  list.replaceChildren();
  if (!logs.length) return renderEmpty(list);
  for (const entry of logs) {
    const row = document.createElement("li");
    const { time, message } = entryParts(entry);
    row.append(time, message);
    list.append(row);
  }
}

async function pairingState() {
  const stored = await chrome.storage.local.get(["backendUrl", "extensionToken"]);
  return { base: stored.backendUrl, token: stored.extensionToken, paired: Boolean(stored.backendUrl && stored.extensionToken) };
}

// Locked areas are blurred, inert, and show the "Log in to use" prompt until the browser is paired.
function setPaired(paired) {
  for (const gate of document.querySelectorAll("[data-gate]")) {
    gate.classList.toggle("locked", !paired);
    gate.querySelector(".gate-content").inert = !paired;
    gate.querySelector(".gate-overlay").hidden = paired;
  }
}

// Fetches an analysis image with the extension token; cached per popup session.
function loadImageUrl(base, token, id, variant) {
  const key = `${base}|${id}|${variant}`;
  if (!thumbCache.has(key)) {
    thumbCache.set(
      key,
      (async () => {
        try {
          const response = await fetch(`${base}/api/v1/analyses/${encodeURIComponent(id)}/image?variant=${variant}`, {
            credentials: "omit",
            headers: { Accept: "image/*", Authorization: `Bearer ${token}` },
          });
          if (!response.ok) return null;
          return URL.createObjectURL(await response.blob());
        } catch {
          return null;
        }
      })(),
    );
  }
  return thumbCache.get(key);
}

async function renderHistory(logs = currentLogs) {
  const renderId = ++historyRenderId;
  const { base, token, paired } = await pairingState();
  if (renderId !== historyRenderId) return;
  historyList.replaceChildren();
  if (!logs.length) return renderEmpty(historyList);
  for (const entry of logs) {
    const row = document.createElement("li");
    const { time, message } = entryParts(entry);
    if (!entry.analysisId) {
      row.append(time, message);
      historyList.append(row);
      continue;
    }
    row.className = "history-entry";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "history-open";
    button.setAttribute("aria-label", `Show analysis ${entry.analysisId}`);
    const thumb = document.createElement("img");
    thumb.className = "history-thumb";
    thumb.alt = "";
    const text = document.createElement("div");
    text.className = "history-text";
    text.append(time, message);
    button.append(thumb, text);
    button.addEventListener("click", () => openAnalysis(entry.analysisId));
    row.append(button);
    historyList.append(row);
    if (paired) {
      void loadImageUrl(base, token, entry.analysisId, "thumb").then((url) => {
        if (url && renderId === historyRenderId) thumb.src = url;
      });
    }
  }
}

function setAnalysisStatus(message, kind = "") {
  adStatus.textContent = message;
  adStatus.className = `status ${kind}`.trim();
}

function showListPanel() {
  analysisRequestId++;
  analysisPanel.hidden = true;
  listPanel.hidden = false;
}

// Shows one saved analysis in the popup, with its picture and result.
async function openAnalysis(id) {
  const requestId = ++analysisRequestId;
  currentAnalysisId = id;
  listPanel.hidden = true;
  analysisPanel.hidden = false;
  adImage.hidden = true;
  adImage.removeAttribute("src");
  adFile.textContent = "";
  adLabel.textContent = "Loading…";
  adConfidence.textContent = "—";
  adAi.textContent = "—";
  adDate.textContent = "—";
  adId.textContent = id;
  setAnalysisStatus("");
  analysisBack.focus();

  const { base, token, paired } = await pairingState();
  if (!paired) {
    adLabel.textContent = "—";
    setAnalysisStatus("Pair this browser to view saved analyses.", "error");
    return;
  }
  try {
    const response = await fetch(`${base}/api/v1/extension/analyses/${encodeURIComponent(id)}`, {
      credentials: "omit",
      headers: { Accept: "application/json", Authorization: `Bearer ${token}` },
    });
    const payload = await response.json().catch(() => ({}));
    if (requestId !== analysisRequestId) return;
    if (!response.ok) {
      throw new Error(
        response.status === 404
          ? "This analysis is no longer available. It may have been deleted."
          : payload.message || `Could not load this analysis (HTTP ${response.status}).`,
      );
    }
    if (payload.status !== "done" || !payload.result) {
      adLabel.textContent = "—";
      setAnalysisStatus("This analysis has not finished yet.");
      return;
    }
    const result = payload.result;
    adLabel.textContent = result.label;
    adConfidence.textContent = `${result.confidence_percent}%`;
    adAi.textContent = `${result.ai_percent}% AI-generated`;
    adDate.textContent = payload.analyzed_at ? new Date(payload.analyzed_at).toLocaleString() : "—";
    adFile.textContent = payload.file?.filename || "";
    const url = await loadImageUrl(base, token, id, "preview");
    if (requestId === analysisRequestId && url) {
      adImage.src = url;
      adImage.hidden = false;
    }
  } catch (error) {
    if (requestId !== analysisRequestId) return;
    adLabel.textContent = "—";
    setAnalysisStatus(error.message || "Could not load this analysis.", "error");
  }
}

async function readJson(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.message || `Request failed (HTTP ${response.status}).`);
  return payload;
}

async function refreshTokenStatus() {
  const stored = await chrome.storage.local.get(["backendUrl", "extensionToken", "tokenExpiresAt", "enabled"]);
  enabledInput.checked = Boolean(stored.enabled);
  enabledInput.disabled = !stored.extensionToken;
  disconnectButton.hidden = !stored.extensionToken;
  // The full history lives on the website, so the link needs a paired site.
  openSiteHistoryButton.disabled = !(stored.backendUrl && stored.extensionToken);
  historySiteStatus.textContent = openSiteHistoryButton.disabled
    ? "Pair this browser to open your full history on HulagwAI."
    : "";
  setPaired(Boolean(stored.backendUrl && stored.extensionToken));
  if (!historyView.hidden) void renderHistory(currentLogs);
  if (stored.extensionToken) {
    const expiry = stored.tokenExpiresAt ? new Date(stored.tokenExpiresAt).toLocaleDateString() : "unknown";
    tokenStatus.textContent = `Paired · expires ${expiry}`;
    if (stored.backendUrl) showStatus(`Paired with ${stored.backendUrl}.`, "success");
  } else {
    tokenStatus.textContent = "Not paired";
  }
}

async function initialize() {
  // Opening the popup means the user saw any fallback badge from a right-click scan.
  await chrome.action.setBadgeText({ text: "" }).catch(() => {});
  await chrome.action.setTitle({ title: "Open HulagwAI Image Scanner" }).catch(() => {});
  const stored = await chrome.storage.local.get(["backendUrl", "extensionToken", "tokenExpiresAt", "enabled", LOG_KEY]);
  if (stored.backendUrl) backendInput.value = stored.backendUrl;
  renderLogs(stored[LOG_KEY] || []);
  await refreshTokenStatus();
  await showScanReview();
}

siteForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  let base;
  try {
    base = normalizeBaseUrl(backendInput.value.trim());
  } catch (error) {
    showStatus(error.message, "error");
    return;
  }

  const origin = `${base}/*`;
  const permissionRequest = chrome.permissions.request({ origins: [origin] });
  showStatus("Requesting access to this HulagwAI site…");
  try {
    const granted = await permissionRequest;
    if (!granted) throw new Error("Site permission was not granted.");
    await chrome.storage.local.set({ backendUrl: base });
    await chrome.tabs.create({ url: `${base}/extension/connect` });
    showStatus("Pairing page opened. Sign in if asked, then copy its one-time code here.", "success");
  } catch (error) {
    showStatus(error.message || "Could not open the HulagwAI pairing page.", "error");
  }
});

pairForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  let base;
  try {
    base = normalizeBaseUrl(backendInput.value.trim());
  } catch (error) {
    showStatus(error.message, "error");
    return;
  }
  const code = pairInput.value.trim().toLowerCase();
  if (!/^[a-f0-9]{32}$/.test(code)) {
    showStatus("Paste the 32-character code from the HulagwAI pairing page.", "error");
    return;
  }
  const hasPermission = await chrome.permissions.contains({ origins: [`${base}/*`] });
  if (!hasPermission) {
    showStatus("Open the secure pairing page first to grant access to this HulagwAI site.", "error");
    return;
  }

  showStatus("Exchanging the one-time code for a private extension token…");
  try {
    const response = await fetch(`${base}/api/v1/extension/exchange`, {
      method: "POST",
      credentials: "omit",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    });
    const payload = await readJson(response);
    if (typeof payload.token !== "string" || !/^[a-f0-9]{64}$/i.test(payload.token)) {
      throw new Error("HulagwAI returned an invalid extension token.");
    }
    await chrome.storage.local.set({
      backendUrl: base,
      extensionToken: payload.token,
      tokenExpiresAt: payload.expires_at,
      enabled: true,
    });
    pairInput.value = "";
    await refreshTokenStatus();
    showStatus("Extension paired. Right-click an image on any website and choose Scan image with HulagwAI.", "success");
  } catch (error) {
    showStatus(error.message || "Pairing failed. Generate a fresh one-time code.", "error");
  }
});

enabledInput.addEventListener("change", async () => {
  await chrome.storage.local.set({ enabled: enabledInput.checked });
});

disconnectButton.addEventListener("click", async () => {
  const stored = await chrome.storage.local.get(["backendUrl", "extensionToken"]);
  try {
    if (stored.backendUrl && stored.extensionToken) {
      const response = await fetch(`${stored.backendUrl}/api/v1/extension/token`, {
        method: "DELETE",
        credentials: "omit",
        headers: { Accept: "application/json", Authorization: `Bearer ${stored.extensionToken}` },
      });
      if (!response.ok && response.status !== 401) {
        throw new Error(`The server could not revoke this token (HTTP ${response.status}).`);
      }
    }
    await chrome.storage.local.remove(["extensionToken", "tokenExpiresAt"]);
    await chrome.storage.local.set({ enabled: false });
    await refreshTokenStatus();
    showStatus("This extension token has been disconnected.");
  } catch (error) {
    showStatus(error.message || "Could not revoke the extension token. Check your connection and try again.", "error");
  }
});

async function clearLog() {
  await chrome.storage.local.set({ [LOG_KEY]: [] });
  renderLogs([]);
}

clearButton.addEventListener("click", clearLog);
historyClear.addEventListener("click", clearLog);

function showHistoryView() {
  settingsView.hidden = true;
  reviewView.hidden = true;
  showListPanel();
  historyView.hidden = false;
  historyBack.focus();
}

function showSettingsFromHistory() {
  historyView.hidden = true;
  settingsView.hidden = false;
  showHistoryButton.focus();
}

showHistoryButton.addEventListener("click", async () => {
  const stored = await chrome.storage.local.get(LOG_KEY);
  renderLogs(stored[LOG_KEY] || []);
  showHistoryView();
});
historyBack.addEventListener("click", showSettingsFromHistory);

openSiteHistoryButton.addEventListener("click", async () => {
  const stored = await chrome.storage.local.get(["backendUrl", "extensionToken"]);
  if (!stored.backendUrl || !stored.extensionToken) return;
  await chrome.tabs.create({ url: `${stored.backendUrl}/history` });
});

function isTrustedImageUrl(raw) {
  try {
    const url = new URL(raw);
    return ["https:", "http:"].includes(url.protocol) && !url.username && !url.password;
  } catch {
    return false;
  }
}

function showReviewStatus(message, kind = "") {
  reviewStatus.textContent = message;
  reviewStatus.className = `status ${kind}`.trim();
}

function showSettingsView() {
  review = null;
  reviewView.hidden = true;
  historyView.hidden = true;
  settingsView.hidden = false;
}

async function clearScanReview() {
  await chrome.storage.session.remove(SCAN_REVIEW_KEY);
}

preview.addEventListener("load", () => {
  preview.hidden = false;
  previewPlaceholder.hidden = true;
});
preview.addEventListener("error", () => {
  preview.hidden = true;
  previewPlaceholder.hidden = false;
  previewPlaceholder.textContent = "The source blocked its preview. You may still confirm the fetch for analysis.";
});

async function refreshReviewState() {
  if (!review) return;
  const [hasImageAccess, stored] = await Promise.all([
    chrome.permissions.contains({ origins: [review.imageOriginPattern] }),
    chrome.storage.local.get(["backendUrl", "extensionToken"]),
  ]);
  review.accessGranted = hasImageAccess;
  review.paired = Boolean(stored.backendUrl && stored.extensionToken);
  permissionBox.hidden = hasImageAccess;
  confirmButton.disabled = !hasImageAccess || !review.paired || review.busy;
  reviewPairState.textContent = review.paired ? "Paired with your account" : "Not paired yet";
  if (hasImageAccess) {
    if (preview.getAttribute("src") !== review.pending.imageUrl) {
      previewPlaceholder.hidden = false;
      previewPlaceholder.textContent = "Loading selected image preview…";
      preview.src = review.pending.imageUrl;
    }
  } else {
    preview.removeAttribute("src");
    preview.hidden = true;
    previewPlaceholder.hidden = false;
    previewPlaceholder.textContent = "Grant image-host access to preview the selected image here.";
  }
  if (!hasImageAccess) {
    showReviewStatus("Grant access for this image host, then confirm the scan. You can revoke it in browser settings.");
  } else if (!review.paired) {
    showReviewStatus("Pair HulagwAI from the extension toolbar first, then return here.", "error");
  } else {
    showReviewStatus("Ready. The image will only be uploaded if you choose Send image for analysis.", "success");
  }
}

// Shows the confirmation in this popup when a right-click scan is waiting. Returns true if it did.
async function showScanReview() {
  const stored = await chrome.storage.session.get(SCAN_REVIEW_KEY);
  const requestId = stored[SCAN_REVIEW_KEY];
  if (!requestId || !/^[a-f0-9-]{20,64}$/i.test(requestId)) return false;

  const key = `${PENDING_PREFIX}${requestId}`;
  const pendingStored = await chrome.storage.session.get(key);
  const pending = pendingStored[key];
  if (!pending || Date.now() - pending.createdAt > REVIEW_TTL_MS) {
    await chrome.storage.session.remove([key, SCAN_REVIEW_KEY]);
    return false;
  }

  review = { requestId, pending, imageOriginPattern: "", accessGranted: false, paired: false, busy: false, done: false };
  settingsView.hidden = true;
  historyView.hidden = true;
  reviewView.hidden = false;
  confirmButton.textContent = "Send image for analysis";
  cancelButton.textContent = "Cancel";
  cancelButton.disabled = false;
  grantButton.disabled = false;
  confirmButton.disabled = true;
  preview.removeAttribute("src");
  preview.hidden = true;
  previewPlaceholder.hidden = false;

  if (pending.error || !isTrustedImageUrl(pending.imageUrl)) {
    reviewHost.textContent = "Unsupported image address";
    showReviewStatus(pending.error || "Only HTTP or HTTPS image URLs can be scanned.", "error");
    confirmButton.disabled = true;
    grantButton.disabled = true;
    return true;
  }

  const imageUrl = new URL(pending.imageUrl);
  review.imageOriginPattern = `${imageUrl.origin}/*`;
  reviewHost.textContent = imageUrl.hostname;
  permissionCopy.textContent = `Allow HulagwAI Image Scanner to fetch the selected image from ${imageUrl.hostname}. This grants access only to this image host; your page URL and browsing history are not sent.`;
  await refreshReviewState();
  return true;
}

grantButton.addEventListener("click", async () => {
  if (!review?.imageOriginPattern || review.busy) return;
  grantButton.disabled = true;
  showReviewStatus("Requesting access to this image host…");
  try {
    const granted = await chrome.permissions.request({ origins: [review.imageOriginPattern] });
    if (!granted) {
      showReviewStatus("Permission was not granted. Nothing was uploaded.", "error");
      grantButton.disabled = false;
      return;
    }
    await refreshReviewState();
  } catch (error) {
    showReviewStatus(error.message || "Could not request image-host access.", "error");
    grantButton.disabled = false;
  }
});

confirmButton.addEventListener("click", () => {
  if (!review || !review.accessGranted || !review.paired || review.busy) return;
  review.busy = true;
  confirmButton.disabled = true;
  cancelButton.disabled = true;
  grantButton.disabled = true;
  confirmButton.textContent = "Analyzing…";
  showReviewStatus("Fetching the selected image, then sending it to HulagwAI…");
  chrome.runtime.sendMessage({ type: "HULAGWAI_CONFIRM_SCAN", requestId: review.requestId }, async (response) => {
    if (!review) return;
    if (chrome.runtime.lastError) {
      review.busy = false;
      cancelButton.disabled = false;
      confirmButton.disabled = false;
      confirmButton.textContent = "Retry scan";
      showReviewStatus(chrome.runtime.lastError.message, "error");
      return;
    }
    if (!response?.ok) {
      review.busy = false;
      cancelButton.disabled = false;
      confirmButton.disabled = false;
      confirmButton.textContent = "Retry scan";
      showReviewStatus(response?.error || "The scan could not be completed.", "error");
      return;
    }
    const result = response.result;
    review.done = true;
    await clearScanReview();
    showReviewStatus(`${result.label} · ${result.confidencePercent}% confidence · Analysis ${result.analysisId}`, "success");
    confirmButton.textContent = "Analysis complete";
    cancelButton.disabled = false;
    cancelButton.textContent = "Close";
  });
});

cancelButton.addEventListener("click", async () => {
  if (!review) return;
  if (review.done) {
    await clearScanReview();
    window.close();
    return;
  }
  const { requestId } = review;
  await chrome.runtime.sendMessage({ type: "HULAGWAI_CANCEL_PENDING_SCAN", requestId }).catch(() => {});
  await clearScanReview();
  showSettingsView();
});

analysisBack.addEventListener("click", () => {
  showListPanel();
  historyList.querySelector(".history-open")?.focus();
});
analysisOpen.addEventListener("click", async () => {
  if (!currentAnalysisId) return;
  const { base, paired } = await pairingState();
  if (!paired) return;
  await chrome.tabs.create({ url: `${base}/detect?analysis=${encodeURIComponent(currentAnalysisId)}` });
});
for (const button of document.querySelectorAll(".gate-pair")) {
  button.addEventListener("click", () => {
    historyView.hidden = true;
    settingsView.hidden = false;
    backendInput.focus();
  });
}

// Background asks an already-open popup to show a pending right-click scan.
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type !== "HULAGWAI_SHOW_SCAN_REVIEW" || sender.id !== chrome.runtime.id) return undefined;
  sendResponse({ ok: true });
  void showScanReview();
  return false;
});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "local" && review && (changes.backendUrl || changes.extensionToken)) void refreshReviewState();
});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== "local") return;
  if (changes[LOG_KEY]) renderLogs(changes[LOG_KEY].newValue || []);
  if (changes.enabled) enabledInput.checked = Boolean(changes.enabled.newValue);
  if (changes.extensionToken || changes.tokenExpiresAt) void refreshTokenStatus();
});

initialize().catch((error) => showStatus(error.message || "Could not load extension settings.", "error"));
