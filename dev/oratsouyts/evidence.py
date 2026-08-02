"""Extract conservative calendar-level evidence from Oratsouyts records.

This module deliberately does *not* select daily-service propers.  It identifies
only the source facts that can feed the public ``Calendar`` response.  Most
source fields use a three-state model: an explicit positive assertion is
``True``; source silence is ``None`` (unknown), never an inferred ``False``.

The annual books contain many words such as ``Խաչ`` and ``Աստուածածին`` inside
service rubrics.  Matching is therefore restricted to the calendar-clause zone
produced by :mod:`dev.oratsouyts.extract`, not the complete daily entry.
"""

from __future__ import annotations

import datetime as _datetime
import re
import unicodedata
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


_INVISIBLE_RE = re.compile(r"[\u00ad\u200b\u200c\u200d\u2060]")
_SPACE_RE = re.compile(r"\s+")


def normalize_evidence_text(text: str) -> str:
    """Return stable Unicode text suitable for source-level pattern matching."""

    text = unicodedata.normalize("NFC", text or "")
    text = _INVISIBLE_RE.sub("", text)
    return _SPACE_RE.sub(" ", text).strip()


def _compile(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


# Named fasts are ordered from most specific to least specific.  Some annual
# books abbreviate ``Սուրբ`` as ``Ս.`` and some omit it entirely.
_FAST_CONTEXT_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    (
        "fast_of_varaga_cross",
        _compile(r"(?:[Ա-Ֆ]{1,5}|[0-9]{1,2})\s*օր\s*Վարագայ\s*"
                 r"(?:Սրբոյ\s*)?Խաչի\s*պահոց"),
    ),
    (
        "fast_of_saint_james",
        _compile(r"(?:[Ա-Ֆ]{1,5}|[0-9]{1,2})\s*օր\s*"
                 r"(?:Ս\.?\s*)?Յակովբայ\s*պահոց"),
    ),
    ("fast_of_catechumens", _compile(r"Առաջաւորաց\s*պահոց")),
    ("great_lent", _compile(r"(?:Մեծի\s*Պահոց|Քառասնորդական)")),
    ("fast_of_prophet_elijah", _compile(r"Եղիական\s*պահոց")),
    (
        "fast_of_saint_gregory",
        _compile(r"(?:Ս\.?\s*)?Գրիգոր(?:ի)?\s*Լուսաւորչի\s*պահոց"),
    ),
    ("fast_of_transfiguration", _compile(r"Վարդավառի\s*պահոց")),
    (
        "fast_of_assumption",
        _compile(r"(?:Ս\.?\s*)?Աստուածածնի\s*պահոց"),
    ),
    (
        "fast_of_holy_cross",
        _compile(r"(?<!Վարագայ\s)(?:Ս\.?\s*)?Խաչի\s*պահոց"),
    ),
    ("fast_of_advent", _compile(r"Յիսնակ(?:ի|աց)\s*պահոց")),
    (
        "fast_of_nativity",
        _compile(r"(?:Ս\.?\s*)?Ծննդեան\s*պահոց"),
    ),
)

