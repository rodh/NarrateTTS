#!/usr/bin/env python3
"""Generate a favicon for NarrateTTS using the sound wave from the artwork."""

import math
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Pillow is required: pip install Pillow")
    sys.exit(1)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "static"
OUTPUT_DIR.mkdir(exist_ok=True)

# Render at high res then downscale for quality
RENDER_SIZE = 512
BG_COLOR = (15, 15, 15)
ACCENT_COLOR = (80, 200, 255)


def draw_waveform(draw: ImageDraw.ImageDraw, size: int):
    """Draw the sound waveform centered in the icon."""
    center_y = size // 2
    bar_width = 8
    gap = 4
    num_bars = 40
    total_width = num_bars * (bar_width + gap) - gap
    start_x = (size - total_width) // 2

    for i in range(num_bars):
        t = i / (num_bars - 1)
        envelope = math.sin(t * math.pi) ** 0.7
        height = int(30 + 160 * envelope * (0.5 + 0.5 * math.sin(t * math.pi * 4)))

        x = start_x + i * (bar_width + gap)
        y_top = center_y - height // 2
        y_bottom = center_y + height // 2

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
    img = Image.new("RGBA", (RENDER_SIZE, RENDER_SIZE), (*BG_COLOR, 255))
    draw = ImageDraw.Draw(img)
    draw_waveform(draw, RENDER_SIZE)

    # Save sizes: 32, 48, 64, 128, 256 into a single .ico
    sizes = [(s, s) for s in (16, 32, 48, 64, 128, 256)]
    ico_path = OUTPUT_DIR / "favicon.ico"
    img.save(ico_path, format="ICO", sizes=sizes)
    print(f"Favicon saved to {ico_path}")

    # Also save a 180x180 apple-touch-icon PNG
    apple = img.resize((180, 180), Image.LANCZOS)
    apple_path = OUTPUT_DIR / "apple-touch-icon.png"
    apple.save(apple_path, "PNG")
    print(f"Apple touch icon saved to {apple_path}")


if __name__ == "__main__":
    main()
