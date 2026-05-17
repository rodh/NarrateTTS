# Status Indicators Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the confusing green-dot/checkmark/pie-chart indicators with a clear bright-dot → progress-ring → dim-dot visual system.

**Architecture:** All changes are in `index.html` (single-file frontend, inline JS). Two code blocks change: the right-side icon logic and the left-side progress circle. Backend is untouched.

**Tech Stack:** Vanilla JS, SVG, Tailwind CSS classes.

**Design doc:** `docs/plans/2026-05-16-status-indicators-design.md`

---

### Task 1: Replace right-side icon — remove checkmark, always show play/pause

**Files:**
- Modify: `index.html:156-170`

**Step 1: Replace the icon block**

Replace lines 156-170 with this logic:
- `completed` + playing → pause icon (gray)
- `completed` + not playing + finished → play icon (dim gray `text-gray-600`)
- `completed` + not playing + not finished → play icon (gray `text-gray-400`)
- `processing` → "Converting..." text (unchanged)
- `error` → error text (unchanged)

```javascript
// Icon for right side
let iconHtml = '';
if (item.status === 'completed' && item.audio_path) {
    if (isPlaying) {
        iconHtml = `<span class="text-gray-400"><svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg></span>`;
    } else {
        const playColor = isFinished ? 'text-gray-600' : 'text-gray-400';
        iconHtml = `<span class="${playColor}"><svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><polygon points="5,3 19,12 5,21"/></svg></span>`;
    }
} else if (item.status === 'processing') {
    iconHtml = `<span class="text-blue-400 text-sm animate-pulse">Converting...</span>`;
} else if (item.status === 'error') {
    iconHtml = `<span class="text-red-400 text-xs truncate max-w-[200px]" title="${escapeHtml(item.error || '')}">${escapeHtml(item.error || 'Error')}</span>`;
}
```

**Step 2: Verify visually**

Run: open the app in browser. Confirm:
- No green checkmarks appear anywhere
- Finished items show a dim play icon
- Unlistened items show a normal gray play icon
- Currently playing item shows pause icon

**Step 3: Commit**

```bash
git add index.html
git commit -m "refactor: remove checkmark, always show play/pause icon"
```

---

### Task 2: Replace left-side progress circle with new indicator system

**Files:**
- Modify: `index.html:172-190`

**Step 1: Replace the progress circle block**

Replace lines 172-190 with new SVG logic using stroke-dasharray for smooth arc progress:

```javascript
// Progress indicator (left side)
let progressCircle = '';
if (item.status === 'completed') {
    if (isFinished) {
        // Finished: dim gray filled dot
        progressCircle = `<svg class="w-3 h-3 flex-shrink-0 mt-[3px]" viewBox="0 0 16 16"><circle cx="8" cy="8" r="5" fill="#4b5563"/></svg>`;
    } else if (pct > 0) {
        // In progress: gray ring with blue arc
        const circumference = 2 * Math.PI * 6;
        const offset = circumference * (1 - Math.min(pct / 0.8, 1));
        progressCircle = `<svg class="w-3 h-3 flex-shrink-0 mt-[3px]" viewBox="0 0 16 16">` +
            `<circle cx="8" cy="8" r="6" fill="none" stroke="#374151" stroke-width="2.5"/>` +
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
    // Queued: no indicator (invisible spacer to keep alignment)
    progressCircle = `<svg class="w-3 h-3 flex-shrink-0 mt-[3px]" viewBox="0 0 16 16"></svg>`;
}
```

Key details:
- Uses `stroke-dasharray` / `stroke-dashoffset` for smooth arc (no SVG arc-path math needed)
- `rotate(-90 8 8)` starts the arc at 12 o'clock instead of 3 o'clock
- `stroke-linecap="round"` gives the arc a rounded end cap
- Progress is scaled to 80% threshold: `pct / 0.8` so the ring is fully filled right at the finished boundary
- r=6 with stroke-width=2.5 fills the 16×16 viewBox well
- r=5 for solid dots is slightly smaller than the ring, visually balanced

**Step 2: Verify visually**

Run: open the app in browser. Confirm:
- Unlistened items: bright blue dot on left
- Partially listened items: blue arc on gray ring, proportional to progress
- Finished items: dim gray dot on left
- Converting items: pulsing blue dot
- Error items: red dot
- All items still aligned correctly

**Step 3: Commit**

```bash
git add index.html
git commit -m "feat: redesign status indicators with dot/ring/dim system"
```

---

### Task 3: Remove unused CSS status classes

**Files:**
- Modify: `index.html:10-22` (style block)

**Step 1: Remove `.status-completed` green color**

The `.status-completed { color: #22c55e; }` class used green for the old "finished" state. Check if it's referenced anywhere else in the file. If only used by the old indicators, remove it. Keep `.status-queued`, `.status-processing`, `.status-error` if they're still used.

**Step 2: Verify no broken styles**

Run: open the app, confirm nothing else relied on `.status-completed` color.

**Step 3: Commit**

```bash
git add index.html
git commit -m "chore: remove unused status-completed CSS class"
```
