#!/usr/bin/env python3
"""Top-down + front-elevation QA render of the bank shell only.

Usage: py -3 specs/render_shell.py [layout.json] [out.png]
Draws wall/frame/ceiling/light props from heist-catalog.json; ignores everything else.
"""

import json
import math
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYOUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "specs", "city-bank-v2.json")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "builds", "shell-qa.png")

WALLS = ("SM_Env_Wall_Exterior_01", "SM_Env_Wall_Interior_01")
FRAME = "SM_Env_VaultDoor_Frame_01"
CEIL = "SM_Env_Ceiling_01"
LIGHT = "SM_Env_Ceiling_Light_01"
ROOMS = ("lobby", "teller", "vault", "corridorL", "corridorR")

SCALE = 30
PAD = 40


def short(p):
    return p.replace("\\", "/").rsplit("/", 1)[-1].replace(".prefab", "")


def rect(cat, p):
    b = cat[short(p["prefab"])]["bounds"]
    yaw = int(round(p["rotation"][1])) % 360
    xs = (b["min"][0], b["max"][0])
    zs = (b["min"][2], b["max"][2])
    pts = []
    for x in xs:
        for z in zs:
            if yaw == 0:
                pts.append((x, z))
            elif yaw == 90:
                pts.append((z, -x))
            elif yaw == 180:
                pts.append((-x, -z))
            else:
                pts.append((-z, x))
    px, _, pz = p["position"]
    return (px + min(q[0] for q in pts), px + max(q[0] for q in pts),
            pz + min(q[1] for q in pts), pz + max(q[1] for q in pts))


def main():
    data = json.load(open(LAYOUT, encoding="utf-8"))
    cat = {e["name"]: e for e in json.load(open(os.path.join(ROOT, "specs", "heist-catalog.json"), encoding="utf-8"))}

    props = []
    for room in data["rooms"]:
        for p in room.get("props") or []:
            n = short(p["prefab"])
            if n in WALLS or n == FRAME or n == CEIL or n == LIGHT:
                props.append((room["id"], n, p))

    xmin, xmax, zmin, zmax = -16.0, 16.0, -4.0, 23.0
    W = int((xmax - xmin) * SCALE) + PAD * 2
    H = int((zmax - zmin) * SCALE) + PAD * 2 + 260
    img = Image.new("RGB", (W, H), (245, 245, 242))
    d = ImageDraw.Draw(img)

    def X(x):
        return PAD + (x - xmin) * SCALE

    def Y(z):
        return PAD + (z - zmin) * SCALE

    # room fills
    colors = {"lobby": (255, 246, 220), "teller": (222, 240, 252), "vault": (252, 224, 224),
              "corridorL": (226, 246, 226), "corridorR": (238, 228, 250), "exterior": (232, 232, 232)}
    for room in data["rooms"]:
        if room["id"] not in ROOMS:
            continue
        b = room["bounds"]
        d.rectangle([X(b["min"][0]), Y(b["min"][2]), X(b["max"][0]), Y(b["max"][2])],
                    fill=colors.get(room["id"], (240, 240, 240)), outline=(120, 120, 120))
        d.text((X(b["min"][0]) + 4, Y(b["min"][2]) + 4), room["id"], fill=(60, 60, 60))

    # ceilings: light fill with grid outline
    for _, n, p in props:
        if n != CEIL:
            continue
        x0, x1, z0, z1 = rect(cat, p)
        d.rectangle([X(x0), Y(z0), X(x1), Y(z1)], fill=(214, 222, 228), outline=(160, 170, 180))
        d.text((X(x0) + 3, Y(z0) + 3), "C%.1f" % p["position"][1], fill=(90, 100, 110))

    # walls and frame on top
    for _, n, p in props:
        if n not in WALLS and n != FRAME:
            continue
        x0, x1, z0, z1 = rect(cat, p)
        if n == FRAME:
            fill, outline = (220, 60, 60), (120, 0, 0)
        elif n == "SM_Env_Wall_Interior_01":
            fill, outline = (70, 90, 150), (30, 40, 90)
        else:
            fill, outline = (55, 55, 55), (0, 0, 0)
        d.rectangle([X(x0), Y(z0), X(x1), Y(z1)], fill=fill, outline=outline)

    # lights
    for _, n, p in props:
        if n != LIGHT:
            continue
        x, y, z = p["position"]
        r = 4
        d.ellipse([X(x) - r, Y(z) - r, X(x) + r, Y(z) + r], fill=(255, 190, 0), outline=(120, 80, 0))

    d.text((PAD, 8), "TOP-DOWN  grey=exterior wall  blue=interior wall  red=vault frame  "
                     "light-grey=ceiling  yellow=light", fill=(20, 20, 20))

    # front elevation strip: x vs y at z<0.3
    ey0 = H - 250
    ey1 = H - 40
    def EYy(y):
        return ey1 - y * (ey1 - ey0) / 12.2

    d.rectangle([X(xmin), ey0, X(xmax), ey1], outline=(150, 150, 150))
    d.text((PAD, ey0 - 18), "FRONT ELEVATION (walls at z<0.3, y 0..12)", fill=(20, 20, 20))
    for _, n, p in props:
        if n not in WALLS:
            continue
        x0, x1, z0, z1 = rect(cat, p)
        if z0 > 0.3:
            continue
        y0 = p["position"][1]
        y1 = y0 + 3.0
        d.rectangle([X(x0), EYy(y1), X(x1), EYy(y0)],
                    fill=(60, 60, 60) if n == "SM_Env_Wall_Exterior_01" else (70, 90, 150),
                    outline=(0, 0, 0))
    for y in (0, 3, 6, 9, 12):
        d.text((X(xmin) - 30, EYy(y) - 6), "%d" % y, fill=(60, 60, 60))
        d.line([X(xmin), EYy(y), X(xmax), EYy(y)], fill=(220, 220, 220))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.save(OUT)
    print("WROTE " + OUT)


if __name__ == "__main__":
    main()
