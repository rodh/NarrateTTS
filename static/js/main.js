import * as player from './player.js';
import * as library from './library.js';
import * as playlists from './playlists.js';
import * as settings from './settings.js';

// Inline onclick=/oninput= handlers in index.html call globals, so expose them:
Object.assign(window, player, library, playlists, settings);

// Tab switching (ported from current index.html switchTab)
let currentTab = 'library';
function switchTab(tab) {
  currentTab = tab;
  document.getElementById('library').classList.toggle('hidden', tab !== 'library');
  document.getElementById('playlists-view').classList.toggle('hidden', tab !== 'playlists');
  document.getElementById('tab-library').classList.toggle('border-[var(--text-accent)]', tab === 'library');
  document.getElementById('tab-library').classList.toggle('text-[var(--text-accent)]', tab === 'library');
  document.getElementById('tab-library').classList.toggle('border-transparent', tab !== 'library');
  document.getElementById('tab-library').classList.toggle('text-[var(--text-muted)]', tab !== 'library');
  document.getElementById('tab-playlists').classList.toggle('border-[var(--text-accent)]', tab === 'playlists');
  document.getElementById('tab-playlists').classList.toggle('text-[var(--text-accent)]', tab === 'playlists');
  document.getElementById('tab-playlists').classList.toggle('border-transparent', tab !== 'playlists');
  document.getElementById('tab-playlists').classList.toggle('text-[var(--text-muted)]', tab !== 'playlists');
  if (tab === 'playlists') playlists.loadPlaylists();
}
window.switchTab = switchTab;

document.addEventListener('visibilitychange', () => { if (document.hidden) player.saveProgress(); });
window.addEventListener('beforeunload', player.saveProgress);

// Init (ported from the bottom of current index.html)
library.loadVoices();
library.loadItems().then(() => {
  if (library.hasProcessing()) library.pollUpdates();
});
document.getElementById('speed-btn').textContent = (player.getStoredSpeed() === 1) ? '1x' : player.getStoredSpeed() + 'x';
