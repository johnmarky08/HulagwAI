const LOG_KEY = "scanLog";
const LOG_LIMIT = 50;
const PENDING_KEY_PREFIX = "pendingScan:";
const SCAN_REVIEW_KEY = "scanReviewRequestId";
const CONTEXT_MENU_ID = "hulagwai-scan-image";
const MAX_UPLOAD_BYTES = 5 * 1024 * 1024;
const POLL_DELAY_MS = 800;
const MAX_POLLS = 90;

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function allowedImageUrl(raw) {
  let url;
  try {
    url = new URL(raw);
  } catch {
    throw new Error("The selected image does not have a valid web address.");
  }
  if (!["https:", "http:"].includes(url.protocol) || url.username || url.password) {
    throw new Error("Only images with an HTTP or HTTPS address can be scanned.");
  }
  return url;
}

async function log(stage, message, details = {}) {
  const { [LOG_KEY]: current = [] } = await chrome.storage.local.get(LOG_KEY);
  const entry = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    time: new Date().toLocaleTimeString(),
    stage,
    message,
    ...details,
  };
  await chrome.storage.local.set({ [LOG_KEY]: [entry, ...current].slice(0, LOG_LIMIT) });
  console.info("[HulagwAI image scan]", entry);
}

async function getBackendConfig() {
  const { backendUrl, extensionToken } = await chrome.storage.local.get(["backendUrl", "extensionToken"]);
  if (!backendUrl || !extensionToken) {
    throw new Error("Pair the extension with your HulagwAI account from the popup first.");
  }
  const parsed = new URL(backendUrl);
  if (!(["http:", "https:"].includes(parsed.protocol)) || parsed.username || parsed.password) {
    throw new Error("Enter a valid HTTP or HTTPS HulagwAI site address.");
  }
  return { base: parsed.origin, originPattern: `${parsed.origin}/*`, token: extensionToken };
}

async function requestSitePermission(originPattern, label = "your HulagwAI site") {
  const allowed = await chrome.permissions.contains({ origins: [originPattern] });
  if (!allowed) {
    throw new Error(`Grant this extension access to ${label} before scanning.`);
  }
}

async function getImageFile(rawUrl) {
  const imageUrl = allowedImageUrl(rawUrl);
  await requestSitePermission(`${imageUrl.origin}/*`, `the selected image host (${imageUrl.hostname})`);
  const response = await fetch(imageUrl.href, {
    credentials: "omit",
    redirect: "follow",
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`Image download failed (HTTP ${response.status}).`);
  const finalUrl = allowedImageUrl(response.url);
  await requestSitePermission(`${finalUrl.origin}/*`, `the image's redirect host (${finalUrl.hostname})`);

  const mime = (response.headers.get("content-type") || "").split(";")[0].toLowerCase();
  if (!["image/jpeg", "image/png", "image/webp"].includes(mime)) {
    throw new Error("This image format is not supported. HulagwAI accepts JPG, PNG, or WEBP.");
  }
  const declaredSize = Number(response.headers.get("content-length") || 0);
  if (declaredSize > MAX_UPLOAD_BYTES) {
    throw new Error("This image is larger than HulagwAI's 5 MB upload limit.");
  }

  let blob;
  if (response.body?.getReader) {
    const reader = response.body.getReader();
    const chunks = [];
    let size = 0;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > MAX_UPLOAD_BYTES) {
        await reader.cancel();
        throw new Error("This image is larger than HulagwAI's 5 MB upload limit.");
      }
      chunks.push(value);
    }
    blob = new Blob(chunks, { type: mime });
  } else {
    blob = await response.blob();
    if (blob.size > MAX_UPLOAD_BYTES) {
      throw new Error("This image is larger than HulagwAI's 5 MB upload limit.");
    }
  }

  const extension = mime === "image/png" ? "png" : mime === "image/webp" ? "webp" : "jpg";
  return new File([blob], `selected-image-${Date.now()}.${extension}`, { type: mime });
}

async function readJson(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.message || `HulagwAI request failed (HTTP ${response.status}).`);
  }
  return payload;
}

async function getAnalysis(base, id, token) {
  const response = await fetch(`${base}/api/v1/extension/analyses/${encodeURIComponent(id)}`, {
    credentials: "omit",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
    },
  });
  return readJson(response);
}

async function waitForAnalysis(base, id, token) {
  for (let attempt = 0; attempt < MAX_POLLS; attempt += 1) {
    const result = await getAnalysis(base, id, token);
    if (result.status === "done" || result.status === "failed") return result;
    await delay(POLL_DELAY_MS);
  }
  throw new Error(`Analysis ${id} is still processing. Check the HulagwAI History page.`);
}

