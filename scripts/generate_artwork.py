#!/usr/bin/env python3
"""Generate podcast artwork for NarrateTTS (3000x3000 PNG)."""

import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow is required: pip install Pillow")
    sys.exit(1)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "static"
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "artwork.png"

WIDTH = HEIGHT = 3000
BG_COLOR = (15, 15, 15)
ACCENT_COLOR = (80, 200, 255)
TEXT_COLOR = (240, 240, 240)


def find_font(size: int):
    """Try system fonts with fallback to default."""
    candidates = [
        "/System/Library/Fonts/SFCompact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_waveform(draw: ImageDraw.ImageDraw):
    """Draw a stylized sound waveform in the center."""
    import math

    center_y = 1600
    bar_width = 30
    gap = 20
    num_bars = 40
    total_width = num_bars * (bar_width + gap) - gap
    start_x = (WIDTH - total_width) // 2

    for i in range(num_bars):
        # Create a wave envelope
        t = i / (num_bars - 1)
        envelope = math.sin(t * math.pi) ** 0.7
        height = int(150 + 500 * envelope * (0.5 + 0.5 * math.sin(t * math.pi * 4)))

        x = start_x + i * (bar_width + gap)
        y_top = center_y - height // 2
        y_bottom = center_y + height // 2

        # Gradient-like effect: brighter in center
        brightness = 0.4 + 0.6 * envelope
        color = (
            int(ACCENT_COLOR[0] * brightness),
            int(ACCENT_COLOR[1] * brightness),
            int(ACCENT_COLOR[2] * brightness),
        )

        draw.rounded_rectangle(
            [x, y_top, x + bar_width, y_bottom],
            radius=bar_width // 2,
            fill=color,
        )


def main():
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Title text
    title_font = find_font(220)
    subtitle_font = find_font(100)

    draw.text((WIDTH // 2, 800), "NarrateTTS", fill=TEXT_COLOR,
              font=title_font, anchor="mm")
    draw.text((WIDTH // 2, 1000), "Articles to Audio", fill=(160, 160, 160),
              font=subtitle_font, anchor="mm")

    # Waveform
    draw_waveform(draw)

    # Bottom accent line
    draw.rectangle([200, 2600, 2800, 2610], fill=ACCENT_COLOR)

    img.save(OUTPUT_PATH, "PNG")
    print(f"Artwork saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
