/** Sims 4–style toast stack (warm panel, plumbob accent). */

const TOAST_LONG = 9000;
const ANIM_MS = 320;

let stackEl = null;

function ensureStack() {
  if (stackEl && stackEl.isConnected) return stackEl;
  stackEl = document.createElement('div');
  stackEl.className = 'sims-toast-stack';
  stackEl.setAttribute('aria-live', 'polite');
  document.body.appendChild(stackEl);
  return stackEl;
}

/**
 * @param {object} opts
 * @param {'success'|'error'|'info'} [opts.variant]
 * @param {string} opts.title
 * @param {string} [opts.body]
 * @param {number} [opts.duration] ms; 0 = no auto-dismiss
 */
export function showToast({ variant = 'info', title, body = '', duration = TOAST_LONG }) {
  const stack = ensureStack();
  const el = document.createElement('div');
  el.className = `sims-toast sims-toast--${variant}`;
  el.setAttribute('role', 'status');

  const icon = document.createElement('span');
  icon.className = 'sims-toast-plumbob';
  icon.setAttribute('aria-hidden', 'true');

  const text = document.createElement('div');
  text.className = 'sims-toast-text';

  const t = document.createElement('div');
  t.className = 'sims-toast-title';
  t.textContent = title;

  text.append(t);
  if (body) {
    const b = document.createElement('div');
    b.className = 'sims-toast-body';
    b.textContent = body;
    text.append(b);
  }

  const close = document.createElement('button');
  close.type = 'button';
  close.className = 'sims-toast-close';
  close.setAttribute('aria-label', 'Dismiss');
  close.textContent = '\u00D7';

  el.append(icon, text, close);
  stack.appendChild(el);

  requestAnimationFrame(() => el.classList.add('sims-toast--visible'));

  let timeoutId = 0;
  const dismiss = () => {
    if (timeoutId) clearTimeout(timeoutId);
    el.classList.remove('sims-toast--visible');
    setTimeout(() => el.remove(), ANIM_MS);
  };

  close.addEventListener('click', dismiss);
  if (duration > 0) {
    timeoutId = setTimeout(dismiss, duration);
  }

  return dismiss;
}
