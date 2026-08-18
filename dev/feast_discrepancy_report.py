"""DEV-ONLY: inventory every feast-NAME discrepancy between the engine and the source.

``tests/test_feast.py`` compares only the *commemoration component* of the feast name, so
whole classes of difference -- year-varying position labels, ``Eve of ...`` notes, and the
engine's own placeholders -- are stripped from BOTH sides before comparison and can never
fail it. bahk, however, persists the RAW ``"Liturgical Day"`` string into ``Feast.name``.
This script compares that raw string, component by component, and writes a reviewable
Markdown inventory to ``reports/feast_name_discrepancies.md``.

Each day's feast string is a list of ``_FEAST_SEP``-joined components (a calendar-position
label, the commemoration, an ``Eve of <Fast>`` status note). Comparing component-wise
rather than byte-wise separates the two failure modes that matter very differently:

  CONTRADICTION  the engine emits a component the source does not have -- it asserts
                 something false, and bahk stores it. This is the serious class.
  OMISSION       the source has a component the engine drops -- incomplete, but not wrong.
  DELIBERATE     the two differ only under the registered ``dev/source_corrections`` folds
                 (companion-enumeration variants, the ``Fiest``->``Feast`` scrape typo,
                 the ``PRESENTATION`` casing, Theodore the General/Tyron). Listed so a
                 reviewer can see these are intentional rather than missed.

Two further classes are independent of the source and are reported alongside:

  LONG           name longer than a typical 256-char column. Informational, not a
                 defect: these names are correct and match the source byte for byte.
  UNTRANSLATED   ``language="hy"`` returns the English string, i.e. no Armenian form.

Usage:
    python dev/feast_discrepancy_report.py            # -> reports/feast_name_discrepancies.md
    python dev/feast_discrepancy_report.py --stdout   # print instead of writing
"""

import collections
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.analyze import load_all                                    # noqa: E402
from dev.feast_names import ORD                                     # noqa: E402
from dev.observance_ids import is_added_text, pool_of_text          # noqa: E402
from dev.source_corrections import (                                # noqa: E402
    canonical_commem, expected_fast_marker_components,
)
from armenian_lectionary.engine import (                            # noqa: E402
    _FEAST_SEP, compute_armenian_lectionary, MAX_YEAR, MIN_YEAR,
)

OUT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "reports", "feast_name_discrepancies.md")

# Names past this are listed as a heads-up for consumers sizing a column or a UI field.
# NOT a defect threshold: these names are correct and byte-identical to the source, they
# are simply long because the feast's name enumerates its saints. Set to a round number
# consumers commonly default to, purely so the report surfaces the ones worth knowing about.
LONG_NAME_NOTICE = 256

# Engine placeholders: not commemorations, and not something bahk should ever persist.
PLACEHOLDERS = ("(movable ordinary-time reading)", "(commemoration)",
                "(day not yet in validated table)")

# A calendar-position component: "Nth day of <Season>", "Nth Sunday after/of <Anchor>",
# a bare "Nth Sunday", the "Fast day"/"Feast day" status marker, or its weekday split.
_POSITION = re.compile(
    rf"^(?:{ORD})\s+(?:day of|Sunday(?:\s+(?:after|of))?)\b"
    r"|^(?:Fast|Feast) day$|^(?:Wednesday|Friday) Fast$")
# Ordinal word + the family it counts within, for the wrong-ordinal diagnosis.
_ORD_FAMILY = re.compile(rf"^({ORD})\s+(.*)$")


def components(feast_str):
    """The feast string's ``_FEAST_SEP``-joined components, stripped and de-blanked."""
    return [c.strip() for c in (feast_str or "").split(_FEAST_SEP) if c.strip()]


def reconciled_components(iso, feast_str):
    """The source's components, with a bare "Fast day"/"Feast day" marker replaced by
    what the engine is now expected to serve for it (a weekday split, a named-fast
    day-count label, or nothing) -- see dev.source_corrections.
    expected_fast_marker_components and docs/feast-name-corrections.md. A day with no
    such marker is returned unchanged."""
    return expected_fast_marker_components(iso, components(feast_str))


def is_position(component):
    return bool(_POSITION.match(component))


