"""Residue classifier: compare compute_armenian_lectionary vs GT cache.

Iterates dev/reference_data/*.json and tallies each day as one of:
  MATCH  -- non-empty ReadingsList exactly equals GT readings
  WRONG  -- non-empty readings disagree with GT from a VALIDATED source
            (validated-table / validated-composite); the contract keeps this 0
  MISS   -- non-empty readings disagree with GT from a best-guess/generative
            source (algorithmic-estimate w/ readings, generative-*, ...)
  BLANK  -- empty ReadingsList (deliberate abstention)
"""
import datetime
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lectionary import compute_armenian_lectionary  # noqa: E402
from dev.source_corrections import apply_cohort_corrections  # noqa: E402

# Source-derived tiers held to the 0-wrong contract. first-volume-cohort ships the
# Tōnats'oyts First-Volume propers directly (source-authoritative), reconciled with the
# cache oracle via the reviewed cohort corrections below.
_VALIDATED = {"validated-table", "validated-composite", "first-volume-cohort"}
_REF_DIR = pathlib.Path(__file__).resolve().parent / "reference_data"
# The build cross-year-validates over this cache range (dev/build_table.py); 2027+
# are deliberately held-out future years, so the residue tally scopes to it.
_CACHE_YEARS = range(2001, 2027)


def _norm(refs):
    return [r.strip() for r in refs]


def main() -> None:
    match = wrong = miss = blank = 0
    wrong_days, blank_days = [], []
    for path in sorted(_REF_DIR.glob("*.json")):
        gt = json.loads(path.read_text())
        d = datetime.date.fromisoformat(gt["date"])
        if d.year not in _CACHE_YEARS:
            continue
        got = compute_armenian_lectionary(d)
        refs = got["ReadingsList"]
        gt_readings = gt["readings"]
        if got["Source"] == "first-volume-cohort":
            # The engine serves the source verse-ranges; apply the reviewed source-vs-cache
            # corrections to the oracle before comparing (scoped to the cohort tier).
            gt_readings = apply_cohort_corrections(gt_readings)
        if _norm(refs) == _norm(gt_readings):
            # Exact agreement -- including the case where both are empty (a day
            # GT itself carries no readings), which is a correct match, not a
            # blank abstention.
            match += 1
        elif not refs:
            blank += 1
            blank_days.append(d.isoformat())
        elif got["Source"] in _VALIDATED:
            wrong += 1
            wrong_days.append((d.isoformat(), got["Source"]))
        else:
            miss += 1
    total = match + wrong + miss + blank
    print(f"days:  {total}")
    print(f"MATCH: {match}")
    print(f"WRONG: {wrong}")
    print(f"MISS:  {miss}")
    print(f"BLANK: {blank}")
    if wrong_days:
        print("\nwrong days:")
        for day, src in wrong_days:
            print(f"  {day}  {src}")


if __name__ == "__main__":
    main()
