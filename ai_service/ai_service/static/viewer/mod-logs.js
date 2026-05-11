const LS_KEY = 'npc_ai_viewer_mod_logs_v1';
const LS_MIN_LEVEL_KEY = 'npc_ai_viewer_mod_log_min_level_v1';
const MAX_STORED = 2000;

/** @type {'debug' | 'info' | 'error'} */
let minLevelFilter = 'debug';

/** Severity order: larger = more severe (Cloud-style minimum threshold). */
const LEVEL_RANK = { debug: 0, info: 1, error: 2 };

/** @type {{ timestamp_utc: string, level: string, tag: string, message: string, traceback?: string|null }[]} */
let entries = [];

/**
 * True = user is intentionally following new lines (pinned to bottom).
 * Updated from real scroll gestures only — not inferred from buggy layout reads.
 * @type {boolean}
 */
let userFollowingTail = true;

/** Ignore `scroll` events while we set scrollTop ourselves (so we don’t overwrite intent). */
let ignoreScrollEvents = false;

export function routeViewerMessage(data) {
  if (data && data.type === 'mod_logs' && Array.isArray(data.entries) && data.entries.length) {
    appendEntries(data.entries);
    return true;
  }
  return false;
}

function loadStored() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      entries = parsed.slice(-MAX_STORED);
    }
  } catch (e) {
    entries = [];
  }
}

function loadMinLevelPref() {
  try {
    const v = localStorage.getItem(LS_MIN_LEVEL_KEY);
    if (v === 'info' || v === 'error' || v === 'debug') {
      minLevelFilter = v;
    }
  } catch (e) {
    /* ignore */
  }
}

function saveMinLevelPref() {
  try {
    localStorage.setItem(LS_MIN_LEVEL_KEY, minLevelFilter);
  } catch (e) {
    /* ignore */
  }
}

function rankForLevel(level) {
  const k = String(level || 'info').toLowerCase();
  if (k in LEVEL_RANK) {
    return LEVEL_RANK[k];
  }
  return LEVEL_RANK.info;
}

/** Entry passes when its severity is at least the chosen minimum (hide lower levels). */
function entryPassesMinLevel(e) {
  return rankForLevel(e.level) >= LEVEL_RANK[minLevelFilter];
}

function getVisibleEntries() {
  return entries.filter(entryPassesMinLevel);
}

function persist() {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(entries));
  } catch (e) {
    /* ignore quota */
  }
}

function formatLine(e) {
  const level = String(e.level || 'info').toUpperCase();
  let t = `${e.timestamp_utc} [${level}] ${e.tag}: ${e.message}`;
  if (e.traceback) {
    t += '\n' + String(e.traceback);
  }
  return t;
}

function formatAllLogs() {
  return getVisibleEntries().map(formatLine).join('\n');
}

/** How close to the bottom counts as “viewing the latest” (subpixel). */
const SCROLL_BOTTOM_STICKY_PX = 4;

function isPinnedToBottom(list) {
  if (!list) return true;
  const scrollable = list.scrollHeight > list.clientHeight + 1;
  if (!scrollable) {
    return true;
  }
  const fromBottom = list.scrollHeight - list.scrollTop - list.clientHeight;
  return fromBottom <= SCROLL_BOTTOM_STICKY_PX;
}

function syncTailIntentFromScroll(list) {
  if (ignoreScrollEvents || !list) return;
  userFollowingTail = isPinnedToBottom(list);
}

function appendEntries(incoming) {
  const list = document.getElementById('modLogList');
  const panel = document.getElementById('modLogPanel');
  let previousScrollTop = 0;
  if (list && panel?.classList.contains('open')) {
    previousScrollTop = list.scrollTop;
  }

  const stickToBottom = userFollowingTail;

  for (const row of incoming) {
    if (!row || typeof row !== 'object') continue;
    entries.push({
      timestamp_utc: String(row.timestamp_utc ?? ''),
      level: String(row.level ?? 'info'),
      tag: String(row.tag ?? ''),
      message: String(row.message ?? ''),
      traceback: row.traceback == null ? null : String(row.traceback),
    });
  }
  if (entries.length > MAX_STORED) {
    entries = entries.slice(-MAX_STORED);
  }
  persist();
  renderList();

  if (!list || !panel?.classList.contains('open')) return;

  ignoreScrollEvents = true;
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      const maxScroll = Math.max(0, list.scrollHeight - list.clientHeight);
      if (stickToBottom) {
        list.scrollTop = list.scrollHeight;
        userFollowingTail = true;
      } else {
        list.scrollTop = Math.min(previousScrollTop, maxScroll);
      }
      requestAnimationFrame(() => {
        ignoreScrollEvents = false;
      });
    });
  });
}

function scrollListToBottom() {
  const list = document.getElementById('modLogList');
  const panel = document.getElementById('modLogPanel');
  if (!list || !panel || !panel.classList.contains('open')) return;
  ignoreScrollEvents = true;
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      list.scrollTop = list.scrollHeight;
      userFollowingTail = true;
      requestAnimationFrame(() => {
        ignoreScrollEvents = false;
      });
    });
  });
}