def diff_components(src_comps, eng_comps):
    """Align the engine's components against the source's.

    Returns ``(contradictions, omissions, deliberate, expansions, additions)``: components
    the engine asserts and the source lacks, components the source has and the engine
    drops, (src, eng) pairs that differ only under the registered corrections, the
    components the engine adds by expanding the Second Volume's brevity into the First
    Volume's canons, and the declared fixed-date observances the source's English never
    names. Matching is greedy in component order -- exact first, then
    correction-equivalent, then packed-pool -- so a component is never counted twice.

    The third pass is what keeps a packed day honest. The source may print one head canon
    where the engine serves that canon plus the others packed onto the same day; the
    Tonats'oyts' own preface says to celebrate them all (see observance_ids._PACKED_POOLS),
    so this is not wrong data -- but it is a departure from the printed string, so it is
    counted rather than folded into silence.
    """
    unmatched_src = list(src_comps)
    contradictions, deliberate = [], []
    matched_src = []

    for eng in eng_comps:
        if eng in unmatched_src:                       # byte-exact
            unmatched_src.remove(eng)
            matched_src.append(eng)
            continue
        equiv = next((s for s in unmatched_src
                      if canonical_commem(s) == canonical_commem(eng)), None)
        if equiv is not None:                          # registered correction
            unmatched_src.remove(equiv)
            matched_src.append(equiv)
            deliberate.append((equiv, eng))
            continue
        contradictions.append(eng)

    pools = [p for p in (pool_of_text(s) for s in matched_src) if p]
    still_wrong, expansions, additions = [], [], []
    for eng in contradictions:
        if is_added_text(eng):
            additions.append(eng)
            continue
        pool = pool_of_text(eng)
        (expansions if pool is not None and pool in pools else still_wrong).append(eng)

    return still_wrong, unmatched_src, deliberate, expansions, additions


def is_casing_only(contradictions, omissions):
    """True when every difference is a pure letter-case change of the same component.

    The source SHOUTS a few feast names ("PRESENTATION of the Holy Mother of God to the
    Temple") and the engine title-cases them. That is a normalization choice, not wrong
    data -- but it is not a *registered* one, so it is reported separately for a decision
    rather than folded away silently.
    """
    # A dropped calendar-position label is its own (omission) finding; what matters here is
    # whether the *commemoration* the engine emits is the source's, modulo case.
    residual = [o for o in omissions if not is_position(o)]
    if not contradictions or len(contradictions) != len(residual):
        return False
    return sorted(c.casefold() for c in contradictions) == \
           sorted(o.casefold() for o in residual)


def cause_of(contradictions, omissions):
    """Short human diagnosis for a contradicting day (drives the report's sub-grouping)."""
    if any(c in PLACEHOLDERS for c in contradictions):
        return "engine placeholder"
    # Same position family on both sides but a different ordinal -> a counting error.
    for eng in contradictions:
        me = _ORD_FAMILY.match(eng)
        if not me:
            continue
        for src in omissions:
            ms = _ORD_FAMILY.match(src)
            # Compare the counted family, ignoring the source's inconsistent article
            # ("Sunday after Assumption" vs "... after the Assumption").
            if ms and ms.group(2).replace("after the ", "after ") == \
                      me.group(2).replace("after the ", "after "):
                return "wrong ordinal"
    if is_casing_only(contradictions, omissions):
        return "casing only"
    if any(c.startswith("Eve of") for c in contradictions):
        return "wrong eve note"
    if any(is_position(c) for c in contradictions):
        return "wrong position label"
    return "saint enumeration"


