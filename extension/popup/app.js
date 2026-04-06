/* ── pyMusic Extension Popup ─────────────────────────────────────────── */

const SERVER = 'http://127.0.0.1:6173';
const POLL_MS = 300;

// ── State ─────────────────────────────────────────────────────────────────

let serverOnline    = false;
let currentUrl      = '';
let activeJobId     = null;
let activeEventSrc  = null;
let searchTimeout   = null;

// ── DOM refs ──────────────────────────────────────────────────────────────

const $  = id => document.getElementById(id);
const serverBadge   = $('server-badge');
const badgeLabel    = $('badge-label');
const noServer      = $('no-server');
const mainContent   = $('main-content');
const trackThumb    = $('track-thumb');
const trackThumbPh  = $('track-thumb-placeholder');
const trackTitle    = $('track-title');
const trackArtist   = $('track-artist');
const trackDetail   = $('track-detail');
const urlInput      = $('url-input');
const formatSelect  = $('format-select');
const qualitySelect = $('quality-select');
const downloadBtn   = $('download-btn');
const downloadBtnTx = $('download-btn-text');
const progressWrap  = $('progress-wrap');
const progressLabel = $('progress-label');
const progressPct   = $('progress-pct');
const progressBar   = $('progress-bar');
const progressSub   = $('progress-sub');
const searchInput   = $('search-input');
const searchBtn     = $('search-btn');
const searchResults = $('search-results');
const recentSection = $('recent-section');
const recentList    = $('recent-list');

// ── Init ──────────────────────────────────────────────────────────────────

(async function init() {
  await checkServer();
  if (serverOnline) {
    await detectCurrentPage();
    await loadRecent();
  }

  // Retry server check every 3 s while offline
  setInterval(async () => {
    if (!serverOnline) {
      await checkServer();
      if (serverOnline) {
        await detectCurrentPage();
        await loadRecent();
      }
    }
  }, 3000);
})();

// ── Server health ─────────────────────────────────────────────────────────

async function checkServer() {
  try {
    const res = await fetchJSON('/health', { timeout: 2000 });
    setServerStatus(true);
  } catch {
    setServerStatus(false);
  }
}

function setServerStatus(online) {
  serverOnline = online;
  serverBadge.className = 'server-badge ' + (online ? 'online' : 'offline');
  badgeLabel.textContent = online ? 'online' : 'offline';

  if (online) {
    noServer.style.display    = 'none';
    mainContent.style.display = 'flex';
  } else {
    noServer.style.display    = 'flex';
    mainContent.style.display = 'none';
  }
}

// ── Page detection ────────────────────────────────────────────────────────

async function detectCurrentPage() {
  trackTitle.textContent = 'Detecting page…';
  trackTitle.classList.add('detecting');
  downloadBtn.disabled = true;

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.url) throw new Error('no url');

    const url = tab.url;

    if (!isMusicUrl(url)) {
      trackTitle.textContent = 'No music URL detected';
      trackTitle.classList.remove('detecting');
      urlInput.placeholder = 'Paste a YouTube / SoundCloud URL…';
      return;
    }

    urlInput.value = url;
    setCurrentUrl(url);
    await loadTrackInfo(url);
  } catch (err) {
    trackTitle.textContent = 'No music detected on this page';
    trackTitle.classList.remove('detecting');
  }
}

function isMusicUrl(url) {
  return /youtube\.com\/(watch|playlist)|youtu\.be\/|music\.youtube\.com|soundcloud\.com\/[^/]+\/[^/]+|open\.spotify\.com\/(track|album|playlist)|bandcamp\.com/i.test(url);
}

async function loadTrackInfo(url) {
  try {
    const data = await fetchJSON(`/info?url=${encodeURIComponent(url)}`, { timeout: 10000 });
    renderTrackInfo(data);
    setCurrentUrl(url);
  } catch {
    trackTitle.textContent = 'Could not load info';
    trackTitle.classList.remove('detecting');
  }
}

function renderTrackInfo(data) {
  trackTitle.classList.remove('detecting');

  if (data.type === 'playlist') {
    trackTitle.textContent = data.title || 'Playlist';
    trackArtist.textContent = data.uploader || '';
    trackDetail.textContent = `${data.total_tracks || '?'} tracks`;
    clearThumb();
  } else {
    trackTitle.textContent  = data.title  || 'Unknown title';
    trackArtist.textContent = data.artist || '';
    trackDetail.textContent = data.duration_str || '';

    if (data.thumbnail_url) {
      trackThumb.src = data.thumbnail_url;
      trackThumb.style.display = 'block';
      trackThumbPh.style.display = 'none';
      trackThumb.onerror = clearThumb;
    }
  }

  downloadBtn.disabled = false;
}

