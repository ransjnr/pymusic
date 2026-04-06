/* ── pyMusic Content Script — Page URL Detector ──────────────────────── */

(function () {
  'use strict';

  // Notify background / popup about the current page URL
  function reportCurrentUrl() {
    chrome.runtime.sendMessage({
      type: 'PAGE_URL',
      url: window.location.href,
      title: document.title,
    });
  }

  // Report on load
  reportCurrentUrl();

  // Report again when YouTube / SPA navigates without a full page reload
  let lastUrl = location.href;
  const observer = new MutationObserver(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      reportCurrentUrl();
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });
})();
