"""DEV-ONLY: freeze ``dev/feast_name_review.tsv`` into ``dev/feast_name_ground_truth.json``,
the reviewed English name for every feast-name component the engine can serve.

Why a separate file from the TSV. The TSV is a *working* document -- it carries review
bookkeeping (``days``, ``last``, ``status``) that exists to help a human decide what to
approve, and drifts every time the cache is refreshed. Once a component is approved, only
one fact about it still matters going forward: what English text it should serve. This
file is that fact, keyed the same way the correction machinery already keys corrections --
by the exact raw ``source`` string -- so it drops straight into
``dev.source_corrections`` (see ``_GROUND_TRUTH_FIXES`` there) without another layer of
lookup logic.

Why keyed by component text, not by date. A misspelled saint's name is a property of the
component ("Saints Gayiane and her companions"), not of any particular day it is served on
-- the same component recurs on ~20 different calendar dates across 2001-2027 for a fixed
feast, or on one date a year for a movable one. A date-keyed table would need ~9,500 rows
(one per served day) nearly all repeating the same handful of distinct strings, and
-- unlike this file -- would say nothing about *why* a name reads the way it does. The
engine has no per-date name lookup to begin with; it assembles a day's name from components
via ``_FEAST_SEP``, so a fix must be expressed at the same granularity to compose correctly
with a day the review process has never seen (2027, or a future re-fetched year).

Each entry:
    id          the observance's frozen catalog id, or "" for a row that is not a single
                served observance (a whole day, or a minority spelling the engine overrides)
    approved_en the reviewed English text the engine should serve for this component
    status      ok | fixed | review -- review means the note asks an unresolved question;
                a component may still be served even under review (the source's own text,
                served as-is, is not obviously worse than an unconfirmed guess)
    note        why it changed, or what is still being asked
    source_hy   the source's own Armenian for the component, where attested -- the
                independent witness that justified several of the fixes
    approved_hy the reviewed Armenian the engine should serve. Stated on every row, not
                only where it differs from ``source_hy``, so the two languages are
                symmetric: ``source_*`` is what was published, ``approved_*`` is what we
                serve.

Regenerate after any edit to ``dev/feast_name_review.tsv``:
    python dev/build_ground_truth.py
"""

import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REVIEW_PATH = os.path.join(HERE, "feast_name_review.tsv")
OUT_PATH = os.path.join(HERE, "feast_name_ground_truth.json")


def main():
    with open(REVIEW_PATH, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))

    ground_truth = {}
    for r in rows:
        ground_truth[r["source_en"]] = {
            "id": r["id"],
            "approved_en": r["approved_en"],
            "status": r["status"],
            "note": r["note"],
            "source_hy": r["source_hy"],
            "approved_hy": r["approved_hy"],
        }

    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(ground_truth, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")

    review = sum(1 for v in ground_truth.values() if v["status"] == "review")
    hy_fixed = sum(1 for v in ground_truth.values()
                   if v["approved_hy"] != v["source_hy"])
    print(f"wrote {OUT_PATH}: {len(ground_truth)} components, "
          f"{review} still under review, {hy_fixed} with a corrected Armenian")


if __name__ == "__main__":
    main()
