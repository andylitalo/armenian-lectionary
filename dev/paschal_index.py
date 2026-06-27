"""Decoder / validator for the Տօնացոյց Great Paschal Cycle index
(`docs/sources/great_paschal_cycle_index.csv`).

What the table is
-----------------
A perpetual (532-year) index from the Տօնացոյց's appendix. For each civil year it
gives two Armenian-letter codes:

* **Veradir** (Վերադիր, "epact") — the lunar position in the 19-year Metonic cycle.
  Purely periodic with period 19; fully determined by ``(year - 1909) % 19``.
* **Taregir** (Տարեգիր, "year-letter" / Dominical letter) — decoded below.

Key finding: the Taregir is an **Armenian-alphabet code for the JULIAN-calendar
Easter date**. Letter position k (Ա=1 … Փ=35) == Julian Easter on (March 21 + k):

    Ա→Mar22  Բ→Mar23  Գ→Mar24 … Ժ→Mar31  Ի→Apr1 … Փ→Apr25

i.e. the 35 possible Julian Easter dates in order. Leap years carry **two** letters;
the *second* is the Easter-date code, the first is the bissextile/solar (weekday)
adjustment. This is verified against the OCR'd CSV: 170 / 171 years agree with the
closed-form ``taregir_for`` below; the lone exception (2034, CSV ``Ջ`` vs computed
``Զ``) is a transcription error — independently confirmed because 2062 (also ``Ջ``)
has Julian Easter Apr 17, the true ``Ջ`` date.

Consequence for the engine (Julian vs Gregorian)
------------------------------------------------
The Taregir tracks **Orthodox/Julian** Easter, while the engine (and
sacredtradition.am) target **Gregorian** Easter — so same-Taregir years can have
different Gregorian Easters and the Taregir is NOT a usable Gregorian year-key.

BUT the lectionary splits cleanly:
  * MOVABLE propers are indexed by **Easter-OFFSET** (days from Easter) and are
    CALENDAR-INDEPENDENT — "Easter-40" is the same liturgical day with the same
    readings in either reckoning. The engine already keys these (``E``/``EB``).
  * FIXED feasts (civil dates) and their COLLISIONS with movable days are
    calendar-specific (the canon rules in ``docs/sources/``).

So a *Julian* source of movable propers (the Տօնացոյց's per-letter "Second Volume"),
re-indexed by Easter-offset via this decoder, transfers to the *Gregorian* engine for
free — the practical route to fill the Easter-offsets the Gregorian cache
under-samples (the single-sample 2008 / 2011 ceiling) without more Gregorian data.
"""
from __future__ import annotations

import csv
import datetime
import os

# Armenian alphabet, in order; position k (1-based) == Julian Easter on Mar 21 + k.
ALPHA = "ԱԲԳԴԵԶԷԸԹԺԻԼԽԾԿՀՁՂՃՄՅՆՇՈՉՊՋՌՍՎՏՐՑՒՓ"

CSV_PATH = os.path.join(os.path.dirname(__file__), os.pardir,
                        "docs", "sources", "great_paschal_cycle_index.csv")


def julian_easter(year: int) -> datetime.date:
    """Easter in the JULIAN calendar (Meeus's Julian algorithm), returned as a
    `date` whose (month, day) are the Julian-calendar values."""
    a, b, c = year % 4, year % 7, year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    f = d + e + 114
    return datetime.date(year, f // 31, f % 31 + 1)


def julian_easter_gregorian(year: int) -> datetime.date:
    """The Julian (Orthodox) Easter expressed as the equivalent GREGORIAN date
    (valid 1900-2099, where the Julian-Gregorian gap is 13 days)."""
    return julian_easter(year) + datetime.timedelta(days=13)


def taregir_for(year: int) -> str:
    """The Easter-date Taregir letter for `year` (the second letter in leap years),
    computed from the Julian Easter date — a closed form for the whole table."""
    k = (julian_easter(year) - datetime.date(year, 3, 21)).days
    return ALPHA[k - 1]


def validate_csv(path: str = CSV_PATH):
    """Compare the closed-form Taregir against the OCR'd CSV; return list of
    (year, csv_taregir, csv_easter_letter, expected_letter) mismatches."""
    mism = []
    with open(path, encoding="utf-8") as f:
        next(f)
        for row in csv.reader(f):
            if not row or not row[0].strip():
                continue
            year, tar = int(row[0]), row[1].strip()
            exp = taregir_for(year)
            if tar[-1] != exp:                       # leap: 2nd letter is the code
                mism.append((year, tar, tar[-1], exp))
    return mism


if __name__ == "__main__":
    bad = validate_csv()
    n = sum(1 for _ in open(CSV_PATH, encoding="utf-8")) - 1
    print(f"validated {n} years; {len(bad)} mismatch(es)")
    for year, tar, got, exp in bad:
        je = julian_easter_gregorian(year)
        print(f"  {year}: CSV {tar!r} (last {got!r}) vs computed {exp!r} "
              f"[Julian Easter = {je:%b %d} Gregorian]")
