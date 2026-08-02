"""Build the reproducible multi-year Oratsouyts evidence corpus.

The extractor is intentionally a one-time development pipeline.  Its verbose
records live under ``.work/`` and are not loaded by the public library.  Compact
reviewed rules and tests can later be promoted into the runtime without adding
PDF parsing, annual-table lookups, or network access to a date query.

Example::

    python -m dev.oratsouyts.pipeline \
      --source-dir "/path/to/Եկեղեցական Օրացույց"
"""

from __future__ import annotations

import argparse
import calendar
import collections
import datetime as _datetime
import hashlib
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from armenian_lectionary import compute_armenian_lectionary
from dev.oratsouyts import EXTRACTOR_VERSION, SCHEMA_VERSION
from dev.oratsouyts.evidence import (
    augment_saint_classes_from_aligned_layout,
    classify_explicit_record,
    explicit_positive_mismatches,
    resolve_year_fast_contexts,
)
from dev.oratsouyts.extract import extract_year, sha256_file, tool_version


_YEAR_RE = re.compile(r"^(?P<year>20[0-9]{2})\b")
SOURCE_MANIFEST_PATH = Path(__file__).with_name("source_manifest.json")
RUNTIME_RECONCILIATION_PATH = Path(__file__).with_name(
    "runtime_reconciliation_allowlist.json"
)
DEFAULT_EXPECTATIONS_PATH = Path("tests/fixtures/oratsouyts_calendar_expectations.json")
_SOURCE_FIELD_ORDER = (
    "weekday",
    "is_sunday",
    "is_dominical",
    "is_fast_day",
    "fast_context",
    "is_saints_day",
    "saint_classes",
    "is_cross_feast",
    "is_marian_feast",
    "is_memorial",
)
_RUNTIME_FIELD_KEYS = {
    "is_fast_day": "Is Fast Day",
    "fast_context": "Fast Context",
    "is_saints_day": "Is Saints Day",
    "saint_classes": "Saint Classes",
    "is_cross_feast": "Is Cross Feast",
    "is_marian_feast": "Is Marian Feast",
    "is_memorial": "Is Memorial",
}


class PipelineError(RuntimeError):
    """Raised when a corpus-wide acceptance invariant fails."""