function clearThumb() {
  trackThumb.style.display = 'none';
  trackThumbPh.style.display = 'flex';
}

function setCurrentUrl(url) {
  currentUrl = url;
  downloadBtn.disabled = !url;
}

// ── URL input ─────────────────────────────────────────────────────────────

urlInput.addEventListener('input', () => {
  const v = urlInput.value.trim();
  setCurrentUrl(v);
  if (v) {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => loadTrackInfo(v), 600);
  }
});

urlInput.addEventListener('paste', e => {
  const pasted = (e.clipboardData || window.clipboardData).getData('text').trim();
  if (pasted) {
    setTimeout(() => {
      setCurrentUrl(pasted);
      loadTrackInfo(pasted);
    }, 50);
  }
});

// ── Download ──────────────────────────────────────────────────────────────

downloadBtn.addEventListener('click', startDownload);

async function startDownload() {
  const url = urlInput.value.trim() || currentUrl;
  if (!url) return;

  // Cancel existing job
  if (activeEventSrc) { activeEventSrc.close(); activeEventSrc = null; }

  downloadBtn.disabled = true;
  downloadBtnTx.textContent = 'Starting…';
  showProgress('Starting download…', 0);

  try {
    const body = {
      url,
      format:   formatSelect.value,
      quality:  parseInt(qualitySelect.value, 10),
    };

    const { job_id } = await fetchJSON('/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    activeJobId = job_id;
    subscribeToJob(job_id);
  } catch (err) {
    hideProgress();
    downloadBtn.disabled = false;
    downloadBtnTx.textContent = 'Download';
    toast(`Download failed: ${err.message}`, 'error');
  }
}

function subscribeToJob(jobId) {
  const src = new EventSource(`${SERVER}/events/${jobId}`);
  activeEventSrc = src;

  src.onmessage = e => {
    const data = JSON.parse(e.data);

    if (data.done || data.error) {
      src.close();
      activeEventSrc = null;
      downloadBtn.disabled = false;
      downloadBtnTx.textContent = 'Download';

      if (data.error) {
        hideProgress();
        toast(data.error, 'error');
      }
      return;
    }

    const { status, progress, speed, title, artist, error } = data;

    if (status === 'completed') {
      showProgress('Completed!', 100);
      progressPct.textContent = '100%';
      progressBar.style.background = 'linear-gradient(90deg, #10b981, #34d399)';
      progressSub.textContent = title ? `${artist ? artist + ' – ' : ''}${title}` : '';
      toast(`Downloaded: ${title || 'Track'}`, 'success');
      loadRecent();
      return;
    }

    if (status === 'failed') {
      hideProgress();
      toast(error || 'Download failed', 'error');
      downloadBtn.disabled = false;
      downloadBtnTx.textContent = 'Download';
      return;
    }

    if (status === 'downloading') {
      const pct = progress || 0;
      showProgress('Downloading…', pct);
      progressPct.textContent = `${Math.round(pct)}%`;
      if (speed) {
        progressSub.textContent = `${formatBytes(speed)}/s${title ? ' · ' + (title.length > 30 ? title.slice(0,30)+'…' : title) : ''}`;
      }
    } else if (status === 'processing') {
      showProgress('Converting…', 99);
      progressPct.textContent = '99%';
    }
  };

  src.onerror = () => {
    src.close();
    activeEventSrc = null;
  };
}

function showProgress(label, pct) {
  progressWrap.style.display = 'block';
  progressLabel.textContent = label;
  progressBar.style.width = `${pct}%`;
  progressBar.style.background = '';  // reset override
}

function hideProgress() { progressWrap.style.display = 'none'; }

// ── Search ────────────────────────────────────────────────────────────────

searchBtn.addEventListener('click', doSearch);
searchInput.addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });

async function doSearch() {
  const q = searchInput.value.trim();
  if (!q) return;

  searchResults.innerHTML = `<div style="padding:12px 0; text-align:center; color:var(--text-3); font-size:0.8rem; display:flex; align-items:center; justify-content:center; gap:8px"><div class="spinner"></div> Searching…</div>`;

  try {
    const { results } = await fetchJSON('/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: q, limit: 8 }),
    });

    renderSearchResults(results);
  } catch (err) {
    searchResults.innerHTML = `<div style="padding:10px 0; color:var(--error); font-size:0.78rem">Search failed: ${esc(err.message)}</div>`;
  }
}

