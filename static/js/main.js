import * as player from './player.js';
import * as library from './library.js';
import * as playlists from './playlists.js';
import * as settings from './settings.js';
import * as home from './home.js';
import { initRouter, navigate } from './router.js';

// Inline onclick=/oninput= handlers in index.html call globals, so expose them:
Object.assign(window, player, library, playlists, settings, home);
window.navigate = navigate;
// Both library and home export render(); the only inline caller of render() is the
// library search box, so window.render must be the library's (Home renders via the
// router calling home.render() directly).
window.render = library.render;

document.addEventListener('visibilitychange', () => { if (document.hidden) player.saveProgress(); });
window.addEventListener('beforeunload', player.saveProgress);

library.loadVoices();

// Load items once up front (Home + Library share the array), then route.
library.loadItems().then(() => {
  if (library.hasProcessing()) library.pollUpdates();
  initRouter((name, route) => {
    if (name === 'home') home.render();
    else if (name === 'feeds') playlists.loadPlaylists();
    else if (name === 'library') library.render();
    else if (name === 'settings') settings.loadShortcutToken();
    else if (name === 'feed') playlists.renderFeedDetail(route.split('/')[1]);
  });
});

document.getElementById('speed-btn').textContent = (player.getStoredSpeed() === 1) ? '1x' : player.getStoredSpeed() + 'x';
