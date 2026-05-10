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

const LS_SORT = 'viewer.sort';
const LS_FILTER = 'viewer.filter';
const SORT_VALUES = new Set(['name', 'tick', 'household', 'age', 'kind']);
const FILTER_VALUES = new Set(['all', 'npc', 'player']);

function loadPref(key, allowed, fallback) {
  try {
    const v = localStorage.getItem(key);
    if (v && allowed.has(v)) return v;
  } catch (e) {
    /* ignore */
  }
  return fallback;
}

let sortMode = loadPref(LS_SORT, SORT_VALUES, 'name');
let filterMode = loadPref(LS_FILTER, FILTER_VALUES, 'all');

function stableSimId(sim) {
  if (!sim) return '';
  return String(sim.sim_id_str != null ? sim.sim_id_str : sim.sim_id);
}

function cap(s) {
  if (!s) return '';
  return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
}

function simDisplayName(sim) {
  if (!sim) return '';
  return [sim.first_name, sim.last_name].filter(Boolean).join(' ') || '(unknown)';
}

function buildTickOrder(sims) {
  const m = new Map();
  if (!Array.isArray(sims)) return m;
  for (let i = 0; i < sims.length; i++) {
    const id = stableSimId(sims[i]);
    if (id && !m.has(id)) m.set(id, i);
  }
  return m;
}

function cmpHousehold(ha, hb) {
  if (ha == null && hb == null) return 0;
  if (ha == null) return 1;
  if (hb == null) return -1;
  const na = Number(ha);
  const nb = Number(hb);
  if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb;
  return String(ha).localeCompare(String(hb), undefined, { numeric: true });
}

function sortCompareSims(aSim, bSim, mode, tickOrder) {
  const ida = stableSimId(aSim);
  const idb = stableSimId(bSim);
  const tieIds = ida.localeCompare(idb, undefined, { numeric: true });
  const byName = () =>
    simDisplayName(aSim).localeCompare(simDisplayName(bSim), undefined, { sensitivity: 'base' }) ||
    tieIds;

  switch (mode) {
    case 'tick': {
      const ia = ida ? tickOrder.get(ida) ?? 1e9 : 1e9;
      const ib = idb ? tickOrder.get(idb) ?? 1e9 : 1e9;
      if (ia !== ib) return ia - ib;
      return tieIds;
    }
    case 'household': {
      const h = cmpHousehold(aSim?.household_id, bSim?.household_id);
      if (h !== 0) return h;
      return byName();
    }
    case 'age': {
      const ac = (aSim?.age ?? '').toString();
      const bc = (bSim?.age ?? '').toString();
      const c = ac.localeCompare(bc, undefined, { sensitivity: 'base' });
      if (c !== 0) return c;
      return byName();
    }
    case 'kind': {
      const na = aSim?.is_npc ? 1 : 0;
      const nb = bSim?.is_npc ? 1 : 0;
      if (na !== nb) return na - nb;
      return byName();
    }
    default:
      return byName();
  }
}

function sortCompareCards(cardA, cardB, mode, tickOrder) {
  const sa = cardA._viewerLastSim;
  const sb = cardB._viewerLastSim;
  if (!sa && !sb) {
    return String(cardA.dataset.simId || '').localeCompare(
      String(cardB.dataset.simId || ''),
      undefined,
      {
        numeric: true,
      }
    );
  }
  if (!sa) return 1;
  if (!sb) return -1;
  return sortCompareSims(sa, sb, mode, tickOrder);
}

function filterPasses(card, mode) {
  if (mode === 'all') return true;
  const sim = card._viewerLastSim;
  if (!sim) return false;
  if (mode === 'npc') return !!sim.is_npc;
  if (mode === 'player') return !sim.is_npc;
  return true;
}

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

function buildInteractionsSection(sim) {
  const wrap = document.createElement('div');
  const run = Array.isArray(sim.interactions_running) ? sim.interactions_running : [];
  const q = Array.isArray(sim.interactions_queue) ? sim.interactions_queue : [];

  if (!run.length && !q.length) {
    const empty = document.createElement('div');
    empty.className = 'interaction-section';
    empty.innerHTML =
      '<h4>Interactions</h4><div class="detail detail--spaced">Idle — nothing running or queued</div>';
    wrap.appendChild(empty);
    return wrap;
  }

  function pill(row) {
    const el = document.createElement('span');
    el.className = 'int-pill u-ellipsis u-font-mono';
    el.textContent = row.class_name || '(unknown)';
    el.title =
      (row.class_name || '') + ' · id ' + (row.interaction_id_str || row.interaction_id || '');
    if (row.interaction_id_str) el.dataset.interactionId = String(row.interaction_id_str);
    return el;
  }

  if (run.length) {
    const sec = document.createElement('div');
    sec.className = 'interaction-section';
    const h = document.createElement('h4');
    h.textContent = 'Running (SI state)';
    sec.appendChild(h);
    const list = document.createElement('div');
    list.className = 'interaction-list';
    for (const row of run) {
      const line = document.createElement('div');
      line.className = 'interaction-row';
      line.appendChild(pill(row));
      list.appendChild(line);
    }
    sec.appendChild(list);
    wrap.appendChild(sec);
  }

  if (q.length) {
    const sec = document.createElement('div');
    sec.className = 'interaction-section';
    const h = document.createElement('h4');
    h.textContent = 'Queue';
    sec.appendChild(h);
    const list = document.createElement('div');
    list.className = 'interaction-list';
    for (const row of q) {
      const line = document.createElement('div');
      line.className = 'interaction-row';
      if (row.is_queue_head) {
        const head = document.createElement('span');
        head.className = 'int-head';
        head.textContent = 'Head';
        line.appendChild(head);
      }
      line.appendChild(pill(row));
      list.appendChild(line);
    }
    sec.appendChild(list);
    wrap.appendChild(sec);
  }

  return wrap;
}