async function scanImage(imageUrl) {
  allowedImageUrl(imageUrl);
  const { base, originPattern, token } = await getBackendConfig();
  await requestSitePermission(originPattern);

  await log("fetch_started", "Fetching the selected web image.");
  const file = await getImageFile(imageUrl);
  await log("image_fetched", "Image fetched and ready to upload.", {
    bytes: file.size,
    mime: file.type,
  });

  const body = new FormData();
  body.append("image", file);
  const response = await fetch(`${base}/api/v1/extension/analyses`, {
    method: "POST",
    credentials: "omit",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
    },
    body,
  });
  const accepted = await readJson(response);
  if (!accepted.id) throw new Error("The API returned no analysis ID.");
  await log("upload_accepted", `HulagwAI accepted the upload (HTTP ${response.status}).`, {
    httpStatus: response.status,
    analysisId: accepted.id,
    bytes: file.size,
    mime: file.type,
  });

  const complete = accepted.status === "done" ? accepted : await waitForAnalysis(base, accepted.id, token);
  if (complete.status === "failed") {
    throw new Error(complete.error?.message || "The analysis failed.");
  }
  const result = complete.result || {};
  const summary = {
    analysisId: accepted.id,
    status: complete.status,
    label: result.label || "Analysis complete",
    verdict: result.verdict || "inconclusive",
    confidencePercent: result.confidence_percent ?? Math.round((result.confidence ?? 0) * 100),
  };
  await log("analysis_complete", "Image analysis completed.", summary);
  return summary;
}

const activeScans = new Set();

function fromExtensionPopup(sender) {
  try {
    const expected = new URL(chrome.runtime.getURL("popup.html"));
    const actual = new URL(sender?.url);
    return actual.origin === expected.origin && actual.pathname === expected.pathname;
  } catch {
    return false;
  }
}

async function setContextMenuVisible(visible) {
  chrome.contextMenus.update(CONTEXT_MENU_ID, { visible: Boolean(visible) }, () => {
    // Read lastError so a missing menu during initial install does not produce an unhandled warning.
    void chrome.runtime.lastError;
  });
}

async function refreshContextMenu() {
  const { enabled: isEnabled = false } = await chrome.storage.local.get("enabled");
  setContextMenuVisible(isEnabled);
}

function registerContextMenu() {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: CONTEXT_MENU_ID,
      title: "Scan image with HulagwAI",
      contexts: ["image"],
      visible: false,
    });
    void refreshContextMenu();
  });
}

chrome.runtime.onInstalled.addListener(registerContextMenu);
chrome.runtime.onStartup.addListener(registerContextMenu);

// Opens the toolbar popup right away so it stays within the right-click's user gesture.
// If an already-open popup is listening, it is asked to show the review instead.
// If neither works, a badge flags the pending request on the toolbar icon.
function openScanReview(windowId) {
  const options = Number.isInteger(windowId) ? { windowId } : {};
  const opened = chrome.action.openPopup(options).then(
    () => true,
    (error) => {
      console.warn("[HulagwAI image scan] could not open the popup automatically", error);
      return false;
    },
  );
  const refreshed = chrome.runtime
    .sendMessage({ type: "HULAGWAI_SHOW_SCAN_REVIEW" })
    .then((response) => response?.ok === true, () => false);
  return Promise.all([opened, refreshed]).then(async ([wasOpened, wasRefreshed]) => {
    if (wasOpened || wasRefreshed) return;
    await chrome.action.setBadgeBackgroundColor({ color: "#4f46e5" });
    await chrome.action.setBadgeText({ text: "1" });
    await chrome.action.setTitle({ title: "HulagwAI: review your image scan" });
  });
}

chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "local" && changes.enabled) void setContextMenuVisible(changes.enabled.newValue);
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId !== CONTEXT_MENU_ID) return;
  let imageUrl = null;
  let requestError = "";
  try {
    imageUrl = allowedImageUrl(info.srcUrl);
  } catch (error) {
    requestError = error?.message || "This image address cannot be scanned.";
  }
  const requestId = crypto.randomUUID();
  const key = `${PENDING_KEY_PREFIX}${requestId}`;
  // Start the storage write, then open the popup in the same turn; the popup reads the request when it loads.
  const saved = chrome.storage.session.set({
    [key]: {
      imageUrl: imageUrl?.href || "",
      error: requestError,
      createdAt: Date.now(),
    },
    [SCAN_REVIEW_KEY]: requestId,
  });
  openScanReview(tab?.windowId).catch((error) => console.error("[HulagwAI image scan] could not show the review", error));
  saved.catch((error) => console.error("[HulagwAI image scan] could not save the request", error));
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!fromExtensionPopup(sender)) return undefined;
  if (message?.type === "HULAGWAI_CANCEL_PENDING_SCAN") {
    const requestId = String(message.requestId || "");
    if (/^[a-f0-9-]{20,64}$/i.test(requestId)) {
      chrome.storage.session.remove(`${PENDING_KEY_PREFIX}${requestId}`);
    }
    sendResponse({ ok: true });
    return undefined;
  }
  if (message?.type !== "HULAGWAI_CONFIRM_SCAN") return undefined;

  const requestId = String(message.requestId || "");
  if (!/^[a-f0-9-]{20,64}$/i.test(requestId) || activeScans.has(requestId)) {
    sendResponse({ ok: false, error: "This scan request is invalid or already running." });
    return undefined;
  }

  activeScans.add(requestId);
  const key = `${PENDING_KEY_PREFIX}${requestId}`;
  chrome.storage.session.get(key).then(async (stored) => {
    const pending = stored[key];
    if (!pending || Date.now() - pending.createdAt > 10 * 60 * 1000) {
      throw new Error("This scan request expired. Right-click the image again.");
    }
    const result = await scanImage(pending.imageUrl);
    await chrome.storage.session.remove(key);
    sendResponse({ ok: true, result });
  }).catch(async (error) => {
    const messageText = error?.message || "The image scan failed.";
    await log("scan_failed", messageText);
    sendResponse({ ok: false, error: messageText });
  }).finally(() => activeScans.delete(requestId));
  return true;
});
