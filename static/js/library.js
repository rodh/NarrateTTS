import * as api from './api.js';
import { playItem, getCurrentItemId, isAudioPlaying, resetProgress, setItems, stopForDeletedItem } from './player.js';

// --- Shared state ---
let items = [];
let playlistMap = {};

// Share the items array reference with the player module.
setItems(items);

export function getItems() {
  return items;
}

export function hasProcessing() {
  return Array.isArray(items) && items.some(i => i.status === 'processing' || i.status === 'queued');
}

// --- Rendering ---

export async function loadItems() {
  try {
    const [itemsRes, mapRes] = await Promise.all([
      api.getItems(100),
      api.getPlaylistMap(),
    ]);
    // Mutate in place so the shared reference (player.setItems) stays valid.
    items.length = 0;
    if (Array.isArray(itemsRes)) items.push(...itemsRes);
    playlistMap = mapRes;
  } catch (e) {
    console.error('Failed to load items:', e);
    return;
  }
  render();
}

export function render() {
  const query = document.getElementById('search').value.toLowerCase();
  const filtered = items.filter(item =>
    item.title.toLowerCase().includes(query) ||
    (item.source_url && item.source_url.toLowerCase().includes(query))
  );

  const currentItemId = getCurrentItemId();
  const library = document.getElementById('library');
  if (filtered.length === 0) {
    library.innerHTML = `
                    <div class="flex flex-col items-center justify-center h-64 text-[var(--text-muted)]">
                        <p class="text-lg mb-1">Nothing here yet</p>
                        <p class="text-sm">Tap + to add a URL or paste text</p>
                    </div>`;
    return;
  }

  library.innerHTML = filtered.map(item => {
    const date = new Date(item.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    const pct = (item.duration_seconds > 0) ? ((item.play_position || 0) / item.duration_seconds) : 0;
    const isFinished = pct >= 0.8 || !!item.consumed_at;
    const isPlaying = currentItemId === item.id && isAudioPlaying();

    let sourceHtml = '';
    if (item.source_url) {
      try {
        const hostname = new URL(item.source_url).hostname.replace('www.', '');
        sourceHtml = `<a href="${escapeHtml(item.source_url)}" target="_blank" class="text-xs text-[var(--text-muted)] hover:text-[var(--text-secondary)] truncate max-w-[200px]" onclick="event.stopPropagation()" title="${escapeHtml(item.source_url)}">${hostname}</a>`;
      } catch(e) {
        sourceHtml = `<span class="text-xs text-[var(--text-muted)]">Link</span>`;
      }
    } else {
      sourceHtml = `<span class="text-xs text-[var(--text-muted)]">Text</span>`;
    }

    // Icon for right side
    let iconHtml = '';
    if (item.status === 'completed' && item.audio_path) {
      if (isPlaying) {
        iconHtml = `<span class="text-[var(--text-faint)]"><svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg></span>`;
      } else {
        const playColor = isFinished ? 'text-[var(--text-faint)]' : 'text-[var(--text-secondary)]';
        iconHtml = `<span class="${playColor}"><svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><polygon points="5,3 19,12 5,21"/></svg></span>`;
      }
    } else if (item.status === 'processing') {
      iconHtml = `<span class="text-blue-400 text-sm animate-pulse">Converting...</span>`;
    } else if (item.status === 'error') {
      iconHtml = `<span class="text-red-400 text-xs truncate max-w-[200px]" title="${escapeHtml(item.error || '')}">${escapeHtml(item.error || 'Error')}</span>`;
    }

    // Progress indicator (left side)
    let progressCircle = '';
    if (item.status === 'completed') {
      if (isFinished) {
        // Finished: dim gray filled dot
        progressCircle = `<svg class="w-3 h-3 flex-shrink-0 mt-[3px]" viewBox="0 0 16 16"><circle cx="8" cy="8" r="5" style="fill: var(--text-faint)"/></svg>`;
      } else if (pct > 0) {
        // In progress: gray ring with blue arc
        const circumference = 2 * Math.PI * 6;
        const offset = circumference * (1 - Math.min(pct / 0.8, 1));
        progressCircle = `<svg class="w-3 h-3 flex-shrink-0 mt-[3px]" viewBox="0 0 16 16">` +
          `<circle cx="8" cy="8" r="6" fill="none" stroke-width="2.5" style="stroke: var(--border-input)"/>` +
          `<circle cx="8" cy="8" r="6" fill="none" stroke="#3b82f6" stroke-width="2.5" stroke-dasharray="${circumference}" stroke-dashoffset="${offset}" transform="rotate(-90 8 8)" stroke-linecap="round"/>` +
          `</svg>`;
      } else {
        // New/unlistened: bright blue dot
        progressCircle = `<svg class="w-3 h-3 flex-shrink-0 mt-[3px]" viewBox="0 0 16 16"><circle cx="8" cy="8" r="5" fill="#3b82f6"/></svg>`;
      }
    } else if (item.status === 'processing') {
      // Converting: pulsing blue dot
      progressCircle = `<svg class="w-3 h-3 flex-shrink-0 mt-[3px] animate-pulse" viewBox="0 0 16 16"><circle cx="8" cy="8" r="5" fill="#3b82f6"/></svg>`;
    } else if (item.status === 'error') {
      // Error: red dot
      progressCircle = `<svg class="w-3 h-3 flex-shrink-0 mt-[3px]" viewBox="0 0 16 16"><circle cx="8" cy="8" r="5" fill="#ef4444"/></svg>`;
    } else {
      // Queued: invisible spacer for alignment
      progressCircle = `<svg class="w-3 h-3 flex-shrink-0 mt-[3px]" viewBox="0 0 16 16"></svg>`;
    }

    // Row click action
    const audioFile = item.audio_path ? item.audio_path.split('/').pop() : '';
    const rowClick = (item.status === 'completed' && item.audio_path)
      ? `onclick="playItem(${item.id}, '${audioFile}')"`
      : '';

    const itemPlaylists = playlistMap[item.id] || [];
    const tagsHtml = itemPlaylists.map(p =>
      `<span class="inline-block text-[11px] leading-tight px-1.5 py-0.5 rounded bg-[var(--bg-button)] text-[var(--text-muted)]">${escapeHtml(p.name)}</span>`
    ).join('');

    return `
                    <div class="item-card flex items-start py-3 border-b border-[var(--border-subtle)] cursor-pointer gap-2" ${rowClick}>
                        ${progressCircle}
                        <div class="flex items-center gap-3 sm:gap-4 flex-1 min-w-0">
                            <div class="flex-1 min-w-0">
                                <p class="text-sm font-medium truncate">${escapeHtml(item.title)}</p>
                                <div class="flex items-center gap-2 mt-0.5">
                                    ${sourceHtml}
                                    <span class="text-xs text-[var(--text-faint)]">&middot;</span>
                                    <span class="text-xs text-[var(--text-muted)]">${date}</span>
                                    <span class="text-xs text-[var(--text-faint)]">&middot;</span>
                                    <span class="text-xs text-[var(--text-muted)]">${item.word_count || 0} words</span>
                                </div>
                                ${tagsHtml ? `<div class="flex flex-wrap gap-1 mt-1">${tagsHtml}</div>` : ''}
                            </div>
                            <div class="flex items-center gap-2 sm:gap-3 flex-shrink-0">
                                ${iconHtml}
                                ${item.status === 'completed' ? `<button onclick="showPlaylistPicker(${item.id}, event)" class="text-[var(--text-faint)] hover:text-[var(--text-secondary)] transition" title="Add to playlist">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                                </button>` : ''}
                                ${item.status === 'error' ? `<button onclick="event.stopPropagation(); retryItem(${item.id})" class="text-[var(--text-faint)] hover:text-[var(--text-accent)] transition" title="Retry">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h5M20 20v-5h-5"/><path stroke-linecap="round" stroke-linejoin="round" d="M20.49 9A9 9 0 105.64 5.64L4 4m16 16l-1.64-1.64A9 9 0 0020.49 9"/></svg>
                                </button>` : ''}
                                ${(item.play_position || 0) > 0 ? `<button onclick="event.stopPropagation(); resetProgress(${item.id})" class="text-[var(--text-faint)] hover:text-[var(--text-secondary)] transition" title="Reset progress">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h5M20 20v-5h-5"/><path stroke-linecap="round" stroke-linejoin="round" d="M20.49 9A9 9 0 105.64 5.64L4 4m16 16l-1.64-1.64A9 9 0 0020.49 9"/></svg>
                                </button>` : ''}
                                <button onclick="event.stopPropagation(); deleteItem(${item.id})" class="text-[var(--text-faint)] hover:text-red-400 transition" title="Delete">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                                </button>
                            </div>
                        </div>
                    </div>`;
  }).join('');
}

export function renderPreservingScroll() {
  const library = document.getElementById('library');
  const scrollTop = library.scrollTop;
  render();
  library.scrollTop = scrollTop;
}

// --- Add Panel ---

export function toggleAddPanel() {
  const panel = document.getElementById('add-panel');
  const isHidden = panel.classList.toggle('hidden');
  if (!isHidden) {
    document.getElementById('url-input').focus();
  }
}

// --- Conversion ---

export async function convert() {
  const input = document.getElementById('url-input');
  const value = input.value.trim();
  if (!value) return;

  const btn = document.getElementById('convert-btn');
  btn.disabled = true;
  btn.textContent = 'Converting...';

  const voice = document.getElementById('voice-select').value;
  const isUrl = /^https?:\/\//i.test(value);
  const body = isUrl ? { url: value, voice } : { text: value, voice };

  try {
    await api.postConvert(body);
    input.value = '';
    input.rows = 1;
    input.style.height = '';
    document.getElementById('add-panel').classList.add('hidden');
    pollUpdates();
  } catch (e) {
    alert('Conversion failed: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Convert';
  }
}

// --- Item actions ---

export async function retryItem(id) {
  try {
    await api.retryItem(id);
    pollUpdates();
  } catch (e) {
    console.error('Retry failed:', e);
  }
}

export async function deleteItem(id) {
  if (!confirm('Delete this item and its audio?')) return;
  try {
    await api.deleteItem(id);
    stopForDeletedItem(id);
    loadItems();
  } catch (e) {
    console.error('Delete failed:', e);
  }
}

// --- Playlist assignment from library ---

export async function showPlaylistPicker(itemId, event) {
  event.stopPropagation();
  // Remove any existing picker
  const existing = document.querySelector('.playlist-picker');
  if (existing) existing.remove();

  // Load playlists and item's current playlists
  const [allPlaylists, itemPlaylists] = await Promise.all([
    api.getPlaylists(),
    api.getItemPlaylists(itemId)
  ]);
  const itemPlaylistIds = new Set(itemPlaylists.map(p => p.id));

  if (allPlaylists.length === 0) {
    alert('Create a playlist first in the Playlists tab.');
    return;
  }

  const picker = document.createElement('div');
  picker.className = 'playlist-picker absolute z-50 bg-[var(--bg-input)] border border-[var(--border-input)] rounded-lg shadow-xl p-2 min-w-[180px]';
  picker.style.top = (event.target.getBoundingClientRect().bottom + 4) + 'px';
  picker.style.right = '16px';
  picker.style.position = 'fixed';

  picker.innerHTML = allPlaylists.map(p => {
    const checked = itemPlaylistIds.has(p.id) ? 'checked' : '';
    return `<label class="flex items-center gap-2 px-2 py-1.5 hover:bg-[var(--hover-bg)] rounded cursor-pointer text-sm">
                    <input type="checkbox" ${checked} onchange="togglePlaylistItem(${p.id}, ${itemId}, this.checked)" class="rounded">
                    <span class="truncate">${escapeHtml(p.name)}</span>
                </label>`;
  }).join('');

  document.body.appendChild(picker);

  // Close on outside click
  setTimeout(() => {
    document.addEventListener('click', function closePicker(e) {
      if (!picker.contains(e.target)) {
        picker.remove();
        document.removeEventListener('click', closePicker);
      }
    });
  }, 0);
}

export async function togglePlaylistItem(playlistId, itemId, add) {
  try {
    if (add) {
      await api.addItemToPlaylist(playlistId, itemId);
    } else {
      await api.removeItemFromPlaylist(playlistId, itemId);
    }
  } catch (e) {
    console.error('Toggle playlist item failed:', e);
  }
}

// --- Utilities ---

export function autoResize(el) {
  el.style.height = '';
  el.style.height = Math.min(el.scrollHeight, 200) + 'px';
}

export function handleInputKey(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    const value = event.target.value.trim();
    const isUrl = /^https?:\/\//i.test(value);
    if (isUrl || value.split('\n').length <= 1) {
      event.preventDefault();
      convert();
    }
  }
}

export function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// --- Polling ---

export function pollUpdates() {
  loadItems().then(() => {
    // If there are processing items, keep polling
    if (!Array.isArray(items)) return;
    const processing = items.some(i => i.status === 'processing' || i.status === 'queued');
    if (processing) {
      setTimeout(pollUpdates, 3000);
    }
  }).catch(e => {
    console.error('Polling error:', e);
    setTimeout(pollUpdates, 5000);
  });
}

// --- Voices ---

const COMMON_VOICES = [
  { id: "af_heart", name: "Heart (F)" },
  { id: "af_bella", name: "Bella (F)" },
  { id: "af_nicole", name: "Nicole (F)" },
  { id: "af_sarah", name: "Sarah (F)" },
  { id: "af_sky", name: "Sky (F)" },
  { id: "am_adam", name: "Adam (M)" },
  { id: "am_michael", name: "Michael (M)" },
  { id: "bf_emma", name: "Emma (F, UK)" },
  { id: "bf_isabella", name: "Isabella (F, UK)" },
  { id: "bm_george", name: "George (M, UK)" },
  { id: "bm_lewis", name: "Lewis (M, UK)" },
];

export async function loadVoices() {
  const select = document.getElementById('voice-select');
  function populateVoices(voices) {
    select.innerHTML = '';
    for (const v of voices) {
      const opt = document.createElement('option');
      opt.value = v.id;
      opt.textContent = v.name;
      select.appendChild(opt);
    }
  }
  try {
    const data = await api.getVoices();
    const voices = data.voices || [];
    populateVoices(voices.length > 0 ? voices : COMMON_VOICES);
  } catch (e) {
    populateVoices(COMMON_VOICES);
  }
}
