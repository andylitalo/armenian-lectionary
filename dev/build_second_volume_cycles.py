"""Distill the Tonatsoyts Second Volume cycles into a committed, offline data file
`dev/second_volume_cycles.json` consumed by the engine's cycle-lookup tier.

Output shape:  { easter_md_julian : { "MM-DD" : [zone, saint_id] } }

For each calendar letter's cycle (located via docs/sources/second_volume_index.csv),
parse its per-date saint entries from the human-corrected translation and match each to
a saint identity in dev/saint_readings.json (so identity -> readings is a fixed lookup at
runtime). Built dev-time from grabar-ocr; the engine never reads the translation.

Run: armenian_lectionary/venv/bin/python dev/build_second_volume_cycles.py
"""
import calendar
import collections
import csv
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lectionary as L  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, os.pardir, "docs", "sources", "second_volume_index.csv")
OUT = os.path.join(HERE, "second_volume_cycles.json")
TR = os.path.expanduser("~/church/grabar-ocr/runs/human__proj__tess__gemini-min/"
                        "translations/gemini-flash/translated.md")
MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], 1)}


# transl-variant aliases folded before tokenizing so spellings unify:
# "Anthony"->y→i->"anthoni" must meet the identity token "anton".
_ALIASES = [("anthoni", "anton")]


def _normstr(t):
    """Lower-case + fold phonetic/translit variants (tryphon/triphon, eugenios/eugenius,
    Anthony/Anton) so the entry text and the identity ids normalize into one spelling.
    Translator "[Note: …]" annotations are dropped first (they carry no saint text)."""
    t = re.sub(r"\[Note:[^\]]*\]", " ", t or "")
    t = t.lower().replace("ph", "f").replace("ios", "ius").replace("ie", "ia").replace("y", "i")
    for a, b in _ALIASES:
        t = t.replace(a, b)
    return t


def _norm(t):
    return set(re.findall(r"[a-z]{4,}", _normstr(t)))


# generic, non-distinctive tokens that must not drive a match. Normalized through the same
# tokenizer so folded forms are excluded too (e.g. "holy"->"holi", else every "Holy …"
# entry falsely hits seventy_two_holy / twelve_holy_doctors on the stray "holi" token).
_GENERIC = {t for w in
            {"feast", "fast", "season", "octave", "sunday", "commemoration", "eve",
             "great", "holy", "hermit", "hermits", "fathers", "saint", "saints",
             "martyr", "martyrs", "bishop", "virgin", "general", "this", "their",
             "prophet", "apostle", "patriarch"}
            for t in _norm(w)}


# Negative disambiguators: an entry may NOT resolve to `sid` if it carries a blocking
# token. These separate name collisions where the distinctive token is a bare given name
# shared with a different, un-tabled saint: "David the Prophet" (≠ David of Dvin),
# "Gregory and Nicholas the Wonderworker" (≠ Gregory the Illuminator/Theologian),
# "Conception of the Holy Virgin" (≠ the Seventy-Two).
# Blocking words are normalized through the tokenizer so folds match too
# (e.g. "prophet"->"profet" via ph->f, else the David-the-Prophet guard never fires).
_EXCLUDE = {sid: {t for w in words for t in _norm(w)} for sid, words in {
    "gregory_the_illuminator": {"nicholas", "wonderworker", "wonderworking"},
    "gregory_of_theologian": {"nicholas", "wonderworker", "wonderworking"},
    "david_of_dvin": {"prophet"},
    "seventy_two_holy": {"conception"},
}.items()}


# saint identity -> (zone, sid, distinctive-name-tokens, blocking-tokens)
def _identities():
    out = []
    for zone, ids in L._SAINT_READINGS.items():
        for sid in ids:
            names = _norm(sid.replace("_", " ")) - _GENERIC   # distinctive saint names
            if names:
                out.append((zone, sid, names, _EXCLUDE.get(sid, frozenset())))
    return out


