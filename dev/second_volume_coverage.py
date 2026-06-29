"""Measure how many of the engine's NON-validated days have their feast/saint named
in the Տօնացոյց Second Volume (the per-year-type "Roman cycle" calendars).

This quantifies whether the Second Volume carries the information needed to lift the
engine's residual best-guess / estimate days (chiefly the floating-saint ceiling) to
validated. It does NOT itself resolve them -- that needs the section->calendar-letter
index (docs/sources/second_volume_index.csv) plus a Julian->Gregorian laydown -- but it
bounds the achievable gain.

Run: armenian_lectionary/venv/bin/python dev/second_volume_coverage.py
"""
import datetime
import re
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lectionary as L  # noqa: E402

# Second Volume English translation (human-corrected OCR run). Adjust if relocated.
SECOND_VOLUME = os.path.expanduser(
    "~/church/grabar-ocr/runs/human__proj__tess__gemini-min/"
    "translations/gemini-flash/translated.md")

# generic words that are not saint identities
_STOP = set(
    "saints saint the holy of and her his father mother bishop patriarch virgin "
    "commemoration hermit hermits martyr martyrs general fathers participating in "
    "ecumenical council eve fast feast day sons thunder soldier deacon king".split())


def _keys(feast: str):
    return [t for t in re.findall(r"[A-Za-z]+", feast.lower())
            if t not in _STOP and len(t) > 3]


def main(start=2014, end=2026):
    sv = open(SECOND_VOLUME, encoding="utf-8").read().lower()
    rows = []
    for y in range(start, end + 1):
        d = datetime.date(y, 1, 1)
        while d.year == y:
            r = L.compute_armenian_lectionary(d)
            if r["Source"] not in ("validated-table", "validated-composite"):
                rows.append((d, r["Source"], r["Liturgical Day"]))
            d += datetime.timedelta(days=1)

    by_src = collections.Counter(s for _, s, _ in rows)
    saint_total = saint_named = 0
    unmatched = []
    for d, s, feast in rows:
        hits = [k for k in _keys(feast) if k in sv]
        is_saint = (s == "generative-saint") or bool(hits)
        if is_saint:
            saint_total += 1
            if hits:
                saint_named += 1
            else:
                unmatched.append((d, s, feast))

    print(f"Non-validated days {start}-{end}: {len(rows)}")
    for s, n in by_src.most_common():
        print(f"  {s:22} {n}")
    print(f"\nSaint-bearing non-validated days: {saint_total}")
    print(f"  named in Second Volume: {saint_named}")
    print(f"  NOT named (out of SV scope -- e.g. fast continua): "
          f"{len(rows) - saint_total} non-saint + {saint_total - saint_named} saint")
    floating = [r for r in rows if r[1] == "generative-saint"]
    fl_named = sum(1 for d, s, f in floating if any(k in sv for k in _keys(f)))
    print(f"\nFloating-saint block (generative-saint): {fl_named}/{len(floating)} named")
    if unmatched:
        print("\nUnmatched saint days:")
        for d, s, f in unmatched:
            print(f"  {d} {s} {f}")


if __name__ == "__main__":
    main()
