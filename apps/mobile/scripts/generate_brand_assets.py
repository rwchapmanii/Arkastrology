from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT / "assets" / "brand"

PALETTE = {
    "bg": "#F7F1E7",
    "card": "#FFF8EE",
    "card_inner": "#FFF2DE",
    "ink": "#16322E",
    "muted": "#5D6A64",
    "gold": "#C39A53",
    "gold_soft": "#E7D0A6",
    "border": "#D8CFC0",
    "border_strong": "#B9AC98",
}

NODES = [
    {"x": 0.5, "y": 0.08, "gold": True},
    {"x": 0.28, "y": 0.2},
    {"x": 0.72, "y": 0.2},
    {"x": 0.5, "y": 0.34, "gold": True},
    {"x": 0.28, "y": 0.46},
    {"x": 0.72, "y": 0.46},
    {"x": 0.5, "y": 0.6, "large": True},
    {"x": 0.28, "y": 0.74},
    {"x": 0.72, "y": 0.74},
    {"x": 0.5, "y": 0.88, "gold": True},
]

LINKS = [
    (0.5, 0.08, 0.28, 0.2),
    (0.5, 0.08, 0.72, 0.2),
    (0.28, 0.2, 0.5, 0.34),
    (0.72, 0.2, 0.5, 0.34),
    (0.28, 0.2, 0.28, 0.46),
    (0.72, 0.2, 0.72, 0.46),
    (0.5, 0.34, 0.28, 0.46),
    (0.5, 0.34, 0.72, 0.46),
    (0.5, 0.34, 0.5, 0.6),
    (0.28, 0.46, 0.5, 0.6),
    (0.72, 0.46, 0.5, 0.6),
    (0.28, 0.46, 0.28, 0.74),
    (0.72, 0.46, 0.72, 0.74),
    (0.5, 0.6, 0.28, 0.74),
    (0.5, 0.6, 0.72, 0.74),
    (0.28, 0.74, 0.5, 0.88),
    (0.72, 0.74, 0.5, 0.88),
    (0.5, 0.6, 0.5, 0.88),
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates: Iterable[str] = (
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Georgia.ttf",
        "/System/Library/Fonts/Supplemental/Gill Sans Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Gill Sans.ttc",
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def rounded_box(draw: ImageDraw.ImageDraw, xy, radius: int, fill: str, outline: str | None = None, width: int = 1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_brand_mark(draw: ImageDraw.ImageDraw, x: int, y: int, size: int):
    outer_radius = int(size * 0.24)
    frame_size = int(size * 0.74)
    frame_x = x + (size - frame_size) // 2
    frame_y = y + (size - frame_size) // 2
    rounded_box(draw, (x, y, x + size, y + size), outer_radius, PALETTE["card"], PALETTE["border_strong"], max(1, size // 60))
    inner_radius = int(size * 0.18)
    rounded_box(
        draw,
        (frame_x, frame_y, frame_x + frame_size, frame_y + frame_size),
        inner_radius,
        PALETTE["card_inner"],
        PALETTE["border"],
        max(1, size // 70),
    )

    line_width = max(2, size // 34)
    for x1, y1, x2, y2 in LINKS:
        draw.line(
            (
                frame_x + int(frame_size * x1),
                frame_y + int(frame_size * y1),
                frame_x + int(frame_size * x2),
                frame_y + int(frame_size * y2),
            ),
            fill=PALETTE["ink"],
            width=line_width,
        )

    for node in NODES:
        diameter = max(12, int(size * (0.12 if node.get("large") else 0.1)))
        cx = frame_x + int(frame_size * node["x"])
        cy = frame_y + int(frame_size * node["y"])
        fill = PALETTE["gold"] if node.get("gold") else PALETTE["card"]
        outline = PALETTE["gold"] if node.get("gold") else PALETTE["border_strong"]
        draw.ellipse((cx - diameter // 2, cy - diameter // 2, cx + diameter // 2, cy + diameter // 2), fill=fill, outline=outline, width=max(1, size // 80))


def save_icon(name: str, size: int, padded: bool = False):
    image = Image.new("RGBA", (size, size), PALETTE["bg"])
    draw = ImageDraw.Draw(image)
    mark_size = int(size * (0.68 if padded else 0.82))
    draw_brand_mark(draw, (size - mark_size) // 2, (size - mark_size) // 2, mark_size)
    image.save(ASSETS_DIR / name)


def save_splash():
    size = 1024
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    mark_size = 620
    draw_brand_mark(draw, (size - mark_size) // 2, (size - mark_size) // 2, mark_size)
    image.save(ASSETS_DIR / "splash-icon.png")


def save_og_card():
    width, height = 1200, 630
    image = Image.new("RGBA", (width, height), PALETTE["bg"])
    draw = ImageDraw.Draw(image)

    rounded_box(draw, (46, 46, width - 46, height - 46), 36, "#FCF7EF", PALETTE["border"], 2)
    draw_brand_mark(draw, 92, 140, 190)

    eyebrow = font(32, bold=False)
    title = font(84, bold=True)
    body = font(34, bold=False)
    accent = font(40, bold=True)

    draw.text((330, 144), "THE ARK", fill=PALETTE["ink"], font=eyebrow)
    draw.ellipse((570, 161, 584, 175), fill=PALETTE["gold"])
    draw.text((606, 144), "ASTROLOGY", fill=PALETTE["ink"], font=eyebrow)
    draw.text((330, 202), "Mystical clarity,\npractical guidance.", fill=PALETTE["ink"], font=title, spacing=10)
    draw.text(
        (330, 410),
        "Traditional astrology readings that explain the chart,\ntranslate the symbolism, and tell you what to do next.",
        fill=PALETTE["muted"],
        font=body,
        spacing=8,
    )
    items = ["real chart data", "daily guidance", "elegant interpretation"]
    x = 96
    for index, item in enumerate(items):
        if index:
            draw.ellipse((x, 558, x + 12, 570), fill=PALETTE["gold"])
            x += 36
        draw.text((x, 540), item, fill=PALETTE["gold"], font=accent)
        bbox = draw.textbbox((x, 540), item, font=accent)
        x = bbox[2] + 24

    image.save(ASSETS_DIR / "og-card.png")


def save_svg_sources():
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024" fill="none">
  <rect width="1024" height="1024" rx="228" fill="{PALETTE['bg']}"/>
  <rect x="108" y="108" width="808" height="808" rx="194" fill="{PALETTE['card']}" stroke="{PALETTE['border_strong']}" stroke-width="16"/>
  <rect x="212" y="212" width="600" height="600" rx="152" fill="{PALETTE['card_inner']}" stroke="{PALETTE['border']}" stroke-width="12"/>
"""
    frame_x = 212
    frame_y = 212
    frame = 600
    for x1, y1, x2, y2 in LINKS:
        svg += (
            f'  <line x1="{frame_x + frame * x1:.1f}" y1="{frame_y + frame * y1:.1f}" '
            f'x2="{frame_x + frame * x2:.1f}" y2="{frame_y + frame * y2:.1f}" stroke="{PALETTE["ink"]}" stroke-width="18" stroke-linecap="round"/>\n'
        )
    for node in NODES:
        diameter = 74 if node.get("large") else 62
        cx = frame_x + frame * node["x"]
        cy = frame_y + frame * node["y"]
        fill = PALETTE["gold"] if node.get("gold") else PALETTE["card"]
        stroke = PALETTE["gold"] if node.get("gold") else PALETTE["border_strong"]
        svg += f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{diameter / 2:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="10"/>\n'
    svg += "</svg>\n"
    (ASSETS_DIR / "brandmark.svg").write_text(svg, encoding="utf-8")


def main():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    save_icon("app-icon.png", 1024)
    save_icon("adaptive-icon.png", 1024, padded=True)
    save_icon("favicon.png", 64)
    save_icon("apple-touch-icon.png", 180)
    save_icon("icon-192.png", 192)
    save_icon("icon-512.png", 512)
    save_splash()
    save_og_card()
    save_svg_sources()


if __name__ == "__main__":
    main()
