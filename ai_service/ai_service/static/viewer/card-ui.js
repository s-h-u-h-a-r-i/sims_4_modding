import { openHistoryDialog } from './history-dialog.js';
import { cap, resolveSimOnRoster, simDisplayName, stableSimId } from './sim-model.js';

/** @param {object} peer */
function initialsFromPeer(peer) {
  if (!peer) return '?';
  const fn = (peer?.first_name != null ? String(peer.first_name) : '').trim();
  const ln = (peer?.last_name != null ? String(peer.last_name) : '').trim();
  if (!fn && !ln) return '?';
  const u = fn.charAt(0).toUpperCase();
  const v = ln ? ln.charAt(0).toUpperCase() : fn.length > 1 ? fn.charAt(1).toUpperCase() : '';
  return (u + v) || '?';
}

/**
 * @param {object} sim
 * @param {object[]|undefined} allSims
 * @param {(wirePeerId: string) => void} [onActivatePeerCard] toggle that Sim's card like the header tap
 */
export function buildSocialPartnersSection(sim, allSims, onActivatePeerCard) {
  const ids = Array.isArray(sim.social_partner_sim_ids) ? sim.social_partner_sim_ids : [];
  if (!ids.length) return null;

  const sec = document.createElement('div');
  sec.className = 'interaction-section social-partners-section';
  const h = document.createElement('h4');
  h.textContent = 'Interacting with';
  sec.appendChild(h);
  const row = document.createElement('div');
  row.className = 'social-peer-row';

  /** @type {Array<{ idStr: string, peer?: object|null }>} */
  const resolved = [];
  for (const rawId of ids) {
    const idStr =
      typeof rawId === 'string'
        ? rawId.trim()
        : rawId != null
          ? String(rawId).trim()
          : '';
    if (!idStr) continue;
    resolved.push({
      idStr,
      peer: resolveSimOnRoster(idStr, allSims),
    });
  }
  if (!resolved.length) return null;

  resolved.forEach((entry, idx) => {
    if (idx > 0) {
      const sep = document.createElement('span');
      sep.className = 'social-peer-sep';
      sep.setAttribute('aria-hidden', 'true');
      sep.textContent = '\u00B7';
      row.appendChild(sep);
    }

    const { peer, idStr } = entry;
    const chip = document.createElement('div');
    chip.className =
      typeof onActivatePeerCard === 'function'
        ? 'social-peer-chip social-peer-chip--action'
        : 'social-peer-chip';
    chip.dataset.peerSimId = idStr;

    const av = document.createElement('div');
    av.className = 'social-peer-avatar';
    av.setAttribute('aria-hidden', 'true');
    av.textContent = initialsFromPeer(peer);

    const lines = document.createElement('div');
    lines.className = 'social-peer-lines';

    const nameEl = document.createElement('span');
    nameEl.className = 'social-peer-name';

    /** @type {string} */
    let displayName = '';
    if (peer) {
      displayName = simDisplayName(peer) || 'Unknown';
      nameEl.textContent = displayName;
    } else {
      nameEl.textContent = 'Unknown peer';
      nameEl.classList.add('social-peer-name--faded');
    }

    const sub = document.createElement('span');
    sub.className = 'social-peer-sub';
    if (peer?.is_npc === false) sub.textContent = 'Player household';
    else if (peer?.is_npc === true) sub.textContent = 'NPC';
    else if (!peer) sub.textContent = ''; // no id line — avoids giant numbers in UI

    lines.append(nameEl);
    if (sub.textContent) lines.append(sub);

    chip.append(av, lines);
    chip.title = peer ? `Expand ${displayName}'s card` : `Expand this sim's card`;
    if (typeof onActivatePeerCard === 'function') {
      chip.setAttribute('role', 'button');
      chip.tabIndex = 0;
      chip.setAttribute(
        'aria-label',
        peer
          ? `Expand or collapse ${displayName}'s card (same as their name bar)`
          : `Expand sim card ${idStr}`
      );
      const activate = () => onActivatePeerCard(idStr);
      chip.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        activate();
      });
      chip.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          e.stopPropagation();
          activate();
        }
      });
    }

    row.appendChild(chip);
  });

  sec.appendChild(row);
  return sec;
}

export function buildInteractionsSection(sim) {
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

export function buildDetailGrid(sim) {
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

/**
 * @param {object} sim
 * @param {(simId: string, action: string) => void} sendCommand
 * @param {Array<object>} historyEntries
 */
export function buildActions(sim, sendCommand, historyEntries) {
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

  const historyBtn = document.createElement('button');
  historyBtn.className = 'action-btn action-btn--secondary history-btn';
  const count = Array.isArray(historyEntries) ? historyEntries.length : 0;
  historyBtn.textContent = count > 0 ? `History (${count})` : 'History';
  historyBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    openHistoryDialog(simDisplayName(sim), historyEntries ?? []);
  });
  wrap.appendChild(historyBtn);

  return wrap;
}

export function fillInfoFromSim(infoEl, sim, extraTagLabel) {
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

/**
 * @param {HTMLElement} card
 * @param {object} sim
 * @param {(simId: string, action: string) => void} sendCommand
 * @param {Array<object>} historyEntries
 * @param {object[]|undefined} allSims
 * @param {(wirePeerId: string) => void} [onActivatePeerCard]
 */
export function updateCardLive(card, sim, sendCommand, historyEntries, allSims, onActivatePeerCard) {
  card._viewerLastSim = sim;
  card.dataset.present = '1';
  card.classList.remove('off-lot');
  fillInfoFromSim(card.querySelector('.info'), sim, null);
  const expandedBody = card.querySelector('.expanded-body');

  /** @type {HTMLElement[]} */
  const parts = [buildDetailGrid(sim)];
  const social = buildSocialPartnersSection(sim, allSims, onActivatePeerCard);
  if (social) parts.push(social);
  parts.push(buildInteractionsSection(sim), buildActions(sim, sendCommand, historyEntries));
  expandedBody.replaceChildren(...parts);
}

export function updateCardOffLot(card, allSims, onActivatePeerCard) {
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
    const social = buildSocialPartnersSection(sim, allSims, onActivatePeerCard);
    const parts = [note, buildDetailGrid(sim)];
    if (social) parts.push(social);
    parts.push(buildInteractionsSection(sim));
    expandedBody.append(...parts);
  }
}

/**
 * @param {object} sim
 * @param {(simId: string, action: string) => void} sendCommand
 * @param {() => void} onExpandToggle reorder grid after expanded state changes
 * @param {Array<object>} historyEntries
 * @param {object[]|undefined} allSims
 * @param {(wirePeerId: string) => void} [onActivatePeerCard]
 */
export function createCard(sim, sendCommand, onExpandToggle, historyEntries, allSims, onActivatePeerCard) {
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

  info.addEventListener('click', () => {
    card.classList.toggle('expanded');
    onExpandToggle();
  });

  updateCardLive(card, sim, sendCommand, historyEntries, allSims, onActivatePeerCard);
  return card;
}