def _json_text(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def _write_json(path: Path, value: object) -> str:
    text = _json_text(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_source_manifest(path: Path = SOURCE_MANIFEST_PATH) -> Dict[int, Dict[str, object]]:
    """Load and validate the exact reviewed source inventory."""

    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PipelineError("Could not read source manifest %s: %s" % (path, exc))
    if manifest.get("schema_version") != 1 or not isinstance(
            manifest.get("sources"), list):
        raise PipelineError("Unsupported source manifest schema: %s" % path)
    by_year: Dict[int, Dict[str, object]] = {}
    for row in manifest["sources"]:
        try:
            year = int(row["year"])
            filename = str(row["filename"])
            digest = str(row["sha256"])
            page_count = int(row["page_count"])
        except (KeyError, TypeError, ValueError) as exc:
            raise PipelineError("Invalid source manifest row: %r" % row) from exc
        if year in by_year:
            raise PipelineError("Duplicate year %d in source manifest" % year)
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise PipelineError("Invalid SHA-256 for %d in source manifest" % year)
        by_year[year] = {
            "year": year,
            "filename": filename,
            "sha256": digest,
            "page_count": page_count,
        }
    if not by_year:
        raise PipelineError("Source manifest is empty: %s" % path)
    return by_year


def load_runtime_reconciliation_allowlist(
    path: Path = RUNTIME_RECONCILIATION_PATH,
) -> List[Dict[str, object]]:
    """Load the exact, reviewed set of permitted source/runtime differences."""

    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PipelineError(
            "Could not read runtime reconciliation allowlist %s: %s" % (path, exc)
        )
    if document.get("schema_version") != 1 or not isinstance(
            document.get("entries"), list):
        raise PipelineError("Unsupported reconciliation allowlist schema: %s" % path)
    entries: List[Dict[str, object]] = []
    for row in document["entries"]:
        try:
            date = _datetime.date.fromisoformat(str(row["date"])).isoformat()
            field = str(row["field"])
            source_value = row["source_value"]
            runtime_value = row["runtime_value"]
            rationale = str(row["rationale"])
        except (KeyError, TypeError, ValueError) as exc:
            raise PipelineError("Invalid reconciliation allowlist row: %r" % row) from exc
        if field not in _RUNTIME_FIELD_KEYS or not rationale.strip():
            raise PipelineError("Invalid reconciliation field/rationale: %r" % row)
        entries.append(
            {
                "date": date,
                "field": field,
                "source_value": source_value,
                "runtime_value": runtime_value,
                "rationale": rationale,
            }
        )
    return sorted(entries, key=lambda item: (item["date"], item["field"]))


def discover_sources(
    source_dir: Path,
    manifest: Optional[Mapping[int, Mapping[str, object]]] = None,
) -> List[Tuple[int, Path]]:
    """Discover exactly one annual PDF for every manifest-locked source."""

    manifest = manifest or load_source_manifest()

    by_year: MutableMapping[int, List[Path]] = collections.defaultdict(list)
    for path in sorted(source_dir.glob("*.pdf"), key=lambda item: item.name):
        match = _YEAR_RE.match(path.name)
        if match:
            by_year[int(match.group("year"))].append(path)
    expected_years = set(manifest)
    discovered_years = set(by_year)
    if discovered_years != expected_years:
        missing = sorted(expected_years - discovered_years)
        unexpected = sorted(discovered_years - expected_years)
        raise PipelineError(
            "Source set differs from manifest; missing=%s, unexpected=%s"
            % (missing or "none", unexpected or "none")
        )
    duplicates = {year: paths for year, paths in by_year.items() if len(paths) != 1}
    if duplicates:
        detail = "; ".join(
            "%d: %s" % (year, ", ".join(path.name for path in paths))
            for year, paths in sorted(duplicates.items())
        )
        raise PipelineError("Expected one PDF per year; found duplicates: %s" % detail)
    sources = [(year, by_year[year][0]) for year in sorted(by_year)]
    renamed = [
        (year, path.name, str(manifest[year]["filename"]))
        for year, path in sources
        if path.name != manifest[year]["filename"]
    ]
    if renamed:
        detail = "; ".join(
            "%d: found %r, expected %r" % item for item in renamed
        )
        raise PipelineError("Source filenames differ from manifest: %s" % detail)
    return sources


def _source_row(extracted: Mapping[str, object]) -> Dict[str, object]:
    source = extracted["source"]
    section = extracted["section"]
    quality = extracted["quality"]
    raw_section = section["poppler_raw"]
    return {
        "year": extracted["year"],
        "filename": source["filename"],
        "sha256": source["sha256"],
        "page_count": source["page_count"],
        "legacy_encoding": source["legacy_encoding"],
        "spread_pages": source["physical_spread_pages"],
        "records": quality["records"],
        "start_page": section["start_physical_page"],
        "end_page": section["end_physical_page"],
        "layout_candidate_count": section["candidate_count"],
        "raw_candidate_count": raw_section["candidate_count"],
        "weekday_conflicts": len(quality["weekday_conflicts"]),
        "mode_conflicts": len(quality["mode_conflicts"]),
        "mode_punctuation_warnings": len(quality["mode_punctuation_warnings"]),
        "extraction_disagreements": len(quality["extraction_disagreements"]),
    }


def _classify_variant(
    record: Mapping[str, object], extraction_mode: str
) -> Dict[str, object]:
    """Classify one already aligned extraction representation."""

    variant = record["extraction_variants"][extraction_mode]
    return classify_explicit_record(
        {
            "date": record["date"],
            "calendar_clause": variant["calendar_clause"],
            "normalized_text": variant["normalized_text"],
            "header": variant["header"],
        }
    )


def _short_clause(text: str, limit: int = 180) -> str:
    text = " ".join((text or "").split()).replace("|", "\\|")
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _years_text(years: Iterable[int]) -> str:
    values = sorted(set(years))
    return ", ".join(str(year) for year in values) if values else "—"


def _expectations_fixture(
    evidence_records: Sequence[Mapping[str, object]],
    reviewed_reconciliations: Sequence[Mapping[str, object]],
    source_manifest_sha256: str,
    reconciliation_allowlist_sha256: str,
) -> Dict[str, object]:
    """Distill source-positive facts into a compact CI fixture."""

    cases: List[Dict[str, object]] = []
    for evidence in evidence_records:
        expected = {
            runtime_key: evidence["facts"][source_key]["value"]
            for source_key, runtime_key in _RUNTIME_FIELD_KEYS.items()
            if evidence["facts"][source_key]["value"] is not None
        }
        if expected:
            cases.append({"date": evidence["date"], "expected": expected})
    reconciled = [
        {
            "date": mismatch["date"],
            "field": _RUNTIME_FIELD_KEYS[mismatch["field"]],
            "source_value": mismatch["source_value"],
            "runtime_value": mismatch["runtime_value"],
        }
        for mismatch in reviewed_reconciliations
        if mismatch["field"] in _RUNTIME_FIELD_KEYS
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "source_manifest_sha256": source_manifest_sha256,
        "reconciliation_allowlist_sha256": reconciliation_allowlist_sha256,
        "comparison_semantics": {
            "Saint Classes": "source list must be a subset of runtime list",
            "other_fields": "exact equality",
        },
        "cases": cases,
        "accepted_reconciliation": reconciled,
    }


def _coverage_markdown(audit: Mapping[str, object]) -> str:
    sources = audit["sources"]
    totals = audit["totals"]
    field_coverage = audit["field_coverage"]
    occurrence_coverage = audit["occurrence_coverage"]
    available_years = [row["year"] for row in sources]
    missing_years = [
        year for year in range(min(available_years), max(available_years) + 1)
        if year not in available_years
    ]

    lines = [
        "# Oratsouyts corpus coverage",
        "",
        "This report is generated by `python -m dev.oratsouyts.pipeline`. It audits "
        "calendar-level evidence only; daily-service selections and individual "
        "շարական appointments are outside this branch.",
        "",
        "## Acceptance result",
        "",
        "- Sources: **%d annual PDFs** (%s)." % (
            len(sources), _years_text(available_years)
        ),
        "- Missing year in the available sequence: **%s**." % _years_text(missing_years),
        "- Accepted new-style civil dates: **%s / %s**; no synthesized or duplicate dates."
        % (f"{totals['records']:,}", f"{totals['expected_records']:,}"),
        "- The exact filenames, page counts, and full PDF SHA-256 digests are locked "
        "by `dev/oratsouyts/source_manifest.json`; missing, added, renamed, or replaced "
        "year files fail before acceptance.",
        "- Both Poppler layout and raw-order streams independently contain a complete "
        "civil-date run for every edition. Layout establishes boundaries; raw order "
        "supplies semantic calendar clauses; both variants are retained.",
        "- Printed modes disagree with the independent constant-time mode engine on "
        "**%d dates**." % totals["mode_conflicts"],
        "- **%s source-positive date cases** are distilled into the committed "
        "offline CI fixture. The corpus build fails if runtime differences depart "
        "from the separately reviewed allowlist."
        % f"{totals['expectation_cases']:,}",
        "- Full output digests are written to local "
        "`.work/oratsouyts/checksums.json` after every successful build.",
        "- The extractor is development-only. The public query path loads none of these "
        "PDFs or annual records.",
        "",
        "## Source inventory",
        "",
        "| Year | SHA-256 | Pages | Layout | Detailed pages | Records | Weekday conflicts | Mode conflicts | Extractor disagreements |",
        "|---:|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    for row in sources:
        layout = "legacy portrait" if row["legacy_encoding"] else (
            "imposed spreads" if row["spread_pages"] else "Unicode portrait"
        )
        lines.append(
            "| {year} | `{sha}` | {pages} | {layout} | {start}–{end} | {records} | "
            "{weekday} | {mode} | {extract} |".format(
                year=row["year"],
                sha=str(row["sha256"]),
                pages=row["page_count"],
                layout=layout,
                start=row["start_page"],
                end=row["end_page"],
                records=row["records"],
                weekday=row["weekday_conflicts"],
                mode=row["mode_conflicts"],
                extract=row["extraction_disagreements"],
            )
        )

    lines.extend(
        [
            "",
            "## Explicit evidence coverage",
            "",
            "A positive count means the calendar clause explicitly states the fact. "
            "The remaining dates are **unknown from this lexical signal**, not false. "
            "Weekday and Sunday are exceptions because civil-date math establishes "
            "both true and false values deterministically.",
            "",
            "| Field | Explicit/deterministic records | Unknown records | Years represented |",
            "|---|---:|---:|---|",
        ]
    )
    for field in _SOURCE_FIELD_ORDER:
        row = field_coverage[field]
        lines.append(
            "| `{field}` | {known:,} | {unknown:,} | {years} |".format(
                field=field,
                known=row["known"],
                unknown=row["unknown"],
                years=_years_text(row["years"]),
            )
        )

    lines.extend(
        [
            "",
            "## Canonical occurrence signals",
            "",
            "| Occurrence ID | Records | Years represented |",
            "|---|---:|---|",
        ]
    )
    for occurrence_id, row in sorted(occurrence_coverage.items()):
        lines.append(
            "| `{}` | {:,} | {} |".format(
                occurrence_id, row["records"], _years_text(row["years"])
            )
        )

    lines.extend(
        [
            "",
            "## Confidence boundaries",
            "",
            "- Highest confidence: civil weekday/Sunday, record completeness, printed "
            "mode agreement, explicit fast markers and names, reviewed Cross/Marian "
            "titles, explicit saint descriptors, and exact memorial banners.",
            "- The dagger (`†`) is preserved as a source token but is **not** interpreted "
            "as Dominical; it occurs on many non-Dominical dates.",
            "- Non-Sunday Dominical identity needs a reviewed canonical occurrence "
            "taxonomy. Source silence cannot establish a negative.",
            "- `is_fast_day` and a future service-level `is_penitential` are distinct. "
            "The books explicitly combine fast markers with festive saint or Marian "
            "offices.",
            "- Recurring editorial variation, collisions, and source/extractor "
            "disagreements are listed in `reports/oratsouyts_reconciliation.md`; full "
            "machine-readable evidence remains under `.work/oratsouyts/`.",
            "",
        ]
    )
    return "\n".join(lines)


def _reconciliation_markdown(audit: Mapping[str, object]) -> str:
    source_irregularities = audit["source_irregularities"]
    method_disagreements = audit["extraction_method_disagreements"]
    semantic_disagreements = audit["semantic_extraction_disagreements"]
    annual_presence = audit["annual_occurrence_presence_variations"]
    source_identity_variations = audit["source_identity_variations"]
    runtime_summary = audit["runtime_mismatch_summary"]
    runtime_examples = audit["runtime_mismatch_examples"]
    april_24 = audit["april_24_evidence"]

    lines = [
        "# Oratsouyts reconciliation",
        "",
        "This is the review queue for places where annual sources, extraction "
        "representations, or the current public classifier do not line up. No item in "
        "this file is resolved by majority vote. An omitted source marker remains "
        "unknown unless a reviewed calendar rule establishes the value.",
        "",
        "## Printed-source irregularities",
        "",
        "These are accepted records. Alignment uses day-number sequence, so a printed "
        "weekday typo or punctuation omission cannot shift later dates.",
        "",
        "| Date | Kind | Printed | Independent expectation | Page |",
        "|---|---|---|---|---:|",
    ]
    for item in source_irregularities:
        lines.append(
            "| {date} | {kind} | `{printed}` | `{expected}` | {page} |".format(
                date=item["date"],
                kind=item["kind"],
                printed=item.get("printed") or "(missing)",
                expected=item.get("expected") or "(punctuation present)",
                page=item["physical_page"],
            )
        )
    if not source_irregularities:
        lines.append("| — | — | — | — | — |")

    lines.extend(
        [
            "",
            "## Independent extraction disagreements",
            "",
            "Poppler layout and raw-order output are intentionally compared. Raw-order "
            "text is canonical for semantic clauses only after both streams independently "
            "pass the complete-date gate. Full paired excerpts are in the local "
            "`.work/oratsouyts/records/<year>.json` files; `audit.json` contains "
            "only aggregate counts and example dates.",
            "",
            "| Year | Records flagged | Flag counts | Examples |",
            "|---:|---:|---|---|",
        ]
    )
    for year, row in sorted(method_disagreements.items(), key=lambda item: int(item[0])):
        flags = ", ".join(
            "`%s`: %d" % (flag, count)
            for flag, count in sorted(row["flags"].items())
        )
        lines.append(
            "| {} | {} | {} | {} |".format(
                year,
                row["records"],
                flags or "—",
                ", ".join(row["examples"]) or "—",
            )
        )

    lines.extend(
        [
            "",
            "## Extraction-level semantic differences",
            "",
            "This is the smaller, field-aware view of the text differences above. "
            "`raw_only` means raw order retained a positive fact that layout lost; "
            "`layout_only` means the reverse; `different` means both produced "
            "non-null but unequal values. Raw order remains canonical. Layout may "
            "augment saint descriptors only after raw order independently establishes "
            "a saints day, preventing broken Marian titles from becoming saints days. "
            "Complete paired values and clauses are in local "
            "`.work/oratsouyts/reconciliation.json`.",
            "",
            "| Year | Records | Field/direction counts | Examples |",
            "|---:|---:|---|---|",
        ]
    )
    for year, row in sorted(
            semantic_disagreements.items(), key=lambda item: int(item[0])):
        flags = ", ".join(
            "`%s`: %d" % (flag, count)
            for flag, count in sorted(row["flags"].items())
        )
        lines.append(
            "| {} | {} | {} | {} |".format(
                year,
                row["records"],
                flags or "—",
                ", ".join(row["examples"]) or "—",
            )
        )

    lines.extend(
        [
            "",
            "## Annual canonical-occurrence presence variations",
            "",
            "These rows mean a reviewed occurrence matcher found a feast or memorial in "
            "some annual clauses but not all available years. Possible causes include a "
            "collision, transfer, editorial wording, or matcher coverage. Absence is not "
            "automatically false.",
            "",
            "| Occurrence ID | Present years | Missing years | Counts by year |",
            "|---|---|---|---|",
        ]
    )
    for row in annual_presence:
        counts = ", ".join(
            "%s:%s" % (year, count) for year, count in sorted(row["counts"].items())
        )
        lines.append(
            "| `{}` | {} | {} | {} |".format(
                row["id"],
                _years_text(row["present_years"]),
                _years_text(row["missing_years"]),
                counts,
            )
        )
    if not annual_presence:
        lines.append("| — | — | — | — |")

    lines.extend(
        [
            "",
            "## Source-fact variants under one canonical runtime identity",
            "",
            "These are positive source assertions that differ even though the current "
            "English runtime identity is the same. They require either an era/occurrence "
            "variant or a correction to the canonical identity; merging their values "
            "would erase source information.",
            "",
            "| Runtime identity | Field | Source variants |",
            "|---|---|---|",
        ]
    )
    for row in source_identity_variations:
        variants = "; ".join(
            "`{}` in {}".format(variant["value"], _years_text(variant["years"]))
            for variant in row["variants"]
        )
        lines.append(
            "| {} | `{}` | {} |".format(
                _short_clause(row["runtime_identity"]), row["field"], variants
            )
        )
    if not source_identity_variations:
        lines.append("| — | — | — |")

    lines.extend(
        [
            "",
            "## April 24 editorial change point",
            "",
            "This fixed commemoration is a concrete reason not to flatten thirteen "
            "years into one majority value. The source wording changes by era; that "
            "change must remain explicit in any canonical rule.",
            "",
            "| Year | Holy-martyrs wording | Explicit requiem | Rest-hymn rubric | Source excerpt |",
            "|---:|---|---|---|---|",
        ]
    )
    for row in april_24:
        lines.append(
            "| {} | {} | {} | {} | {} |".format(
                row["year"],
                "yes" if row["holy_martyrs_wording"] else "no",
                "yes" if row["explicit_requiem"] else "no",
                "yes" if row["rest_hymn_rubric"] else "no",
                _short_clause(row["full_entry_excerpt"]),
            )
        )

    lines.extend(
        [
            "",
            "## Current runtime versus explicit positive source facts",
            "",
            "This comparison is directional: it reports when the source explicitly says "
            "a fact that the current `Calendar` response loses. It does not call source "
            "silence a runtime error. The build fails unless this exact set matches "
            "`dev/oratsouyts/runtime_reconciliation_allowlist.json`.",
            "",
            "| Field | Mismatched source records |",
            "|---|---:|",
        ]
    )
    for field, count in sorted(runtime_summary.items()):
        lines.append("| `{}` | {:,} |".format(field, count))

    lines.extend(
        [
            "",
            "Representative records (the complete list is in "
            "`.work/oratsouyts/reconciliation.json`):",
            "",
            "| Date | Field | Source | Runtime | Calendar clause |",
            "|---|---|---|---|---|",
        ]
    )
    for item in runtime_examples:
        lines.append(
            "| {date} | `{field}` | `{source}` | `{runtime}` | {clause} |".format(
                date=item["date"],
                field=item["field"],
                source=str(item["source_value"]).replace("|", "\\|"),
                runtime=str(item["runtime_value"]).replace("|", "\\|"),
                clause=_short_clause(item["calendar_clause"]),
            )
        )

    lines.extend(
        [
            "",
            "## Review decisions still required",
            "",
            "- Define the non-Sunday Dominical occurrence taxonomy; never substitute the dagger.",
            "- Consider whether the national memorial attached to Vardanants also needs "
            "a narrower subtype; its explicit marker is already retained in public "
            "`Is Memorial`.",
            "- Add reviewed canonical identity mappings where a saint class is biographical "
            "rather than explicit in the annual title.",
            "- Expand the Armenian descriptor patterns for declined or extraction-spaced "
            "forms such as `առաքելոցն` and `միայնակեցւոյն`; the runtime currently derives "
            "those classes from the canonical English identity, but the independent source "
            "evidence parser does not yet corroborate them.",
            "- Decide whether `illuminator` names only Saint Gregory himself or also his "
            "family and descendants. The current English-title matcher classifies the July "
            "25 sons-and-grandsons commemoration because its possessive title contains "
            "`Gregory the Illuminator`.",
            "- Reconcile annual omissions of fast markers around Assumption and Cross "
            "post-feasts before treating those omissions as negative assertions.",
            "",
        ]
    )
    return "\n".join(lines)


def build_corpus(
    source_dir: Path,
    work_dir: Path,
    reports_dir: Path,
    manifest_path: Path = SOURCE_MANIFEST_PATH,
    expectations_path: Path = DEFAULT_EXPECTATIONS_PATH,
    reconciliation_allowlist_path: Path = RUNTIME_RECONCILIATION_PATH,
) -> Dict[str, object]:
    """Extract, classify, compare, and write the complete local evidence corpus."""

    source_manifest = load_source_manifest(manifest_path)
    source_manifest_sha256 = sha256_file(manifest_path)
    reviewed_reconciliations = load_runtime_reconciliation_allowlist(
        reconciliation_allowlist_path
    )
    reconciliation_allowlist_sha256 = sha256_file(
        reconciliation_allowlist_path
    )
    sources = discover_sources(source_dir, source_manifest)
    record_dir = work_dir / "records"
    if record_dir.exists():
        expected_record_names = {"%d.json" % year for year in source_manifest}
        stale_record_names = sorted(
            path.name
            for path in record_dir.glob("*.json")
            if path.name not in expected_record_names
        )
        if stale_record_names:
            raise PipelineError(
                "Stale annual record outputs require review: %s"
                % ", ".join(stale_record_names)
            )
    source_rows: List[Dict[str, object]] = []
    all_evidence: List[Dict[str, object]] = []
    runtime_mismatches: List[Dict[str, object]] = []
    source_irregularities: List[Dict[str, object]] = []
    extraction_method_disagreements: Dict[str, object] = {}
    semantic_extraction_disagreements: Dict[str, object] = {}
    semantic_extraction_details: List[Dict[str, object]] = []
    occurrence_year_counts: MutableMapping[str, collections.Counter[int]] = (
        collections.defaultdict(collections.Counter)
    )
    runtime_identity_evidence: MutableMapping[str, List[Dict[str, object]]] = (
        collections.defaultdict(list)
    )
    year_output_hashes: Dict[str, str] = {}
    april_24: List[Dict[str, object]] = []

    field_known: MutableMapping[str, int] = collections.Counter()
    field_years: MutableMapping[str, set[int]] = collections.defaultdict(set)
    total_records = 0

    for year, path in sources:
        extracted = extract_year(path=path, year=year)
        expected_source = source_manifest[year]
        actual_source = extracted["source"]
        source_differences = {
            field: {"expected": expected_source[field], "actual": actual_source[field]}
            for field in ("filename", "sha256", "page_count")
            if actual_source[field] != expected_source[field]
        }
        if source_differences:
            raise PipelineError(
                "%d source differs from manifest: %s"
                % (year, json.dumps(source_differences, ensure_ascii=False))
            )
        quality = extracted["quality"]
        critical_extraction_disagreements = [
            disagreement
            for disagreement in quality["extraction_disagreements"]
            if {"header_provenance", "parsed_header_fields"}.intersection(
                disagreement["flags"]
            )
        ]
        if (
            quality["records"] != quality["expected_records"]
            or quality["missing_dates"]
            or quality["duplicate_dates"]
            or quality["mode_conflicts"]
            or critical_extraction_disagreements
        ):
            raise PipelineError("%d failed corpus acceptance gates" % year)

        method_counter: collections.Counter[str] = collections.Counter()
        method_examples: List[str] = []
        for disagreement in quality["extraction_disagreements"]:
            method_counter.update(disagreement["flags"])
            if len(method_examples) < 5:
                method_examples.append(disagreement["date"])
        extraction_method_disagreements[str(year)] = {
            "records": len(quality["extraction_disagreements"]),
            "flags": dict(sorted(method_counter.items())),
            "examples": method_examples,
        }

        for item in quality["weekday_conflicts"]:
            source_irregularities.append({"kind": "printed_weekday", **item})
        for item in quality["mode_conflicts"]:
            source_irregularities.append({"kind": "printed_mode", **item})
        for item in quality["mode_punctuation_warnings"]:
            source_irregularities.append(
                {
                    "kind": "mode_period_missing",
                    "expected": ".",
                    **item,
                }
            )

        evidence_records = [
            _classify_variant(record, "poppler_raw")
            for record in extracted["records"]
        ]
        layout_evidence_records = [
            _classify_variant(record, "poppler_layout")
            for record in extracted["records"]
        ]
        resolve_year_fast_contexts(evidence_records)
        resolve_year_fast_contexts(layout_evidence_records)

        semantic_counter: collections.Counter[str] = collections.Counter()
        semantic_examples: List[str] = []
        for record, raw_evidence, layout_evidence in zip(
                extracted["records"], evidence_records, layout_evidence_records):
            for field in _SOURCE_FIELD_ORDER:
                raw_value = raw_evidence["facts"][field]["value"]
                layout_value = layout_evidence["facts"][field]["value"]
                if raw_value == layout_value:
                    continue
                if raw_value is None:
                    direction = "layout_only"
                elif layout_value is None:
                    direction = "raw_only"
                else:
                    direction = "different"
                flag = "%s:%s" % (field, direction)
                semantic_counter[flag] += 1
                if record["date"] not in semantic_examples and len(
                        semantic_examples) < 5:
                    semantic_examples.append(record["date"])
                detail = {
                    "date": record["date"],
                    "year": year,
                    "field": field,
                    "direction": direction,
                    "poppler_raw": raw_value,
                    "poppler_layout": layout_value,
                    "raw_clause": raw_evidence["calendar_clause"],
                    "layout_clause": layout_evidence["calendar_clause"],
                }
                semantic_extraction_details.append(detail)
                if (
                    raw_value is not None
                    and layout_value is not None
                    and raw_value != layout_value
                    and field != "saint_classes"
                ):
                    raise PipelineError(
                        "%s has conflicting non-null %s extraction facts"
                        % (record["date"], field)
                    )
            augment_saint_classes_from_aligned_layout(
                raw_evidence, layout_evidence
            )
        semantic_extraction_disagreements[str(year)] = {
            "records": len({
                detail["date"]
                for detail in semantic_extraction_details
                if detail["year"] == year
            }),
            "flags": dict(sorted(semantic_counter.items())),
            "examples": semantic_examples,
        }

        for record, evidence in zip(extracted["records"], evidence_records):
            runtime_result = compute_armenian_lectionary(
                _datetime.date.fromisoformat(record["date"])
            )
            runtime = runtime_result["Calendar"]
            mismatches = explicit_positive_mismatches(evidence, runtime)
            for mismatch in mismatches:
                runtime_mismatches.append(
                    {
                        "date": record["date"],
                        "year": year,
                        "physical_page": record["physical_page"],
                        "calendar_clause": evidence["calendar_clause"],
                        **mismatch,
                    }
                )
            for field in _SOURCE_FIELD_ORDER:
                if evidence["facts"][field]["value"] is not None:
                    field_known[field] += 1
                    field_years[field].add(year)
            for occurrence in evidence["occurrences"]:
                occurrence_year_counts[occurrence["id"]][year] += 1
            explicit_classes = evidence["facts"]["saint_classes"]["value"]
            if explicit_classes is not None:
                runtime_identity_evidence[runtime_result["Liturgical Day"]].append(
                    {
                        "year": year,
                        "date": record["date"],
                        "saint_classes": explicit_classes,
                    }
                )
            all_evidence.append(evidence)
            if record["date"].endswith("-04-24"):
                full_text = record["normalized_text"]
                april_24.append(
                    {
                        "year": year,
                        "calendar_clause": evidence["calendar_clause"],
                        "holy_martyrs_wording": bool(
                            re.search(r"սրբոց\s+նահատակաց", full_text, re.I)
                        ),
                        "explicit_requiem": bool(
                            re.search(r"հոգեհանգիստ", full_text, re.I)
                        ),
                        "rest_hymn_rubric": bool(
                            re.search(r"Հանգստեան\s+շարականի", full_text, re.I)
                        ),
                        "full_entry_excerpt": _short_clause(full_text, limit=500),
                    }
                )
        total_records += len(evidence_records)
        extracted["calendar_evidence"] = evidence_records
        year_output_hashes[str(year)] = _write_json(
            record_dir / ("%d.json" % year), extracted
        )
        source_rows.append(_source_row(extracted))

    expected_records = sum(
        366 if calendar.isleap(year) else 365 for year, _ in sources
    )
    if total_records != expected_records:
        raise PipelineError(
            "Corpus has %d records; expected %d" % (total_records, expected_records)
        )

    all_years = [year for year, _ in sources]
    occurrence_coverage = {
        occurrence_id: {
            "records": sum(counts.values()),
            "years": sorted(counts),
            "counts": {str(year): counts[year] for year in sorted(counts)},
        }
        for occurrence_id, counts in sorted(occurrence_year_counts.items())
    }
    annual_presence_variations = []
    for occurrence_id, row in occurrence_coverage.items():
        if not occurrence_id.startswith(("feast:", "memorial:")):
            continue
        present = row["years"]
        missing = [year for year in all_years if year not in present]
        if missing:
            annual_presence_variations.append(
                {
                    "id": occurrence_id,
                    "present_years": present,
                    "missing_years": missing,
                    "counts": row["counts"],
                }
            )

    source_identity_variations: List[Dict[str, object]] = []
    for runtime_identity, rows in sorted(runtime_identity_evidence.items()):
        variants: MutableMapping[Tuple[str, ...], List[Dict[str, object]]] = (
            collections.defaultdict(list)
        )
        for row in rows:
            variants[tuple(row["saint_classes"])].append(row)
        if len(variants) <= 1:
            continue
        source_identity_variations.append(
            {
                "runtime_identity": runtime_identity,
                "field": "saint_classes",
                "variants": [
                    {
                        "value": list(value),
                        "years": sorted({item["year"] for item in variant_rows}),
                        "dates": [item["date"] for item in variant_rows],
                    }
                    for value, variant_rows in sorted(variants.items())
                ],
            }
        )

    mismatch_counts = collections.Counter(
        item["field"] for item in runtime_mismatches
    )
    actual_reconciliations = sorted(
        [
            {
                "date": item["date"],
                "field": item["field"],
                "source_value": item["source_value"],
                "runtime_value": item["runtime_value"],
            }
            for item in runtime_mismatches
        ],
        key=lambda item: (item["date"], item["field"]),
    )
    expected_reconciliations = [
        {
            "date": item["date"],
            "field": item["field"],
            "source_value": item["source_value"],
            "runtime_value": item["runtime_value"],
        }
        for item in reviewed_reconciliations
    ]
    if actual_reconciliations != expected_reconciliations:
        raise PipelineError(
            "Runtime mismatches differ from reviewed allowlist: actual=%s expected=%s"
            % (
                json.dumps(actual_reconciliations, ensure_ascii=False),
                json.dumps(expected_reconciliations, ensure_ascii=False),
            )
        )
    expectations_fixture = _expectations_fixture(
        all_evidence,
        reviewed_reconciliations,
        source_manifest_sha256,
        reconciliation_allowlist_sha256,
    )
    examples: List[Dict[str, object]] = []
    seen_example_fields: collections.Counter[str] = collections.Counter()
    for mismatch in runtime_mismatches:
        field = mismatch["field"]
        if seen_example_fields[field] >= 5:
            continue
        examples.append(mismatch)
        seen_example_fields[field] += 1

    totals = {
        "sources": len(sources),
        "expected_records": expected_records,
        "records": total_records,
        "weekday_conflicts": sum(row["weekday_conflicts"] for row in source_rows),
        "mode_conflicts": sum(row["mode_conflicts"] for row in source_rows),
        "mode_punctuation_warnings": sum(
            row["mode_punctuation_warnings"] for row in source_rows
        ),
        "extraction_disagreements": sum(
            row["extraction_disagreements"] for row in source_rows
        ),
        "runtime_explicit_positive_mismatches": len(runtime_mismatches),
        "expectation_cases": len(expectations_fixture["cases"]),
    }
    field_coverage = {
        field: {
            "known": field_known[field],
            "unknown": total_records - field_known[field],
            "years": sorted(field_years[field]),
        }
        for field in _SOURCE_FIELD_ORDER
    }
    audit = {
        "schema_version": SCHEMA_VERSION,
        "extractor_version": EXTRACTOR_VERSION,
        "source_manifest_sha256": source_manifest_sha256,
        "reconciliation_allowlist_sha256": reconciliation_allowlist_sha256,
        "tools": {
            "pdftotext": tool_version("pdftotext"),
            "pdfinfo": tool_version("pdfinfo"),
        },
        "totals": totals,
        "sources": source_rows,
        "field_coverage": field_coverage,
        "occurrence_coverage": occurrence_coverage,
        "source_irregularities": sorted(
            source_irregularities, key=lambda item: (item["date"], item["kind"])
        ),
        "extraction_method_disagreements": extraction_method_disagreements,
        "semantic_extraction_disagreements": semantic_extraction_disagreements,
        "annual_occurrence_presence_variations": annual_presence_variations,
        "source_identity_variations": source_identity_variations,
        "april_24_evidence": april_24,
        "runtime_mismatch_summary": dict(sorted(mismatch_counts.items())),
        "runtime_mismatch_examples": examples,
        "year_output_sha256": year_output_hashes,
    }
    reconciliation_detail = {
        "schema_version": SCHEMA_VERSION,
        "source_irregularities": audit["source_irregularities"],
        "extraction_method_disagreements": extraction_method_disagreements,
        "semantic_extraction_disagreements": semantic_extraction_disagreements,
        "semantic_extraction_disagreement_details": semantic_extraction_details,
        "annual_occurrence_presence_variations": annual_presence_variations,
        "source_identity_variations": source_identity_variations,
        "april_24_evidence": april_24,
        "runtime_explicit_positive_mismatches": runtime_mismatches,
    }
    audit_sha256 = _write_json(work_dir / "audit.json", audit)
    reconciliation_sha256 = _write_json(
        work_dir / "reconciliation.json", reconciliation_detail
    )
    reports_dir.mkdir(parents=True, exist_ok=True)
    _write_json(expectations_path, expectations_fixture)
    (reports_dir / "oratsouyts_coverage.md").write_text(
        _coverage_markdown(audit), encoding="utf-8"
    )
    (reports_dir / "oratsouyts_reconciliation.md").write_text(
        _reconciliation_markdown(audit), encoding="utf-8"
    )
    output_hashes = {
        "audit.json": audit_sha256,
        "reconciliation.json": reconciliation_sha256,
    }
    output_hashes.update(
        {
            "records/%s.json" % year: digest
            for year, digest in sorted(year_output_hashes.items())
        }
    )
    output_hashes.update(
        {
            "expectations/oratsouyts_calendar_expectations.json": sha256_file(
                expectations_path
            ),
            "reports/oratsouyts_coverage.md": sha256_file(
                reports_dir / "oratsouyts_coverage.md"
            ),
            "reports/oratsouyts_reconciliation.md": sha256_file(
                reports_dir / "oratsouyts_reconciliation.md"
            ),
        }
    )
    _write_json(
        work_dir / "checksums.json",
        {"schema_version": SCHEMA_VERSION, "outputs": output_hashes},
    )
    return audit


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument(
        "--manifest", type=Path, default=SOURCE_MANIFEST_PATH,
        help="reviewed exact source inventory (default: %(default)s)",
    )
    parser.add_argument(
        "--reconciliation-allowlist",
        type=Path,
        default=RUNTIME_RECONCILIATION_PATH,
        help="reviewed permitted runtime differences (default: %(default)s)",
    )
    parser.add_argument(
        "--work-dir", type=Path, default=Path(".work/oratsouyts")
    )
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    parser.add_argument(
        "--expectations",
        type=Path,
        default=DEFAULT_EXPECTATIONS_PATH,
        help="committed source-positive CI fixture (default: %(default)s)",
    )
    args = parser.parse_args(argv)
    audit = build_corpus(
        source_dir=args.source_dir.resolve(),
        work_dir=args.work_dir.resolve(),
        reports_dir=args.reports_dir.resolve(),
        manifest_path=args.manifest.resolve(),
        expectations_path=args.expectations.resolve(),
        reconciliation_allowlist_path=args.reconciliation_allowlist.resolve(),
    )
    print(
        "Accepted {records:,}/{expected_records:,} dates from {sources} PDFs; "
        "{mismatches:,} explicit-positive runtime mismatches.".format(
            records=audit["totals"]["records"],
            expected_records=audit["totals"]["expected_records"],
            sources=audit["totals"]["sources"],
            mismatches=audit["totals"]["runtime_explicit_positive_mismatches"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
