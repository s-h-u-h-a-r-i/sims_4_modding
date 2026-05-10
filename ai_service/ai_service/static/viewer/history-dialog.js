/**
 * Single <dialog> lazily created and reused across all sims.
 */

const STATUS_LABEL = {
  success: 'Success',
  failure: 'Failure',
  dispatched: 'Sent',
  pending: 'Pending',
};

function statusPill(status) {
  const el = document.createElement('span');
  el.className = 'tag history-status history-status--' + status;
  el.textContent = STATUS_LABEL[status] ?? status;
  return el;
}

function getOrCreateDialog() {
  let dlg = document.getElementById('history-dialog');
  if (dlg) return dlg;

  dlg = document.createElement('dialog');
  dlg.id = 'history-dialog';
  dlg.innerHTML = `
    <div class="history-dlg-header">
      <span class="history-dlg-title" id="history-dlg-title">Decision History</span>
      <button type="button" class="history-close-btn" aria-label="Close">&times;</button>
    </div>
    <div class="history-dlg-body" id="history-dlg-body"></div>
  `;

  dlg.querySelector('.history-close-btn').addEventListener('click', () => dlg.close());

  dlg.addEventListener('click', (e) => {
    const rect = dlg.getBoundingClientRect();
    const outside =
      e.clientX < rect.left ||
      e.clientX > rect.right ||
      e.clientY < rect.top ||
      e.clientY > rect.bottom;
    if (outside) dlg.close();
  });

  document.body.appendChild(dlg);
  return dlg;
}

function fmtTime(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return iso;
  }
}

/**
 * @param {string} simName
 * @param {Array<object>} entries  DecisionRecord dicts from the snapshot
 */
export function openHistoryDialog(simName, entries) {
  const dlg = getOrCreateDialog();
  const title = dlg.querySelector('#history-dlg-title');
  const body = dlg.querySelector('#history-dlg-body');

  title.textContent = simName + ' — Decision History';
  body.replaceChildren();

  if (!entries || entries.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'history-empty';
    empty.textContent = 'No decisions recorded yet.';
    body.appendChild(empty);
  } else {
    for (const entry of [...entries].reverse()) {
      const row = document.createElement('div');
      row.className = 'history-row';

      const left = document.createElement('div');
      left.className = 'history-row-left';

      const action = document.createElement('span');
      action.className = 'history-action u-font-mono';
      action.textContent = entry.action ?? '—';
      left.appendChild(action);

      if (entry.reason) {
        const reason = document.createElement('span');
        reason.className = 'history-reason';
        reason.textContent = entry.reason;
        left.appendChild(reason);
      }

      const right = document.createElement('div');
      right.className = 'history-row-right';
      right.appendChild(statusPill(entry.status ?? 'pending'));

      const ts = document.createElement('span');
      ts.className = 'history-ts u-font-mono';
      ts.textContent = fmtTime(entry.dispatched_at_utc_iso ?? entry.queued_at_utc_iso);
      right.appendChild(ts);

      row.append(left, right);
      body.appendChild(row);
    }
  }

  if (!dlg.open) dlg.showModal();
}
