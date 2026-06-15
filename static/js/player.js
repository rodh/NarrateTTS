import { patchProgress } from './api.js';
import { renderPreservingScroll } from './library.js';

// --- Module-scoped state ---
let audio = null;
let currentItemId = null;
let highWaterMark = 0;
let saveTimeout = null;

// Shared reference to the library's items array (set via setItems).
let items = [];

export function setItems(itemsRef) {
  items = itemsRef;
}

export function getCurrentItemId() {
  return currentItemId;
}

export function isAudioPlaying() {
  return !!(audio && !audio.paused);
}

// --- Now-Playing + waveform ---

let currentPeaks = null;

function bigArtStyle(item) {
  if (item && item.image_url) return `background-image:url('${item.image_url}')`;
  // gradient fallback consistent with imagery.js palette
  return `background-image:linear-gradient(135deg,#f1582c,#5b2c91)`;
}

async function computePeaks(url, itemId, n = 80) {
  const key = 'peaks_' + itemId;
  const cached = localStorage.getItem(key);
  if (cached) { try { return JSON.parse(cached); } catch {} }
  try {
    const buf = await (await fetch(url)).arrayBuffer();
    const Ctx = window.AudioContext || window.webkitAudioContext;
    const ctx = new Ctx();
    const audioBuf = await ctx.decodeAudioData(buf);
    const data = audioBuf.getChannelData(0);
    const block = Math.max(1, Math.floor(data.length / n));
    const peaks = [];
    for (let i = 0; i < n; i++) {
      let max = 0;
      for (let j = 0; j < block; j++) { const v = Math.abs(data[i * block + j] || 0); if (v > max) max = v; }
      peaks.push(max);
    }
    ctx.close();
    const m = Math.max(...peaks, 0.01);
    const norm = peaks.map(p => p / m);
    localStorage.setItem(key, JSON.stringify(norm));
    return norm;
  } catch (e) {
    return Array.from({ length: n }, () => 0.35); // flat fallback
  }
}

function renderWaveBars(peaks) {
  const wave = document.getElementById('np-wave');
  if (!wave) return;
  wave.innerHTML = peaks.map(p => `<i style="height:${Math.max(8, Math.round(p * 100))}%"></i>`).join('');
}

function updateWaveProgress() {
  const wave = document.getElementById('np-wave');
  if (!wave || !audio || !audio.duration) return;
  const frac = audio.currentTime / audio.duration;
  const bars = wave.children;
  const lit = Math.floor(frac * bars.length);
  for (let i = 0; i < bars.length; i++) bars[i].classList.toggle('on', i <= lit);
}

export function seekWaveform(event) {
  const wave = document.getElementById('np-wave');
  if (!wave || !audio || !audio.duration) return;
  const rect = wave.getBoundingClientRect();
  const frac = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
  audio.currentTime = frac * audio.duration;
}

export function openNowPlaying() {
  const item = items.find(i => i.id === currentItemId);
  if (!item) return;
  document.getElementById('np-art').style.cssText += ';' + bigArtStyle(item);
  document.getElementById('np-title').textContent = item.title || '';
  let src = 'Text';
  try { if (item.source_url) src = new URL(item.source_url).hostname.replace(/^www\./, ''); } catch {}
  document.getElementById('np-source').textContent = src;
  document.getElementById('np-speed').textContent = (getStoredSpeed() === 1) ? '1x' : getStoredSpeed() + 'x';
  if (currentPeaks) renderWaveBars(currentPeaks);
  updateWaveProgress();
  syncNpPlayIcon();
  document.getElementById('now-playing').classList.add('open');
}

export function closeNowPlaying() {
  document.getElementById('now-playing').classList.remove('open');
}

function syncNpPlayIcon() {
  const playing = audio && !audio.paused;
  const pi = document.getElementById('np-play-icon'), pa = document.getElementById('np-pause-icon');
  if (pi && pa) { pi.classList.toggle('hidden', playing); pa.classList.toggle('hidden', !playing); }
}

// --- Playback ---