function renderSearchResults(results) {
  if (!results?.length) {
    searchResults.innerHTML = `<div style="padding:10px 0; color:var(--text-3); font-size:0.78rem">No results found.</div>`;
    return;
  }

  searchResults.innerHTML = results.map((r, i) => `
    <div class="result-item" data-url="${esc(r.url)}" data-idx="${i}">
      ${r.thumbnail_url
        ? `<img class="result-thumb" src="${esc(r.thumbnail_url)}" alt="" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'" /><div class="result-thumb-placeholder" style="display:none">🎵</div>`
        : `<div class="result-thumb-placeholder">🎵</div>`
      }
      <div class="result-info">
        <div class="result-title">${esc(r.title || 'Unknown')}</div>
        <div class="result-artist">${esc(r.artist || '')}</div>
      </div>
      ${r.duration_str ? `<span class="result-dur">${esc(r.duration_str)}</span>` : ''}
      <button class="result-dl-btn" title="Download" data-url="${esc(r.url)}">
        <svg viewBox="0 0 24 24" fill="none"><path d="M12 3v12m0 0l-4-4m4 4l4-4M3 17v2a2 2 0 002 2h14a2 2 0 002-2v-2" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </button>
    </div>
  `).join('');

  // Clicking a result row sets the URL; clicking the download button downloads
  searchResults.querySelectorAll('.result-item').forEach(el => {
    el.addEventListener('click', e => {
      if (e.target.closest('.result-dl-btn')) return;
      const url = el.dataset.url;
      urlInput.value = url;
      setCurrentUrl(url);
      const idx = parseInt(el.dataset.idx, 10);
      renderTrackInfo({ type: 'track', ...results[idx] });
    });
  });

  searchResults.querySelectorAll('.result-dl-btn').forEach(btn => {
    btn.addEventListener('click', e => {
      e.stopPropagation();
      const url = btn.dataset.url;
      urlInput.value = url;
      setCurrentUrl(url);
      startDownload();
    });
  });
}

// ── Recent downloads ──────────────────────────────────────────────────────

async function loadRecent() {
  try {
    const { downloads } = await fetchJSON('/recent');
    if (!downloads?.length) return;

    recentSection.style.display = 'block';
    recentList.innerHTML = downloads.slice(0, 8).map(d => {
      const ok = d.status === 'completed';
      const name = (d.artist ? d.artist + ' – ' : '') + (d.title || d.url || 'Unknown');
      return `
        <div class="recent-item">
          <div class="recent-status ${ok ? 'ok' : 'fail'}">
            <svg viewBox="0 0 24 24" fill="none">
              ${ok
                ? '<path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
                : '<path d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>'
              }
            </svg>
          </div>
          <span class="recent-name" title="${esc(name)}">${esc(name.length > 38 ? name.slice(0,38)+'…' : name)}</span>
          <span class="recent-fmt">${esc(d.format || 'mp3')}</span>
        </div>
      `;
    }).join('');
  } catch { /* ignore */ }
}

// ── Helpers ───────────────────────────────────────────────────────────────

async function fetchJSON(path, opts = {}) {
  const url = path.startsWith('http') ? path : SERVER + path;
  const controller = new AbortController();
  const timer = opts.timeout
    ? setTimeout(() => controller.abort(), opts.timeout)
    : null;

  try {
    const res = await fetch(url, { ...opts, signal: controller.signal });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }
    return res.json();
  } finally {
    if (timer) clearTimeout(timer);
  }
}

function esc(str) {
  return String(str ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function formatBytes(bytes) {
  if (!bytes) return '';
  if (bytes < 1024)       return bytes + ' B';
  if (bytes < 1024*1024)  return (bytes/1024).toFixed(1) + ' KB';
  return (bytes/1024/1024).toFixed(1) + ' MB';
}

// ── Toast ─────────────────────────────────────────────────────────────────

function toast(msg, type = 'info') {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const icons = {
    success: '<path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>',
    error:   '<path d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>',
    info:    '<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path d="M12 8v4m0 4h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  };

  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<svg viewBox="0 0 24 24" fill="none">${icons[type] || icons.info}</svg><span>${esc(msg)}</span>`;
  container.appendChild(el);

  setTimeout(() => el.remove(), 4000);
}
