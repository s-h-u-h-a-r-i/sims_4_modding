import { createCard, updateCardLive, updateCardOffLot } from './card-ui.js';
import {
  clearStoredModLogsForNewBridgeSession,
  initModLogPanel,
  routeViewerMessage,
} from './mod-logs.js';
import { FILTER_VALUES, loadPref, LS_FILTER, LS_SORT, SORT_VALUES } from './prefs.js';
import {
  buildTickOrder,
  filterPasses,
  resolveSimOnRoster,
  sortCompareCards,
  stableSimId,
} from './sim-model.js';

const statusEl = document.getElementById('status');
const simGrid = document.getElementById('simGrid');
const aiToggle = document.getElementById('aiToggle');
const aiLabel = document.getElementById('aiLabel');

const LS_LAST_FRAME_KEY = 'npc_ai_viewer_last_tick_frame_v1';

/** Last bridge_session_id from the server; null until first snapshot/tick_frame. */
let viewerBridgeSessionId = null;
/** From localStorage tick frame; used to detect stale grid after game restart. */
let storedFrameBridgeSessionId = null;

let ws = null;
let aiEnabled = true;
/** @type {Map<string, HTMLElement>} */
const cardBySimId = new Map();

/** Last known `world.sims` from tick_frame (expand/collapse reordering). */
let lastGridSims = [];

/**
 * decision_history from the latest snapshot: { sim_id_str: DecisionRecord[] }
 * @type {Record<string, Array<object>>}
 */
let lastDecisionHistory = {};

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

/** Same behaviour as tapping a card header: toggle expanded + reorder grid + scroll peer into view. */
function expandPeerFromSocial(peerIdWire) {
  const raw = peerIdWire == null ? '' : String(peerIdWire).trim();
  if (!raw) return;
  const peer = resolveSimOnRoster(raw, lastGridSims);
  const canon = peer ? stableSimId(peer) : raw;
  if (!canon) return;
  const card = cardBySimId.get(canon);
  if (!card || card.dataset.present !== '1') return;
  card.classList.toggle('expanded');
  card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  reorderSimGrid(lastGridSims);
}

function loadStoredFrame() {
  storedFrameBridgeSessionId = null;
  try {
    const raw = localStorage.getItem(LS_LAST_FRAME_KEY);
    if (!raw) return;
    const o = JSON.parse(raw);
    const sid = o?.tick?.bridge_session_id;
    if (!sid) {
      try {
        localStorage.removeItem(LS_LAST_FRAME_KEY);
      } catch (e2) {
        /* ignore */
      }
      return;
    }
    storedFrameBridgeSessionId = String(sid);
    if (o?.world?.sims && Array.isArray(o.world.sims)) {
      lastGridSims = o.world.sims;
    }
  } catch (e) {
    /* ignore */
  }
}

function clearStaleBridgeSessionUi() {
  lastGridSims = [];
  lastDecisionHistory = {};
  try {
    localStorage.removeItem(LS_LAST_FRAME_KEY);
  } catch (e) {
    /* ignore */
  }
  for (const card of cardBySimId.values()) {
    card.remove();
  }
  cardBySimId.clear();
  clearStoredModLogsForNewBridgeSession();
  storedFrameBridgeSessionId = viewerBridgeSessionId;
}

/** Returns true when the UI was cleared here (caller may defer status text updates). */
function noteServerBridgeSession(serverSidRaw) {
  const serverSid = serverSidRaw == null ? '' : String(serverSidRaw).trim();
  if (!serverSid) {
    return false;
  }

  const rotating =
    viewerBridgeSessionId !== null && viewerBridgeSessionId !== serverSid;
  const lsStaleWhenHandshake =
    viewerBridgeSessionId === null &&
    storedFrameBridgeSessionId !== null &&
    storedFrameBridgeSessionId !== serverSid;

  viewerBridgeSessionId = serverSid;
  storedFrameBridgeSessionId = serverSid;

  if (rotating || lsStaleWhenHandshake) {
    clearStaleBridgeSessionUi();
    return true;
  }
  return false;
}

function applyTickFrame(data) {
  const rotated = noteServerBridgeSession(data?.tick?.bridge_session_id);

  const world = data?.world;
  if (!world || !Array.isArray(world.sims)) return;
  try {
    localStorage.setItem(LS_LAST_FRAME_KEY, JSON.stringify({ tick: data.tick, world }));
  } catch (e) {
    /* ignore */
  }
  renderSims(world.sims);
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
    const history = lastDecisionHistory[id] ?? [];
    let card = cardBySimId.get(id);
    if (!card) {
      card = createCard(sim, sendCommand, onExpandToggle, history, sims, expandPeerFromSocial);
      cardBySimId.set(id, card);
    } else {
      updateCardLive(card, sim, sendCommand, history, sims, expandPeerFromSocial);
    }
    simGrid.appendChild(card);
  }

  for (const [id, card] of cardBySimId) {
    if (!present.has(id)) {
      updateCardOffLot(card, lastGridSims, expandPeerFromSocial);
      simGrid.appendChild(card);
    }
  }

  reorderSimGrid(sims);
}

function applySnapshot(data) {
  const rotated = noteServerBridgeSession(data.bridge_session_id);

  lastDecisionHistory =
    data.decision_history && typeof data.decision_history === 'object' ? data.decision_history : {};
  statusEl.className = '';
  setAiState(data.ai_enabled ?? true);
  renderSims(lastGridSims);

  let notHere = 0;
  for (const card of cardBySimId.values()) {
    if (card.dataset.present === '0') notHere++;
  }
  const list = Array.isArray(lastGridSims) ? lastGridSims : [];
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
  if (rotated && onLot === 0 && !notHere) {
    statusEl.textContent = seq + ' · new bridge session · waiting for sims…';
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
      const data = JSON.parse(ev.data);
      if (data && data.type === 'tick_frame') {
        applyTickFrame(data);
        return;
      }
      if (routeViewerMessage(data)) return;
      if (data && data.type === 'snapshot') {
        applySnapshot(data);
      }
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
initModLogPanel();
loadStoredFrame();
renderSims(lastGridSims);
connect();
