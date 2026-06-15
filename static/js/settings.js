import * as api from './api.js';

// --- Settings / Shortcut token ---

let shortcutToken = null;
let tokenRevealed = false;

function renderToken() {
  const el = document.getElementById('settings-token');
  if (!shortcutToken) { el.textContent = '…'; return; }
  el.textContent = tokenRevealed
    ? shortcutToken
    : shortcutToken.slice(0, 6) + '•'.repeat(18) + shortcutToken.slice(-4);
}

async function loadShortcutToken() {
  document.getElementById('settings-endpoint').textContent = location.origin + '/api/shortcut';
  try {
    const data = await api.getToken();
    shortcutToken = data.token;
    renderToken();
  } catch (e) {
    console.error('Failed to load token:', e);
  }
}

export function toggleSettingsPanel() {
  const panel = document.getElementById('settings-panel');
  const isHidden = panel.classList.toggle('hidden');
  if (!isHidden) loadShortcutToken();
}

export function toggleTokenReveal() {
  tokenRevealed = !tokenRevealed;
  renderToken();
}

export function copyToken() {
  if (!shortcutToken) return;
  navigator.clipboard.writeText(shortcutToken).then(() => {
    const btn = document.getElementById('token-copy-btn');
    btn.classList.add('text-[var(--text-accent)]');
    setTimeout(() => btn.classList.remove('text-[var(--text-accent)]'), 1200);
  });
}

export async function regenerateToken() {
  if (!confirm('Regenerate token? The shortcut already installed on your phone will stop working until you re-add it.')) return;
  try {
    const data = await api.regenerateToken();
    shortcutToken = data.token;
    tokenRevealed = true;
    renderToken();
  } catch (e) {
    console.error('Regenerate failed:', e);
  }
}