def collect():
    """Walk the whole cache once; return per-day findings plus the flag lists."""
    days = load_all()
    findings, storage, untranslated = [], [], []
    compared = skipped = exact = expanded = added = 0

    for iso in sorted(days):
        d = datetime.date.fromisoformat(iso)
        res_en = compute_armenian_lectionary(d)
        eng = res_en["Liturgical Day"]
        hy = compute_armenian_lectionary(d, language="hy")["Liturgical Day"]

        # Source-independent flags: these hold for every date the engine can answer,
        # including the years the cache has no ground truth for.
        if len(eng) > LONG_NAME_NOTICE:
            storage.append((iso, len(eng), eng))
        if hy == eng:
            untranslated.append((iso, eng))

        src = (days[iso].get("feast") or "").strip()
        if not src:
            skipped += 1                    # no oracle for this day (see the 2027 note)
            continue
        compared += 1

        contradictions, omissions, deliberate, expansions, additions = diff_components(
            reconciled_components(iso, src), components(eng))
        if expansions:
            expanded += 1
        if additions:
            added += 1
        if not contradictions and not omissions:
            exact += 1                      # byte-exact, or exact under the folds
            continue
        cause = cause_of(contradictions, omissions) if contradictions else ""
        if not contradictions:
            kind = "OMISSION"
        elif cause == "casing only":
            kind = "CASING"
        else:
            kind = "CONTRADICTION"
        findings.append({
            "iso": iso, "src": src, "eng": eng, "tier": res_en["Source"],
            "contradictions": contradictions, "omissions": omissions,
            "deliberate": deliberate, "expansions": expansions,
            "additions": additions, "kind": kind, "cause": cause,
        })

    return {
        "days": days, "findings": findings, "storage": storage,
        "untranslated": untranslated, "compared": compared,
        "skipped": skipped, "exact": exact, "expanded": expanded, "added": added,
        "total": len(days),
    }


def context_table(days, iso, span=2):
    """Markdown table of the day plus ``span`` days either side of ground truth.

    Almost every defect here is a counting error, and a counting error only reads as wrong
    against its neighbours -- 2011-02-13 is plainly misnamed once you see 02-14 opening the
    Fast of the Catechumens directly after it.
    """
    centre = datetime.date.fromisoformat(iso)
    rows = ["| date | wd | ground truth (sacredtradition.am) | engine `Liturgical Day` |",
            "|---|---|---|---|"]
    for delta in range(-span, span + 1):
        d = centre + datetime.timedelta(days=delta)
        if not MIN_YEAR <= d.year <= MAX_YEAR:
            continue        # a Jan 1 or Dec 31 finding reaches past the supported range
        key = d.isoformat()
        src = (days.get(key, {}).get("feast") or "").strip() or "_(no ground truth)_"
        eng = compute_armenian_lectionary(d)["Liturgical Day"]

        contradictions, omissions, _, _, _ = diff_components(
            reconciled_components(key, days.get(key, {}).get("feast") or ""),
            components(eng))
        if contradictions and is_casing_only(contradictions, omissions):
            mark, shown = " ⚠ casing", eng
        elif contradictions:
            mark, shown = " ❌", eng
        elif omissions:
            mark, shown = " ⚠ omission", eng
        else:
            mark, shown = "", ("=" if delta else eng)

        bold = "**" if delta == 0 else ""
        rows.append(f"| {bold}{key}{bold} | {bold}{d.strftime('%a')}{bold} "
                    f"| {bold}{src}{bold} | {bold}{shown}{bold}{mark} |")
    return "\n".join(rows)


def signature(f):
    """Group key collapsing the same defect recurring on the same liturgical coordinate."""
    return (f["kind"], f["cause"], tuple(f["omissions"]), tuple(f["contradictions"]))


