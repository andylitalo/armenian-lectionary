"""DEV-ONLY: write one TSV per year listing what every day of it is called, and by which id.

The catalog id is what a consumer is meant to store instead of display text
(CLAUDE.md, "Observance ids are stated, not derived"), and the id is invisible in the
current payload -- ``Liturgical Day`` is prose, and nothing published shows which id
produced which words. That is fine while the ids are ours; it stops being fine the moment
they are exposed as a key downstream, because a wrong id is then a wrong row forever, and
the only way to notice is to read them.

So this is a reviewing artifact, not a build input: nothing at runtime loads it, and the
engine does not change if it is deleted. Its whole job is to put a year on one page, in the
shape the id contract actually has --

    the ids of a day, in order, positionally aligned with the words they stand for

-- so a reader can check a name against its id by looking straight down the row, and check
a year's shape (which days carry two or three observances, where a fast starts, when a
saint moves) by looking down the column.

Both name columns are joined on ``_OBSERVANCE_SEP``, exactly as the engine serves them, and
the ``observance_ids`` column is joined on the same separator rather than a comma -- not
because an id list has a separator (it does not; it is a list, and section 7's rule is that
a day is identified by the whole ordered list) but so the k-th id sits under the k-th name
when the file is read as a table.

**Resolution is all-or-nothing**, the same rule ``ObservanceIds`` will apply: a day with any
unresolvable component raises rather than writing a row with a hole in it, because a partial
id list is not a key -- it silently identifies a different observance. A year that writes at
all is a year in which every component resolved.

Usage:
    python dev/observance_year_table.py 2026 2027           # print a summary
    python dev/observance_year_table.py 2026 2027 --write   # write docs/observance-names-<year>.tsv
"""

import csv
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary import engine                                 # noqa: E402
from armenian_lectionary.engine import (                               # noqa: E402
    _OBSERVANCE_SEP, compute_armenian_lectionary,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(REPO_ROOT, "docs")

COLUMNS = ("date", "weekday", "season", "source", "observances", "observance_ids",
           "en", "hy")


def observance_ids(label):
    """The stable catalog id of each component of ``label``, in order.

    Resolved through the same reverse index ``language="hy"`` goes through, from the
    ENGLISH text, so the ids are by construction the ones the Armenian was keyed on.
    """
    catalog = engine._OBSERVANCE_CATALOG
    ids = []
    for part in label.split(_OBSERVANCE_SEP):
        sid = catalog.id_of(part)
        if sid is None:
            raise KeyError(f"no catalog id for served component {part!r}")
        ids.append(sid)
    return ids


def rows_for_year(year):
    """One row per day of ``year``, in date order."""
    rows = []
    d = datetime.date(year, 1, 1)
    while d.year == year:
        en = compute_armenian_lectionary(d)
        hy = compute_armenian_lectionary(d, language="hy")
        ids = observance_ids(en["Liturgical Day"])
        rows.append({
            "date": d.isoformat(),
            "weekday": d.strftime("%a"),
            "season": en["Season"],
            "source": en["Source"],
            "observances": len(ids),
            "observance_ids": _OBSERVANCE_SEP.join(ids),
            "en": en["Liturgical Day"],
            "hy": hy["Liturgical Day"],
        })
        d += datetime.timedelta(days=1)
    return rows


def write_year(year, rows):
    path = os.path.join(DOCS_DIR, f"observance-names-{year}.tsv")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, delimiter="\t",
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path


def main():
    years = [int(a) for a in sys.argv[1:] if not a.startswith("-")]
    if not years:
        print(__doc__.strip().splitlines()[-1])
        return 2
    write = "--write" in sys.argv
    for year in years:
        rows = rows_for_year(year)
        distinct = len({sid for row in rows for sid in row["observance_ids"].split(_OBSERVANCE_SEP)})
        multi = sum(1 for row in rows if row["observances"] > 1)
        print(f"{year}: {len(rows)} days, {distinct} distinct observance ids, "
              f"{multi} days naming more than one")
        if write:
            print(f"  wrote {os.path.relpath(write_year(year, rows), REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
