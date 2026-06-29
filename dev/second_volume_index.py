"""Maintain docs/sources/second_volume_index.csv -- the map from each Second-Volume
"Roman cycle" section to the Tonatsoyts calendar-letter (Taregir) it belongs to.

Why this file exists
--------------------
The Second Volume is organised as one day-by-day calendar per year-type (calendar
letter). To wire it into the engine we must know WHICH letter each printed section is.
The section headers in the OCR are sparse/garbled, so the *printed* Armenian letter
must be verified by a human against the page scans. This tool:

  * `scaffold` -- (re)derives the machine-knowable columns (page, header text, the
    Easter date stated inside the section, and the Taregir that Julian Easter implies)
    from the translation, WITHOUT clobbering the human-verified columns.
  * `validate` -- for every row whose `letter_printed` is filled in, checks it agrees
    with `taregir_inferred`; prints mismatches (the same closed-form cross-check that
    caught the 2034 error in great_paschal_cycle_index.csv).

Source of truth: docs/sources/second_volume_index.csv. Humans edit ONLY the
`letter_printed`, `verified`, and `notes` columns; the rest are regenerated.

Verify the printed letter against the PAGE SCAN (the `page` column), not the English
translation (which is regenerable OCR). The grabar `merged.md` section header is a
secondary check.
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

ALPHA = "ԱԲԳԴԵԶԷԸԹԺԻԼԽԾԿՀՁՂՃՄՅՆՇՈՉՊՋՌՍՎՏՐՑՒՓ"
MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], 1)}
_HDR = re.compile(r"(CYCLE OF THE ROMANS|ROMAN.*CYCLE|YEARLY LETTER|ROMAN CALENDAR|"
                  r"ROMAN.*WEEKS|Roman.*Cycle|Roman Weekly|Roman Calendar)", re.I)
FIELDS = ["page", "header", "easter_md_inferred", "taregir_inferred",
          "letter_printed", "verified", "notes"]


def _taregir(month, day):
    k = (datetime.date(2001, month, day) - datetime.date(2001, 3, 21)).days
    return ALPHA[k - 1] if 1 <= k <= 35 else ""


def _parse_sections():
    page = month = None
    sections, cur = [], None
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
            cur = {"page": page, "header": s, "easter_md_inferred": ""}
            sections.append(cur)
            month = None
        if cur and not cur["easter_md_inferred"] and re.search(
                r"\bEaster\b|Resurrection of Christ", s, re.I):
            dm = re.match(r"(\d+)\.", s)
            if dm and month in (3, 4):
                cur["easter_md_inferred"] = f"{month:02d}-{int(dm.group(1)):02d}"
    for sec in sections:
        e = sec["easter_md_inferred"]
        sec["taregir_inferred"] = _taregir(*map(int, e.split("-"))) if e else ""
    return sections


def _load_existing():
    if not os.path.exists(CSV_PATH):
        return {}
    out = {}
    with open(CSV_PATH, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[(r["page"], r["header"])] = {k: r.get(k, "") for k in
                                             ("letter_printed", "verified", "notes")}
    return out


def scaffold():
    keep = _load_existing()
    secs = _parse_sections()
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for sec in secs:
            human = keep.get((str(sec["page"]), sec["header"]), {})
            w.writerow({**sec, **human})
    print(f"wrote {len(secs)} sections to {CSV_PATH} "
          f"(preserved {sum(1 for v in keep.values() if v.get('letter_printed'))} verified)")


def validate():
    bad = 0
    with open(CSV_PATH, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            lp, ti = r["letter_printed"].strip(), r["taregir_inferred"].strip()
            if lp and ti and lp != ti:
                bad += 1
                print(f"  MISMATCH p{r['page']}: printed {lp!r} vs Easter-inferred "
                      f"{ti!r} (Easter {r['easter_md_inferred']}) -- {r['header'][:40]}")
    print(f"validate: {bad} mismatch(es) between letter_printed and Easter-inferred Taregir")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "scaffold"
    {"scaffold": scaffold, "validate": validate}[cmd]()