_STANDALONE_FAST_RE = _compile(r"(?:^|[:։]\s*)Պահք(?=\s*[:։.]|\s|$)")
_NUMBERED_FAST_DAY_RE = _compile(
    r"(?:[Ա-Ֆ]{1,5}|[0-9]{1,2})\.?\s*օր\s*[^:։]{0,100}?պահոց\b"
)
_FAST_BEGIN_RE = _compile(r"Սկիզբն\s+պահոց")
_FAST_EVE_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    (
        "fast_eve:catechumens",
        _compile(r"Բարեկենդան\s+Առաջաւորաց\s+պահոց"),
    ),
    (
        "fast_eve:prophet_elijah",
        _compile(r"Բարեկենդան\s+Եղիական\s+պահոց"),
    ),
    (
        "fast_eve:saint_gregory",
        _compile(r"Բարեկենդան\s+(?:Ս\.?\s*)?Գրիգոր(?:ի)?\s+"
                 r"Լուսաւորչի\s+պահոց"),
    ),
    (
        "fast_eve:transfiguration",
        _compile(r"Բարեկենդան\s+Վարդավառի\s+պահոց"),
    ),
    (
        "fast_eve:assumption",
        _compile(r"Բարեկենդան\s+(?:Ս\.?\s*)?Աստուածածնի\s+պահոց"),
    ),
    (
        "fast_eve:holy_cross",
        _compile(r"Բարեկենդան\s+(?:Ս\.?\s*)?Խաչի\s+պահոց"),
    ),
    (
        "fast_eve:varaga_cross",
        _compile(r"Բարեկենդան\s+Վարագայ\s+(?:Սրբոյ\s+)?Խաչի(?:ն)?"),
    ),
    (
        "fast_eve:advent",
        _compile(r"Բարեկենդան\s+Յիսնակ(?:ի|աց)\s+պահոց"),
    ),
    (
        "fast_eve:saint_james",
        _compile(r"Բարեկենդան\s+(?:Ս\.?\s*)?Յակովբայ\s+պահոց"),
    ),
    (
        "fast_eve:nativity",
        _compile(r"Բարեկենդան\s+(?:Ս\.?\s*)?Ծննդեան\s+պահոց"),
    ),
)


_CROSS_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    ("feast:cross:appearance", _compile(r"(?:Տօն\s+)?Երեւ(?:ումն|ման)\s+(?:Ս\.?\s*)?Խաչի?")),
    ("feast:cross:exaltation", _compile(r"ԽԱՉՎԵՐԱՑ")),
    (
        "feast:cross:cross_octave",
        _compile(r"Տօն\s+(?:է\s+)?(?:Ս\.?\s*)?Խաչի"),
    ),
    (
        "feast:cross:varaga_cross",
        _compile(r"Տօն\s+(?:է\s+)?Վարագայ\s+(?:Սրբոյ\s+)?Խաչի"),
    ),
    ("feast:cross:discovery", _compile(r"Գիւտ\s*(?:Ս\.?\s*)?Խաչի")),
)

_MARIAN_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    (
        "feast:marian:annunciation",
        _compile(r"Ա\s*ւետումն\s+(?:Ս\.?\s*)?Աստուածածնի"),
    ),
    (
        "feast:marian:assumption",
        _compile(r"ՎԵՐԱՓՈԽՈՒՄՆ?\s*(?:ՍՈՒՐԲ\s*)?ԱՍՏՈՒԱԾԱԾՆԻ"),
    ),
    (
        "feast:marian:assumption_postfeast",
        _compile(
            r"(?:(?:[Բ-Թ])\.?\s+օր\s+Վերափոխման|"
            r"Բ\.?\s+կիր\.?\s+զկնի\s+Վերափոխման)"
        ),
    ),
    (
        "feast:marian:nativity_theotokos",
        _compile(r"Ծննդեան\s+Սրբուհւոյ\s+Կուսին\s+Մարիամ"),
    ),
    (
        "feast:marian:presentation",
        _compile(r"(?:Ընծայումն|Տաճարամուտ)\s+(?:Ս\.?\s*)?Աստուածածնի"),
    ),
    (
        "feast:marian:conception",
        _compile(r"Յղութիւն\s*(?:Ս\.?\s*)?Աստուածածնի"),
    ),
    (
        "feast:marian:discovery_box",
        _compile(r"(?:Տօն\s+)?գիւտի?\s+(?:տփոյ|տուփի)\s+"
                 r"(?:Սրբուհւոյ\s+)?Աստուածածնի"),
    ),
    (
        "feast:marian:discovery_belt",
        _compile(r"(?:Տօն\s+)?գիւտի?\s+գ[օո]տւոյ\s+"
                 r"(?:Սրբուհւոյ\s+)?Աստուածածնի"),
    ),
)

