"""refimg.py - reference-image inspection for stage reconstruction.

Subcommands
  info     <img>                          size, mode, aspect
  crop     <img> <out> --box x0,y0,x1,y1  native-resolution crop (pixels or fractions)
  zoom     <img> <out> --box ... --scale N  crop and upscale with NEAREST/LANCZOS
  palette  <img> [--k 8] [--out strip.png] dominant colours + share, mapped to material class
  annotate <img> <out> --points "1:x,y;2:x,y"   numbered markers for element discussion

Coordinates are pixels unless --frac is passed (0..1 fractions of width/height).

Usage examples
  py -3 tools/refimg.py info "C:/Users/ABCD/Downloads/Bank_robbery_map_scene_74c35317_2K.jpg"
  py -3 tools/refimg.py palette <img> --k 8 --out builds/ref/palette.png
  py -3 tools/refimg.py crop <img> builds/ref/crop1.png --frac 0.1,0.1,0.5,0.5 --scale 2
"""

import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont


def _box(value, frac, w, h):
    parts = [float(p) for p in value.split(",")]
    if len(parts) != 4:
        raise SystemExit("--box needs four values x0,y0,x1,y1")
    if frac:
        parts = [parts[0] * w, parts[1] * h, parts[2] * w, parts[3] * h]
    x0, y0, x1, y1 = [int(round(v)) for v in parts]
    x0, x1 = sorted((max(0, x0), min(w, x1)))
    y0, y1 = sorted((max(0, y0), min(h, y1)))
    if x1 - x0 < 2 or y1 - y0 < 2:
        raise SystemExit("empty crop box")
    return x0, y0, x1, y1


def cmd_info(a):
    im = Image.open(a.img)
    print("path :", a.img)
    print("size : %d x %d" % im.size)
    print("mode :", im.mode)
    print("aspect: %.3f" % (im.size[0] / float(im.size[1])))
    try:
        print("frames:", getattr(im, "n_frames", 1))
    except Exception:
        pass


def _save_crop(a, upscale=False):
    im = Image.open(a.img).convert("RGB")
    box = _box(a.box, a.frac, im.size[0], im.size[1])
    crop = im.crop(box)
    if upscale and a.scale > 1:
        crop = crop.resize((crop.size[0] * a.scale, crop.size[1] * a.scale), Image.LANCZOS)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    crop.save(a.out)
    print("wrote %s  box=%s  size=%dx%d" % (a.out, box, crop.size[0], crop.size[1]))


def _classify(rgb):
    r, g, b = [c / 255.0 for c in rgb]
    mx, mn = max(r, g, b), min(r, g, b)
    sat = 0.0 if mx == 0 else (mx - mn) / mx
    val = mx
    if sat < 0.08:
        return "neutral/stone" if val > 0.35 else "tactical black"
    if val < 0.22:
        return "tactical black"
    if r > g > b and r - b > 0.25:
        return "warm stone/brick" if val > 0.45 else "dark timber"
    if r > 0.55 and g > 0.42 and b < 0.35:
        return "brass/gold"
    if b >= r and b >= g and sat > 0.12:
        return "glass/steel blue"
    if g > r and g > b:
        return "foliage/emissive green"
    return "mixed"


def cmd_palette(a):
    im = Image.open(a.img).convert("RGB")
    small = im.copy()
    small.thumbnail((640, 640), Image.LANCZOS)
    q = small.quantize(colors=max(2, a.k), method=Image.MEDIANCUT).convert("RGB")
    counts = {}
    for px in q.getdata():
        counts[px] = counts.get(px, 0) + 1
    total = float(sum(counts.values()))
    ordered = sorted(counts.items(), key=lambda kv: -kv[1])
    print("dominant colours (k=%d, sample %dx%d):" % (a.k, small.size[0], small.size[1]))
    for rgb, n in ordered:
        share = 100.0 * n / total
        print("  #%02X%02X%02X  %5.1f%%  %s" % (rgb[0], rgb[1], rgb[2], share, _classify(rgb)))
    if a.out:
        sw = 120
        strip = Image.new("RGB", (sw * len(ordered), sw + 26), (24, 24, 24))
        d = ImageDraw.Draw(strip)
        for i, (rgb, n) in enumerate(ordered):
            strip.paste(Image.new("RGB", (sw, sw), rgb), (i * sw, 0))
            d.text((i * sw + 4, sw + 6), "#%02X%02X%02X" % rgb, fill=(230, 230, 230))
        os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
        strip.save(a.out)
        print("wrote", a.out)


def cmd_annotate(a):
    im = Image.open(a.img).convert("RGB")
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("arial.ttf", max(14, im.size[0] // 60))
    except Exception:
        font = ImageFont.load_default()
    n = 0
    for chunk in a.points.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        label, xy = chunk.split(":")
        x, y = [float(v) for v in xy.split(",")]
        if a.frac:
            x, y = x * im.size[0], y * im.size[1]
        r = max(8, im.size[0] // 120)
        d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 40, 40), width=3)
        d.text((x + r + 4, y - r), label, fill=(255, 220, 60), font=font)
        n += 1
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    im.save(a.out)
    print("wrote %s with %d markers" % (a.out, n))


def main(argv):
    p = argparse.ArgumentParser(description="reference-image inspection")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("info"); s.add_argument("img"); s.set_defaults(fn=cmd_info)

    s = sub.add_parser("crop")
    s.add_argument("img"); s.add_argument("out")
    s.add_argument("--box", required=True); s.add_argument("--frac", action="store_true"); s.add_argument("--scale", type=int, default=1)
    s.set_defaults(fn=lambda a: _save_crop(a, False))

    s = sub.add_parser("zoom")
    s.add_argument("img"); s.add_argument("out")
    s.add_argument("--box", required=True); s.add_argument("--frac", action="store_true"); s.add_argument("--scale", type=int, default=2)
    s.set_defaults(fn=lambda a: _save_crop(a, True))

    s = sub.add_parser("palette")
    s.add_argument("img"); s.add_argument("--k", type=int, default=8); s.add_argument("--out")
    s.set_defaults(fn=cmd_palette)

    s = sub.add_parser("annotate")
    s.add_argument("img"); s.add_argument("out"); s.add_argument("--points", required=True); s.add_argument("--frac", action="store_true")
    s.set_defaults(fn=cmd_annotate)

    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main(sys.argv[1:])
