/* ── pyMusic Background Service Worker ───────────────────────────────── */

const SERVER = 'http://127.0.0.1:6173';

// ── Installation / update ──────────────────────────────────────────────────

chrome.runtime.onInstalled.addListener(({ reason }) => {
  if (reason === 'install') {
    console.log('[pyMusic] Extension installed.');
  }
});

// ── Messages from popup / content scripts ────────────────────────────────

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'PING_SERVER') {
    fetch(`${SERVER}/health`, { signal: AbortSignal.timeout(2000) })
      .then(r => r.json())
      .then(data => sendResponse({ ok: true, data }))
      .catch(() => sendResponse({ ok: false }));
    return true; // keep channel open for async response
  }

  if (msg.type === 'GET_INFO') {
    fetch(`${SERVER}/info?url=${encodeURIComponent(msg.url)}`, {
      signal: AbortSignal.timeout(10000),
    })
      .then(r => r.json())
      .then(data => sendResponse({ ok: true, data }))
      .catch(err => sendResponse({ ok: false, error: err.message }));
    return true;
  }

  if (msg.type === 'START_DOWNLOAD') {
    fetch(`${SERVER}/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(msg.payload),
    })
      .then(r => r.json())
      .then(data => sendResponse({ ok: true, data }))
      .catch(err => sendResponse({ ok: false, error: err.message }));
    return true;
  }
});

// ── Tab updates: notify popup when a music page is navigated to ───────────

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status !== 'complete') return;
  if (!tab.url) return;

  const isMusicPage = /youtube\.com\/(watch|playlist)|youtu\.be\/|music\.youtube\.com|soundcloud\.com\/[^/]+\/[^/]+|open\.spotify\.com\/(track|album|playlist)|bandcamp\.com/i.test(tab.url);

  if (isMusicPage) {
    // Update the badge to indicate a downloadable page is active
    chrome.action.setBadgeText({ text: '♪', tabId });
    chrome.action.setBadgeBackgroundColor({ color: '#8b5cf6', tabId });
  } else {
    chrome.action.setBadgeText({ text: '', tabId });
  }
});
