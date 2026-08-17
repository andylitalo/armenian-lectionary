"""DEV-ONLY: classify every difference between the served Armenian feast name and
sacredtradition.am's own Armenian.

The Armenian counterpart of ``dev/feast_discrepancy_report.py``, and it exists for the
same reason: so the accuracy test and the human-readable numbers can never drift apart.
It was written after a refactor regressed ``language="hy"`` on ~118 days with nothing to
catch it -- English had a 9,496-day contract and Armenian had none.

Three normalizations are applied to the SOURCE before comparing, each matching a
deliberate, already-registered decision rather than papering over a defect:

  * ``dev/fetch_translations.to_mashtots_names`` -- the source types a handful of proper
    nouns in reformed ("Soviet") orthography inside otherwise-traditional text
    (``Դանիել`` for ``Դանիէլ``). v1.2.3 reversed those in the shipped maps on purpose, so
    comparing against the raw scrape would re-report a fix as a defect.
  * ``source_corrections.ground_truth_hy_fixes`` -- the reviewed Armenian corrections, the
    counterpart of what ``canonical_commem`` does for English. Without it a correction a
    human signed and a regression nobody noticed are the same finding.
  * component splitting on ``_FEAST_SEP``, so a day is compared as a set of observances
    rather than one string -- the same projection the English test uses.

Findings are classified, strongest first:

  * ``CONTRADICTION`` -- the engine emits an Armenian component the source does not have.
  * ``OMISSION`` -- the source states a component the engine drops.
  * ``ORDER`` -- the same components in a different order.
  * ``DOMINANT_FORM`` -- the source spells one name several ways and the engine serves the
    one it uses most often. Not a defect: it is the same policy the English side applies to
    ``Phillip``/``Philip`` (docs/feast-name-corrections.md section 4), and the day the cache
    happens to sample decides nothing. Separated out so the counts above mean
    "unexplained", not "everything that differs".
  * ``INTERNAL_DELIMITER`` -- identical to the source once the catalog's internal delimiter
    is read back as the component separator. Also not a defect, and a deliberate trade: the
    source's Armenian glues a trailing note ("— Նաւակատիք") onto a name whose English has
    no such piece, so reproducing its punctuation exactly cost ``hy`` an extra component
    that ``en`` did not have. The text is identical; only the delimiter differs. See
    ``dev/build_observance_catalog._INTERNAL_SEP``.

Unlike the English side, none of these is zero yet, and the residue is not all engine
defect. Of the 11 contradictions at the time of writing: 7 are days where the shipped
table's commemoration enumerates a different companion list than the year the cache
sampled -- the same class ``canonical_commem`` folds away on the English side, which has
no Armenian analogue; 2 are word-form variants (``Առաջաւորի``/``Առաջաւորաց``) where the
engine again serves the dominant form, but which ``normalized`` is too crude to group --
it compares spacing and case, not morphology, on purpose; and 2 are single-day punctuation
differences. Callers should treat the counts as ratchets, not as a defect list: what
matters is that no NEW divergence appears.

Coverage caveat: ``dev/reference_data_hy/`` holds 433 days, one representative date per
distinct English feast string (``dev/fetch_translations.py`` builds it that way), not the
full 9,861-day range. So this covers the distinct NAMES well and per-year calendar
behaviour thinly -- a wrong ordinal in a year the cache does not sample is invisible here.
A regression detector, not a completeness proof.

Usage:
    python dev/hy_discrepancy.py            # summary
    python dev/hy_discrepancy.py --list     # every finding, with both strings
"""

import collections
import datetime
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary.engine import (                                # noqa: E402
    _FEAST_SEP, compute_armenian_lectionary,
)
from dev.build_observance_catalog import _INTERNAL_SEP                  # noqa: E402
from dev.fetch_translations import to_mashtots_names                    # noqa: E402
from dev.source_corrections import ground_truth_hy_fixes                # noqa: E402

REF_DIR_HY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reference_data_hy")


def components(feast_str):
    """The feast string's ``_FEAST_SEP``-joined components, stripped and de-blanked."""
    return [c.strip() for c in (feast_str or "").split(_FEAST_SEP) if c.strip()]


def source_days():
    """``{iso: armenian feast string}`` for every cached day that carries one."""
    days = {}
    for path in sorted(glob.glob(os.path.join(REF_DIR_HY, "*.json"))):
        with open(path, encoding="utf-8") as fh:
            day = json.load(fh)
        feast = (day.get("feast") or "").strip()
        if feast:
            days[day["date"]] = feast
    return days


