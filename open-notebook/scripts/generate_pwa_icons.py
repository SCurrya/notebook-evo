# -*- coding: utf-8 -*-
"""Generate PWA PNG icons matching the logo.svg gradient-node design.

Creates 192x192 and 512x512 PNGs (with maskable padding) plus favicon-32.
Requires Pillow. Run from the repo root:
    python scripts/generate_pwa_icons.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

OUT_DIR = Path(__file__).resolve().parent.parent / "frontend" / "public"


def _lerp(a, b, t):
    return int(a + (b - a) * t)


def _gradient_color(t: float) -> tuple:
    """Interpolate between #bd34fe (purple) and #41d1ff (cyan)."""
    return (
        _lerp(0xBD, 0x41, t),
        _lerp(0x34, 0xD1, t),
        _lerp(0xFE, 0xFF, t),
    )


def _draw(size: int, maskable: bool = False) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background: dark rounded rect so icons look good on any launcher.
    margin = int(size * 0.12) if maskable else 0
    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg_draw = ImageDraw.Draw(bg)
    bg_draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=int(size * 0.22),
        fill=(15, 15, 18, 255),
    )
    img.alpha_composite(bg)

    # Coordinate space (fractions of size), matching the 240x240 logo.
    def P(x: float, y: float) -> tuple:
        return (x * size, y * size)

    center = (120, 80)
    left = (80, 120)
    right = (160, 120)
    bottom = (120, 160)

    def norm_frac(pt):
        return (pt[0] / 240.0, pt[1] / 240.0)

    def px(pt):
        return P(*norm_frac(pt))

    # Connection lines (semi-transparent gradient-ish)
    line_colors = [(189, 52, 254, 70), (65, 209, 255, 70)]
    for a, b in [
        (center, left),
        (center, right),
        (left, bottom),
        (right, bottom),
        (left, right),
    ]:
        draw.line([px(a), px(b)], fill=line_colors[0], width=max(2, int(size * 0.008)))

    # Nodes: outer ring + inner fill
    def node(pt, r_frac):
        cx, cy = px(pt)
        r = r_frac * size
        # ring
        ring_r = r * 1.2
        draw.ellipse(
            [cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r],
            outline=line_colors[0],
            width=max(2, int(size * 0.006)),
        )
        # filled circle with gradient approximation
        grad_steps = 32
        for i in range(grad_steps, 0, -1):
            t = i / grad_steps
            rr = r * (i / grad_steps)
            color = _gradient_color(t)
            draw.ellipse(
                [cx - rr, cy - rr, cx + rr, cy + rr],
                fill=(*color, 255),
            )

    node(center, 20 / 240)
    node(left, 16 / 240)
    node(right, 16 / 240)
    node(bottom, 18 / 240)

    return img


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Normal + maskable variants
    for size in (192, 512):
        _draw(size, maskable=False).save(OUT_DIR / f"icon-{size}x{size}.png")
        _draw(size, maskable=True).save(
            OUT_DIR / f"icon-maskable-{size}x{size}.png"
        )
        print(f"generated icon-{size}x{size}.png + icon-maskable-{size}x{size}.png")
    _draw(64, maskable=False).resize(
        (32, 32), Image.LANCZOS
    ).save(OUT_DIR / "favicon.png")
    print("generated favicon.png")
    print(f"output dir: {OUT_DIR}")


if __name__ == "__main__":
    main()
