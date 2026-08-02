"""Deterministically extract the new-calendar daily Oratsouyts records.

The annual books contain a detailed new-calendar section and, in most editions,
an independent old-calendar section.  They also use several physical layouts.
This module:

* extracts independent Poppler ``-layout`` and ``-raw`` text page by page;
* splits imposed landscape spreads into left and right logical pages;
* decodes the 2013 legacy Armenian font;
* finds the earliest complete civil-date sequence (the new-calendar section);
* preserves raw/decoded/normalized excerpts and physical-page provenance; and
* validates printed weekday and mode independently of sequence alignment.

It is build tooling only.  No PDF parser or annual record table is loaded by the
runtime package.
"""

from __future__ import annotations

import datetime as _datetime
import hashlib
import math
import re
import shutil
import subprocess
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from dev.oratsouyts.encoding import decode_legacy_armenian


WEEKDAY_CODES = ("Բշ", "Գշ", "Դշ", "Եշ", "Ուր", "Շբ", "Կիր")
WEEKDAY_NAMES = (
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
    "Sunday",
)
MODES = ("ԱՁ", "ԱԿ", "ԲՁ", "ԲԿ", "ԳՁ", "ԳԿ", "ԴՁ", "ԴԿ")

_PAGE_COUNT_RE = re.compile(r"(?m)^Pages:\s+(?P<count>[0-9]+)\s*$")
_PAGE_SIZE_RE = re.compile(
    r"(?m)^Page\s+(?P<page>[0-9]+)\s+size:\s+"
    r"(?P<width>[0-9.]+)\s+x\s+(?P<height>[0-9.]+)\s+pts\s*$"
)

# Mode is optional here so a damaged mode token cannot erase a date boundary.
# It remains mandatory at the validation gate and will be recorded as a warning
# if absent.  Some editions expose "Ա­ ւագ" after layout extraction; line
# normalization repairs that one known split before applying this expression.
DATE_HEADER_RE = re.compile(
    r"^"
    # Poppler -raw can place the lunar day from the opposite margin before the
    # civil day (for example ``13 18 † Աւագ Եշ.``).  It is source
    # evidence, not the alignment day, so capture it separately.
    r"(?:(?P<marginal_lunar_day>[0-9]{1,2})\s+)?"
    r"(?P<day>[1-9]|[12][0-9]|3[01])\s*"
    r"(?P<dagger>†)?\s*"
    # Several editions concatenate the Holy Week label and weekday in their
    # raw content stream (``ԱւագԳշ.``), although they render with a
    # visible gap.  The weekday token makes the zero-width boundary unambiguous.
    r"(?:(?P<holy_week>Աւագ)\s*)?"
    r"(?P<weekday>Բշ|Գշ|Դշ|Եշ|Ուր|Շբ|Կիր)\s*\."
    # The 2016 source omits the period after one otherwise unambiguous mode
    # token.  Preserve that typography as evidence without losing the mode.
    r"(?:\s*(?P<mode>ԱՁ|ԱԿ|ԲՁ|ԲԿ|ԳՁ|ԳԿ|ԴՁ|ԴԿ)\s*(?P<mode_period>\.)?)?"
)

_OLD_CALENDAR_MARKER_RE = re.compile(r"Ըստ\s+հին\s+տոմարի", re.IGNORECASE)
_ARMENIAN_CHAR = r"\u0531-\u0587"
_VISIBLE_LINE_HYPHEN_RE = re.compile(
    r"(?<=[%s])-[ \t]*\n[ \t]*(?=[%s])" % (_ARMENIAN_CHAR, _ARMENIAN_CHAR)
)
_SOFT_LINE_HYPHEN_RE = re.compile(r"\u00ad[ \t]*\n[ \t]*")
_ARMENIAN_SOFT_FRAGMENT_RE = re.compile(
    r"(?<=[%s])\u00ad[ \t\r\n]*(?=[%s])" % (_ARMENIAN_CHAR, _ARMENIAN_CHAR)
)
_HOLY_WEEK_SPLIT_RE = re.compile(r"\bԱ\s+ւագ\b")
_APPOINTMENT_START_RE = re.compile(
    r"\b(?:Օրհ|Հրց|Մեծ|Մնկ|Ժմտ|Ճշ|Հետ|Քրզ|Սրբ|Մեսդ|Հմբ)\."
)