def _match(entry, identities):
    """Best (zone, sid) for a cycle entry line, or None. A group entry ("Vahan …, and
    Eugenia …") files its readings under the FIRST-named (senior) saint (preface §6), so
    rank identities by the EARLIEST position of any of their distinctive name tokens in
    the entry, then by overlap. Tokens are normalized so Tryphon≈Triphon etc. Translator
    "[Note: …]" annotations are stripped, and an identity is skipped if the entry carries
    one of its blocking tokens (name-collision guard)."""
    en = _normstr(entry)
    et = _norm(entry)
    best, best_key = None, None
    for zone, sid, names, block in identities:
        if block & et:
            continue
        hit = names & et
        if not hit:
            continue
        # earliest whole-word position of any hit token (not a substring-of-a-word match)
        pos = min((m.start() for t in hit
                   if (m := re.search(rf"\b{re.escape(t)}", en))), default=len(en))
        key = (pos, -len(hit))              # first-named saint, then most overlap
        if best_key is None or key < best_key:
            best, best_key = (zone, sid), key
    return best


# --- Vardavar-anchored summer (post-Transfiguration) saint laydown ---------------
# The Second-Volume canons place the summer floating saints on a fixed weekday march
# after Transfiguration's octave: the Saturday of the third week begins it, then
# Mon/Tue/Thu/Sat step through the canonical order below. That order is invariant
# across canons (only the anchor date moves), so rather than parse each canon body --
# whose two-column OCR reading-order is scrambled and whose day-numbers are noisy --
# we anchor the canonical sequence to the served year's own Vardavar (Gregorian
# Easter + 98, always a Sunday). Per-year leap shifts (a leap year advances the first
# Saturday) are absorbed by the cache drop-guard, which ships only the placements every
# cached year of the Easter-date agrees on. Sequence verified against 2005/2016 ground
# truth; saint_ids are the Tr-zone keys of dev/saint_readings.json.
_SUMMER_SEQUENCE = [
    (5, "peter_the_patriarch"),         # Saturday  (Peter, Blaise, Absalom)
    (0, "hermit_saints_anton"),         # Monday    (Anton the Hermit)
    (1, "theodosius_and_the"),          # Tuesday   (Theodosius & Children of Ephesus)
    (3, "cyricus_and_his"),             # Thursday  (Cyricus & Julitta, Gordius ...)
    (5, "fathers_saints_athanasius"),   # Saturday  (Athanasius, Cyril, Gregory Theol.)
    (0, "vahan_of_goghtn"),             # Monday    (Vahan of Goghtn, Eugenia ...)
    (1, "hermits_saints_triphon"),      # Tuesday   (Tryphon, Barsauma, Onuphrius)
    (3, "eugenios_makarios_valerian"),  # Thursday  (Eugenios, Makarios ...)
]


def _rep_easter(easter_md):
    """A representative Gregorian date on which this Easter month-day is a Sunday,
    for weekday anchoring. Post-March walk arithmetic is year-independent, so any
    such year serves every Gregorian year with this Easter date."""
    m, d = (int(x) for x in easter_md.split("-"))
    for y in range(2001, 2101):
        try:
            dt = datetime.date(y, m, d)
        except ValueError:
            return None
        if dt.weekday() == 6:      # Sunday
            return dt
    return None


# --- Leap-year summer overrides (Tonatsoyts Second Volume, per-Dominical-letter leap
# rubrics; see docs/sources/second_volume_leap_rules.md) ---------------------------
# In a leap year the summer Saturday chain ADVANCES: a saint whose nominal slot straddled
# the Feb-29 boundary was already kept "under the first letter," so it is skipped here and
# the Saturdays shift up one. The weekday (Mon/Tue/Thu) saints are unchanged. Keyed by the
# leap year's GREGORIAN Easter month-day (the same key the runtime/drop-guard use), so the
# override serves the leap parity of that Easter date while the common march serves the
# non-leap parity. Verified against ground truth for the in-window leap taregir it governs.
#   03-27 = ՍՌ (2016): drop Peter (kept after Nativity); Sat0=Athanasius, Sat1=Gregory
#   the Theologian. Verified vs 2016-07-23 (Athanasius) / 2016-07-30 (Gregory Theol.).
_LEAP_SUMMER = {
    "03-27": [
        (5, "fathers_saints_athanasius"),   # Saturday  (was Peter)
        (0, "hermit_saints_anton"),         # Monday
        (1, "theodosius_and_the"),          # Tuesday
        (3, "cyricus_and_his"),             # Thursday
        (5, "gregory_of_theologian"),       # Saturday  (was Athanasius)
        (0, "vahan_of_goghtn"),             # Monday
        (1, "hermits_saints_triphon"),      # Tuesday
        (3, "eugenios_makarios_valerian"),  # Thursday
    ],
}


