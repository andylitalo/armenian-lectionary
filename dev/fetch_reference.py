"""DEV-ONLY ground-truth fetcher for sacredtradition.am.

NOT imported by the app at runtime. Used purely to build a local reference
dataset of (date -> feast name + reading references) so we can reverse-engineer
and validate the offline algorithm in ../lectionary.py.

Caches each day as JSON under dev/reference_data/ to avoid re-fetching.

Usage:
    python dev/fetch_reference.py 2026-06-01            # one day
    python dev/fetch_reference.py 2026-06-01 2026-06-30 # inclusive range
"""

import datetime
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dev.source_corrections import normalize_confusables  # noqa: E402

CACHE_DIR = os.path.join(os.path.dirname(__file__), "reference_data")
URL = ("https://www.sacredtradition.am/Calendar/nter.php"
       "?NM=0&iM=1103&iA=0&iL=2&ymd={ymd}")


# Separator joining the <br>-delimited components the source packs into one field
# (position label, commemoration, eve/status note). Must match the engine's join
# convention (armenian_lectionary.engine._FEAST_SEP) so the shipped table and the
# reference cache carry component boundaries identically.
FEAST_SEP = " — "


def _strip(s: str) -> str:
    import html as _html
    # Preserve component boundaries before deleting tags: the previous version mapped
    # <br> to "" (re.sub of every tag), silently mashing the components together. Map
    # <br> to a sentinel first, drop the remaining tags, then rejoin on FEAST_SEP.
    s = re.sub(r"\s*<br\s*/?>\s*", "\x00", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = _html.unescape(s)
    # The source occasionally types English feast text with Cyrillic homoglyphs
    # (Cyrillic Е/о); fold them to Latin at ingestion so the whole pipeline stays clean.
    s = normalize_confusables(s)
    parts = [p.strip() for p in s.split("\x00") if p.strip()]
    return FEAST_SEP.join(parts)


def fetch_day(d: datetime.date, force: bool = False) -> dict:
    """Return {date, weekday, feast, readings:[refs]} for a day, using cache."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, d.isoformat() + ".json")
    if os.path.exists(path) and not force:
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    url = URL.format(ymd=d.strftime("%Y%m%d"))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="replace")

    dsound = re.search(r"<div class=dsound>(.*?)</div>", raw, re.S)
    dname = re.search(r"<div class=dname>(.*?)</div>", raw, re.S)
    # Reading references are the <b>...</b> headers in the body. Filter to ones
    # that look like scripture citations (contain a chapter.verse number).
    refs = [_strip(m) for m in re.findall(r"<b>(.*?)</b>", raw, re.S)]
    refs = [r for r in refs if re.search(r"\d+\.\d", r)]

    data = {
        "date": d.isoformat(),
        "weekday": d.strftime("%A"),
        "feast": _strip(dname.group(1)) if dname else "",
        "date_label": _strip(dsound.group(1)) if dsound else "",
        "readings": refs,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def main(argv):
    if not argv:
        print(__doc__)
        return
    start = datetime.date.fromisoformat(argv[0])
    end = datetime.date.fromisoformat(argv[1]) if len(argv) > 1 else start
    d = start
    while d <= end:
        data = fetch_day(d)
        cached = os.path.exists(os.path.join(CACHE_DIR, d.isoformat() + ".json"))
        print(f"{data['date']} {data['weekday']:9} | {data['feast']}")
        for r in data["readings"]:
            print(f"    {r}")
        if not cached:
            time.sleep(0.5)  # be polite to the server
        d += datetime.timedelta(days=1)


if __name__ == "__main__":
    main(sys.argv[1:])