function renderList() {
  const list = document.getElementById('modLogList');
  const countEl = document.getElementById('modLogCount');
  if (!list) return;

  const visible = getVisibleEntries();

  if (countEl) {
    const n = entries.length;
    const m = visible.length;
    if (minLevelFilter === 'debug' || n === 0) {
      countEl.textContent = n + ' line' + (n !== 1 ? 's' : '');
    } else {
      countEl.textContent = m + ' / ' + n + ' lines (min ' + minLevelFilter + ')';
    }
  }

  list.replaceChildren();

  if (!entries.length) {
    const empty = document.createElement('p');
    empty.className = 'mod-log-empty';
    empty.textContent = 'No mod log lines yet.';
    list.appendChild(empty);
    return;
  }

  if (!visible.length) {
    const empty = document.createElement('p');
    empty.className = 'mod-log-empty';
    empty.textContent =
      'No lines at this minimum level. Choose a lower Min level or clear the filter.';
    list.appendChild(empty);
    return;
  }

  for (const e of visible) {
    const row = document.createElement('div');
    row.className = 'mod-log-row';
    const levelRaw = (e.level || 'info').toLowerCase();
    const levelSafe =
      levelRaw === 'debug' || levelRaw === 'error' || levelRaw === 'info'
        ? levelRaw
        : 'info';
    row.innerHTML = `
      <div class="mod-log-meta">
        <time class="mod-log-ts" datetime="${escapeAttr(e.timestamp_utc)}">${escapeHtml(shortTs(e.timestamp_utc))}</time>
        <span class="mod-log-level mod-log-level--${levelSafe}">${escapeHtml(levelSafe)}</span>
        <span class="mod-log-tag u-ellipsis">${escapeHtml(e.tag || '—')}</span>
      </div>
      <p class="mod-log-msg">${escapeHtml(e.message || '')}</p>
    `;
    if (e.traceback) {
      const pre = document.createElement('pre');
      pre.className = 'mod-log-trace u-font-mono';
      pre.textContent = e.traceback;
      row.appendChild(pre);
    }
    list.appendChild(row);
  }
}

function shortTs(iso) {
  if (!iso) return '—';
  const t = iso.replace(/^(\d{4}-\d{2}-\d{2})T([\d:]+).*/, (_, d, hm) => d + ' ' + hm);
  return t.length < iso.length ? t : iso;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function escapeAttr(s) {
  return escapeHtml(s).replace(/'/g, '&#39;');
}

export function initModLogPanel() {
  loadStored();
  loadMinLevelPref();

  const panel = document.getElementById('modLogPanel');
  const list = document.getElementById('modLogList');
  const toggleBtn = document.getElementById('modLogToggle');
  const closeBtn = document.getElementById('modLogClose');
  const clearBtn = document.getElementById('modLogClear');
  const copyAllBtn = document.getElementById('modLogCopyAll');
  const minLevelSelect = document.getElementById('modLogMinLevel');

  if (minLevelSelect) {
    minLevelSelect.value = minLevelFilter;
    minLevelSelect.addEventListener('change', () => {
      const v = minLevelSelect.value;
      if (v === 'info' || v === 'error' || v === 'debug') {
        minLevelFilter = v;
        saveMinLevelPref();
        renderList();
      }
    });
  }

  list?.addEventListener(
    'scroll',
    () => {
      syncTailIntentFromScroll(list);
    },
    { passive: true },
  );

  function openPanel() {
    userFollowingTail = true;
    panel?.classList.add('open');
    panel?.setAttribute('aria-hidden', 'false');
    if (toggleBtn) toggleBtn.textContent = 'Hide log';
    renderList();
    scrollListToBottom();
  }

  function closePanel() {
    panel?.classList.remove('open');
    panel?.setAttribute('aria-hidden', 'true');
    if (toggleBtn) toggleBtn.textContent = 'Logs';
  }

  toggleBtn?.addEventListener('click', () => {
    if (panel?.classList.contains('open')) {
      closePanel();
    } else {
      openPanel();
    }
  });

  closeBtn?.addEventListener('click', () => closePanel());

  clearBtn?.addEventListener('click', () => {
    entries = [];
    userFollowingTail = true;
    persist();
    renderList();
  });

  const COPY_ALL_LABEL = 'Copy all';

  copyAllBtn?.addEventListener('click', async () => {
    const text = formatAllLogs();
    if (!text) {
      copyAllBtn.textContent = 'Nothing to copy';
      setTimeout(() => {
        copyAllBtn.textContent = COPY_ALL_LABEL;
      }, 1200);
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      copyAllBtn.textContent = 'Copied';
      setTimeout(() => {
        copyAllBtn.textContent = COPY_ALL_LABEL;
      }, 1600);
    } catch (err) {
      copyAllBtn.textContent = 'Failed';
      setTimeout(() => {
        copyAllBtn.textContent = COPY_ALL_LABEL;
      }, 1600);
    }
  });

  renderList();
}