def _summer_entries(easter_md, sequence=_SUMMER_SEQUENCE):
    """{ "MM-DD": ["Tr", sid] } for the post-Transfiguration saints of the canon whose
    Easter is `easter_md`, from a canonical weekday march anchored to that year's Vardavar.
    The march starts on the Saturday of Transfiguration's third week (Vardavar + 20; cursor
    seeded at the preceding Friday). Pass a leap-override `sequence` for a leap taregir."""
    easter = _rep_easter(easter_md)
    if easter is None:
        return {}
    cursor = easter + datetime.timedelta(days=98 + 19)   # Vardavar + 19 = Friday, wk 3
    out = {}
    for wd, sid in sequence:
        nd = cursor + datetime.timedelta(days=1)
        while nd.weekday() != wd:
            nd += datetime.timedelta(days=1)
        cursor = nd
        out[f"{nd.month:02d}-{nd.day:02d}"] = ["Tr", sid]
    return out


# --- Post-Nativity (winter) saint laydown ----------------------------------------
# The Second Volume repeats the floating saints in the post-Nativity window (Jan 14, the
# Theophany octave -> eve of the Fast of Catechumens). Unlike the summer march they fill
# CONSECUTIVE saint-weekdays from the window start (no fixed weekday per saint), after the
# Birth of John the Forerunner on the first saint-weekday. The order below is the canonical
# long-window sequence read from 2011 ground truth (PN-zone saint ids). Short windows
# compress it differently and stay best-effort under the drop-guard. Because Feb-29 falls
# BETWEEN this January window and Easter, the civil dates shift by leap parity, so the
# march is generated per parity and shipped through the same leap-conditional records as
# summer -- the drop-guard validates each side against the matching cache years.
_WINTER_SEQUENCE = [
    "peter_the_patriarch", "hermits_saints_anton", "theodosius_and_the",
    "fathers_saints_athanasius", "cyricus_and_his", "vahan_of_goghtn",
    "eugenios_makarios_valerian", "gregory_of_theologian", "cyprian_the_bishop",
    "athenogenes_the_bishop", "forefathers_adam_abel", "gregory_the_illuminator",
    "maccabees_eleazar_the", "twelve_prophets_hosea", "sophia_and_her",
    "thaddeus_apostle_of",
]


def _rep_year(easter_md, leap):
    """A representative year of the requested leap parity whose Gregorian Easter is
    `easter_md`, for anchoring the pre-Easter (January) weekday walk -- which, unlike the
    post-March summer walk, DOES depend on leap parity (Feb-29 sits between January and
    Easter). None if no such year in range."""
    for y in range(2001, 2101):
        if calendar.isleap(y) != leap:
            continue
        e = L.calculate_gregorian_easter(y)
        if f"{e.month:02d}-{e.day:02d}" == easter_md:
            return y
    return None


