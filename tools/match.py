"""match.py - catalogue matcher for reference-image elements (v2).

What it fixes over v1
  * CamelCase names were treated as one token ("TellerDesk"), so "teller desk" never matched.
    Names are now split into words before scoring.
  * Plurals and gerunds are handled ("cases" -> "case", "shelves" -> "shelf").
  * Domain synonyms via specs/reference/lexicon.json ("counter" -> teller desk, "safe" ->
    safe deposit, "ac" -> aircon, "sofa" -> couch, ...).
  * Category is inferred from the query and used as a scoring signal (not just a filter).
  * Material class filters (glass / emissive / sign) and collider requirements (--solid).
  * Scored confidence with explicit bands (strong / weak / none) and ambiguity reporting
    when the top two candidates are within 0.04.
  * Explainable scoring (--explain) with per-term IDF contribution.
  * Decision cache (specs/reference/match_cache.json) so a reviewed mapping is stable.
  * Built-in regression suite (subcommand "test") driven by specs/reference/match_tests.json.

Subcommands
  query   "<text>" [--min W,D,H] [--max W,D,H] [--category C] [--material glass]
                   [--solid] [--top 6] [--json] [--explain] [--rotate]
  sheet   <ref.json> [--write] [--force] [--refresh] [--no-cache]
  test    [--verbose]

Sizes are metres, reported W x D x H (catalogue bounds x/z/y).
"""

import argparse
import hashlib
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "specs", "heist-catalog.json")
LEXICON = os.path.join(ROOT, "specs", "reference", "lexicon.json")
CACHE = os.path.join(ROOT, "specs", "reference", "match_cache.json")
TESTS = os.path.join(ROOT, "specs", "reference", "match_tests.json")

STOP = set("the a an of for and with to in on at is are be this that any some sm prop env item".split())
IRREGULAR = {"shelves": "shelf", "knives": "knife", "wolves": "wolf", "halves": "half"}
STRONG = 0.72
WEAK = 0.45
AMBIG_GAP = 0.04


# ----------------------------------------------------------------------------- text
def camel_split(s):
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s)
    s = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", s)
    return s


def forms(word):
    """Small set of normalised forms so plural/gerund variants still match."""
    w = word.lower()
    out = {w}
    if w in IRREGULAR:
        out.add(IRREGULAR[w])
        return out
    if len(w) > 4 and w.endswith("ies"):
        out.add(w[:-3] + "y")
    if len(w) > 4 and w.endswith("ves"):
        out.add(w[:-3] + "f")
        out.add(w[:-3] + "fe")
    if len(w) > 3 and w.endswith("es"):
        out.add(w[:-1])
        out.add(w[:-2])
    elif len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        out.add(w[:-1])
    if len(w) > 5 and w.endswith("ing"):
        out.add(w[:-3])
    if len(w) > 4 and w.endswith("ed"):
        out.add(w[:-2])
    return out


