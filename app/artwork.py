import logging
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.config import STATIC_DIR

logger = logging.getLogger(__name__)

ARTWORK_SIZE = 3000
BG_COLOR = (15, 15, 15)
TITLE_COLOR = (240, 240, 240)
FONT_PATH = "/System/Library/Fonts/HelveticaNeue.ttc"
FONT_BOLD_INDEX = 1

# Text area to paint over on the base artwork
TEXT_AREA_TOP = 680

# Sound wave region in the base artwork and repositioned location
WAVE_TOP = 1250
WAVE_BOTTOM = 1950
WAVE_NEW_TOP = 1850


def _fit_text(draw: ImageDraw.ImageDraw, text: str, max_width: int,
              font_path: str, font_index: int, max_size: int, min_size: int) -> tuple:
    """Find the best font size and line wrapping to fit text within max_width.

    Returns (font, lines, line_height).
    """
    for size in range(max_size, min_size - 1, -4):
        font = ImageFont.truetype(font_path, size=size, index=font_index)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]

        if text_width <= max_width:
            line_height = bbox[3] - bbox[1]
            return font, [text], line_height

        # Try wrapping
        for wrap_width in range(30, 8, -1):
            lines = textwrap.wrap(text, width=wrap_width)
            fits = all(
                draw.textbbox((0, 0), line, font=font)[2] <= max_width
                for line in lines
            )
            if fits and len(lines) <= 3:
                line_height = draw.textbbox((0, 0), "Ag", font=font)[3]
                return font, lines, line_height

    # Minimum size, force wrap
    font = ImageFont.truetype(font_path, size=min_size, index=font_index)
    lines = textwrap.wrap(text, width=15)[:3]
    line_height = draw.textbbox((0, 0), "Ag", font=font)[3]
    return font, lines, line_height


def generate_playlist_artwork(name: str, playlist_id: int) -> Path:
    """Generate artwork for a playlist and save it to static/."""
    base = Image.open(STATIC_DIR / "artwork.png").copy()

    # Crop the sound wave before blanking
    wave = base.crop((0, WAVE_TOP, ARTWORK_SIZE, WAVE_BOTTOM))

    # Blank everything from text area to bottom, then paste wave lower
    draw = ImageDraw.Draw(base)
    draw.rectangle(
        [(0, TEXT_AREA_TOP), (ARTWORK_SIZE, ARTWORK_SIZE)],
        fill=BG_COLOR,
    )
    base.paste(wave, (0, WAVE_NEW_TOP))
    draw = ImageDraw.Draw(base)

    max_width = ARTWORK_SIZE - 400  # 200px padding each side
    center_x = ARTWORK_SIZE // 2

    # Draw playlist name (large, bold)
    title_font, title_lines, title_lh = _fit_text(
        draw, name, max_width, FONT_PATH, FONT_BOLD_INDEX,
        max_size=300, min_size=100,
    )

    # Center title vertically between text area top and wave
    title_block_h = title_lh * len(title_lines) + 12 * (len(title_lines) - 1)
    area_center_y = (TEXT_AREA_TOP + WAVE_NEW_TOP) // 2
    start_y = area_center_y - title_block_h // 2

    y = start_y
    for line in title_lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        w = bbox[2] - bbox[0]
        draw.text((center_x - w // 2, y), line, fill=TITLE_COLOR, font=title_font)
        y += title_lh + 12

    out_path = STATIC_DIR / f"artwork-playlist-{playlist_id}.png"
    base.save(out_path, "PNG")
    logger.info("Generated artwork for playlist %d: %s", playlist_id, out_path)
    return out_path
