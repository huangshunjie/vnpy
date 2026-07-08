"""make_portfolio_ico.py — 生成投资组合饼图图标"""
import math
from PIL import Image, ImageDraw
import pathlib

def draw_pie_icon(size=64):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy, r = size // 2, size // 2, size // 2 - 2

    # 饼图分块：角度、颜色（与截图配色一致）
    slices = [
        (0,   120, "#E8694A"),   # 橙红
        (120, 210, "#4A9E8E"),   # 青绿
        (210, 280, "#F0B429"),   # 黄
        (280, 360, "#6C8EBF"),   # 蓝灰
    ]

    for start, end, color in slices:
        draw.pieslice(
            [cx - r, cy - r, cx + r, cy + r],
            start=start - 90, end=end - 90,
            fill=color, outline="#1a1a2e", width=1
        )

    # 中心小圆（甜甜圈效果）
    inner = r * 0.38
    draw.ellipse(
        [cx - inner, cy - inner, cx + inner, cy + inner],
        fill=(0, 0, 0, 0)
    )

    return img

out = pathlib.Path(r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\trader\ui\ico\portfolio.ico")

sizes = [16, 32, 48, 64]
frames = [draw_pie_icon(s) for s in sizes]
frames[0].save(
    out, format="ICO",
    sizes=[(s, s) for s in sizes],
    append_images=frames[1:]
)
print("saved:", out)