# Later Sundays described merely as being "after Assumption" are positional,
# not Marian feasts.  The first post-feast days are resolved from their reviewed
# Assumption-anchor coordinate by the evidence aggregator rather than by this
# lexical matcher.
_MEMORIAL_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    ("memorial:dead", _compile(r"ՅԻՇԱՏԱԿ\s+ՄԵՌԵԼՈՑ")),
    (
        "memorial:dead_and_national_feast",
        _compile(r"Յիշատակ\s+մեռելոց\s+(?:եւ|և)\s+տօն\s+ազգային"),
    ),
    ("memorial:all_departed", _compile(r"համօրէն\s+ննջեցելոց")),
)

_SAINT_SIGNAL_RE = _compile(
    r"(?:Սրբոցն?|Սրբոյն|Սրբուհւոյ|սրբոց\s+նահատակաց|"
    r"Տօն\s+Ծննդեան\s+Ս\.?\s*Յովհաննու\s+Կարապետին|"
    r"Գիւտ\s+նշխարաց\s+Սրբոյն)"
)

# A bare ``Ս.`` is not accepted as a saint signal because it also names the
# Cross, Theotokos, Nativity, Church, Trinity, and Resurrection.  Only reviewed
# unambiguous title forms are accepted here.
_SAINT_CLASS_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    ("apostle", _compile(r"առաքեալ|աւետարանիչ|աշակերտ")),
    ("prophet", _compile(r"մարգարէ")),
    (
        "martyr",
        _compile(
            r"(?:\bվկայ(?:իցն?|աց|ք|քն|ն)?\b|"
            r"\bնահատակ[Ա-Ֆա-ֆ]*\b|\bնախավկայ[Ա-Ֆա-ֆ]*\b)"
        ),
    ),
    (
        "hierarch",
        _compile(
            r"հ\s*ա\s*յ\s*ր\s*ա\s*պ\s*ե\s*տ|"
            r"ե\s*պ\s*ի\s*ս\s*կ\s*ո\s*պ\s*ո\s*ս|"
            r"կ\s*ա\s*թ\s*ո\s*ղ\s*ի\s*կ\s*ո\s*ս|պատրիարք"
        ),
    ),
    (
        "vartapet",
        _compile(
            r"վ\s*ա\s*ր\s*դ\s*ա\s*պ\s*ե\s*տ|"
            r"ա\s*ս\s*տ\s*ո\s*ւ\s*ա\s*ծ\s*ա\s*բ\s*ա\s*ն"
        ),
    ),
    (
        "monastic",
        _compile(
            r"ճգնաւո-\s*(?:[0-9Ա-Ֆ]+\s+){1,12}ր|"
            r"ճ\s*գ\s*ն\s*ա\s*ւ\s*ո\s*ր|"
            r"մ\s*ե\s*ն\s*ա\s*կ\s*ե\s*ա\s*ց|"
            r"ա\s*ն\s*ա\s*պ\s*ա\s*տ\s*ա\s*կ\s*ա\s*ն|"
            r"ս\s*ի\s*ւ\s*ն\s*ա\s*կ\s*ե\s*ա\s*ց"
        ),
    ),
    ("virgin", _compile(r"(?:^|\W)կոյս|կուս(?:ին|անաց)")),
    ("illuminator", _compile(r"Լուսաւորիչ")),
    (
        "hripsimian",
        _compile(r"Հ\s*ռ\s*ի\s*փ\s*ս\s*ի\s*մ\s*ե\s*ա\s*ն\s*ց"),
    ),
)


def _matches(
    text: str,
    patterns: Sequence[Tuple[str, re.Pattern[str]]],
) -> List[Dict[str, object]]:
    found: List[Dict[str, object]] = []
    for identifier, pattern in patterns:
        match = pattern.search(text)
        if match:
            found.append(
                {
                    "id": identifier,
                    "evidence": match.group(0),
                    "span": [match.start(), match.end()],
                }
            )
    return found


def _without_spans(text: str, matches: Sequence[Dict[str, object]]) -> str:
    """Blank reviewed non-saint identity spans before saint-title matching."""

    characters = list(text)
    for match in matches:
        start, end = match["span"]
        characters[int(start):int(end)] = " " * (int(end) - int(start))
    return "".join(characters)


