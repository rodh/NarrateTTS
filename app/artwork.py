import logging
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.config import STATIC_DIR

logger = logging.getLogger(__name__)

ARTWORK_SIZE = 3000
BG_COLOR = (15, 15, 15)
TITLE_COLOR = (240, 240, 240)
BRAND_COLOR = (160, 160, 160)
FONT_PATH = "/System/Library/Fonts/HelveticaNeue.ttc"
FONT_BOLD_INDEX = 1
FONT_REGULAR_INDEX = 0

# Text area to paint over on the base artwork (covers original title + subtitle)
TEXT_AREA_TOP = 680
TEXT_AREA_BOTTOM = 1100


def _base_image() -> Image.Image:
    """Load the default artwork and blank out the text area."""
    base = Image.open(STATIC_DIR / "artwork.png").copy()
    draw = ImageDraw.Draw(base)
    draw.rectangle(
        [(0, TEXT_AREA_TOP), (ARTWORK_SIZE, TEXT_AREA_BOTTOM)],
        fill=BG_COLOR,
    )
    return base


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
    img = _base_image()
    draw = ImageDraw.Draw(img)

    max_width = ARTWORK_SIZE - 400  # 200px padding each side
    center_x = ARTWORK_SIZE // 2

    # Draw playlist name (large, bold)
    title_font, title_lines, title_lh = _fit_text(
        draw, name, max_width, FONT_PATH, FONT_BOLD_INDEX,
        max_size=200, min_size=80,
    )

    # Draw brand text (smaller, regular)
    brand_size = 72
    brand_font = ImageFont.truetype(FONT_PATH, size=brand_size, index=FONT_REGULAR_INDEX)
    brand_bbox = draw.textbbox((0, 0), "NarrateTTS", font=brand_font)
    brand_h = brand_bbox[3] - brand_bbox[1]

    # Calculate vertical positions - center the whole text block in the text area
    title_block_h = title_lh * len(title_lines) + 12 * (len(title_lines) - 1)
    gap = 30
    total_h = title_block_h + gap + brand_h
    area_center_y = (TEXT_AREA_TOP + TEXT_AREA_BOTTOM) // 2
    start_y = area_center_y - total_h // 2

    # Draw title lines
    y = start_y
    for line in title_lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        w = bbox[2] - bbox[0]
        draw.text((center_x - w // 2, y), line, fill=TITLE_COLOR, font=title_font)
        y += title_lh + 12

    # Draw brand
    y = start_y + title_block_h + gap
    brand_w = brand_bbox[2] - brand_bbox[0]
    draw.text((center_x - brand_w // 2, y), "NarrateTTS", fill=BRAND_COLOR, font=brand_font)

    out_path = STATIC_DIR / f"artwork-playlist-{playlist_id}.png"
    img.save(out_path, "PNG")
    logger.info("Generated artwork for playlist %d: %s", playlist_id, out_path)
    return out_path
