import { getItems } from './library.js';
import { getPlaylists } from './api.js';
import { itemArt, gradientFor } from './imagery.js';
import { playItem } from './player.js';
import { navigate } from './router.js';

function fmtMeta(item) {
  const d = item.source_url ? (() => { try { return new URL(item.source_url).hostname.replace(/^www\./, ''); } catch { return 'Text'; } })() : 'Text';
  return `${d} · ${item.word_count || 0} words`;
}

function continueItem(items) {
  // most-recently-updated completed item with progress that isn't finished
  return items
    .filter(i => i.status === 'completed' && (i.play_position || 0) > 0 && !i.consumed_at &&
      (!i.duration_seconds || (i.play_position / i.duration_seconds) < 0.95))
    .sort((a, b) => (b.updated_at || '').localeCompare(a.updated_at || ''))[0];
}

export async function render() {
  const host = document.getElementById('screen-home');
  const items = getItems();
  const recent = items.filter(i => i.status === 'completed' && i.audio_path).slice(0, 8);
  const cont = continueItem(items);

  let playlists = [];
  try { playlists = await getPlaylists(); } catch (e) { /* ignore */ }

  const heroHtml = cont ? `
    <div class="section-label">Continue listening</div>
    <div class="hero" style="background:${gradientFor(cont.source_url || '')}" onclick="playItem(${cont.id}, '${cont.audio_path ? cont.audio_path.split('/').pop() : ''}')">
      <div style="font-weight:700;font-size:15px">${escapeHtml(cont.title)}</div>
      <div style="font-size:12px;opacity:.85">${escapeHtml(fmtMeta(cont))}</div>
      <div class="hero-prog"><i style="width:${Math.round(100 * (cont.play_position || 0) / (cont.duration_seconds || 1))}%"></i></div>
    </div>` : '';

  const feedsHtml = playlists.length ? `
    <div class="section-label">Your feeds</div>
    <div class="feed-row">
      ${playlists.map(p => `
        <div class="feed-tile" onclick="navigate('#/feed/${p.id}')">
          <div class="art" style="background:url('/static/artwork-playlist-${p.id}.png') center/cover, ${gradientFor(p.name)}"></div>
          <p>${escapeHtml(p.name)}</p>
        </div>`).join('')}
    </div>` : '';

  const recentHtml = `
    <div class="section-label">Recently added</div>
    ${recent.length ? recent.map(i => `
      <div class="item-card flex items-center gap-3 py-2 cursor-pointer" onclick="playItem(${i.id}, '${i.audio_path ? i.audio_path.split('/').pop() : ''}')">
        ${itemArt(i)}
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium truncate">${escapeHtml(i.title)}</p>
          <p class="text-xs text-[var(--text-muted)] truncate">${escapeHtml(fmtMeta(i))}</p>
        </div>
      </div>`).join('') : `<p class="text-sm text-[var(--text-muted)]">Nothing yet — tap ＋ to capture something.</p>`}`;

  host.innerHTML = heroHtml + feedsHtml + recentHtml;
}

function escapeHtml(str) { const d = document.createElement('div'); d.textContent = str == null ? '' : str; return d.innerHTML; }
