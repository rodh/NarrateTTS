# Status Indicators Redesign

## Problem

The current indicators are confusing:
- Green filled dot reads as "new/fresh" but means "finished" — inverted from convention
- Hollow dot for unlistened looks subdued, implying "already seen"
- Right-side checkmark is redundant with the left-side progress indicator
- Pie chart uses chunky quarter increments instead of smooth progress

## Four States

| State | Left indicator | Right icon |
|-------|---------------|------------|
| New/unlistened | Bright solid blue dot (`#3b82f6`) | Play (gray) |
| In progress | Open ring with smooth arc fill (gray stroke `#374151`, blue arc proportional to `play_position / duration`) | Play (gray) |
| Finished (>=80%) | Subdued filled circle (dim gray `#4b5563`) | Play (dim gray) |
| Converting / Error | Pulsing blue dot / red dot | "Converting..." / error text |

## Changes

1. Left indicator overhaul: 4-quarter pie chart becomes solid dot (new), smooth arc ring (in-progress), or dim filled circle (finished)
2. Remove green checkmark: right side always shows Play / Pause, never a checkmark
3. Color semantics flip: bright = needs attention (unlistened), dim = done
4. Smooth arc: progress ring fills continuously based on actual percentage

## Visual Hierarchy

- Bright blue dots pop out for unlistened items
- Partially filled rings are visually distinct for in-progress items
- Dim gray circles recede for finished items

## Unchanged

- Play / Pause behavior on right side
- 80% threshold for "finished"
- `consumed_at` as alternate finished trigger
- Converting/error text labels
- All backend logic and data model