def _winter_entries(easter_md, leap):
    """{ "MM-DD": ["PN", sid] } for the post-Nativity floating saints of the year-type with
    Gregorian Easter `easter_md` and the given leap parity: the canonical sequence laid on
    consecutive saint-weekdays of the PN window, after the first (John the Forerunner)."""
    y = _rep_year(easter_md, leap)
    if y is None:
        return {}
    start, end = L._SAINT_ZONES["PN"]["window"](y)
    slots = []
    d = start
    while d <= end:
        if d.weekday() in (0, 1, 3, 5):     # Mon/Tue/Thu/Sat saint-weekdays
            slots.append(d)
        d += datetime.timedelta(days=1)
    out = {}
    for nd, sid in zip(slots[1:], _WINTER_SEQUENCE):   # slots[0] = John the Forerunner
        out[f"{nd.month:02d}-{nd.day:02d}"] = ["PN", sid]
    return out


def _cycle_pages():
    rows = [r for r in csv.DictReader(open(INDEX, encoding="utf-8")) if r["page"]]
    pages = sorted(int(r["page"]) for r in rows)
    span = {}
    for r in rows:
        p0 = int(r["page"])
        p1 = min([q for q in pages if q > p0], default=p0 + 3)
        span[r["easter_md_julian"]] = (p0, p1)
    return span


def main():
    identities = _identities()
    spans = _cycle_pages()
    # Raw lines indexed by page (no month state here). Month context is derived PER CANON
    # span below, with fresh state, so a month header can never leak across a page break
    # into a different canon (the "Sept 'Exaltation' tagged month 02" bug).
    lines_by_page = collections.defaultdict(list)
    cur = None
    for ln in open(TR, encoding="utf-8"):
        s = ln.strip()
        pm = re.match(r"## page_(\d+)", s)
        if pm:
            cur = int(pm.group(1))
            continue
        if cur is not None:
            lines_by_page[cur].append(s)

    out = {}
    for easter_md, (p0, p1) in spans.items():
        if not easter_md:
            continue
        day_map = {}
        month = None                        # fresh per canon; persists across its pages
        for p in range(p0, p1):
            for s in lines_by_page.get(p, []):
                mm = re.match(r"(?:In )?([A-Z][a-z]+):?$", s)
                if mm and mm.group(1) in MONTHS:
                    month = MONTHS[mm.group(1)]
                    continue
                dm = re.match(r"(\d{1,2})\.\s", s)
                if dm and month:
                    hit = _match(s, identities)
                    if hit:
                        day_map.setdefault(f"{month:02d}-{int(dm.group(1)):02d}",
                                           list(hit))
        if day_map:
            out[easter_md] = day_map

    # Summer floating saints: canonical Vardavar-anchored march per Easter-date,
    # filling only days the dated-line parser left uncovered (setdefault, so a
    # correct dated entry is never displaced). The drop-guard validates each.
    leapov = {}                             # easter_md -> {md: [z, sid]} leap-only overrides
    for easter_md in spans:
        if not easter_md:
            continue
        dm = out.setdefault(easter_md, {})
        for md, rec in _summer_entries(easter_md).items():
            dm.setdefault(md, rec)
        # Leap-year summer override: a distinct placement for the leap parity of this
        # Easter date (only the days that differ from the common march).
        seq = _LEAP_SUMMER.get(easter_md)
        if seq:
            lm = {}
            for md, rec in _summer_entries(easter_md, seq).items():
                # Only a genuine SAINT change is a leap override; a mere zone/id-label
                # difference for the same saint (identical readings) is not.
                if _intrinsic(dm.get(md)) != _intrinsic(rec):
                    lm[md] = rec
            if lm:
                leapov[easter_md] = lm

        # Post-Nativity (winter) march: consecutive-fill per parity (the January weekday
        # alignment shifts with leap parity). Common fills the shared map; the leap variant
        # supplies leap-only records for the days it genuinely differs on.
        for md, rec in _winter_entries(easter_md, leap=False).items():
            dm.setdefault(md, rec)
        lm = leapov.setdefault(easter_md, {})
        for md, rec in _winter_entries(easter_md, leap=True).items():
            if _intrinsic(dm.get(md)) != _intrinsic(rec):
                lm.setdefault(md, rec)
        if not lm:
            leapov.pop(easter_md, None)

    dropped = _drop_cache_contradicted(out, leapov)
    merged = _merge_parity(out, leapov)
    json.dump(merged, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=0, sort_keys=True)
    n = sum(len(v) for v in merged.values())
    print(f"wrote {OUT}: {len(merged)} cycles, {n} dated saint entries "
          f"({dropped} dropped as cache-contradicted)")