def _fact(
    value: object,
    basis: str,
    evidence: Optional[Iterable[str]] = None,
    confidence: str = "explicit",
) -> Dict[str, object]:
    return {
        "value": value,
        "basis": basis,
        "confidence": confidence,
        "evidence": list(evidence or ()),
    }


def classify_explicit_record(record: Dict[str, object]) -> Dict[str, object]:
    """Classify only facts explicitly supported by one extracted daily record."""

    date = _datetime.date.fromisoformat(str(record["date"]))
    clause = normalize_evidence_text(
        str(record.get("calendar_clause") or record.get("heading") or "")
    )
    entry_text = normalize_evidence_text(str(record.get("normalized_text") or clause))
    header = record.get("header") or {}

    # Patterns are most-specific first.  A Varaga Cross phrase also contains
    # the words matched by the generic Holy Cross pattern, but represents one
    # context and must emit only one canonical occurrence.
    fast_context_matches = _matches(clause, _FAST_CONTEXT_PATTERNS)[:1]
    fast_context = (
        str(fast_context_matches[0]["id"]) if fast_context_matches else None
    )
    numbered_fast = _NUMBERED_FAST_DAY_RE.search(clause)
    standalone_fast = _STANDALONE_FAST_RE.search(clause)
    fast_begin = _FAST_BEGIN_RE.search(clause)
    fast_eve_matches = _matches(entry_text, _FAST_EVE_PATTERNS)
    holy_week = bool(header.get("holy_week_prefix"))
    explicit_fast = bool(numbered_fast or standalone_fast or fast_begin or holy_week)
    if holy_week:
        fast_context = "holy_week"

    cross_matches = _matches(clause, _CROSS_PATTERNS)
    marian_matches = _matches(clause, _MARIAN_PATTERNS)
    # Exact memorial banners are often printed after the service appointments.
    # Unlike feast-family keywords, these reviewed phrases are safe to match
    # within the already-bounded daily record.
    memorial_matches = _matches(entry_text, _MEMORIAL_PATTERNS)
    # A fast merely named for a saint and a Marian title such as ``Սրբուհւոյ
    # Կուսին Մարիամու`` must not enter the generic saints branch.  Blank only
    # reviewed non-saint spans; a separate saints clause on the same date remains.
    non_saint_matches = list(fast_context_matches) + cross_matches + marian_matches
    saint_text = _without_spans(clause, non_saint_matches)
    saint_signal = _SAINT_SIGNAL_RE.search(saint_text)
    if saint_signal and re.search(r"Տօն\s*Շողակաթի", clause, re.I):
        # The title describes the feast of Holy Etchmiadzin "according to the
        # vision of St Gregory"; it is not a commemoration of Gregory himself.
        saint_signal = None
    saint_class_matches = [
        (identifier, match)
        for identifier, pattern in _SAINT_CLASS_PATTERNS
        for match in ([pattern.search(saint_text)] if saint_signal else [])
        if match
    ]
    saint_classes = [identifier for identifier, _match in saint_class_matches]

    occurrences: List[Dict[str, object]] = []
    occurrences.extend(
        {
            "id": "fast:%s" % str(match["id"]).removeprefix("fast_of_"),
            "kind": "fast",
            "confidence": "explicit",
            "evidence": match["evidence"],
        }
        for match in fast_context_matches
    )
    if holy_week:
        occurrences.append(
            {
                "id": "fast:holy_week",
                "kind": "fast",
                "confidence": "explicit",
                "evidence": "Աւագ",
            }
        )
    if explicit_fast and not fast_context:
        occurrences.append(
            {
                "id": "fast:unresolved",
                "kind": "fast",
                "confidence": "explicit_context_unknown",
                "evidence": (
                    numbered_fast.group(0)
                    if numbered_fast
                    else standalone_fast.group(0)
                    if standalone_fast
                    else fast_begin.group(0)
                    if fast_begin
                    else "Աւագ"
                ),
            }
        )
    occurrences.extend(
        {
            "id": match["id"],
            "kind": "fast_eve",
            "confidence": "explicit",
            "evidence": match["evidence"],
        }
        for match in fast_eve_matches
    )
    for match in cross_matches + marian_matches + memorial_matches:
        occurrences.append(
            {
                "id": match["id"],
                "kind": str(match["id"]).split(":", 1)[0],
                "confidence": "explicit",
                "evidence": match["evidence"],
            }
        )

    return {
        "date": date.isoformat(),
        "calendar_clause": clause,
        "source_has_dagger": bool(header.get("dagger")),
        "occurrences": occurrences,
        "facts": {
            "weekday": _fact(
                date.strftime("%A"), "civil_date", confidence="deterministic"
            ),
            "is_sunday": _fact(
                date.weekday() == 6, "civil_date", confidence="deterministic"
            ),
            # The annual dagger is not a Dominical marker.  Non-Sunday taxonomy
            # must be assigned by a separately reviewed canonical occurrence map.
            "is_dominical": _fact(
                True if date.weekday() == 6 else None,
                "sunday_only; non_sunday_unknown",
                confidence="partial",
            ),
            "is_fast_day": _fact(
                True if explicit_fast else None,
                "explicit_fast_marker" if explicit_fast else "source_silence",
                [
                    value
                    for value in (
                        numbered_fast.group(0) if numbered_fast else None,
                        standalone_fast.group(0) if standalone_fast else None,
                        fast_begin.group(0) if fast_begin else None,
                        "Աւագ" if holy_week else None,
                    )
                    if value
                ],
            ),
            "fast_context": _fact(
                fast_context,
                "explicit_named_fast" if fast_context else "unresolved_or_absent",
                [str(match["evidence"]) for match in fast_context_matches],
            ),
            "is_saints_day": _fact(
                True if saint_signal else None,
                "explicit_saint_title" if saint_signal else "source_silence",
                [saint_signal.group(0)] if saint_signal else [],
            ),
            "saint_classes": _fact(
                saint_classes if saint_classes else None,
                "explicit_title_descriptors" if saint_classes else "not_established",
                [
                    "%s: %s" % (identifier, match.group(0))
                    for identifier, match in saint_class_matches
                ],
            ),
            "is_cross_feast": _fact(
                True if cross_matches else None,
                "canonical_cross_title" if cross_matches else "source_silence",
                [str(match["evidence"]) for match in cross_matches],
            ),
            "is_marian_feast": _fact(
                True if marian_matches else None,
                "canonical_marian_title" if marian_matches else "source_silence",
                [str(match["evidence"]) for match in marian_matches],
            ),
            "is_memorial": _fact(
                True if memorial_matches else None,
                "canonical_memorial_marker" if memorial_matches else "source_silence",
                [str(match["evidence"]) for match in memorial_matches],
            ),
        },
    }