class ExtractionError(RuntimeError):
    """Raised when a mechanical completeness invariant is not satisfied."""


@dataclass(frozen=True)
class PageSize:
    physical_page: int
    width: float
    height: float

    @property
    def is_spread(self) -> bool:
        return self.width > self.height


@dataclass(frozen=True)
class LogicalChunk:
    logical_index: int
    physical_page: int
    column: str
    raw_text: str
    raw_order_text: str


@dataclass(frozen=True)
class HeaderCandidate:
    candidate_index: int
    logical_index: int
    physical_page: int
    column: str
    line_index: int
    extraction_mode: str
    day: int
    marginal_lunar_day: Optional[int]
    dagger: bool
    holy_week: bool
    weekday: str
    mode: Optional[str]
    mode_period: bool
    raw_line: str
    decoded_line: str
    normalized_line: str


@dataclass(frozen=True)
class SourceSpec:
    year: int
    path: Path
    sha256: str
    page_sizes: Tuple[PageSize, ...]
    legacy_encoding: bool

    @property
    def page_count(self) -> int:
        return len(self.page_sizes)


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of ``path`` without loading it all at once."""

    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tool_version(executable: str) -> str:
    """Return the first non-empty version line for a Poppler executable."""

    completed = subprocess.run(
        [executable, "-v"],
        check=True,
        capture_output=True,
        text=True,
    )
    text = "\n".join((completed.stdout, completed.stderr))
    return next((line.strip() for line in text.splitlines() if line.strip()), "")


def _require_tool(name: str, explicit: Optional[str] = None) -> str:
    executable = explicit or shutil.which(name)
    if not executable:
        raise ExtractionError(
            "%s is required for build-time Oratsouyts extraction" % name
        )
    return executable


def inspect_pdf(
    path: Path,
    year: int,
    pdfinfo: Optional[str] = None,
) -> SourceSpec:
    """Return source hash, page dimensions, and encoding adapter metadata."""

    pdfinfo_bin = _require_tool("pdfinfo", pdfinfo)
    overview = subprocess.run(
        [pdfinfo_bin, str(path)], check=True, capture_output=True, text=True
    ).stdout
    count_match = _PAGE_COUNT_RE.search(overview)
    if not count_match:
        raise ExtractionError("Could not determine PDF page count: %s" % path)
    page_count = int(count_match.group("count"))
    details = subprocess.run(
        [pdfinfo_bin, "-f", "1", "-l", str(page_count), "-box", str(path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    sizes = tuple(
        PageSize(
            physical_page=int(match.group("page")),
            width=float(match.group("width")),
            height=float(match.group("height")),
        )
        for match in _PAGE_SIZE_RE.finditer(details)
    )
    if len(sizes) != page_count:
        raise ExtractionError(
            "Expected %d page dimensions for %s, found %d"
            % (page_count, path, len(sizes))
        )
    return SourceSpec(
        year=year,
        path=path,
        sha256=sha256_file(path),
        page_sizes=sizes,
        legacy_encoding=year == 2013,
    )


def _poppler_pages(path: Path, expected_pages: int) -> List[str]:
    text = path.read_text(encoding="utf-8")
    parts = text.split("\f")
    if len(parts) < expected_pages:
        raise ExtractionError(
            "Poppler emitted %d page chunks; expected %d for %s"
            % (len(parts), expected_pages, path)
        )
    pages = parts[:expected_pages]
    if any(part.strip() for part in parts[expected_pages:]):
        raise ExtractionError("Unexpected text after final page in %s" % path)
    return pages


def _run_pdftotext(
    executable: str,
    source: Path,
    output: Path,
    extraction_mode: str,
    crop: Optional[Tuple[int, int, int, int]] = None,
) -> None:
    if extraction_mode not in ("layout", "raw"):
        raise ValueError("Unsupported pdftotext extraction mode: %s" % extraction_mode)
    args = [executable, "-%s" % extraction_mode, "-enc", "UTF-8"]
    if crop is not None:
        x, y, width, height = crop
        args.extend(
            ["-x", str(x), "-y", str(y), "-W", str(width), "-H", str(height)]
        )
    args.extend([str(source), str(output)])
    completed = subprocess.run(args, capture_output=True, text=True)
    if completed.returncode:
        raise ExtractionError(
            "pdftotext failed for %s: %s" % (source, completed.stderr.strip())
        )


def extract_logical_chunks(
    source: SourceSpec,
    pdftotext: Optional[str] = None,
) -> List[LogicalChunk]:
    """Extract ordered logical pages, splitting every imposed physical spread."""

    pdftotext_bin = _require_tool("pdftotext", pdftotext)
    with tempfile.TemporaryDirectory(prefix="oratsouyts-poppler-") as temp_name:
        temp = Path(temp_name)
        whole_layout_path = temp / "whole-layout.txt"
        whole_raw_path = temp / "whole-raw.txt"
        _run_pdftotext(
            pdftotext_bin,
            source.path,
            whole_layout_path,
            extraction_mode="layout",
        )
        _run_pdftotext(
            pdftotext_bin,
            source.path,
            whole_raw_path,
            extraction_mode="raw",
        )
        whole_layout = _poppler_pages(whole_layout_path, source.page_count)
        whole_raw = _poppler_pages(whole_raw_path, source.page_count)

        spread_sizes = [size for size in source.page_sizes if size.is_spread]
        left_layout: Optional[List[str]] = None
        right_layout: Optional[List[str]] = None
        left_raw: Optional[List[str]] = None
        right_raw: Optional[List[str]] = None
        if spread_sizes:
            # All three imposed editions use the same spread width within their
            # daily section.  The maximum handles portrait cover/front-matter pages
            # without affecting pages selected as spreads below.
            spread_width = max(size.width for size in spread_sizes)
            spread_height = max(size.height for size in spread_sizes)
            midpoint = int(round(spread_width / 2.0))
            height = int(math.ceil(spread_height)) + 1
            left_layout_path = temp / "left-layout.txt"
            right_layout_path = temp / "right-layout.txt"
            left_raw_path = temp / "left-raw.txt"
            right_raw_path = temp / "right-raw.txt"
            _run_pdftotext(
                pdftotext_bin,
                source.path,
                left_layout_path,
                extraction_mode="layout",
                crop=(0, 0, midpoint, height),
            )
            _run_pdftotext(
                pdftotext_bin,
                source.path,
                right_layout_path,
                extraction_mode="layout",
                crop=(midpoint, 0, midpoint + 1, height),
            )
            _run_pdftotext(
                pdftotext_bin,
                source.path,
                left_raw_path,
                extraction_mode="raw",
                crop=(0, 0, midpoint, height),
            )
            _run_pdftotext(
                pdftotext_bin,
                source.path,
                right_raw_path,
                extraction_mode="raw",
                crop=(midpoint, 0, midpoint + 1, height),
            )
            left_layout = _poppler_pages(left_layout_path, source.page_count)
            right_layout = _poppler_pages(right_layout_path, source.page_count)
            left_raw = _poppler_pages(left_raw_path, source.page_count)
            right_raw = _poppler_pages(right_raw_path, source.page_count)

        chunks: List[LogicalChunk] = []
        for index, size in enumerate(source.page_sizes):
            if size.is_spread:
                if any(
                    value is None
                    for value in (left_layout, right_layout, left_raw, right_raw)
                ):
                    raise ExtractionError("Spread extraction was not initialized")
                assert left_layout is not None
                assert right_layout is not None
                assert left_raw is not None
                assert right_raw is not None
                for column, layout_text, raw_order_text in (
                    ("left", left_layout[index], left_raw[index]),
                    ("right", right_layout[index], right_raw[index]),
                ):
                    chunks.append(
                        LogicalChunk(
                            logical_index=len(chunks),
                            physical_page=size.physical_page,
                            column=column,
                            raw_text=layout_text,
                            raw_order_text=raw_order_text,
                        )
                    )
            else:
                chunks.append(
                    LogicalChunk(
                        logical_index=len(chunks),
                        physical_page=size.physical_page,
                        column="whole",
                        raw_text=whole_layout[index],
                        raw_order_text=whole_raw[index],
                    )
                )
        return chunks


def decode_source_text(text: str, legacy_encoding: bool) -> str:
    """Decode one source string exactly once and normalize it to NFC."""

    if legacy_encoding:
        return decode_legacy_armenian(text)
    return unicodedata.normalize("NFC", text)


def normalize_line(text: str, legacy_encoding: bool) -> str:
    """Normalize one line for structural matching without changing source text."""

    decoded = decode_source_text(text, legacy_encoding)
    decoded = _ARMENIAN_SOFT_FRAGMENT_RE.sub("", decoded)
    decoded = (
        decoded.replace("\u00ad", "")
        .replace("\u200b", "")
        .replace("\u200c", "")
        .replace("\u200d", "")
        .replace("\u2060", "")
    )
    normalized = " ".join(decoded.split())
    return _HOLY_WEEK_SPLIT_RE.sub("Աւագ", normalized)


def normalize_entry(text: str, legacy_encoding: bool) -> str:
    """Return human-inspectable, one-line Unicode text for semantic matching."""

    decoded = decode_source_text(text, legacy_encoding).replace("\r\n", "\n")
    # Poppler exposes discretionary soft-hyphen fragments differently in its
    # two modes.  In particular, -raw may emit ``Ծնն\u00ad դեան`` while
    # -layout drops the intervening fragment.  A soft hyphen bracketed by
    # Armenian letters is unambiguously internal to one printed word, even if
    # Poppler inserts horizontal whitespace or a line break after it.
    decoded = _ARMENIAN_SOFT_FRAGMENT_RE.sub("", decoded)
    decoded = _SOFT_LINE_HYPHEN_RE.sub("", decoded)
    decoded = _VISIBLE_LINE_HYPHEN_RE.sub("", decoded)
    decoded = (
        decoded.replace("\u00ad", "")
        .replace("\u200b", "")
        .replace("\u200c", "")
        .replace("\u200d", "")
        .replace("\u2060", "")
        .replace("\f", "\n")
    )
    normalized = " ".join(decoded.split())
    return _HOLY_WEEK_SPLIT_RE.sub("Աւագ", normalized)


def _chunk_text(chunk: LogicalChunk, extraction_mode: str) -> str:
    if extraction_mode == "layout":
        return chunk.raw_text
    if extraction_mode == "raw":
        return chunk.raw_order_text
    raise ValueError("Unsupported extraction mode: %s" % extraction_mode)


def scan_headers(
    chunks: Sequence[LogicalChunk],
    legacy_encoding: bool,
    extraction_mode: str = "layout",
) -> List[HeaderCandidate]:
    """Return every structurally plausible daily header in logical reading order."""

    candidates: List[HeaderCandidate] = []
    for chunk in chunks:
        text = _chunk_text(chunk, extraction_mode)
        for line_index, raw_line in enumerate(text.splitlines()):
            decoded_line = decode_source_text(raw_line, legacy_encoding)
            normalized_line = normalize_line(raw_line, legacy_encoding)
            match = DATE_HEADER_RE.match(normalized_line)
            if not match:
                continue
            candidates.append(
                HeaderCandidate(
                    candidate_index=len(candidates),
                    logical_index=chunk.logical_index,
                    physical_page=chunk.physical_page,
                    column=chunk.column,
                    line_index=line_index,
                    extraction_mode=extraction_mode,
                    day=int(match.group("day")),
                    marginal_lunar_day=(
                        int(match.group("marginal_lunar_day"))
                        if match.group("marginal_lunar_day")
                        else None
                    ),
                    dagger=bool(match.group("dagger")),
                    holy_week=bool(match.group("holy_week")),
                    weekday=match.group("weekday"),
                    mode=match.group("mode"),
                    mode_period=bool(match.group("mode_period")),
                    raw_line=raw_line,
                    decoded_line=decoded_line,
                    normalized_line=normalized_line,
                )
            )
    return candidates


def dates_in_year(year: int) -> List[_datetime.date]:
    date = _datetime.date(year, 1, 1)
    dates: List[_datetime.date] = []
    while date.year == year:
        dates.append(date)
        date += _datetime.timedelta(days=1)
    return dates


def select_new_calendar_headers(
    year: int,
    candidates: Sequence[HeaderCandidate],
) -> Tuple[List[HeaderCandidate], List[int]]:
    """Select the earliest complete day-number run and return all full-run starts.

    Day number and sequence are alignment keys.  Printed weekday and mode are
    independent assertions: using them as keys would silently shift the corpus at
    a source typo, precisely the failure this pipeline is meant to prevent.
    """

    expected = dates_in_year(year)
    full_starts: List[int] = []
    longest = 0
    longest_start: Optional[int] = None
    for start, candidate in enumerate(candidates):
        if candidate.day != 1:
            continue
        matched = 0
        while matched < len(expected) and start + matched < len(candidates):
            if candidates[start + matched].day != expected[matched].day:
                break
            matched += 1
        if matched > longest:
            longest = matched
            longest_start = start
        if matched == len(expected):
            full_starts.append(start)
    if not full_starts:
        detail = "none"
        if longest_start is not None:
            failed_date = expected[longest]
            got = candidates[longest_start + longest]
            detail = "%s: expected day %d, found %d on page %d" % (
                failed_date.isoformat(),
                failed_date.day,
                got.day,
                got.physical_page,
            )
        raise ExtractionError(
            "No complete %d-date run for %d (longest %d; %s)"
            % (len(expected), year, longest, detail)
        )
    start = full_starts[0]
    return list(candidates[start:start + len(expected)]), full_starts


def _slice_entry(
    chunks: Sequence[LogicalChunk],
    start: HeaderCandidate,
    end_logical_index: int,
    end_line_index: int,
    extraction_mode: str = "layout",
) -> Tuple[str, List[Dict[str, object]]]:
    pieces: List[str] = []
    spans: List[Dict[str, object]] = []
    for logical_index in range(start.logical_index, end_logical_index + 1):
        chunk = chunks[logical_index]
        lines = _chunk_text(chunk, extraction_mode).splitlines()
        first_line = start.line_index if logical_index == start.logical_index else 0
        last_line = end_line_index if logical_index == end_logical_index else len(lines)
        if last_line < first_line:
            raise ExtractionError("Invalid entry span at logical page %d" % logical_index)
        selected = lines[first_line:last_line]
        if not selected and logical_index not in (
            start.logical_index,
            end_logical_index,
        ):
            continue
        pieces.append("\n".join(selected))
        spans.append(
            {
                "logical_index": logical_index,
                "physical_page": chunk.physical_page,
                "column": chunk.column,
                "extraction_mode": extraction_mode,
                "start_line": first_line + 1,
                "end_line": last_line,
            }
        )
    return "\n\f\n".join(pieces), spans


def _old_calendar_boundary(
    chunks: Sequence[LogicalChunk],
    legacy_encoding: bool,
    after_logical_index: int,
    before_logical_index: int,
    extraction_mode: str = "layout",
) -> Optional[int]:
    for logical_index in range(after_logical_index + 1, before_logical_index + 1):
        text = normalize_entry(
            _chunk_text(chunks[logical_index], extraction_mode),
            legacy_encoding,
        )
        if _OLD_CALENDAR_MARKER_RE.search(text):
            return logical_index
    return None


def extract_heading(normalized_entry: str) -> str:
    """Return every calendar-level clause before the daily appointments.

    A colon does not end the calendar identity. Collision dates commonly print
    independent clauses such as ``Պահք: Յղութիւն ...`` or a numbered fast day
    followed by a Marian feast. Stopping at the first colon silently drops the
    very overlaps this corpus is intended to preserve.
    """

    header = DATE_HEADER_RE.match(normalized_entry)
    if not header:
        return ""
    remainder = normalized_entry[header.end():].strip()
    appointment = _APPOINTMENT_START_RE.search(remainder)
    end = appointment.start() if appointment else min(len(remainder), 1600)
    heading = remainder[:end].strip(" .")
    # Lunar day is printed at the far margin on the header's first line and can
    # land at the end of an otherwise clean heading.
    heading = re.sub(r"\s+[0-9]{1,2}$", "", heading).strip()
    return heading


def heading_comparison_key(heading: str) -> str:
    """Return a whitespace-insensitive key for extraction-method comparison."""

    return "".join(character for character in heading if not character.isspace())


def _section_end(
    chunks: Sequence[LogicalChunk],
    candidates: Sequence[HeaderCandidate],
    selected: Sequence[HeaderCandidate],
    legacy_encoding: bool,
    extraction_mode: str,
) -> Tuple[int, int]:
    """Return the exclusive logical-page/line boundary of the selected year."""

    following_index = selected[-1].candidate_index + 1
    if following_index < len(candidates):
        following = candidates[following_index]
        final_end_logical = following.logical_index
        final_end_line = following.line_index
    else:
        final_end_logical = len(chunks) - 1
        final_end_line = len(
            _chunk_text(chunks[-1], extraction_mode).splitlines()
        )

    marker_boundary = _old_calendar_boundary(
        chunks,
        legacy_encoding,
        selected[-1].logical_index,
        final_end_logical,
        extraction_mode=extraction_mode,
    )
    if marker_boundary is not None:
        final_end_logical = marker_boundary
        final_end_line = 0
    return final_end_logical, final_end_line


def _header_evidence(header: HeaderCandidate) -> Dict[str, object]:
    return {
        "raw": header.raw_line,
        "decoded": header.decoded_line,
        "normalized": header.normalized_line,
        "printed_day": header.day,
        "marginal_lunar_day": header.marginal_lunar_day,
        "printed_weekday": header.weekday,
        "printed_mode": header.mode,
        "printed_mode_period": header.mode_period,
        "dagger": header.dagger,
        "holy_week_prefix": header.holy_week,
        "physical_page": header.physical_page,
        "logical_index": header.logical_index,
        "column": header.column,
        "line": header.line_index + 1,
        "extraction_mode": header.extraction_mode,
    }


def _mode_for_date(date: _datetime.date) -> str:
    # Imported lazily so the extractor remains independently testable.  This is
    # a validation signal, never an alignment key.
    from armenian_lectionary.engine import calculate_liturgical_mode

    return calculate_liturgical_mode(date)["Tone"]


def build_records(
    source: SourceSpec,
    chunks: Sequence[LogicalChunk],
) -> Dict[str, object]:
    """Build complete date records and source/validation summary for one year."""

    layout_candidates = scan_headers(
        chunks, source.legacy_encoding, extraction_mode="layout"
    )
    layout_selected, layout_full_starts = select_new_calendar_headers(
        source.year, layout_candidates
    )
    raw_candidates = scan_headers(
        chunks, source.legacy_encoding, extraction_mode="raw"
    )
    raw_selected, raw_full_starts = select_new_calendar_headers(
        source.year, raw_candidates
    )
    dates = dates_in_year(source.year)
    layout_final_end_logical, layout_final_end_line = _section_end(
        chunks,
        layout_candidates,
        layout_selected,
        source.legacy_encoding,
        extraction_mode="layout",
    )
    raw_final_end_logical, raw_final_end_line = _section_end(
        chunks,
        raw_candidates,
        raw_selected,
        source.legacy_encoding,
        extraction_mode="raw",
    )

    # Both extractors must identify the same civil section before either can be
    # trusted as evidence.  Individual header lines can move within a logical
    # page, but selecting a different first or last logical page would indicate
    # that one method aligned to the independent old-calendar schedule.
    if (
        layout_selected[0].logical_index != raw_selected[0].logical_index
        or layout_selected[-1].logical_index != raw_selected[-1].logical_index
    ):
        raise ExtractionError(
            "%d layout/raw selected different calendar sections: "
            "layout logical pages %d-%d, raw logical pages %d-%d"
            % (
                source.year,
                layout_selected[0].logical_index,
                layout_selected[-1].logical_index,
                raw_selected[0].logical_index,
                raw_selected[-1].logical_index,
            )
        )

    records: List[Dict[str, object]] = []
    weekday_conflicts: List[Dict[str, object]] = []
    mode_conflicts: List[Dict[str, object]] = []
    mode_punctuation_warnings: List[Dict[str, object]] = []
    extraction_disagreements: List[Dict[str, object]] = []
    for index, (date, layout_header, raw_header) in enumerate(
        zip(dates, layout_selected, raw_selected)
    ):
        if index + 1 < len(layout_selected):
            following = layout_selected[index + 1]
            layout_end_logical = following.logical_index
            layout_end_line = following.line_index
        else:
            layout_end_logical = layout_final_end_logical
            layout_end_line = layout_final_end_line
        if index + 1 < len(raw_selected):
            following = raw_selected[index + 1]
            raw_end_logical = following.logical_index
            raw_end_line = following.line_index
        else:
            raw_end_logical = raw_final_end_logical
            raw_end_line = raw_final_end_line

        layout_text, layout_spans = _slice_entry(
            chunks,
            layout_header,
            layout_end_logical,
            layout_end_line,
            extraction_mode="layout",
        )
        raw_order_text, raw_order_spans = _slice_entry(
            chunks,
            raw_header,
            raw_end_logical,
            raw_end_line,
            extraction_mode="raw",
        )
        layout_decoded_text = decode_source_text(
            layout_text, source.legacy_encoding
        )
        raw_order_decoded_text = decode_source_text(
            raw_order_text, source.legacy_encoding
        )
        layout_normalized_text = normalize_entry(
            layout_text, source.legacy_encoding
        )
        raw_order_normalized_text = normalize_entry(
            raw_order_text, source.legacy_encoding
        )
        layout_heading = extract_heading(layout_normalized_text)
        raw_order_heading = extract_heading(raw_order_normalized_text)
        expected_weekday = WEEKDAY_CODES[date.weekday()]
        expected_mode = _mode_for_date(date)
        warnings: List[str] = []
        disagreements: List[str] = []
        if (
            layout_header.logical_index,
            layout_header.physical_page,
            layout_header.column,
        ) != (
            raw_header.logical_index,
            raw_header.physical_page,
            raw_header.column,
        ):
            disagreements.append("header_provenance")
        if (
            layout_header.day,
            layout_header.weekday,
            layout_header.mode,
            layout_header.mode_period,
            layout_header.dagger,
            layout_header.holy_week,
        ) != (
            raw_header.day,
            raw_header.weekday,
            raw_header.mode,
            raw_header.mode_period,
            raw_header.dagger,
            raw_header.holy_week,
        ):
            disagreements.append("parsed_header_fields")
        if heading_comparison_key(layout_heading) != heading_comparison_key(
            raw_order_heading
        ):
            disagreements.append("calendar_clause_text")
        if disagreements:
            warnings.append("extraction_method_disagreement")
            extraction_disagreements.append(
                {
                    "date": date.isoformat(),
                    "flags": disagreements,
                    "poppler_layout": {
                        "physical_page": layout_header.physical_page,
                        "logical_index": layout_header.logical_index,
                        "column": layout_header.column,
                        "calendar_clause": layout_heading,
                    },
                    "poppler_raw": {
                        "physical_page": raw_header.physical_page,
                        "logical_index": raw_header.logical_index,
                        "column": raw_header.column,
                        "calendar_clause": raw_order_heading,
                    },
                }
            )

        # Printed source assertions come from the semantic (-raw) extraction;
        # the corresponding layout fields remain preserved below for audit.
        if raw_header.weekday != expected_weekday:
            warnings.append("printed_weekday_conflict")
            weekday_conflicts.append(
                {
                    "date": date.isoformat(),
                    "physical_page": raw_header.physical_page,
                    "printed": raw_header.weekday,
                    "expected": expected_weekday,
                    "header": raw_header.normalized_line,
                }
            )
        if raw_header.mode is None:
            warnings.append("printed_mode_missing")
            mode_conflicts.append(
                {
                    "date": date.isoformat(),
                    "physical_page": raw_header.physical_page,
                    "printed": None,
                    "expected": expected_mode,
                    "header": raw_header.normalized_line,
                }
            )
        elif raw_header.mode != expected_mode:
            warnings.append("printed_mode_conflict")
            mode_conflicts.append(
                {
                    "date": date.isoformat(),
                    "physical_page": raw_header.physical_page,
                    "printed": raw_header.mode,
                    "expected": expected_mode,
                    "header": raw_header.normalized_line,
                }
            )
        if raw_header.mode is not None and not raw_header.mode_period:
            warnings.append("printed_mode_period_missing")
            mode_punctuation_warnings.append(
                {
                    "date": date.isoformat(),
                    "physical_page": raw_header.physical_page,
                    "printed": raw_header.mode,
                    "header": raw_header.normalized_line,
                }
            )

        canonical_header = _header_evidence(raw_header)
        canonical_header.update(
            {
                "expected_weekday": expected_weekday,
                "expected_weekday_name": WEEKDAY_NAMES[date.weekday()],
                "expected_mode": expected_mode,
            }
        )
        records.append(
            {
                "date": date.isoformat(),
                "year": source.year,
                "calendar_system": "new_style",
                "source_sha256": source.sha256,
                "source_filename": source.path.name,
                "physical_page": raw_header.physical_page,
                "logical_index": raw_header.logical_index,
                "column": raw_header.column,
                "line": raw_header.line_index + 1,
                "alignment_source": "poppler_layout",
                "semantic_source": "poppler_raw",
                "entry_spans": raw_order_spans,
                "header": canonical_header,
                "heading": raw_order_heading,
                "calendar_clause": raw_order_heading,
                "raw_text": raw_order_text,
                "decoded_text": raw_order_decoded_text,
                "normalized_text": raw_order_normalized_text,
                "extraction_variants": {
                    "poppler_layout": {
                        "entry_spans": layout_spans,
                        "header": _header_evidence(layout_header),
                        "calendar_clause": layout_heading,
                        "raw_text": layout_text,
                        "decoded_text": layout_decoded_text,
                        "normalized_text": layout_normalized_text,
                    },
                    "poppler_raw": {
                        "entry_spans": raw_order_spans,
                        "header": _header_evidence(raw_header),
                        "calendar_clause": raw_order_heading,
                        "raw_text": raw_order_text,
                        "decoded_text": raw_order_decoded_text,
                        "normalized_text": raw_order_normalized_text,
                    },
                },
                "extraction_disagreements": disagreements,
                "validation_warnings": warnings,
            }
        )

    expected_count = len(dates)
    unique_dates = {record["date"] for record in records}
    if len(records) != expected_count or len(unique_dates) != expected_count:
        raise ExtractionError(
            "%d extraction has %d records / %d unique dates; expected %d"
            % (source.year, len(records), len(unique_dates), expected_count)
        )
    missing_modes = [
        record["date"] for record in records
        if record["header"]["printed_mode"] is None
    ]
    if missing_modes:
        raise ExtractionError(
            "%d has headers without a printed mode: %s"
            % (source.year, ", ".join(missing_modes))
        )

    return {
        "year": source.year,
        "source": {
            "filename": source.path.name,
            "sha256": source.sha256,
            "page_count": source.page_count,
            "legacy_encoding": source.legacy_encoding,
            "physical_spread_pages": sum(
                1 for size in source.page_sizes if size.is_spread
            ),
        },
        "section": {
            "calendar_system": "new_style",
            "start_physical_page": layout_selected[0].physical_page,
            "end_physical_page": layout_selected[-1].physical_page,
            "candidate_start_index": layout_selected[0].candidate_index,
            "complete_day_number_runs": layout_full_starts,
            "candidate_count": len(layout_candidates),
            "alignment_source": "poppler_layout",
            "semantic_source": "poppler_raw",
            "poppler_raw": {
                "start_physical_page": raw_selected[0].physical_page,
                "end_physical_page": raw_selected[-1].physical_page,
                "candidate_start_index": raw_selected[0].candidate_index,
                "complete_day_number_runs": raw_full_starts,
                "candidate_count": len(raw_candidates),
            },
        },
        "quality": {
            "expected_records": expected_count,
            "records": len(records),
            "unique_dates": len(unique_dates),
            "missing_dates": 0,
            "duplicate_dates": 0,
            "weekday_conflicts": weekday_conflicts,
            "mode_conflicts": mode_conflicts,
            "mode_punctuation_warnings": mode_punctuation_warnings,
            "extraction_disagreements": extraction_disagreements,
        },
        "records": records,
    }


def extract_year(
    path: Path,
    year: int,
    pdftotext: Optional[str] = None,
    pdfinfo: Optional[str] = None,
) -> Dict[str, object]:
    """Inspect and fully extract one annual source PDF."""

    source = inspect_pdf(path=path, year=year, pdfinfo=pdfinfo)
    chunks = extract_logical_chunks(source, pdftotext=pdftotext)
    return build_records(source, chunks)
