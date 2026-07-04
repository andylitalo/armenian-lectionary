"""Resolve a date's saint via the Tonatsoyts Second Volume cycle, and measure it
against ground truth.

Chain (all calendar-independent for post-Easter days):
    civil year -> Gregorian Easter date
              -> Second Volume cycle whose Easter matches (second_volume_index.csv)
              -> that cycle's calendar entry for the date's (month, day).

Why matching by Easter DATE works across calendars: Easter is always a Sunday, so the
Easter date fixes the weekday of every other date in the year (given leap parity). A
Gregorian year with Gregorian Easter on April 20 therefore has the SAME post-Feb-29
weekday structure as the cycle whose (Julian) Easter is April 20 -- so the floating
saints land on the same civil dates. (Pre-Easter / January dates additionally need leap
parity; not yet handled here.)

Result (2014-2026 floating-saint days; see __main__): the engine's best guess is WRONG
on 19/22; where the matched cycle lists the date explicitly it matches ground truth on
8/11. The remaining 11 are deferred -- the saint is cross-referenced to another letter
(preface point 2) or sits outside the parser's page range. Saint identity -> readings is
already a lookup in dev/saint_readings.json, so a validated cycle saint yields readings.
"""
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
TR = os.path.expanduser("~/church/grabar-ocr/runs/human__proj__tess__gemini-min/"
                        "translations/gemini-flash/translated.md")
MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], 1)}


def _index():
    rows = [r for r in csv.DictReader(open(INDEX, encoding="utf-8")) if r["page"]]
    by_easter = {r["easter_md_julian"]: r for r in rows}
    pages = sorted(int(r["page"]) for r in rows)
    return by_easter, pages


def cycle_entry(d, by_easter, pages):
    """The Second-Volume cycle calendar line for date d (or None if not listed)."""
    e = L.calculate_gregorian_easter(d.year)
    row = by_easter.get(f"{e.month:02d}-{e.day:02d}")
    if not row:
        return None, None
    p0 = int(row["page"])
    p1 = min([q for q in pages if q > p0], default=p0 + 3)
    cur = month = None
    for ln in open(TR, encoding="utf-8"):
        s = ln.strip()
        pm = re.match(r"## page_(\d+)", s)
        if pm:
            cur = int(pm.group(1))
            continue
        if cur is None or not (p0 <= cur < p1):
            continue
        mm = re.match(r"(?:In )?([A-Z][a-z]+):?$", s)
        if mm and mm.group(1) in MONTHS:
            month = MONTHS[mm.group(1)]
            continue
        dm = re.match(r"(\d{1,2})\.\s", s)
        if dm and month == d.month and int(dm.group(1)) == d.day:
            return row, s
    return row, None


def _gt(d):
    p = os.path.join(HERE, "reference_data", f"{d.isoformat()}.json")
    if not os.path.exists(p):
        return None
    j = json.load(open(p))
    return j.get("feast") or j.get("Liturgical Day") or ""


def _norm(t):
    t = re.sub(r"\[Note:[^\]]*\]", " ", t or "")
    t = t.lower().replace("ph", "f").replace("ios", "ius").replace("ie", "ia").replace("y", "i")
    t = t.replace("anthoni", "anton")   # Anthony/Anton translit unify
    return set(re.findall(r"[a-z]{4,}", t)) - {
        "saint", "saints", "holy", "bishop", "virgin", "feast", "tone", "sunday",
        "monday", "tuesday", "thursday", "others", "their", "general", "martyrs",
        "hermit", "hermits", "father", "mother", "canticle"}


def measure():
    by_easter, pages = _index()
    days = []
    for y in range(2014, 2027):
        d = datetime.date(y, 1, 1)
        while d.year == y:
            if L.compute_armenian_lectionary(d)["Source"] == "generative-saint":
                days.append(d)
            d += datetime.timedelta(days=1)
    match = differ = defer = eng_wrong = 0
    for d in days:
        row, entry = cycle_entry(d, by_easter, pages)
        g = _gt(d)
        if g and _norm(L.compute_armenian_lectionary(d)["Liturgical Day"]).isdisjoint(_norm(g)):
            eng_wrong += 1
        if entry is None:
            defer += 1
        elif g and _norm(entry) & _norm(g):
            match += 1
        else:
            differ += 1
    print(f"floating-saint days: {len(days)}")
    print(f"  engine guess WRONG vs ground truth: {eng_wrong}")
    print(f"  cycle entry matches ground truth:   {match}")
    print(f"  cycle entry differs:                {differ}")
    print(f"  deferred (cross-ref / out of range): {defer}")


if __name__ == "__main__":
    measure()
