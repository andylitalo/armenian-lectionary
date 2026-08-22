"""DEV-ONLY: report catalog entries whose Armenian is a MINORITY variant of what the
source actually publishes.

Why this can happen at all. ``feast_names_hy.json`` is built by pairing each English feast
string with the Armenian of one representative day (``dev/fetch_translations.py``). When
the source spells a name two ways across the years -- and it does: ``Ս. Աստուածածնի`` in
four cached years, ``ս. Աստուածածնի`` in two, ``ս.Աստուածածնի`` in one -- the pairing
picks whichever day it happened to sample. Nothing downstream re-examines that choice, so
a one-off malformation can become the shipped Armenian for every occurrence of the name.

That is exactly what happened to the Presentation of the Theotokos: the catalog serves the
1-of-7 form with no space after the abbreviation dot, on every Nov 21.

This script counts every witness in ``dev/reference_data_hy/`` and flags any entry whose
shipped Armenian is not the most frequent form. It compares COMPONENTS, not whole days, so
a name is judged on its own evidence rather than on the company it keeps.

Fix what it reports in ``observance_name_review.tsv``'s ``approved_hy`` column (with the counts in
the comment) and rebuild -- never by editing ``feast_names_hy.json``, which
``dev/fetch_translations.py`` regenerates from the cache.

Not every flagged row is a defect: the source genuinely writes a couple of names two ways
and the engine reproduces both on purpose. Judge each, then record the decision.

Usage:
    python dev/audit_hy_variants.py
"""

import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.hy_discrepancy import component_witnesses, normalized          # noqa: E402

DEV_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(DEV_DIR)
CATALOG_PATH = os.path.join(REPO_ROOT, "armenian_lectionary", "data",
                            "observance_catalog.json")


def minority_variants():
    """``[(id, shipped, shipped_count, majority, majority_count, all_variants), ...]``.

    Empty is the healthy state. Exposed as a function so tests can assert on it directly
    rather than re-deriving the comparison and drifting from this script.
    """
    with open(CATALOG_PATH, encoding="utf-8") as fh:
        catalog = json.load(fh)

    witnesses = component_witnesses()
    by_shape = collections.defaultdict(collections.Counter)
    for component, count in witnesses.items():
        by_shape[normalized(component)][component] += count

    findings = []
    for sid, entry in sorted(catalog.items()):
        shipped = entry["hy"]
        variants = by_shape.get(normalized(shipped))
        if not variants or len(variants) == 1:
            continue                        # unwitnessed, or the source is consistent
        majority, majority_count = variants.most_common(1)[0]
        if majority == shipped:
            continue                        # already serving the dominant form
        findings.append((sid, shipped, witnesses.get(shipped, 0),
                         majority, majority_count, variants))
    return findings


def main():
    findings = minority_variants()

    if not findings:
        print("0 entries serve a minority Armenian variant.")
        return 0

    print(f"{len(findings)} entr(y/ies) serve a MINORITY Armenian variant:\n")
    for sid, shipped, shipped_count, majority, majority_count, variants in findings:
        print(f"  {sid}")
        print(f"    serves   {shipped!r}  ({shipped_count} witness(es))")
        print(f"    majority {majority!r}  ({majority_count} witness(es))")
        others = [f"{v!r} x{n}" for v, n in variants.most_common()]
        print(f"    all      {', '.join(others)}")
        print()
    print("Record the fix in observance_name_review.tsv's approved_hy column, "
          "with a note, and rebuild.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
