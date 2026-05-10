export function stableSimId(sim) {
  if (!sim) return '';
  return String(sim.sim_id_str != null ? sim.sim_id_str : sim.sim_id);
}

export function cap(s) {
  if (!s) return '';
  return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
}

export function simDisplayName(sim) {
  if (!sim) return '';
  return [sim.first_name, sim.last_name].filter(Boolean).join(' ') || '(unknown)';
}

export function buildTickOrder(sims) {
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

export function sortCompareSims(aSim, bSim, mode, tickOrder) {
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

export function sortCompareCards(cardA, cardB, mode, tickOrder) {
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

export function filterPasses(card, mode) {
  if (mode === 'all') return true;
  const sim = card._viewerLastSim;
  if (!sim) return false;
  if (mode === 'npc') return !!sim.is_npc;
  if (mode === 'player') return !sim.is_npc;
  return true;
}
