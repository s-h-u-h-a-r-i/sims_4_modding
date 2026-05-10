export const LS_SORT = 'viewer.sort';
export const LS_FILTER = 'viewer.filter';

export const SORT_VALUES = new Set(['name', 'tick', 'household', 'age', 'kind']);
export const FILTER_VALUES = new Set(['all', 'npc', 'player']);

export function loadPref(key, allowed, fallback) {
  try {
    const v = localStorage.getItem(key);
    if (v && allowed.has(v)) return v;
  } catch (e) {
    /* ignore */
  }
  return fallback;
}
