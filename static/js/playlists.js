import * as api from './api.js';
import { escapeHtml } from './library.js';

// --- Playlists ---

let playlists = [];
let viewingPlaylistId = null;

export async function loadPlaylists() {
  try {
    playlists = await api.getPlaylists();
  } catch (e) {
    console.error('Failed to load playlists:', e);
    return;
  }
  renderPlaylists();
}

function renderPlaylists() {
  const view = document.getElementById('playlists-view');
  const feedBase = location.origin;

  let html = `
                <div class="mb-4 p-3 bg-[var(--bg-input)] rounded-lg">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-sm font-medium">All Items Feed</p>
                            <p class="text-xs text-[var(--text-muted)] mt-0.5 truncate">${feedBase}/feed</p>
                        </div>
                        <div class="flex gap-2">
                            <button onclick="copyFeedUrl('${feedBase}/feed')" class="text-xs bg-[var(--bg-button)] hover:bg-[var(--bg-button-hover)] px-3 py-1.5 rounded transition">Copy URL</button>
                            <a href="/feed/opml" download="narratetts.opml" class="text-xs bg-[var(--bg-button)] hover:bg-[var(--bg-button-hover)] px-3 py-1.5 rounded transition inline-block">Export OPML</a>
                        </div>
                    </div>
                </div>
                <div class="mb-4 flex gap-2">
                    <input id="new-playlist-name" type="text" placeholder="New playlist name..." class="flex-1 bg-[var(--bg-input)] border border-[var(--border-input)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[var(--border-focus)]" onkeydown="if(event.key==='Enter')createPlaylist()">
                    <button onclick="createPlaylist()" class="btn-accent px-4 py-2 rounded-lg text-sm transition">Create</button>
                </div>`;

  if (playlists.length === 0) {
    html += `<p class="text-[var(--text-muted)] text-sm text-center mt-8">No playlists yet</p>`;
  } else {
    html += playlists.map(p => `
                    <div class="item-card flex items-center justify-between py-3 border-b border-[var(--border-subtle)]">
                        <div class="flex-1 min-w-0 cursor-pointer" onclick="viewPlaylist(${p.id})">
                            <p class="text-sm font-medium truncate">${escapeHtml(p.name)}</p>
                            <p class="text-xs text-[var(--text-muted)] mt-0.5">${p.item_count} item${p.item_count !== 1 ? 's' : ''}</p>
                        </div>
                        <div class="flex items-center gap-2 flex-shrink-0">
                            <button onclick="copyFeedUrl('${feedBase}/feed/playlist/${p.id}')" class="text-xs bg-[var(--bg-button)] hover:bg-[var(--bg-button-hover)] px-2.5 py-1.5 rounded transition" title="Copy feed URL">Feed URL</button>
                            <button onclick="confirmDeletePlaylist(${p.id})" class="text-[var(--text-faint)] hover:text-red-400 transition" title="Delete">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                            </button>
                        </div>
                    </div>`).join('');
  }

  view.innerHTML = html;
}

export async function createPlaylist() {
  const input = document.getElementById('new-playlist-name');
  const name = input.value.trim();
  if (!name) return;
  try {
    await api.createPlaylist(name);
    input.value = '';
    loadPlaylists();
  } catch (e) {
    console.error('Create playlist failed:', e);
  }
}

export async function confirmDeletePlaylist(id) {
  if (!confirm('Delete this playlist?')) return;
  try {
    await api.deletePlaylist(id);
    loadPlaylists();
  } catch (e) {
    console.error('Delete playlist failed:', e);
  }
}

export async function viewPlaylist(id) {
  viewingPlaylistId = id;
  const playlist = playlists.find(p => p.id === id);
  try {
    const playlistItems = await api.getPlaylistItems(id);
    renderPlaylistDetail(playlist, playlistItems);
  } catch (e) {
    console.error('Failed to load playlist items:', e);
  }
}

function renderPlaylistDetail(playlist, playlistItems) {
  const view = document.getElementById('playlists-view');
  const feedBase = location.origin;
  let html = `
                <div class="mb-4">
                    <button onclick="loadPlaylists()" class="text-sm text-[var(--text-muted)] hover:text-[var(--text-accent)] transition">&larr; All Playlists</button>
                </div>
                <div class="mb-4 p-3 bg-[var(--bg-input)] rounded-lg">
                    <p class="text-sm font-medium">${escapeHtml(playlist.name)}</p>
                    <div class="flex items-center justify-between mt-1">
                        <p class="text-xs text-[var(--text-muted)] truncate">${feedBase}/feed/playlist/${playlist.id}</p>
                        <button onclick="copyFeedUrl('${feedBase}/feed/playlist/${playlist.id}')" class="text-xs bg-[var(--bg-button)] hover:bg-[var(--bg-button-hover)] px-3 py-1.5 rounded transition ml-2">Copy URL</button>
                    </div>
                </div>`;

  if (playlistItems.length === 0) {
    html += `<p class="text-[var(--text-muted)] text-sm text-center mt-8">No items in this playlist. Add items from the Library tab.</p>`;
  } else {
    html += playlistItems.map(item => {
      const date = new Date(item.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      return `
                    <div class="item-card flex items-center justify-between py-3 border-b border-[var(--border-subtle)]">
                        <div class="flex-1 min-w-0">
                            <p class="text-sm font-medium truncate">${escapeHtml(item.title)}</p>
                            <span class="text-xs text-[var(--text-muted)]">${date}</span>
                        </div>
                        <button onclick="removeFromPlaylist(${playlist.id}, ${item.id})" class="text-[var(--text-faint)] hover:text-red-400 transition flex-shrink-0 ml-2" title="Remove from playlist">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" d="M6 18L18 6M6 6l12 12"/></svg>
                        </button>
                    </div>`;
    }).join('');
  }

  view.innerHTML = html;
}

export async function removeFromPlaylist(playlistId, itemId) {
  try {
    await api.removeItemFromPlaylist(playlistId, itemId);
    viewPlaylist(playlistId);
  } catch (e) {
    console.error('Remove from playlist failed:', e);
  }
}

export function copyFeedUrl(url) {
  navigator.clipboard.writeText(url).then(() => {
    // Brief visual feedback
    const btn = event.target;
    const orig = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(() => { btn.textContent = orig; }, 1500);
  });
}