export function playItem(id, audioFile) {
  if (currentItemId === id && audio) {
    togglePlay();
    return;
  }

  // Save progress from previous item
  if (currentItemId && highWaterMark > 0) {
    saveProgress();
  }

  currentItemId = id;
  if (audio) { audio.pause(); audio = null; }
  audio = new Audio(`/audio/${audioFile}`);
  const speed = getStoredSpeed();
  audio.playbackRate = speed;

  currentPeaks = null;
  computePeaks(`/audio/${audioFile}`, id).then(p => { currentPeaks = p; renderWaveBars(p); updateWaveProgress(); });

  const item = items.find(i => i.id === id);
  highWaterMark = item?.play_position || 0;

  audio.addEventListener('timeupdate', updatePlayerUI);
  audio.addEventListener('ended', () => {
    highWaterMark = audio.duration;
    saveProgress();
    document.getElementById('play-icon').classList.remove('hidden');
    document.getElementById('pause-icon').classList.add('hidden');
    syncNpPlayIcon();
    renderPreservingScroll();
  });

  // Resume from saved position
  if (highWaterMark > 0) {
    audio.addEventListener('canplay', function seekOnce() {
      if (audio.currentTime < highWaterMark) {
        audio.currentTime = highWaterMark;
      }
      audio.removeEventListener('canplay', seekOnce);
    });
  }

  if ('mediaSession' in navigator) {
    navigator.mediaSession.metadata = new MediaMetadata({
      title: item ? item.title : '',
      artist: 'NarrateTTS'
    });
    navigator.mediaSession.setActionHandler('play', () => togglePlay());
    navigator.mediaSession.setActionHandler('pause', () => togglePlay());
    navigator.mediaSession.setActionHandler('seekbackward', () => skipBack());
    navigator.mediaSession.setActionHandler('seekforward', () => skipForward());
  }

  audio.play();
  document.getElementById('player').classList.remove('hidden');
  document.getElementById('player-title').textContent = item ? item.title : '';
  document.getElementById('play-icon').classList.add('hidden');
  document.getElementById('pause-icon').classList.remove('hidden');
  renderPreservingScroll();
}

export function togglePlay() {
  if (!audio) return;
  if (audio.paused) {
    audio.play();
    document.getElementById('play-icon').classList.add('hidden');
    document.getElementById('pause-icon').classList.remove('hidden');
    syncNpPlayIcon();
  } else {
    audio.pause();
    saveProgress();
    document.getElementById('play-icon').classList.remove('hidden');
    document.getElementById('pause-icon').classList.add('hidden');
    syncNpPlayIcon();
  }
  renderPreservingScroll();
}

export function seekTo(value) {
  if (!audio) return;
  audio.currentTime = (value / 100) * audio.duration;
}

export function skipBack() {
  if (!audio) return;
  audio.currentTime = Math.max(0, audio.currentTime - 30);
}

export function skipForward() {
  if (!audio) return;
  const newTime = audio.currentTime + 30;
  if (newTime >= audio.duration) {
    audio.currentTime = audio.duration;
  } else {
    audio.currentTime = newTime;
  }
}

export const SPEED_OPTIONS = [1, 1.25, 1.5, 2, 0.75];

export function getStoredSpeed() {
  const stored = localStorage.getItem('narrateTTS_playbackSpeed');
  const val = parseFloat(stored);
  return (val && SPEED_OPTIONS.includes(val)) ? val : 1;
}

export function cycleSpeed() {
  const current = getStoredSpeed();
  const idx = SPEED_OPTIONS.indexOf(current);
  const next = SPEED_OPTIONS[(idx + 1) % SPEED_OPTIONS.length];
  localStorage.setItem('narrateTTS_playbackSpeed', next);
  if (audio) audio.playbackRate = next;
  document.getElementById('speed-btn').textContent = next === 1 ? '1x' : next + 'x';
  const nps = document.getElementById('np-speed'); if (nps) nps.textContent = next === 1 ? '1x' : next + 'x';
}

export function updatePlayerUI() {
  if (!audio || !audio.duration) return;
  const pct = (audio.currentTime / audio.duration) * 100;
  document.getElementById('player-progress').value = pct;
  document.getElementById('player-time').textContent = formatTime(audio.currentTime);
  document.getElementById('player-duration').textContent = formatTime(audio.duration);

  const npt = document.getElementById('np-time'); if (npt) npt.textContent = formatTime(audio.currentTime);
  const npd = document.getElementById('np-duration'); if (npd) npd.textContent = formatTime(audio.duration);
  updateWaveProgress();

  if (audio.currentTime > highWaterMark) {
    highWaterMark = audio.currentTime;
    debouncedSaveProgress();
  }
}

export async function resetProgress(id) {
  try {
    await patchProgress(id, 0);
    const item = items.find(i => i.id === id);
    if (item) item.play_position = 0;
    if (currentItemId === id) {
      highWaterMark = 0;
      if (audio) audio.currentTime = 0;
    }
    renderPreservingScroll();
  } catch (e) {
    console.error('Reset progress failed:', e);
  }
}

export function saveProgress() {
  if (!currentItemId || highWaterMark <= 0) return;
  const item = items.find(i => i.id === currentItemId);
  if (item && highWaterMark > (item.play_position || 0)) {
    item.play_position = highWaterMark;
  }
  patchProgress(currentItemId, highWaterMark).catch(e => console.error('Save progress failed:', e));
}

export function debouncedSaveProgress() {
  if (saveTimeout) clearTimeout(saveTimeout);
  saveTimeout = setTimeout(saveProgress, 5000);
}

// Called when the currently-playing item is deleted: tear down playback.
export function stopForDeletedItem(id) {
  if (currentItemId === id) {
    if (audio) { audio.pause(); audio = null; }
    currentItemId = null;
    document.getElementById('player').classList.add('hidden');
  }
}

export function formatTime(s) {
  if (!s || isNaN(s)) return '0:00';
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, '0')}`;
}