def render(data):
    days, findings = data["days"], data["findings"]
    contradicting = [f for f in findings if f["kind"] == "CONTRADICTION"]
    omitting = [f for f in findings if f["kind"] == "OMISSION"]
    casing = [f for f in findings if f["kind"] == "CASING"]

    out = []
    w = out.append

    w("# Feast-name discrepancies: engine vs. sacredtradition.am\n")
    w(f"Generated by `dev/feast_discrepancy_report.py` on "
      f"{datetime.date.today().isoformat()} over the whole ground-truth cache "
      f"(`dev/reference_data/`).\n")
    w("Compares the **raw `\"Liturgical Day\"` string** — the value bahk persists into "
      "`Feast.name` — component by component on the `—` separator. `tests/test_feast.py` "
      "compares only the *commemoration* component, so everything below is invisible to it.\n")

    # ---- summary ----------------------------------------------------------- #
    w("## Summary\n")
    w("| class | days | meaning |")
    w("|---|---:|---|")
    w(f"| **CONTRADICTION** | {len(contradicting)} | engine asserts a component the source "
      "lacks — **wrong data, persisted by bahk** |")
    w(f"| OMISSION | {len(omitting)} | source has a component the engine drops — incomplete, "
      "not wrong |")
    w(f"| CASING | {len(casing)} | same component, different letter case — an *unregistered* "
      "normalization |")
    w(f"| LONG | {len(data['storage'])} | name over {LONG_NAME_NOTICE} chars "
      "(informational — correct, just long) |")
    w(f"| UNTRANSLATED | {len(data['untranslated'])} | `language=\"hy\"` returns the English "
      "string |")
    w(f"| _exact_ | {data['exact']} | byte-exact, or equal under the registered "
      "`dev/source_corrections` folds |")
    w("")
    w(f"Cache holds **{data['total']}** days; **{data['compared']}** carry a source feast "
      f"name and were compared; **{data['skipped']}** have no ground truth and were skipped "
      "(see *Coverage gap* below).\n")

    w("### Contradictions by cause\n")
    w("| cause | days |")
    w("|---|---:|")
    for cause, n in collections.Counter(f["cause"] for f in contradicting).most_common():
        w(f"| {cause} | {n} |")
    w("")

    w("### Contradictions by engine tier\n")
    w("The concentration in the **validated** tiers is the headline: those tiers carry a "
      "0-wrong contract for *readings*, and nothing equivalent for *names*.\n")
    w("| engine `Source` | days |")
    w("|---|---:|")
    for tier, n in collections.Counter(f["tier"] for f in contradicting).most_common():
        w(f"| `{tier}` | {n} |")
    w("")

    w("### Discrepancies by year\n")
    by_year = collections.Counter(f["iso"][:4] for f in findings)
    w("| " + " | ".join(sorted(by_year)) + " |")
    w("|" + "---:|" * len(by_year))
    w("| " + " | ".join(str(by_year[y]) for y in sorted(by_year)) + " |")
    w("")

    w("### Coverage gap\n")
    missing_years = sorted({iso[:4] for iso in days
                            if not (days[iso].get("feast") or "").strip()})
    w(f"No day in **{', '.join(missing_years) or '(none)'}** carries a source feast name, so "
      "no oracle test asserts anything about those years — while bahk serves feast names "
      "through 2027. sacredtradition.am publishes nothing for 2027 (probed 2026-07-30: the "
      "page returns an empty shell), so this gap cannot be closed by re-fetching. Those years "
      "are covered by the source-independent invariants instead (UNTRANSLATED "
      "above, and `tests/test_feast_contract.py`).\n")

    # ---- contradictions ---------------------------------------------------- #
    w("---\n")
    w("## CONTRADICTIONS\n")
    w("Grouped by defect: one entry per distinct (source, engine) component pair, since the "
      "same liturgical coordinate recurs across civil years. Each entry shows the earliest "
      "affected date in context.\n")

    groups = collections.OrderedDict()
    for f in sorted(contradicting, key=lambda f: f["iso"]):
        groups.setdefault(signature(f), []).append(f)

    for group in sorted(groups.values(), key=lambda g: (-len(g), g[0]["iso"])):
        first = group[0]
        w(f"### {first['iso']}"
          + (f" (+{len(group) - 1} more)" if len(group) > 1 else "")
          + f" — {first['cause']}\n")
        w(f"engine tier: `{first['tier']}`"
          + (f" · affects **{len(group)} days**" if len(group) > 1 else "") + "\n")
        for eng in first["contradictions"]:
            w(f"- engine asserts `{eng}` — not in the source's string for this day")
        for src in first["omissions"]:
            w(f"- source has `{src}` — engine drops it")
        w("")
        w(context_table(days, first["iso"]))
        w("")
        if len(group) > 1:
            w("<details><summary>All affected dates</summary>\n")
            w(", ".join(f["iso"] for f in group))
            w("\n</details>\n")

    # ---- casing ------------------------------------------------------------ #
    w("---\n")
    w("## CASING\n")
    w("The engine and the source name the same commemoration with different letter case. "
      "Not wrong data, but not a *registered* difference either: `canonical_commem` folds "
      "`PRESENTATION OF OUR LORD TO THE TEMPLE` and says nothing about these. Decide "
      "explicitly — either register the fold in `dev/source_corrections` or preserve the "
      "source's casing — so the raw-string oracle has no unexplained residue.\n")
    case_groups = collections.OrderedDict()
    for f in sorted(casing, key=lambda f: f["iso"]):
        case_groups.setdefault(
            (tuple(f["contradictions"]), tuple(c for c in f["omissions"]
                                               if not is_position(c))), []).append(f)
    w("| source | engine | days |")
    w("|---|---|---:|")
    for (eng_comps, src_comps), group in sorted(case_groups.items(),
                                                key=lambda kv: -len(kv[1])):
        w(f"| {' · '.join(src_comps)} | {' · '.join(eng_comps)} | {len(group)} |")
    w("")

    # ---- omissions --------------------------------------------------------- #
    w("---\n")
    w("## OMISSIONS\n")
    w("The engine drops a component the source carries. Safe (it asserts nothing false) but "
      "incomplete — these are what the position-label regeneration should recover. Days "
      "listed under CONTRADICTION or CASING usually drop a position label too; they are "
      "counted under their more serious class, not here.\n")
    om_groups = collections.OrderedDict()
    for f in sorted(omitting, key=lambda f: f["iso"]):
        om_groups.setdefault(tuple(f["omissions"]), []).append(f)
    w("| dropped component(s) | days | example |")
    w("|---|---:|---|")
    for comps, group in sorted(om_groups.items(), key=lambda kv: -len(kv[1])):
        w(f"| {' · '.join(f'`{c}`' for c in comps)} | {len(group)} | {group[0]['iso']} |")
    w("")

    # ---- storage ----------------------------------------------------------- #
    w("---\n")
    w("## LONG NAMES\n")
    w(f"Names over {LONG_NAME_NOTICE} characters. **Not defects** — they match the source "
      "byte for byte and are long only because the feast's name enumerates its saints. "
      "Listed as a heads-up when sizing a database column or a UI field.\n")
    by_name = collections.OrderedDict()
    for iso, length, name in data["storage"]:
        by_name.setdefault(name, []).append(iso)
    for name, isos in by_name.items():
        w(f"**{len(name)} chars · {len(isos)} days** (first {isos[0]}, last {isos[-1]})\n")
        w(f"> {name}\n")
        src_len = len((days.get(isos[0], {}).get("feast") or "").strip())
        w(f"Source string on {isos[0]} is {src_len} chars — "
          + ("**identical**, so the retired scrape had the same failure: pre-existing, not a "
             "regression from serving names off the engine.\n" if src_len == len(name)
             else "differs.\n"))
        w("<details><summary>All affected dates</summary>\n")
        w(", ".join(isos))
        w("\n</details>\n")

    # ---- untranslated ------------------------------------------------------ #
    w("---\n")
    w("## UNTRANSLATED\n")
    w("`language=\"hy\"` returns the English string, so bahk records `name_hy = None` and the "
      "app falls back to English.\n")
    if data["untranslated"]:
        w("| date | engine name (en == hy) |")
        w("|---|---|")
        for iso, name in data["untranslated"]:
            w(f"| {iso} | {name} |")
        w("")
        w("Every one of these is also a CONTRADICTION above — the engine has no Armenian form "
          "precisely *because* the English name it invented is not a real feast name. A "
          "single invariant (`hy != en` on every date) therefore catches this whole class "
          "without needing any ground truth.\n")
    else:
        w("_None — every date resolves to a genuine Armenian name._\n")

    return "\n".join(out) + "\n"


def main():
    data = collect()
    text = render(data)
    if "--stdout" in sys.argv:
        sys.stdout.write(text)
        return
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(text)
    kinds = collections.Counter(f["kind"] for f in data["findings"])
    print(f"wrote {os.path.relpath(OUT_PATH)}: "
          f"{kinds['CONTRADICTION']} contradictions, "
          f"{kinds['OMISSION']} omissions, "
          f"{kinds['CASING']} casing, "
          f"{len(data['storage'])} over-length, "
          f"{len(data['untranslated'])} untranslated "
          f"({data['exact']}/{data['compared']} exact)")


if __name__ == "__main__":
    main()