def augment_saint_classes_from_aligned_layout(
    canonical: Dict[str, object],
    layout: Dict[str, object],
) -> None:
    """Recover explicit descriptors split only in Poppler raw-order text.

    Raw order is canonical because it preserves calendar clauses that layout can
    omit.  Layout is nevertheless useful for words that raw order splits internally
    (for example ``Աս տուածաբանին``).  Only augment the class set after raw order has
    independently established a saints day.  This guard prevents folio numbers inside
    a Marian title from turning that feast into a generic saints day.
    """

    if canonical["facts"]["is_saints_day"]["value"] is not True:
        return
    layout_classes = layout["facts"]["saint_classes"]["value"] or []
    if not layout_classes:
        return
    canonical_fact = canonical["facts"]["saint_classes"]
    existing = set(canonical_fact["value"] or [])
    merged = [
        identifier
        for identifier, _pattern in _SAINT_CLASS_PATTERNS
        if identifier in existing or identifier in layout_classes
    ]
    if merged == (canonical_fact["value"] or []):
        return
    canonical_fact.update(
        {
            "value": merged,
            "basis": "explicit_title_descriptors_across_aligned_extractors",
            "confidence": "explicit",
            "evidence": list(dict.fromkeys(
                list(canonical_fact["evidence"])
                + list(layout["facts"]["saint_classes"]["evidence"])
            )),
        }
    )