function buildDetailGrid(sim) {
  const fields = [
    ['ID', sim.sim_id],
    ['Age', cap(sim.age)],
    ['Gender', cap(sim.gender)],
    ['Household', sim.household_id ?? '—'],
    ['Zone', sim.zone_id ?? '—'],
  ];
  const grid = document.createElement('div');
  grid.className = 'detail-grid';
  for (const [k, v] of fields) {
    const dk = document.createElement('span');
    dk.className = 'dk';
    dk.textContent = k;
    const dv = document.createElement('span');
    dv.className = 'dv';
    dv.textContent = v ?? '—';
    grid.append(dk, dv);
  }
  return grid;
}

function buildActions(sim) {
  const wrap = document.createElement('div');
  wrap.className = 'actions';

  const goHome = document.createElement('button');
  goHome.className = 'action-btn';
  goHome.textContent = 'Go Home';
  goHome.addEventListener('click', (e) => {
    e.stopPropagation();
    sendCommand(sim.sim_id_str || String(sim.sim_id), 'go_home');
  });
  wrap.appendChild(goHome);

  return wrap;
}

function fillInfoFromSim(infoEl, sim, extraTagLabel) {
  const nameEl = infoEl.querySelector('.name');
  const full = simDisplayName(sim);
  nameEl.textContent = full;
  nameEl.title = full;

  const tags = infoEl.querySelector('.tags');
  tags.replaceChildren();

  if (extraTagLabel) {
    const left = document.createElement('span');
    left.className = 'tag';
    left.style.color = 'var(--warn)';
    left.style.borderColor = 'var(--warn)';
    left.style.background = '#2a220a';
    left.textContent = extraTagLabel;
    tags.appendChild(left);
  }

  const npcTag = document.createElement('span');
  npcTag.className = 'tag ' + (sim.is_npc ? 'npc' : 'player');
  npcTag.textContent = sim.is_npc ? 'NPC' : 'Player';
  tags.appendChild(npcTag);

  if (sim.age) {
    const ageTag = document.createElement('span');
    ageTag.className = 'tag age';
    ageTag.textContent = cap(sim.age);
    tags.appendChild(ageTag);
  }
  if (sim.gender) {
    const gTag = document.createElement('span');
    gTag.className = 'tag gender';
    gTag.textContent = cap(sim.gender);
    tags.appendChild(gTag);
  }

  let hhEl = infoEl.querySelector('.detail.hh');
  if (sim.household_id != null) {
    if (!hhEl) {
      hhEl = document.createElement('div');
      hhEl.className = 'detail hh u-ellipsis';
      infoEl.appendChild(hhEl);
    }
    hhEl.textContent = 'HH ' + sim.household_id;
  } else if (hhEl) {
    hhEl.remove();
  }
}

function updateCardLive(card, sim) {
  card._viewerLastSim = sim;
  card.dataset.present = '1';
  card.classList.remove('off-lot');
  fillInfoFromSim(card.querySelector('.info'), sim, null);
  const expandedBody = card.querySelector('.expanded-body');
  expandedBody.replaceChildren(
    buildDetailGrid(sim),
    buildInteractionsSection(sim),
    buildActions(sim)
  );
}

function updateCardOffLot(card) {
  card.dataset.present = '0';
  card.classList.add('off-lot');
  const sim = card._viewerLastSim;
  const info = card.querySelector('.info');
  if (sim) {
    fillInfoFromSim(info, sim, 'Left lot');
  } else {
    const nameEl = info.querySelector('.name');
    nameEl.textContent = '(unknown sim)';
    nameEl.title = '';
    info.querySelector('.tags').replaceChildren();
    const hhEl = info.querySelector('.detail.hh');
    if (hhEl) hhEl.remove();
  }
  const expandedBody = card.querySelector('.expanded-body');
  const banner = document.createElement('div');
  banner.className = 'off-lot-banner';
  banner.textContent = 'Not instanced on this lot';
  expandedBody.replaceChildren(banner);
  if (sim) {
    const note = document.createElement('div');
    note.className = 'detail';
    note.style.marginBottom = '0.35rem';
    note.textContent = 'Last snapshot (stale):';
    expandedBody.append(note, buildDetailGrid(sim), buildInteractionsSection(sim));
  }
}

function createCard(sim) {
  const id = stableSimId(sim);
  const card = document.createElement('div');
  card.className = 'sim-card';
  card.dataset.simId = id;

  const info = document.createElement('div');
  info.className = 'info';
  const name = document.createElement('div');
  name.className = 'name u-ellipsis';
  const tags = document.createElement('div');
  tags.className = 'tags';
  info.append(name, tags);

  const expandedBody = document.createElement('div');
  expandedBody.className = 'expanded-body';
  card.append(info, expandedBody);

  card.addEventListener('click', (e) => {
    if (e.target.closest('button')) return;
    card.classList.toggle('expanded');
    reorderSimGrid(lastGridSims);
  });

  updateCardLive(card, sim);
  return card;
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

function renderSims(sims) {
  if (!Array.isArray(sims)) sims = [];
  lastGridSims = sims;
  const present = new Set();

  for (const sim of sims) {
    const id = stableSimId(sim);
    if (!id) continue;
    present.add(id);
    let card = cardBySimId.get(id);
    if (!card) {
      card = createCard(sim);
      cardBySimId.set(id, card);
    } else {
      updateCardLive(card, sim);
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
initViewerControls();
connect();
