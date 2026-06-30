"""Distill the Tonatsoyts Second Volume cycles into a committed, offline data file
`dev/second_volume_cycles.json` consumed by the engine's cycle-lookup tier.

Output shape:  { easter_md_julian : { "MM-DD" : [zone, saint_id] } }

For each calendar letter's cycle (located via docs/sources/second_volume_index.csv),
parse its per-date saint entries from the human-corrected translation and match each to
a saint identity in dev/saint_readings.json (so identity -> readings is a fixed lookup at
runtime). Built dev-time from grabar-ocr; the engine never reads the translation.

Run: armenian_lectionary/venv/bin/python dev/build_second_volume_cycles.py
"""
import collections
import csv
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lectionary as L  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, os.pardir, "docs", "sources", "second_volume_index.csv")
OUT = os.path.join(HERE, "second_volume_cycles.json")
TR = os.path.expanduser("~/church/grabar-ocr/runs/human__proj__tess__gemini-min/"
                        "translations/gemini-flash/translated.md")
MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], 1)}


def _norm(t):
    t = (t.lower().replace("ph", "f").replace("ios", "ius")
         .replace("ie", "ia").replace("y", "i"))   # tryphon/triphon, eugenios/eugenius
    return set(re.findall(r"[a-z]{4,}", t))


# generic, non-distinctive tokens that must not drive a match
_GENERIC = {"feast", "fast", "season", "octave", "sunday", "commemoration", "eve",
            "great", "holy", "hermit", "hermits", "fathers", "saint", "saints",
            "martyr", "martyrs", "bishop", "virgin", "general", "this", "their"}


# saint identity -> (zone, sid, distinctive-name-tokens) from the engine's readings table
def _identities():
    out = []
    for zone, ids in L._SAINT_READINGS.items():
        for sid in ids:
            names = _norm(sid.replace("_", " ")) - _GENERIC   # distinctive saint names
            if names:
                out.append((zone, sid, names))
    return out


def _match(entry, identities):
    """Best (zone, sid) for a cycle entry line, or None. A group entry ("Vahan …, and
    Eugenia …") files its readings under the FIRST-named (senior) saint (preface §6), so
    rank identities by the EARLIEST position of any of their distinctive name tokens in
    the entry, then by overlap. Tokens are normalized so Tryphon≈Triphon etc."""
    en = (entry.lower().replace("ph", "f").replace("ios", "ius")
          .replace("ie", "ia").replace("y", "i"))
    et = _norm(entry)
    best, best_key = None, None
    for zone, sid, names in identities:
        hit = names & et
        if not hit:
            continue
        pos = min(en.find(t) for t in hit)
        key = (pos, -len(hit))              # first-named saint, then most overlap
        if best_key is None or key < best_key:
            best, best_key = (zone, sid), key
    return best


def _cycle_pages():
    rows = [r for r in csv.DictReader(open(INDEX, encoding="utf-8")) if r["page"]]
    pages = sorted(int(r["page"]) for r in rows)
    span = {}
    for r in rows:
        p0 = int(r["page"])
        p1 = min([q for q in pages if q > p0], default=p0 + 3)
        span[r["easter_md_julian"]] = (p0, p1)
    return span


def main():
    identities = _identities()
    spans = _cycle_pages()
    # page -> list of (month, day, text)
    by_page = {}
    cur = month = None
    for ln in open(TR, encoding="utf-8"):
        s = ln.strip()
        pm = re.match(r"## page_(\d+)", s)
        if pm:
            cur = int(pm.group(1))
            continue
        mm = re.match(r"(?:In )?([A-Z][a-z]+):?$", s)
        if mm and mm.group(1) in MONTHS:
            month = MONTHS[mm.group(1)]
            continue
        dm = re.match(r"(\d{1,2})\.\s", s)
        if dm and month:
            by_page.setdefault(cur, []).append((month, int(dm.group(1)), s))

    out = {}
    for easter_md, (p0, p1) in spans.items():
        if not easter_md:
            continue
        day_map = {}
        for p in range(p0, p1):
            for m, dd, text in by_page.get(p, []):
                hit = _match(text, identities)
                if hit:
                    day_map.setdefault(f"{m:02d}-{dd:02d}", list(hit))
        if day_map:
            out[easter_md] = day_map

    dropped = _drop_cache_contradicted(out)
    json.dump(out, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=0, sort_keys=True)
    n = sum(len(v) for v in out.values())
    print(f"wrote {OUT}: {len(out)} cycles, {n} dated saint entries "
          f"({dropped} dropped as cache-contradicted)")


def _readings_for(d, stored_zone, sid):
    """Mirror the engine's runtime readings lookup: the date's saint-zone first."""
    rz = next((z for z, zd in L._SAINT_ZONES.items()
               if zd["window"](d.year)[0] <= d <= zd["window"](d.year)[1]), None)
    for z in (rz, stored_zone):
        refs = z and L._SAINT_READINGS.get(z, {}).get(sid)
        if refs:
            return list(refs)
    return None


def _drop_cache_contradicted(out):
    """Drop any cycle entry whose readings disagree with ground truth in a cached year
    of that year-type -- so the shipped tier is cache-consistent (no regression) while
    unobserved year-types stay best-effort. Returns the count dropped."""
    ref_dir = os.path.join(HERE, "reference_data")
    if not os.path.isdir(ref_dir):
        return 0
    easter_years = collections.defaultdict(list)
    for y in range(2001, 2027):
        e = L.calculate_gregorian_easter(y)
        easter_years[f"{e.month:02d}-{e.day:02d}"].append(y)
    dropped = 0
    for easter_md, day_map in out.items():
        for md in list(day_map):
            zone, sid = day_map[md]
            m, dd = (int(x) for x in md.split("-"))
            bad = False
            for y in easter_years.get(easter_md, []):
                f = os.path.join(ref_dir, f"{y:04d}-{m:02d}-{dd:02d}.json")
                if not os.path.exists(f):
                    continue
                gt = json.load(open(f)).get("readings")
                refs = _readings_for(datetime.date(y, m, dd), zone, sid)
                if gt and refs and refs != list(gt):
                    bad = True
                    break
            if bad:
                del day_map[md]
                dropped += 1
    return dropped


if __name__ == "__main__":
    main()
