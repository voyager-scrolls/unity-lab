"""compare.py - reference-vs-render comparison for stage matching.

Subcommands
  diff    <render.png> <reference.png> --out diff.png [--grid 3] [--ssim-size 256]
          Writes a 3-panel image (render | reference | 50/50 overlay), reports
          global SSIM on a downscaled luminance image and a per-cell colour delta table.
  overlay <a.png> <b.png> --out out.png [--alpha 0.5]
  side    <a.png> <b.png> --out out.png [--height 720]

Notes
  * images are resized to the first image's size (aspect kept, letterboxed by crop).
  * SSIM is computed on a 256 px luminance thumbnail (pure python, fast enough).
  * per-cell delta is mean |dRGB| in 0-255; lower is better.

Examples
  py -3 tools/compare.py diff builds/shots/view_0.png builds/ref/target.png --out builds/ref/diff0.png
  py -3 tools/compare.py overlay render.png reference.png --out builds/ref/ov.png --alpha 0.5
"""

import argparse
import math
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageStat


def _prep(a_path, b_path):
    a = Image.open(a_path).convert("RGB")
    b = Image.open(b_path).convert("RGB")
    if a.size != b.size:
        b = b.resize(a.size, Image.LANCZOS)
    return a, b


def _luma(im, size):
    g = im.convert("L")
    g.thumbnail((size, size), Image.LANCZOS)
    return list(g.getdata()), g.size


def ssim(a, b, size=256):
    la, sz = _luma(a, size)
    lb, _ = _luma(b, size)
    n = float(len(la))
    ma = sum(la) / n
    mb = sum(lb) / n
    va = sum((x - ma) ** 2 for x in la) / n
    vb = sum((y - mb) ** 2 for y in lb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(la, lb)) / n
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    return ((2 * ma * mb + c1) * (2 * cov + c2)) / ((ma * ma + mb * mb + c1) * (va + vb + c2))


def cell_table(a, b, grid):
    w, h = a.size
    out = []
    for gy in range(grid):
        row = []
        for gx in range(grid):
            box = (int(gx * w / grid), int(gy * h / grid), int((gx + 1) * w / grid), int((gy + 1) * h / grid))
            ca, cb = a.crop(box), b.crop(box)
            sa, sb = ImageStat.Stat(ca), ImageStat.Stat(cb)
            d = sum(abs(sa.mean[i] - sb.mean[i]) for i in range(3)) / 3.0
            row.append(d)
        out.append(row)
    return out


def cmd_diff(a):
    ra, rb = _prep(a.a, a.b)
    ov = Image.blend(ra, rb, 0.5)
    w, h = ra.size
    panel = Image.new("RGB", (w * 3 + 16, h), (20, 20, 20))
    panel.paste(ra, (0, 0))
    panel.paste(rb, (w + 8, 0))
    panel.paste(ov, (w * 2 + 16, 0))
    d = ImageDraw.Draw(panel)
    d.text((6, 6), "RENDER", fill=(255, 255, 0))
    d.text((w + 14, 6), "REFERENCE", fill=(255, 255, 0))
    d.text((w * 2 + 22, 6), "OVERLAY 50/50", fill=(255, 255, 0))
    s = ssim(ra, rb, a.ssim_size)
    table = cell_table(ra, rb, a.grid)
    print("SSIM %.4f  (1.0 identical, >0.75 close massing, <0.55 different layout)" % s)
    print("per-cell mean |dRGB| (%dx%d grid, rows top->bottom):" % (a.grid, a.grid))
    for row in table:
        print("  " + "  ".join("%5.1f" % v for v in row))
    worst = max((v, gy, gx) for gy, row in enumerate(table) for gx, v in enumerate(row))
    print("worst cell: row %d col %d  delta %.1f" % (worst[1], worst[2], worst[0]))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    panel.save(a.out)
    print("wrote", a.out)


def cmd_overlay(a):
    ra, rb = _prep(a.a, a.b)
    Image.blend(ra, rb, a.alpha).save(a.out)
    print("wrote", a.out)


def cmd_side(a):
    ra, rb = _prep(a.a, a.b)
    w, h = ra.size
    panel = Image.new("RGB", (w * 2 + 8, h), (20, 20, 20))
    panel.paste(ra, (0, 0))
    panel.paste(rb, (w + 8, 0))
    panel.save(a.out)
    print("wrote", a.out)


def main(argv):
    p = argparse.ArgumentParser(description="reference vs render comparison")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("diff")
    s.add_argument("a"); s.add_argument("b"); s.add_argument("--out", required=True)
    s.add_argument("--grid", type=int, default=3); s.add_argument("--ssim-size", type=int, default=256)
    s.set_defaults(fn=cmd_diff)

    s = sub.add_parser("overlay")
    s.add_argument("a"); s.add_argument("b"); s.add_argument("--out", required=True); s.add_argument("--alpha", type=float, default=0.5)
    s.set_defaults(fn=cmd_overlay)

    s = sub.add_parser("side")
    s.add_argument("a"); s.add_argument("b"); s.add_argument("--out", required=True)
    s.set_defaults(fn=cmd_side)

    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main(sys.argv[1:])
