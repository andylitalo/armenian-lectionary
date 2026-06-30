"""Maintain docs/sources/second_volume_index.csv -- one row per Tonatsoyts calendar
letter (Ա..Ք, 36) mapping that year-type to its Second-Volume "Roman cycle" section.

Row identity = the calendar letter and its Julian Easter date (`easter_md_julian`),
derived closed-form from the paschal-table convention validated 171/171 in
great_paschal_cycle_index (Ա = Mar 22 ... Փ = Apr 25). Detected Second-Volume sections
are attached to a row by MATCHING THAT EASTER DATE -- not by the printed header letter,
because the printed labels may be offset from the paschal convention (e.g. p557's
Mar-22 section is headed `Գ`, which is `Ա`'s date here). That offset is the thing to
resolve during verification; until then, attaching by Easter is convention-independent.

Humans fill `letter_printed` (the glyph printed at the section head, read from the PAGE
SCAN -- not the regenerable translation), `verified`, and `notes`. The tool fills
`taregir`, `easter_md_julian`, and -- where a section's Easter matches -- `page`/`header`.

  scaffold  (re)build the 36 rows, preserving human columns (merge-safe by taregir)
  validate  for rows with letter_printed set, report where it != taregir
            (a CONSISTENT offset across rows reveals the labeling convention)
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

# Classical Armenian alphabet, 36 letters Ա..Ք (the year-letter range).
ALPHA = "ԱԲԳԴԵԶԷԸԹԺԻԼԽԾԿՀՁՂՃՄՅՆՇՈՉՊՋՌՍՎՏՐՑՒՓՔ"
MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], 1)}
_HDR = re.compile(r"(CYCLE OF THE ROMANS|ROMAN.*CYCLE|YEARLY LETTER|ROMAN CALENDAR|"
                  r"ROMAN.*WEEKS|Roman.*Cycle|Roman Weekly|Roman Calendar)", re.I)
FIELDS = ["taregir", "easter_md_julian", "page", "header",
          "letter_printed", "verified", "notes"]
HUMAN = ("letter_printed", "verified", "notes")


def _easter_md(pos):
    """Julian Easter (MM-DD) for letter position pos (1..35); '' beyond the range."""
    if not 1 <= pos <= 35:           # Julian Easter spans only Mar 22..Apr 25 (35 days)
        return ""
    d = datetime.date(2001, 3, 21) + datetime.timedelta(days=pos)
    return f"{d.month:02d}-{d.day:02d}"


def _detect():
    """{easter_md -> (page, header)} for sections whose own Easter line we can read."""
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
            cur = {"page": page, "header": s, "done": False}
            month = None
        if cur and not cur["done"] and re.search(
                r"\bEaster\b|Resurrection of Christ", s, re.I):
            dm = re.match(r"(\d+)\.", s)
            if dm and month in (3, 4):
                md = f"{month:02d}-{int(dm.group(1)):02d}"
                out.setdefault(md, (cur["page"], cur["header"]))
                cur["done"] = True
    return out


def _load_human():
    if not os.path.exists(CSV_PATH):
        return {}
    with open(CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows or "taregir" not in rows[0]:
        return {}                                  # old/foreign format: nothing to keep
    return {r["taregir"]: {k: r.get(k, "") for k in HUMAN} for r in rows}


def scaffold():
    keep = _load_human()
    det = _detect()
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for i, letter in enumerate(ALPHA, 1):
            md = _easter_md(i)
            page, header = det.get(md, ("", ""))
            row = {"taregir": letter, "easter_md_julian": md,
                   "page": page, "header": header,
                   **{k: "" for k in HUMAN}}
            row.update(keep.get(letter, {}))
            w.writerow(row)
    n_sec = sum(1 for L in ALPHA if _easter_md(ALPHA.index(L) + 1) in det)
    print(f"wrote 36 letter rows; attached {n_sec} detected sections; "
          f"preserved {sum(1 for v in keep.values() if v.get('letter_printed'))} verified")


def validate():
    bad = 0
    with open(CSV_PATH, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            lp = r["letter_printed"].strip()
            if lp and lp != r["taregir"]:
                bad += 1
                off = (ALPHA.find(lp) - ALPHA.find(r["taregir"]))
                print(f"  {r['taregir']} (Easter {r['easter_md_julian']}, p{r['page']}): "
                      f"printed {lp!r}  offset {off:+d}")
    print(f"validate: {bad} row(s) where printed letter != row taregir "
          f"(a constant offset = the convention shift)")


if __name__ == "__main__":
    {"scaffold": scaffold, "validate": validate}.get(
        sys.argv[1] if len(sys.argv) > 1 else "scaffold", scaffold)()