def tokens(text):
    text = camel_split(text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    out = []
    for raw in text.split():
        w = raw.lower()
        if not w or w in STOP:
            continue
        if w.isdigit():
            continue
        out.append(w)
    return out


def load_lexicon():
    if os.path.exists(LEXICON):
        with open(LEXICON, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return {"aliases": {}, "categories": {}, "material_classes": {}}


def expand(qtok, lex):
    """Return (expanded_token_set, hints) where hints are category/material words."""
    out = set(qtok)
    hints = {"category": None, "material": None}
    for t in list(out):
        for alt in lex.get("aliases", {}).get(t, []):
            out.add(alt)
        if t in lex.get("categories", {}) and hints["category"] is None:
            hints["category"] = lex["categories"][t]
        if t in lex.get("material_classes", {}) and hints["material"] is None:
            hints["material"] = lex["material_classes"][t]
    return out, hints


# ----------------------------------------------------------------------------- catalog
def load_catalog():
    with open(CATALOG, "r", encoding="utf-8") as fh:
        d = json.load(fh)
    rows = d["entries"] if isinstance(d, dict) and "entries" in d else d
    out = []
    for e in rows:
        b = e["bounds"]
        size = [b["max"][0] - b["min"][0], b["max"][2] - b["min"][2], b["max"][1] - b["min"][1]]
        name = e["name"]
        toks = set()
        for t in tokens(name):
            toks |= forms(t)
        out.append({
            "name": name,
            "path": e["path"],
            "category": e.get("category", ""),
            "size": size,
            "material": e.get("material", "") or "",
            "collider": (e.get("collider") or {}).get("type", "") or "",
            "tokens": toks,
        })
    return out


def build_idf(cat):
    df = {}
    for e in cat:
        for t in e["tokens"]:
            df[t] = df.get(t, 0) + 1
    n = float(len(cat))
    return {t: math.log((n + 1.0) / (c + 1.0)) + 1.0 for t, c in df.items()}


def match_terms(qtokens, entry_tokens):
    """How many query tokens hit the entry, and the summed query-side IDF weight."""
    hits = []
    for qt in qtokens:
        qf = forms(qt)
        if qf & entry_tokens:
            hits.append(qt)
            continue
        # containment credit: partial word (e.g. "trolley" vs "vaulttrolley")
        if any(qt in et or et in qt for et in entry_tokens if len(et) > 3 and len(qt) > 3):
            hits.append(qt)
    return hits


def envelope(size, lo, hi):
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
    return min(pen, 3.0), ", ".join(notes)


def rank(query, lo=None, hi=None, category=None, top=6, catalog=None, idf=None,
         material=None, solid=False, no_collider=False, rotate=False, lex=None):
    catalog = catalog or load_catalog()
    idf = idf or build_idf(catalog)
    lex = lex or load_lexicon()
    qtok = tokens(query)
    exp, hints = expand(qtok, lex)
    if category is None:
        category = hints["category"]
    if material is None:
        material = hints["material"]

    qweight = sum(idf.get(t, 1.0) for t in exp) or 1.0
    known = [t for t in exp if t in idf]
    # Only raw query words that are neither in the catalogue nor covered by an alias
    # count as unmatched modifiers ("marble"); alias bridges ("counter") do not.
    unknown_tokens = [t for t in qtok if t not in idf and not lex.get("aliases", {}).get(t)]
    scored = []
    for e in catalog:
        if lo is not None and hi is not None and rotate:
            size = [e["size"][1], e["size"][0], e["size"][2]]
        else:
            size = e["size"]
        hits = match_terms(known, e["tokens"])
        if not hits:
            continue
        matched_w = sum(idf.get(t, 1.0) for t in hits)
        known_w = sum(idf.get(t, 1.0) for t in known)
        denom = known_w + 0.6 * len(unknown_tokens)
        name = (matched_w / denom) ** 1.25 if denom > 0 else 0.0
        cat = 1.0 if not category else (1.0 if e["category"].lower() == category.lower() else 0.0)
        pen, note = envelope(size, lo, hi)
        fit = 1.0 - min(1.0, pen)
        mat = 1.0
        if material:
            mat = 1.0 if material.lower() in e["material"].lower() else 0.0
        col = 1.0
        if solid:
            col = 1.0 if e["collider"] and e["collider"].lower() != "none" else 0.0
        if no_collider:
            col = 1.0 if (not e["collider"] or e["collider"].lower() == "none") else 0.0
        # specificity: entries carrying words the query never asked for rank slightly lower
        qforms = set()
        for t in exp:
            qforms |= forms(t)
        extra = len([t for t in e["tokens"] if t not in qforms])
        spec = 1.0 / (1.0 + 0.05 * extra)
        conf = (0.66 * name + 0.12 * cat + 0.12 * fit + 0.10 * mat) * spec
        if unknown_tokens:
            conf *= 1.0 / (1.0 + 0.40 * len(unknown_tokens))
        # head noun gate: if the thing being asked for (last word) is not resolved by this
        # entry - directly or through an alias - the candidate is not the object wanted.
        head = qtok[-1] if qtok else ""
        if head and head not in hits:
            alts = lex.get("aliases", {}).get(head, [])
            if not any(a in hits for a in alts):
                conf *= 0.30
        if col == 0.0:
            conf *= 0.45
        conf = round(max(0.0, min(1.0, conf)), 3)
        note_txt = note or "fits"
        if unknown_tokens:
            note_txt = (note_txt + "; unmatched: " + ", ".join(unknown_tokens)).strip("; ")
        scored.append({
            "name": e["name"], "category": e["category"], "size": e["size"],
            "material": e["material"], "collider": e["collider"],
            "confidence": conf, "band": band(conf),
            "name_score": round(name, 3), "cat_score": cat,
            "fit": round(fit, 3), "material_score": mat, "collider_ok": col == 1.0,
            "hits": sorted(set(hits)), "note": note_txt, "ambiguous": False,
        })
    scored.sort(key=lambda r: -r["confidence"])
    if len(scored) >= 2 and (scored[0]["confidence"] - scored[1]["confidence"]) < AMBIG_GAP:
        scored[0]["ambiguous"] = True
        scored[0]["note"] = (scored[0]["note"] + "; ambiguous with " + scored[1]["name"]).strip("; ")
    return (scored[:top], {"query": query, "expanded": sorted(exp), "category": category,
                           "material": material})


def band(conf):
    if conf >= STRONG:
        return "strong"
    if conf >= WEAK:
        return "weak"
    return "none"


def fmt(size):
    return "%.2f x %.2f x %.2f" % (size[0], size[1], size[2])


# ----------------------------------------------------------------------------- cache
def load_cache(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except ValueError:
            return {}
    return {}


def cache_key(query, lo, hi, category, material, solid, no_collider, rotate):
    blob = json.dumps([query, lo, hi, category, material, solid, no_collider, rotate], sort_keys=True)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


def save_cache(path, cache):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, indent=2, sort_keys=True)


# ----------------------------------------------------------------------------- commands
def cmd_query(a):
    lo = [float(v) for v in a.min.split(",")] if a.min else None
    hi = [float(v) for v in a.max.split(",")] if a.max else None
    for v in (lo, hi):
        if v and len(v) != 3:
            raise SystemExit("--min/--max need W,D,H")
    res, meta = rank(a.text, lo, hi, a.category, a.top, material=a.material,
                     solid=a.solid, no_collider=a.no_collider, rotate=a.rotate)
    if a.json:
        print(json.dumps({"meta": meta, "results": res}, indent=2))
        return
    print("query: %r" % a.text)
    print("  expanded: %s" % ", ".join(meta["expanded"]))
    print("  envelope: %s .. %s   category: %s   material: %s"
          % (fmt(lo) if lo else "any", fmt(hi) if hi else "any",
             meta["category"] or "any", meta["material"] or "any"))
    if not res:
        print("NO-MATCH  nothing in the catalogue matches %r" % a.text)
        return
    print("%-38s %-12s %-20s %5s %-7s %s"
          % ("prefab", "category", "size WxDxH", "conf", "band", "note"))
    for r in res:
        print("%-38s %-12s %-20s %5.2f %-7s %s"
              % (r["name"], r["category"], fmt(r["size"]), r["confidence"], r["band"], r["note"]))
        if a.explain:
            print("      name %.2f  cat %.2f  fit %.2f  mat %.2f  collider %s  hits: %s"
                  % (r["name_score"], r["cat_score"], r["fit"], r["material_score"],
                     "ok" if r["collider_ok"] else "MISS", ", ".join(r["hits"])))


def cmd_sheet(a):
    with open(a.ref, "r", encoding="utf-8") as fh:
        ref = json.load(fh)
    cat = load_catalog()
    idf = build_idf(cat)
    lex = load_lexicon()
    cache = {} if a.no_cache else load_cache(CACHE)
    changed = 0
    usage = {}
    problems = []
    for el in ref.get("elements", []):
        if el.get("prefab") and not a.force:
            continue
        lo = el.get("size_min")
        hi = el.get("size_max")
        q = el.get("label", "") or el.get("type", "") or ""
        key = cache_key(q, lo, hi, el.get("category"), el.get("material"),
                        bool(el.get("solid")), bool(el.get("no_collider")), bool(el.get("rotate")))
        if key in cache and not a.refresh:
            pick = cache[key]
            el["prefab"] = pick["name"]
            el["match"] = pick["match"]
            el["match_confidence"] = pick["confidence"]
            el["match_note"] = pick.get("note", "cached")
            print("%-6s %-26s CACHE -> %-32s %s (%.2f)"
                  % (el.get("id", "?"), q[:26], pick["name"], pick["match"], pick["confidence"]))
            changed += 1
            usage[pick["name"]] = usage.get(pick["name"], 0) + int(el.get("qty", 1) or 1)
            continue
        res, meta = rank(q, lo, hi, el.get("category"), 4, cat, idf, lex=lex,
                         material=el.get("material"), solid=bool(el.get("solid")),
                         no_collider=bool(el.get("no_collider")), rotate=bool(el.get("rotate")))
        if not res:
            print("%-6s %-26s NO-MATCH" % (el.get("id", "?"), q[:26]))
            el["match"] = "none"
            el["match_confidence"] = 0.0
            el["match_note"] = "no catalogue candidate"
            problems.append("%s: no match for %r" % (el.get("id", "?"), q))
            changed += 1
            continue
        best = res[0]
        if best["confidence"] < WEAK:
            print("%-6s %-26s NO-MATCH (best %s %.2f)"
                  % (el.get("id", "?"), q[:26], best["name"], best["confidence"]))
            el["match"] = "none"
            el["match_confidence"] = best["confidence"]
            el["match_note"] = best["note"]
            el.pop("prefab", None)
            el["alternatives"] = [r["name"] for r in res[:3]]
            problems.append("%s: no usable match for %r (best %s %.2f)"
                            % (el.get("id", "?"), q, best["name"], best["confidence"]))
            changed += 1
            continue
        state = "exact" if best["confidence"] >= 0.80 and best["fit"] >= 0.999 else "approx"
        el["prefab"] = best["name"]
        el["match"] = state
        el["match_confidence"] = best["confidence"]
        el["match_note"] = best["note"]
        el["alternatives"] = [r["name"] for r in res[1:3]]
        changed += 1
        usage[best["name"]] = usage.get(best["name"], 0) + int(el.get("qty", 1) or 1)
        print("%-6s %-26s -> %-32s %-6s %.2f  %s"
              % (el.get("id", "?"), q[:26], best["name"], state, best["confidence"], best["note"]))
        for alt in res[1:3]:
            print("        alt %-32s %.2f  %s" % (alt["name"], alt["confidence"], alt["note"]))
        if best["ambiguous"]:
            problems.append("%s: ambiguous (%s vs %s)" % (el.get("id", "?"), best["name"], res[1]["name"]))
        if state == "none":
            problems.append("%s: weak match %.2f %s" % (el.get("id", "?"), best["confidence"], best["name"]))
        cache[key] = {"name": best["name"], "confidence": best["confidence"],
                      "match": state, "note": best["note"]}

    if changed:
        print("\nusage:")
        for name, n in sorted(usage.items(), key=lambda kv: -kv[1]):
            print("  %-38s x%d" % (name, n))
            if n >= 4:
                print("      note: heavy reuse - consider a variant for readability")
        if problems:
            print("\nreview:")
            for p in problems:
                print("  - " + p)
    if a.write and changed:
        with open(a.ref, "w", encoding="utf-8") as fh:
            json.dump(ref, fh, indent=2)
        if not a.no_cache:
            save_cache(CACHE, cache)
        print("\nwrote %s with %d matches (cache %s)" % (a.ref, changed, CACHE))


def cmd_test(a):
    if not os.path.exists(TESTS):
        raise SystemExit("no test file at " + TESTS)
    with open(TESTS, "r", encoding="utf-8") as fh:
        cases = json.load(fh)
    cat = load_catalog()
    idf = build_idf(cat)
    lex = load_lexicon()
    passed = failed = 0
    for c in cases:
        lo = c.get("min")
        hi = c.get("max")
        res, meta = rank(c["query"], lo, hi, c.get("category"), c.get("top", 3), cat, idf,
                         lex=lex, material=c.get("material"), solid=bool(c.get("solid")),
                         rotate=bool(c.get("rotate")))
        names = [r["name"] for r in res]
        if c.get("expect_none"):
            ok = not res or res[0]["confidence"] < WEAK
            detail = "NO-MATCH" if ok else ("unexpected " + names[0])
        else:
            ok = any(n in c["expect"] for n in names[:c.get("top", 3)])
            detail = ", ".join("%s %.2f" % (r["name"], r["confidence"]) for r in res[:3]) or "none"
            cap = c.get("expect_max_conf")
            if ok and cap is not None and res and res[0]["confidence"] > cap:
                ok = False
                detail += " (confidence %.2f > cap %.2f)" % (res[0]["confidence"], cap)
        if ok:
            passed += 1
            print("PASS  %-34s %s" % (c["query"][:34], detail if a.verbose else ""))
        else:
            failed += 1
            print("FAIL  %-34s expect %s | got %s"
                  % (c["query"][:34], c.get("expect") or "NO-MATCH", detail))
    print("\n%d passed, %d failed, %d cases" % (passed, failed, len(cases)))
    if failed:
        sys.exit(1)


def main(argv):
    p = argparse.ArgumentParser(description="catalogue matcher for reference elements")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("query")
    s.add_argument("text")
    s.add_argument("--min")
    s.add_argument("--max")
    s.add_argument("--category")
    s.add_argument("--material")
    s.add_argument("--solid", action="store_true")
    s.add_argument("--no-collider", action="store_true")
    s.add_argument("--rotate", action="store_true")
    s.add_argument("--top", type=int, default=6)
    s.add_argument("--json", action="store_true")
    s.add_argument("--explain", action="store_true")
    s.set_defaults(fn=cmd_query)

    s = sub.add_parser("sheet")
    s.add_argument("ref")
    s.add_argument("--write", action="store_true")
    s.add_argument("--force", action="store_true")
    s.add_argument("--refresh", action="store_true")
    s.add_argument("--no-cache", action="store_true")
    s.set_defaults(fn=cmd_sheet)

    s = sub.add_parser("test")
    s.add_argument("--verbose", action="store_true")
    s.set_defaults(fn=cmd_test)

    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main(sys.argv[1:])