def _merge_parity(common, leapov):
    """Collapse the common map and the leap-override map into the shipped cycle shape:
    a per-date value is the flat [zone, sid] when both parities agree, or
    {"common": [...], "leap": [...]} when a leap override differs (either side may be
    absent -> that parity simply has no cycle entry for the day)."""
    out = {}
    for easter_md, dm in common.items():
        lov = leapov.get(easter_md, {})
        day = {}
        for md in set(dm) | set(lov):
            c, l = dm.get(md), lov.get(md, dm.get(md))
            if c is not None and l is not None and c == l:
                day[md] = c
            elif c == l:                    # both None -- unreachable, guarded above
                continue
            else:
                rec = {}
                if c is not None:
                    rec["common"] = c
                if l is not None:
                    rec["leap"] = l
                day[md] = rec
        if day:
            out[easter_md] = day
    return out


def _intrinsic(rec):
    """The intrinsic readings of a [zone, sid] cycle record (or None), for comparing two
    records by the saint they actually ship rather than by their zone/id label."""
    if not rec:
        return None
    zone, sid = rec
    refs = L._SAINT_READINGS.get(zone, {}).get(sid)
    return tuple(refs) if refs else ("?", zone, sid)


def _readings_for(d, stored_zone, sid):
    """Mirror the engine's runtime readings lookup: the date's saint-zone first."""
    rz = next((z for z, zd in L._SAINT_ZONES.items()
               if zd["window"](d.year)[0] <= d <= zd["window"](d.year)[1]), None)
    for z in (rz, stored_zone):
        refs = z and L._SAINT_READINGS.get(z, {}).get(sid)
        if refs:
            return list(refs)
    return None


def _drop_cache_contradicted(out, leapov=None):
    """Drop any cycle entry whose readings disagree with ground truth in a cached year of
    that year-type -- so the shipped tier is cache-consistent (no regression) while
    unobserved year-types stay best-effort. Returns the count dropped.

    Parity-aware: the common map is validated against the NON-leap cache years of an Easter
    date wherever a leap override exists for the day (else against all years), and each leap
    override is validated against the LEAP cache years. This lets the same Easter date ship
    a Peter (non-leap) and an Athanasius (leap) placement without either dropping the other.
    """
    leapov = leapov or {}
    ref_dir = os.path.join(HERE, "reference_data")
    if not os.path.isdir(ref_dir):
        return 0
    common_years = collections.defaultdict(list)
    leap_years = collections.defaultdict(list)
    for y in range(2001, 2027):
        e = L.calculate_gregorian_easter(y)
        (leap_years if calendar.isleap(y) else common_years)[
            f"{e.month:02d}-{e.day:02d}"].append(y)

    def _bad(md, rec, years):
        m, dd = (int(x) for x in md.split("-"))
        zone, sid = rec
        for y in years:
            f = os.path.join(ref_dir, f"{y:04d}-{m:02d}-{dd:02d}.json")
            if not os.path.exists(f):
                continue
            gt = json.load(open(f)).get("readings")
            refs = _readings_for(datetime.date(y, m, dd), zone, sid)
            if gt and refs and refs != list(gt):
                return True
        return False

    dropped = 0
    for easter_md, day_map in out.items():
        lov = leapov.get(easter_md, {})
        for md in list(day_map):
            # A day with a leap override serves only the non-leap parity from the common map.
            years = common_years.get(easter_md, [])
            if md not in lov:
                years = years + leap_years.get(easter_md, [])
            if _bad(md, day_map[md], years):
                del day_map[md]
                dropped += 1
    for easter_md, lov in leapov.items():
        for md in list(lov):
            if _bad(md, lov[md], leap_years.get(easter_md, [])):
                del lov[md]
                dropped += 1
    return dropped


if __name__ == "__main__":
    main()
