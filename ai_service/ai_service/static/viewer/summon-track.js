import { simDisplayName } from './sim-model.js';
import { showToast } from './toast.js';

export const SUMMON_ACTION = 'summon_sim';

const OUTCOME_WARN_MS = 45000;

/**
 * @typedef {object} SummonPending
 * @property {string} simCanon
 * @property {string|null} decisionId
 * @property {HTMLElement|null} card
 * @property {object|null} sim
 * @property {number} startedAt
 * @property {ReturnType<typeof setTimeout>|null} warnTimer
 */

/** @type {SummonPending | null} */
let summonPending = null;

function clearCardLoading() {
  const c = summonPending?.card;
  if (c) c.classList.remove('summon-loading');
}

/**
 * Drop any in-flight summon UI (e.g. bridge session rotation).
 */
export function cancelSummonTracking() {
  if (summonPending?.warnTimer) clearTimeout(summonPending.warnTimer);
  clearCardLoading();
  summonPending = null;
}

/**
 * @param {string} simCanon stableSimId / history key
 * @param {HTMLElement} card
 * @param {object} sim snapshot object for display name
 */
export function beginSummonFlow(simCanon, card, sim) {
  cancelSummonTracking();
  card.classList.add('summon-loading');
  summonPending = {
    simCanon,
    decisionId: null,
    card,
    sim,
    startedAt: Date.now(),
    warnTimer: setTimeout(() => {
      if (!summonPending) return;
      showToast({
        variant: 'info',
        title: 'Still waiting on the game',
        body:
          'Summon is queued until the next live tick from the mod. Unpause or wait for the game to send another tick.',
        duration: 10000,
      });
    }, OUTCOME_WARN_MS),
  };
}

/** @param {Array<object>|undefined} entries */
function findLatestSummonAfter(entries, startedAtMs) {
  if (!Array.isArray(entries)) return null;
  const slackMs = 600_000; // tolerate client/server clock skew; ignore stale history
  for (let i = entries.length - 1; i >= 0; i--) {
    const r = entries[i];
    if (r.action !== SUMMON_ACTION) continue;
    const q = Date.parse(r.queued_at_utc_iso);
    if (!Number.isFinite(q) || q < startedAtMs - slackMs) continue;
    return r;
  }
  return null;
}

/**
 * Call after `lastDecisionHistory` is updated (e.g. WebSocket snapshot).
 * @param {Record<string, Array<object>>} decisionHistory
 */
export function reconcileSummonFromHistory(decisionHistory) {
  if (!summonPending) return;
  const { simCanon, startedAt, sim } = summonPending;
  const rec = findLatestSummonAfter(decisionHistory[simCanon], startedAt);
  if (!rec) return;

  if (!summonPending.decisionId) {
    summonPending.decisionId = rec.id;
  }
  if (rec.id !== summonPending.decisionId) return;

  if (rec.status === 'pending' || rec.status === 'dispatched') {
    return;
  }

  const name = sim ? simDisplayName(sim) : simCanon;

  if (rec.status === 'success') {
    if (summonPending.warnTimer) clearTimeout(summonPending.warnTimer);
    showToast({
      variant: 'success',
      title: 'Summon applied',
      body: `${name} should walk in soon — Sims can take a few seconds to spawn on the lot.`,
      duration: 11000,
    });
    cancelSummonTracking();
    return;
  }

  if (rec.status === 'failure') {
    if (summonPending.warnTimer) clearTimeout(summonPending.warnTimer);
    showToast({
      variant: 'error',
      title: 'Summon failed',
      body: rec.reason && String(rec.reason).trim() ? String(rec.reason) : 'The game reported failure with no reason.',
      duration: 14000,
    });
    cancelSummonTracking();
  }
}