def resolve_year_fast_contexts(
    evidence_records: Sequence[Dict[str, object]],
) -> None:
    """Resolve plain ``Պահք`` records from source-marked annual windows.

    The Varaga Cross and St James calendars print their Barekendan marker at
    the end of the governing Sunday entry; the following Monday-Friday clauses
    usually say only ``Պահք``.  Resolve those two five-day windows first, then
    apply the source-supported fallback of ``weekly_fast`` to every remaining
    explicit fast whose context is unnamed.
    """

    window_contexts = {
        "fast_eve:catechumens": "fast_of_catechumens",
        "fast_eve:prophet_elijah": "fast_of_prophet_elijah",
        "fast_eve:saint_gregory": "fast_of_saint_gregory",
        "fast_eve:transfiguration": "fast_of_transfiguration",
        "fast_eve:assumption": "fast_of_assumption",
        "fast_eve:holy_cross": "fast_of_holy_cross",
        "fast_eve:varaga_cross": "fast_of_varaga_cross",
        "fast_eve:advent": "fast_of_advent",
        "fast_eve:saint_james": "fast_of_saint_james",
        "fast_eve:nativity": "fast_of_nativity",
    }

    def assign(record: Dict[str, object], context: str, basis: str) -> None:
        fact = record["facts"]["fast_context"]
        if fact["value"] is not None:
            return
        fact.update(
            {
                "value": context,
                "basis": basis,
                "confidence": "derived_from_explicit_source_window",
                "evidence": [basis],
            }
        )
        occurrence_id = "fast:%s" % context.removeprefix("fast_of_")
        for occurrence in record["occurrences"]:
            if occurrence["id"] == "fast:unresolved":
                occurrence.update(
                    {
                        "id": occurrence_id,
                        "confidence": "derived_from_explicit_source_window",
                        "evidence": basis,
                    }
                )
                break

    for index, evidence in enumerate(evidence_records):
        ids = {item["id"] for item in evidence["occurrences"]}
        for eve_id, context in window_contexts.items():
            if eve_id not in ids:
                continue
            for following in evidence_records[index + 1:index + 6]:
                if following["facts"]["is_fast_day"]["value"] is True:
                    assign(following, context, eve_id)

    for evidence in evidence_records:
        if evidence["facts"]["is_fast_day"]["value"] is True:
            assign(evidence, "weekly_fast", "unnamed_explicit_fast_fallback")


def explicit_positive_mismatches(
    evidence: Dict[str, object],
    runtime_calendar: Dict[str, object],
) -> List[Dict[str, object]]:
    """Compare source-positive facts with a runtime ``Calendar`` response.

    Unknown source fields are intentionally ignored.  This avoids interpreting a
    source omission as a contradiction.
    """

    key_map = {
        "weekday": "Weekday",
        "is_sunday": "Is Sunday",
        "is_dominical": "Is Dominical",
        "is_fast_day": "Is Fast Day",
        "fast_context": "Fast Context",
        "is_saints_day": "Is Saints Day",
        "saint_classes": "Saint Classes",
        "is_cross_feast": "Is Cross Feast",
        "is_marian_feast": "Is Marian Feast",
        "is_memorial": "Is Memorial",
    }
    mismatches: List[Dict[str, object]] = []
    facts = evidence["facts"]
    for source_key, runtime_key in key_map.items():
        source_value = facts[source_key]["value"]
        if source_value is None:
            continue
        runtime_value = runtime_calendar.get(runtime_key)
        if source_key == "saint_classes":
            missing = sorted(set(source_value) - set(runtime_value or []))
            if not missing:
                continue
            detail = {"missing_explicit_classes": missing}
        elif runtime_value == source_value:
            continue
        else:
            detail = {}
        mismatches.append(
            {
                "field": source_key,
                "source_value": source_value,
                "runtime_value": runtime_value,
                "source_basis": facts[source_key]["basis"],
                "source_evidence": facts[source_key]["evidence"],
                **detail,
            }
        )
    return mismatches
