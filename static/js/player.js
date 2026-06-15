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

  const item = items.find(i => i.id === id);
  highWaterMark = item?.play_position || 0;

  audio.addEventListener('timeupdate', updatePlayerUI);
  audio.addEventListener('ended', () => {
    highWaterMark = audio.duration;
    saveProgress();
    document.getElementById('play-icon').classList.remove('hidden');
    document.getElementById('pause-icon').classList.add('hidden');
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
  } else {
    audio.pause();
    saveProgress();
    document.getElementById('play-icon').classList.remove('hidden');
    document.getElementById('pause-icon').classList.add('hidden');
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
}

export function updatePlayerUI() {
  if (!audio || !audio.duration) return;
  const pct = (audio.currentTime / audio.duration) * 100;
  document.getElementById('player-progress').value = pct;
  document.getElementById('player-time').textContent = formatTime(audio.currentTime);
  document.getElementById('player-duration').textContent = formatTime(audio.duration);

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
