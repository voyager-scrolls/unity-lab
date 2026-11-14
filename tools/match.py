"""match.py - match described reference elements against the prop catalogue.

Scores each catalog entry on:
  * name-token overlap with the query (word stems, fuzzy contains)
  * category hint (Props / Environment / Items / Weapons / Characters / Vehicles / FX / Masks)
  * size envelope fitness (each axis must sit inside [min,max] with a tolerance)
A candidate outside the envelope is shown but marked OVERSIZE/UNDERSIZE, never silently used.

Subcommands
  query   "<text>" [--min W,D,H] [--max W,D,H] [--category Props] [--top 6]
  sheet   <ref.json> [--write]     match every element without a prefab; --write stores picks

Sizes are metres, catalog order is (x, z, y) = (width, depth, height) from bounds.

Examples
  py -3 tools/match.py query "jewellery display case" --min 2.0,0.4,0.8 --max 3.0,0.8,1.4
  py -3 tools/match.py query "marble column" --category Props --top 4
  py -3 tools/match.py sheet specs/reference/bank_scene.json --write
"""

import argparse
import json
import math
import os
import re
import sys

CATALOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "specs", "heist-catalog.json")

STOP = set("the a an of for and with to in on at is are be this that".split())


def load_catalog():
    with open(CATALOG, "r", encoding="utf-8") as fh:
        d = json.load(fh)
    rows = d["entries"] if isinstance(d, dict) and "entries" in d else d
    out = []
    for e in rows:
        b = e["bounds"]
        size = [b["max"][0] - b["min"][0], b["max"][2] - b["min"][2], b["max"][1] - b["min"][1]]
        out.append({
            "name": e["name"],
            "path": e["path"],
            "category": e.get("category", ""),
            "size": size,
            "material": e.get("material", ""),
            "collider": (e.get("collider") or {}).get("type", ""),
        })
    return out


def tokens(text):
    t = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return [w for w in t.split() if w and w not in STOP]


def name_score(qtok, name):
    nt = set(tokens(name.replace("SM_", " ").replace("Prop", " ").replace("Env", " ")))
    if not qtok:
        return 0.0
    hit = sum(1 for w in qtok if any(w in n or n in w for n in nt))
    return hit / float(len(qtok))


def envelope(size, lo, hi):
    """Return (penalty, note). Penalty 0 = inside; higher = further out."""
    if lo is None or hi is None:
        return 0.0, ""
    pen = 0.0
    notes = []
    for i, axis in enumerate("WDH"):
        s = size[i]
        if s < lo[i]:
            pen += (lo[i] - s) / max(lo[i], 0.05)
            notes.append("%s short %.2f" % (axis, lo[i] - s))
        if s > hi[i]:
            pen += (s - hi[i]) / max(hi[i], 0.05)
            notes.append("%s over %.2f" % (axis, s - hi[i]))
    return pen, ", ".join(notes)


def rank(query, lo=None, hi=None, category=None, top=6, catalog=None):
    catalog = catalog or load_catalog()
    qtok = tokens(query)
    scored = []
    for e in catalog:
        if category and e["category"].lower() != category.lower():
            continue
        ns = name_score(qtok, e["name"])
        if ns <= 0:
            continue
        pen, note = envelope(e["size"], lo, hi)
        score = ns * 5.0 - pen * 2.0
        scored.append((score, ns, pen, note, e))
    scored.sort(key=lambda t: -t[0])
    return scored[:top]


def fmt(size):
    return "%.2f x %.2f x %.2f" % (size[0], size[1], size[2])


def cmd_query(a):
    lo = [float(v) for v in a.min.split(",")] if a.min else None
    hi = [float(v) for v in a.max.split(",")] if a.max else None
    for v in (lo, hi):
        if v and len(v) != 3:
            raise SystemExit("--min/--max need W,D,H")
    res = rank(a.text, lo, hi, a.category, a.top)
    if not res:
        print("NO-MATCH  nothing in the catalogue matches %r" % a.text)
        return
    print("query: %r   envelope: %s .. %s   category: %s"
          % (a.text, fmt(lo) if lo else "any", fmt(hi) if hi else "any", a.category or "any"))
    print("%-38s %-12s %-22s %6s  %s" % ("prefab", "category", "size WxDxH", "score", "note"))
    for score, ns, pen, note, e in res:
        print("%-38s %-12s %-22s %6.2f  %s" % (e["name"], e["category"], fmt(e["size"]), score, note or "fits"))


def cmd_sheet(a):
    with open(a.ref, "r", encoding="utf-8") as fh:
        ref = json.load(fh)
    cat = load_catalog()
    changed = 0
    for el in ref.get("elements", []):
        if el.get("prefab") and not a.force:
            continue
        lo = el.get("size_min")
        hi = el.get("size_max")
        res = rank(el.get("label", ""), lo, hi, el.get("category"), 3, cat)
        if not res:
            print("%-6s %-28s NO-MATCH" % (el.get("id", "?"), el.get("label", "")))
            el["match"] = "none"
            continue
        score, ns, pen, note, e = res[0]
        el["prefab"] = e["name"]
        el["match"] = "exact" if pen == 0 and ns >= 0.99 else ("approx" if pen < 0.6 else "none")
        el["match_note"] = note or "fits"
        changed += 1
        print("%-6s %-28s -> %-34s %s  (%.2f)" % (el.get("id", "?"), el.get("label", ""), e["name"], el["match"], score))
        for alt in res[1:]:
            print("        alt: %-34s %s" % (alt[4]["name"], alt[3] or "fits"))
    if a.write and changed:
        with open(a.ref, "w", encoding="utf-8") as fh:
            json.dump(ref, fh, indent=2)
        print("wrote", a.ref, "with", changed, "matches")


def main(argv):
    p = argparse.ArgumentParser(description="catalogue matcher for reference elements")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("query")
    s.add_argument("text"); s.add_argument("--min"); s.add_argument("--max")
    s.add_argument("--category"); s.add_argument("--top", type=int, default=6)
    s.set_defaults(fn=cmd_query)

    s = sub.add_parser("sheet")
    s.add_argument("ref"); s.add_argument("--write", action="store_true"); s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_sheet)

    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main(sys.argv[1:])