def source_feast(raw):
    """The source's Armenian for a day, as we have decided to read it.

    Both normalizations are registered decisions, not fuzz: the orthography reversal
    v1.2.3 applied to the shipped maps, and the reviewed Armenian corrections from
    ``approved_hy``. Comparing against the unfolded scrape re-reports each of those as a
    defect -- which is precisely what it did before this existed, since a deliberate
    Armenian correction and a regression both read as "the engine emits a component the
    source does not have".
    """
    fixes = ground_truth_hy_fixes()
    return _FEAST_SEP.join(fixes.get(c, c)
                           for c in to_mashtots_names(raw).split(_FEAST_SEP))


def normalized(text):
    """Collapse whitespace and case, so spellings of one name group together.

    Deliberately crude: it must group ``Ս. Աստուածածնի`` with ``ս.Աստուածածնի`` (a case
    change AND a lost space) without merging two genuinely different names. Armenian names
    differing only in spacing and case are the same name.
    """
    return "".join(text.split()).casefold()


def component_witnesses():
    """``{armenian component: times the source publishes it}`` over the whole cache."""
    seen = collections.Counter()
    for raw in source_days().values():
        for component in components(source_feast(raw)):
            seen[component] += 1
    return seen


def _dominant_forms(witnesses):
    """``{normalized name: the spelling the source uses most often}``."""
    by_shape = collections.defaultdict(collections.Counter)
    for component, count in witnesses.items():
        by_shape[normalized(component)][component] += count
    return {shape: variants.most_common(1)[0][0] for shape, variants in by_shape.items()}


def diff_components(src_comps, eng_comps):
    """``(contradictions, omissions)``: what the engine asserts that the source lacks, and
    what the source states that the engine drops.

    Matching is exact and greedy in component order, so a component is never counted as
    both. There is no correction-equivalence pass as there is on the English side: the
    Armenian has no ``canonical_commem``, and inventing a fuzzy match here would hide
    exactly the kind of near-miss (a minority spelling variant, a lost sub-component) this
    module exists to surface.
    """
    unmatched_src = list(src_comps)
    contradictions = []
    for eng in eng_comps:
        if eng in unmatched_src:
            unmatched_src.remove(eng)
        else:
            contradictions.append(eng)
    return contradictions, unmatched_src


def _is_dominant_form(contradictions, omissions, dominant):
    """True when the day's whole difference is spelling, and we serve the source's own
    most-frequent spelling of each name."""
    if not contradictions or len(contradictions) != len(omissions):
        return False
    dropped = {normalized(o): o for o in omissions}
    for served in contradictions:
        shape = normalized(served)
        if shape not in dropped or dominant.get(shape) != served:
            return False
    return True


def collect():
    """Walk the Armenian cache once; return per-day findings and the totals."""
    findings = []
    compared = exact = 0
    dominant = _dominant_forms(component_witnesses())

    for iso, raw in sorted(source_days().items()):
        src = source_feast(raw)
        eng = compute_armenian_lectionary(
            datetime.date.fromisoformat(iso), language="hy")["Liturgical Day"]
        compared += 1
        if eng == src:
            exact += 1
            continue

        src_comps, eng_comps = components(src), components(eng)
        contradictions, omissions = diff_components(src_comps, eng_comps)
        if eng.replace(_INTERNAL_SEP, _FEAST_SEP) == src:
            kind = "INTERNAL_DELIMITER"
        elif _is_dominant_form(contradictions, omissions, dominant):
            kind = "DOMINANT_FORM"
        elif contradictions:
            kind = "CONTRADICTION"
        elif omissions:
            kind = "OMISSION"
        else:
            kind = "ORDER"
        findings.append({
            "iso": iso, "kind": kind, "src": src, "eng": eng,
            "contradictions": contradictions, "omissions": omissions,
        })

    return {"compared": compared, "exact": exact, "findings": findings}


KINDS = ("CONTRADICTION", "OMISSION", "ORDER", "DOMINANT_FORM", "INTERNAL_DELIMITER")


def counts(data):
    """``{kind: n}`` over the findings, for the ratchets."""
    tally = {kind: 0 for kind in KINDS}
    for finding in data["findings"]:
        tally[finding["kind"]] += 1
    return tally


def main():
    data = collect()
    tally = counts(data)
    print(f"compared {data['compared']}   exact {data['exact']}")
    for kind in KINDS:
        print(f"  {kind:<14} {tally[kind]}")

    if "--list" in sys.argv:
        for finding in data["findings"]:
            print(f"\n--- {finding['iso']}  {finding['kind']}")
            print(f"  src: {finding['src']}")
            print(f"  eng: {finding['eng']}")
            for component in finding["contradictions"]:
                print(f"    + {component}")
            for component in finding["omissions"]:
                print(f"    - {component}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
