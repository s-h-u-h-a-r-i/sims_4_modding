import {
  createCard,
  updateCardLive,
  updateCardOffLot,
} from './card-ui.js';
import {
  FILTER_VALUES,
  LS_FILTER,
  LS_SORT,
  loadPref,
  SORT_VALUES,
} from './prefs.js';
import {
  buildTickOrder,
  filterPasses,
  sortCompareCards,
  stableSimId,
} from './sim-model.js';

const statusEl = document.getElementById('status');
const simGrid = document.getElementById('simGrid');
const aiToggle = document.getElementById('aiToggle');
const aiLabel = document.getElementById('aiLabel');

let ws = null;
let aiEnabled = true;
/** @type {Map<string, HTMLElement>} */
const cardBySimId = new Map();

/** Snapshot `tick_request.world.sims` from last frame (expand/collapse reordering). */
let lastGridSims = [];

let sortMode = loadPref(LS_SORT, SORT_VALUES, 'name');
let filterMode = loadPref(LS_FILTER, FILTER_VALUES, 'all');

function setAiState(enabled) {
  aiEnabled = enabled;
  aiToggle.classList.toggle('on', enabled);
  aiLabel.textContent = 'AI ' + (enabled ? 'on' : 'off');
}

aiToggle.addEventListener('click', () => {
  const next = !aiEnabled;
  setAiState(next);
  wsSend({ type: 'set_ai_enabled', enabled: next });
});

function wsSend(msg) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(msg));
  }
}

function sendCommand(simId, action) {
  wsSend({ type: 'command', action, sim_id: simId });
}

/**
 * Expanded on-lot first, then other on-lot, then off-lot. Within each tier, order
 * follows `sortMode`; hidden sims (per `filterMode`) sort after visible ones.
 */
function reorderSimGrid(sims) {
  const tickOrder = buildTickOrder(sims);
  const cards = [...cardBySimId.values()];
  const tierOf = (card) => {
    if (card.dataset.present === '0') return 2;
    if (card.classList.contains('expanded')) return 0;
    return 1;
  };
  cards.sort((a, b) => {
    const pa = filterPasses(a, filterMode) ? 0 : 1;
    const pb = filterPasses(b, filterMode) ? 0 : 1;
    if (pa !== pb) return pa - pb;
    const ta = tierOf(a);
    const tb = tierOf(b);
    if (ta !== tb) return ta - tb;
    return sortCompareCards(a, b, sortMode, tickOrder);
  });
  for (const c of cards) {
    c.hidden = !filterPasses(c, filterMode);
    simGrid.appendChild(c);
  }
}

function renderSims(sims) {
  if (!Array.isArray(sims)) sims = [];
  lastGridSims = sims;
  const present = new Set();

  const onExpandToggle = () => reorderSimGrid(lastGridSims);

  for (const sim of sims) {
    const id = stableSimId(sim);
    if (!id) continue;
    present.add(id);
    let card = cardBySimId.get(id);
    if (!card) {
      card = createCard(sim, sendCommand, onExpandToggle);
      cardBySimId.set(id, card);
    } else {
      updateCardLive(card, sim, sendCommand);
    }
    simGrid.appendChild(card);
  }

  for (const [id, card] of cardBySimId) {
    if (!present.has(id)) {
      updateCardOffLot(card);
      simGrid.appendChild(card);
    }
  }

  reorderSimGrid(sims);
}

function applySnapshot(data) {
  const sims = data?.tick_request?.world?.sims ?? [];
  const list = Array.isArray(sims) ? sims : [];
  statusEl.className = '';
  setAiState(data.ai_enabled ?? true);
  renderSims(list);

  let notHere = 0;
  for (const card of cardBySimId.values()) {
    if (card.dataset.present === '0') notHere++;
  }
  const onLot = list.length;
  const seq = 'Seq ' + (data.seq ?? '—');
  if (onLot && notHere) {
    statusEl.textContent = seq + ' · ' + onLot + ' on lot · ' + notHere + ' not here';
  } else if (onLot) {
    statusEl.textContent = seq + ' · ' + onLot + ' sim' + (onLot !== 1 ? 's' : '') + ' on lot';
  } else if (notHere) {
    statusEl.textContent = seq + ' · no one on lot · ' + notHere + ' not here';
  } else {
    statusEl.textContent = seq + ' · no sims on lot';
  }
}

function connect() {
  const wsUrl =
    (location.protocol === 'https:' ? 'wss:' : 'ws:') +
    '//' +
    location.host +
    location.pathname.replace(/\/?$/, '') +
    '/ws';
  ws = new WebSocket(wsUrl);
  ws.onopen = () => {
    statusEl.textContent = 'Connected…';
    statusEl.className = '';
  };
  ws.onmessage = (ev) => {
    try {
      applySnapshot(JSON.parse(ev.data));
    } catch (e) {
      statusEl.textContent = String(e);
      statusEl.className = 'error';
    }
  };
  ws.onclose = () => {
    statusEl.textContent = 'Disconnected — reconnecting…';
    statusEl.className = 'error';
    setTimeout(connect, 2000);
  };
  ws.onerror = () => {
    statusEl.className = 'error';
  };
}

function initViewerControls() {
  const sortSelect = document.getElementById('sortSelect');
  const filterSelect = document.getElementById('filterSelect');
  if (!sortSelect || !filterSelect) return;
  sortSelect.value = sortMode;
  filterSelect.value = filterMode;
  sortSelect.addEventListener('change', () => {
    sortMode = sortSelect.value;
    try {
      localStorage.setItem(LS_SORT, sortMode);
    } catch (e) {
      /* ignore */
    }
    reorderSimGrid(lastGridSims);
  });
  filterSelect.addEventListener('change', () => {
    filterMode = filterSelect.value;
    try {
      localStorage.setItem(LS_FILTER, filterMode);
    } catch (e) {
      /* ignore */
    }
    reorderSimGrid(lastGridSims);
  });
}

initViewerControls();
connect();
