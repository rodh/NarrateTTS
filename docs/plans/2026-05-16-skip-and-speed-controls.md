# Skip & Speed Controls Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add skip-back-30s, skip-forward-30s, and playback speed controls to the NarrateTTS audio player.

**Architecture:** Frontend-only changes to `index.html`. Skip buttons flank the play/pause button, speed button at far right of player bar. Speed persists via localStorage.

**Tech Stack:** Vanilla JS, HTML, Tailwind CSS (CDN)

---

### Task 1: Add skip buttons to player bar

**Files:**
- Modify: `index.html:59-73` (player bar HTML)

**Step 1: Add skip-back and skip-forward buttons flanking play/pause**

Replace the player bar's button/content section (lines 60-73):

```html
    <div id="player" class="hidden border-t border-gray-800 px-4 sm:px-6 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))]">
        <div class="flex items-center gap-3 sm:gap-4">
            <div class="flex items-center gap-1">
                <button onclick="skipBack()" class="w-8 h-8 flex items-center justify-center rounded-full text-gray-400 hover:text-white transition flex-shrink-0" title="Back 30s">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0019 16V8a1 1 0 00-1.6-.8l-5.333 4zM4.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0011 16V8a1 1 0 00-1.6-.8l-5.334 4z"/></svg>
                </button>
                <button id="play-btn" onclick="togglePlay()" class="w-10 h-10 flex items-center justify-center rounded-full bg-white text-black hover:bg-gray-200 transition flex-shrink-0">
                    <svg id="play-icon" class="w-5 h-5 ml-0.5" fill="currentColor" viewBox="0 0 24 24"><polygon points="5,3 19,12 5,21"/></svg>
                    <svg id="pause-icon" class="w-5 h-5 hidden" fill="currentColor" viewBox="0 0 24 24"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
                </button>
                <button onclick="skipForward()" class="w-8 h-8 flex items-center justify-center rounded-full text-gray-400 hover:text-white transition flex-shrink-0" title="Forward 30s">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M11.933 12.8a1 1 0 000-1.6L6.6 7.2A1 1 0 005 8v8a1 1 0 001.6.8l5.333-4zM19.933 12.8a1 1 0 000-1.6l-5.334-4A1 1 0 0013 8v8a1 1 0 001.6.8l5.333-4z"/></svg>
                </button>
            </div>
            <div class="flex-1 min-w-0">
                <p id="player-title" class="text-sm font-medium truncate"></p>
                <div class="flex items-center gap-2 mt-1">
                    <span id="player-time" class="text-xs text-gray-500 flex-shrink-0">0:00</span>
                    <input id="player-progress" type="range" min="0" max="100" value="0" class="flex-1 h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white" oninput="seekTo(this.value)">
                    <span id="player-duration" class="text-xs text-gray-500 flex-shrink-0">0:00</span>
                </div>
            </div>
            <button id="speed-btn" onclick="cycleSpeed()" class="text-xs text-gray-400 hover:text-white transition flex-shrink-0 px-2 py-1 rounded bg-gray-800 hover:bg-gray-700 min-w-[3rem] text-center" title="Playback speed">1x</button>
        </div>
    </div>
```

**Step 2: Verify in browser**

Open http://localhost:8090, play an item, confirm buttons appear correctly.

**Step 3: Commit**

```bash
git add index.html
git commit -m "feat: add skip and speed button HTML to player bar"
```

---

### Task 2: Add skip functions

**Files:**
- Modify: `index.html` (JavaScript section, after `seekTo` function ~line 295)

**Step 1: Add skipBack and skipForward functions**

Insert after the `seekTo` function:

```javascript
        function skipBack() {
            if (!audio) return;
            audio.currentTime = Math.max(0, audio.currentTime - 30);
        }

        function skipForward() {
            if (!audio) return;
            const newTime = audio.currentTime + 30;
            if (newTime >= audio.duration) {
                audio.currentTime = audio.duration;
            } else {
                audio.currentTime = newTime;
            }
        }
```

**Step 2: Update high-water mark on skip forward**

The existing `updatePlayerUI` already handles high-water-mark updates on `timeupdate` events, which fire after `currentTime` changes. No additional code needed — skipping forward will trigger `timeupdate` and the existing `if (audio.currentTime > highWaterMark)` check handles it.

**Step 3: Verify in browser**

Play an item, tap skip-back and skip-forward, confirm time jumps by 30s in each direction.

**Step 4: Commit**

```bash
git add index.html
git commit -m "feat: add skip forward/back 30s functions"
```

---

### Task 3: Add speed cycling with localStorage persistence

**Files:**
- Modify: `index.html` (JavaScript section)

**Step 1: Add speed constants and cycleSpeed function**

Insert after the skip functions:

```javascript
        const SPEED_OPTIONS = [1, 1.25, 1.5, 2, 0.75];

        function getStoredSpeed() {
            const stored = localStorage.getItem('narrateTTS_playbackSpeed');
            const val = parseFloat(stored);
            return (val && SPEED_OPTIONS.includes(val)) ? val : 1;
        }

        function cycleSpeed() {
            const current = getStoredSpeed();
            const idx = SPEED_OPTIONS.indexOf(current);
            const next = SPEED_OPTIONS[(idx + 1) % SPEED_OPTIONS.length];
            localStorage.setItem('narrateTTS_playbackSpeed', next);
            if (audio) audio.playbackRate = next;
            document.getElementById('speed-btn').textContent = next === 1 ? '1x' : next + 'x';
        }
```

**Step 2: Apply stored speed in playItem function**

In the `playItem` function, after `audio = new Audio(...)` (around line 245), add:

```javascript
            const speed = getStoredSpeed();
            audio.playbackRate = speed;
```

**Step 3: Initialize speed button label on page load**

In the Init section (end of script), add after `loadItems()`:

```javascript
        // Init speed button label
        const initSpeed = getStoredSpeed();
        document.getElementById('speed-btn').textContent = initSpeed === 1 ? '1x' : initSpeed + 'x';
```

**Step 4: Verify in browser**

- Play item, tap speed button, confirm it cycles through 1x -> 1.25x -> 1.5x -> 2x -> 0.75x -> 1x
- Confirm audio plays at new speed
- Refresh page, confirm speed label shows persisted value
- Play a new item, confirm it uses the persisted speed

**Step 5: Commit**

```bash
git add index.html
git commit -m "feat: add playback speed cycling with localStorage persistence"
```

---

### Task 4: Final integration test

**Step 1: Full manual test**

1. Load page, add/play an item
2. Tap skip-back — time goes back 30s (or to 0)
3. Tap skip-forward — time goes forward 30s
4. Skip forward near end — triggers ended behavior correctly
5. Tap speed — cycles through all options, audio rate changes
6. Refresh — speed label and actual playback rate match persisted value
7. Progress bar still works, row-tap still works, pause/resume still works

**Step 2: Commit (if any fixes needed)**

```bash
git add index.html
git commit -m "fix: address integration issues with skip/speed controls"
```
