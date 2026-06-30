"""Maintain docs/sources/second_volume_index.csv -- one row per Tonatsoyts calendar
letter (Ա..Ք, 36), mapping that year-type to its Second-Volume cycle.

Columns
-------
  taregir           the calendar letter (row key), Ա..Ք
  easter_md_julian  the Julian Easter date that letter encodes (Ա=Mar22 .. Փ=Apr25)
  page              page where that letter's Second-Volume section begins
  cycle             the "Cycle of the Romans" number printed in the section heading

The heading printed at each section is **ԵՕԹՆԵՐԵԱԿ ՀՌՈՄԱՅԵՑՒՈՑ #** ("Septenary of the
Romans #"); the English OCR renders the word inconsistently as "Seven-year / Seven-day /
Seven-week cycle of the Romans". The number # runs **1..7 descending** as the letter
advances, so it is a closed form of the letter position:

    cycle(pos) = ((11 - pos) % 7) + 1          # anchored Ի(pos 11) = 1

verified against every printed heading Ա..Ի (4,3,2,1,7,6,5,4,3,2,1) and Ծ,Կ,Ճ,Մ.

  scaffold  rebuild the 36 rows; cycle = closed form; page preserved from the existing
            CSV (curated by hand), else filled from the translation by Easter match.
  validate  for each row with a page, parse that page's printed cycle number from the
            translation and flag where it != the row's cycle (= a misattached page).
"""
import csv
import datetime
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, os.pardir, "docs", "sources",
                        "second_volume_index.csv")
TRANSLATION = os.path.expanduser(
    "~/church/grabar-ocr/runs/human__proj__tess__gemini-min/"
    "translations/gemini-flash/translated.md")

ALPHA = "ԱԲԳԴԵԶԷԸԹԺԻԼԽԾԿՀՁՂՃՄՅՆՇՈՉՊՋՌՍՎՏՐՑՒՓՔ"   # 36 letters
MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], 1)}
_HDR = re.compile(r"CYCLE OF THE ROMANS|ROMAN.*CYCLE|ROMAN CALENDAR|ROMAN.*WEEKS|"
                  r"Roman.*Cycle|Roman Weekly|Roman Calendar", re.I)
FIELDS = ["taregir", "easter_md_julian", "page", "cycle"]


def cycle_for(pos):                       # pos is 1-based letter index
    return ((11 - pos) % 7) + 1


def easter_md(pos):
    if not 1 <= pos <= 35:                # Julian Easter spans Mar 22..Apr 25 only
        return ""
    d = datetime.date(2001, 3, 21) + datetime.timedelta(days=pos)
    return f"{d.month:02d}-{d.day:02d}"


def _detect_pages_by_easter():
    """{easter_md -> page} from sections whose own Easter line is on the page."""
    page = month = None
    out, cur = {}, None
    for ln in open(TRANSLATION, encoding="utf-8"):
        s = ln.strip()
        pm = re.match(r"## page_(\d+)", s)
        if pm:
            page = int(pm.group(1))
            continue
        mm = re.match(r"(?:In )?([A-Z][a-z]+):?$", s)
        if mm and mm.group(1) in MONTHS:
            month = MONTHS[mm.group(1)]
        if _HDR.search(s) and len(s) < 70:
            cur = page
            month = None
        if cur and re.search(r"\bEaster\b|Resurrection of Christ", s, re.I):
            dm = re.match(r"(\d+)\.", s)
            if dm and month in (3, 4):
                out.setdefault(f"{month:02d}-{int(dm.group(1)):02d}", cur)
                cur = None
    return out


def _existing_pages():
    if not os.path.exists(CSV_PATH):
        return {}
    with open(CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if rows and "taregir" in rows[0]:
        return {r["taregir"]: r.get("page", "") for r in rows}
    return {}


def scaffold():
    keep = _existing_pages()
    det = _detect_pages_by_easter()
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for i, letter in enumerate(ALPHA, 1):
            md = easter_md(i)
            page = keep.get(letter) or det.get(md, "")
            w.writerow({"taregir": letter, "easter_md_julian": md,
                        "page": page, "cycle": cycle_for(i)})
    print("wrote 36 letter rows (cycle = closed form; pages preserved)")


def _printed_cycle_by_page():
    page, out = None, {}
    for ln in open(TRANSLATION, encoding="utf-8"):
        s = ln.strip()
        pm = re.match(r"## page_(\d+)", s)
        if pm:
            page = int(pm.group(1))
        elif _HDR.search(s) and len(s) < 70:
            m = re.search(r"\b([1-7])\b", s)
            if m and page not in out:
                out[page] = int(m.group(1))
    return out


def validate():
    printed = _printed_cycle_by_page()
    bad = 0
    with open(CSV_PATH, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r["page"]:
                continue
            p = int(r["page"])
            if p in printed and printed[p] != int(r["cycle"]):
                bad += 1
                print(f"  {r['taregir']} p{p}: row cycle {r['cycle']} but page "
                      f"heading prints cycle {printed[p]} -> page likely misattached")
    print(f"validate: {bad} page/cycle mismatch(es)")


if __name__ == "__main__":
    {"scaffold": scaffold, "validate": validate}.get(
        sys.argv[1] if len(sys.argv) > 1 else "scaffold", scaffold)()
