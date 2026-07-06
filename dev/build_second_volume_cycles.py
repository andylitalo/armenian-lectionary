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


# --- Source-derived per-canon summer marches (Tonatsoyts Second Volume) ------------
# The generic `_SUMMER_SEQUENCE` above is a truncated 8-saint approximation that is wrong
# for the long/compressed year-types. Two canons are transcribed here directly from the
# grabar-ocr source, keyed by the GREGORIAN Easter md the canon's taregir-years actually
# query at runtime (`_cycle_saint` selects by Gregorian Easter; the CSV/`spans` julian
# label of the same md is vestigial). Each march opens on the first saint-Saturday after
# Vardavar (`start_off` = 5) and runs Sat/Mon/Tue/Thu to the Fast of the Assumption; the
# drop-guard validates every placement against the cached years of the type.
#
#   03-31  <- taregir Ր (Julian Easter 04-22; cache years 2002/2013/2024). The full
#            17-saint march. Summer saint lines: winter section p.627 (human) + the
#            post-Assumption p.628 (auto) naming Andrew/Adrian/Abraham; the leap rubric on
#            p.627 names "Andrew the Commander ... and Adrian" in this canon. Reproduces
#            GT 2002 exactly, incl. Eugenios/Makarios/Valerian on 08-05 (the miss day).
#   04-05  <- taregir Թ (Julian Easter 03-30; cache years 2015/2026). The COMPRESSED
#            march: p.576 (auto) jumps Sat-Athanasius -> Mon-Eugenia -> Tue-Andrew ->
#            Thu-Adrian, dropping the Cyricus/Vahan/Triphon/Gregory-Theologian middle that
#            the long Ր march carries. Reproduces GT 2015 (Andrew 08-04, Adrian 08-06).
# Weekday codes: Mon=0 Tue=1 Thu=3 Sat=5.
_SUMMER_R = [
    (5, "thaddeus_apostle_of"), (0, "cyprian_the_bishop"), (1, "athenogenes_the_bishop"),
    (3, "forefathers_adam_abel"), (5, "gregory_the_illuminator"), (0, "maccabees_eleazar_the"),
    (1, "twelve_prophets_hosea"), (3, "sophia_and_her"), (5, "fathers_saints_athanasius"),
    (0, "cyricus_and_his"), (1, "vahan_of_goghtn"), (3, "hermits_saints_triphon"),
    (5, "gregory_of_theologian"), (0, "eugenios_makarios_valerian"), (1, "andrew_the_general"),
    (3, "adrian_and_his"), (5, "200_fathers_of"),
]
_SUMMER_T = [
    (5, "thaddeus_apostle_of"), (0, "cyprian_the_bishop"), (1, "athenogenes_the_bishop"),
    (3, "forefathers_adam_abel"), (5, "gregory_the_illuminator"), (0, "maccabees_eleazar_the"),
    (1, "twelve_prophets_hosea"), (3, "sophia_and_her"), (5, "fathers_saints_athanasius"),
    (0, "eugenia_the_virgin"), (1, "andrew_the_general"), (3, "adrian_and_his"),
    (5, "200_fathers_of"),
]
#   03-23  <- taregir ՉՈ (2008; leap pair, post-Vardavar uses the lower letter Ո per the
#            p.610 rubric `զչի տօնին դորա ի յետին տարեգիրն Ո ... զկնի Վարդավառին`). The full
#            21-saint march: the leap year pushes Eugenia/Gregory-Theol/Eugenios/Andrew/Adrian
#            into the summer window (they sit in January in the common Չ year). Reproduces GT
#            2008 exactly, incl. the two miss days Eugenia 07-31 and Eugenios 08-04.
#            [SOURCE: sequence read off GT 2008 and the Ո summer section; the intermediate
#            saints match the Ր/Թ marches, tail confirmed by the p.610 leap redirection.]
_SUMMER_CHVO = [
    (5, "thaddeus_apostle_of"), (0, "cyprian_the_bishop"), (1, "athenogenes_the_bishop"),
    (3, "forefathers_adam_abel"), (5, "gregory_the_illuminator"), (0, "maccabees_eleazar_the"),
    (1, "twelve_prophets_hosea"), (3, "sophia_and_her"), (5, "peter_the_patriarch"),
    (0, "hermit_saints_anton"), (1, "theodosius_and_the"), (3, "cyricus_and_his"),
    (5, "fathers_saints_athanasius"), (0, "vahan_of_goghtn"), (1, "hermits_saints_triphon"),
    (3, "eugenia_the_virgin"), (5, "gregory_of_theologian"), (0, "eugenios_makarios_valerian"),
    (1, "andrew_the_general"), (3, "adrian_and_his"), (5, "200_fathers_of"),
]
_SOURCE_SUMMER = {
    "03-31": (_SUMMER_R, 5),
    "04-05": (_SUMMER_T, 5),
    "03-23": (_SUMMER_CHVO, 5),
}


# --- Solar-anchored autumn march (Andrew / Adrian / Abraham & Khoren) ----------------
# These three commemorations are SOLAR-anchored, not Easter-keyed: they cross-validate
# across DIFFERENT taregirs that share a Gregorian Easter (2010 Ա == 2021 Ս, both Greg
# Easter 04-04). The canons place them "after the last feasts of the fourth week of the
# Assumption" in most years, but the Ս leap rubric (p.619) states they move to "after the
# tenth Sunday [of the Cross]" -- the pre-Advent week. Anchored to the engine's Heesnak
# (Advent-eve) Sunday = sunday_closest_to(y, 11, 18): Andrew = Mon (HE-6), Adrian = Tue
# (HE-5), Abraham & Khoren = Thu (HE-3). Reproduces GT 2010/2021 (Nov 15/16/18) exactly.
# Applied to every cycle (solar, calendar-derived); the drop-guard ships it only where the
# cached years of the type agree -- August placements (e.g. taregir Ր) drop the Nov copy.
# Readings resolve in the Ex (post-Exaltation) zone at runtime.
_AUTUMN_MARCH = [
    (6, "Ex", "andrew_the_general"),        # Heesnak - 6 = Monday
    (5, "Ex", "adrian_and_his"),            # Heesnak - 5 = Tuesday
    (3, "Ex", "abraham_and_khoren"),        # Heesnak - 3 = Thursday
]

# Per-taregir autumn-order overrides for the leap parity, keyed by the leap year's Gregorian
# Easter md. The default `_AUTUMN_MARCH` order reproduces the non-leap taregirs (2010 Ա /
# 2021 Ս), but taregir ԹԸ (2004, Greg Easter 04-11) lays the triplet in a different order --
# Abraham & Khoren (Mon), Andrew (Tue), Adrian (Thu). [SOURCE-CONFIRMATION PENDING: the Ը
# canon (p.573) carries a leap redirection rather than the plain triplet at these coordinates;
# this order reproduces 2004 GT (Nov 15 Abraham, Nov 16 Andrew, Nov 18 Adrian) and is validated
# by the cache drop-guard, but has not yet been read off the plate line-for-line.]
_SOURCE_AUTUMN_LEAP = {
    "04-11": [
        (6, "Ex", "abraham_and_khoren"),    # Heesnak - 6 = Monday
        (5, "Ex", "andrew_the_general"),    # Heesnak - 5 = Tuesday
        (3, "Ex", "adrian_and_his"),        # Heesnak - 3 = Thursday
    ],
}


def _autumn_entries(easter_md, ref=None, sequence=_AUTUMN_MARCH):
    """{ "MM-DD": [zone, sid] } for the solar autumn triplet of the year-type with Gregorian
    Easter `easter_md`, anchored to that type's Heesnak (Advent-eve) Sunday. Anchored to a
    representative year's November weekday grid (`ref`, default a rep year of the Easter date);
    a per-taregir leap override passes a leap rep year and its own `sequence`."""
    ref = ref or _rep_easter(easter_md)
    if ref is None:
        return {}
    he = L.sunday_closest_to(ref.year, 11, 18)
    out = {}
    for back, zone, sid in sequence:
        nd = he - datetime.timedelta(days=back)
        out[f"{nd.month:02d}-{nd.day:02d}"] = [zone, sid]
    return out


def _summer_entries(easter_md, sequence=_SUMMER_SEQUENCE, start_off=19):
    """{ "MM-DD": ["Tr", sid] } for the post-Transfiguration saints of the canon whose
    Easter is `easter_md`, from a canonical weekday march anchored to that year's Vardavar.
    The generic march starts on the Saturday of Transfiguration's third week (Vardavar + 20;
    cursor seeded at the preceding Friday, `start_off` = 19). A source-derived per-canon
    sequence (see `_SOURCE_SUMMER`) supplies its own `start_off` -- the full Ր / Թ marches
    open on the first saint-Saturday after Vardavar (`start_off` = 5). Pass a leap-override
    `sequence` for a leap taregir."""
    easter = _rep_easter(easter_md)
    if easter is None:
        return {}
    cursor = easter + datetime.timedelta(days=98 + start_off)
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


# Per-taregir winter (post-Nativity) sequence overrides, keyed by Gregorian Easter md. The
# generic `_WINTER_SEQUENCE` (distilled from 2011) is right for many taregirs but wrong for
# these two: it omits Eugenia and orders Athanasius before Cyricus. Fed into the same
# consecutive-saint-weekday fill. [SOURCE-CONFIRMATION PENDING: sequences read off GT
# (2004/2009) and consistent with the Թ/Հ canon January sections; drop-guard validated.]
_SOURCE_WINTER = {
    # ԹԸ (2004, leap; winter uses the higher letter Թ, pre-Feb-29): Eugenia sits between
    # Vahan and Eugenios (the generic omission is what shifts the 01-27/01-29 tail).
    "04-11": ["peter_the_patriarch", "hermits_saints_anton", "theodosius_and_the",
              "cyricus_and_his", "fathers_saints_athanasius", "vahan_of_goghtn",
              "eugenia_the_virgin", "eugenios_makarios_valerian"],
    # Հ (2009): compressed -- Vahan absorbs Eugenia and Eugenios absorbs Andrew (readings
    # follow the senior saint per preface §6), then Adrian closes the window.
    "04-12": ["peter_the_patriarch", "hermits_saints_anton", "theodosius_and_the",
              "cyricus_and_his", "fathers_saints_athanasius", "vahan_of_goghtn",
              "eugenios_makarios_valerian", "adrian_and_his"],
}


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
    sequence = _SOURCE_WINTER.get(easter_md, _WINTER_SEQUENCE)
    start, end = L._SAINT_ZONES["PN"]["window"](y)
    slots = []
    d = start
    while d <= end:
        if d.weekday() in (0, 1, 3, 5):     # Mon/Tue/Thu/Sat saint-weekdays
            slots.append(d)
        d += datetime.timedelta(days=1)
    out = {}
    for nd, sid in zip(slots[1:], sequence):           # slots[0] = John the Forerunner
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
    nonleap_only = {}                       # easter_md -> {md} common entries to validate vs
                                            # non-leap cache years only (parity-split winters)
    for easter_md in spans:
        if not easter_md:
            continue
        dm = out.setdefault(easter_md, {})
        # Summer march: a source-derived per-canon sequence where one is transcribed
        # (`_SOURCE_SUMMER`, keyed by Gregorian Easter), else the generic approximation.
        # The transcribed march is authoritative for its year-type and OVERRIDES any dated
        # line the parser lifted from the (mis-keyed) canon sharing this md's Julian label
        # -- that canon governs a different taregir, so its summer saints are wrong here.
        src = _SOURCE_SUMMER.get(easter_md)
        if src:
            for md, rec in _summer_entries(easter_md, src[0], src[1]).items():
                dm[md] = rec
        else:
            for md, rec in _summer_entries(easter_md).items():
                dm.setdefault(md, rec)
        # Solar autumn triplet (Andrew / Adrian / Abraham & Khoren), Heesnak-anchored.
        for md, rec in _autumn_entries(easter_md).items():
            dm.setdefault(md, rec)
        # Per-taregir leap autumn-order override (e.g. ԹԸ 04-11): a distinct triplet order for
        # the leap parity, anchored to that leap year's own November grid, shipped as a leap
        # override so the common map is unaffected.
        aseq = _SOURCE_AUTUMN_LEAP.get(easter_md)
        if aseq:
            ry = _rep_year(easter_md, leap=True)
            if ry is not None:
                lm = leapov.setdefault(easter_md, {})
                for md, rec in _autumn_entries(
                        easter_md, ref=datetime.date(ry, 1, 1), sequence=aseq).items():
                    if _intrinsic(dm.get(md)) != _intrinsic(rec):
                        lm.setdefault(md, rec)
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
                # merge, not overwrite -- an autumn/winter leap override may already exist here
                leapov.setdefault(easter_md, {}).update(lm)

        # Post-Nativity (winter) march: consecutive-fill per parity (the January weekday
        # alignment shifts with leap parity). Common fills the shared map; the leap variant
        # supplies leap-only records for the days it genuinely differs on. A per-taregir
        # `_SOURCE_WINTER` sequence is authoritative and OVERRIDES the (mis-keyed) parse of the
        # canon sharing this md's Julian label -- exactly as `_SOURCE_SUMMER` does.
        win_override = easter_md in _SOURCE_WINTER
        cwin = _winter_entries(easter_md, leap=False)
        for md, rec in cwin.items():
            if win_override:
                dm[md] = rec
            else:
                dm.setdefault(md, rec)
        if win_override:
            # A source-winter grid serves its own parity; the January grid shifts wholesale by
            # leap parity, so validate these common entries against non-leap cache years only
            # (else a leap cache year of the same Gregorian Easter -- on different, fast-day
            # dates -- would spuriously drop them).
            nonleap_only.setdefault(easter_md, set()).update(cwin)
        lm = leapov.setdefault(easter_md, {})
        for md, rec in _winter_entries(easter_md, leap=True).items():
            if _intrinsic(dm.get(md)) != _intrinsic(rec):
                lm.setdefault(md, rec)
        if not lm:
            leapov.pop(easter_md, None)

    dropped = _drop_cache_contradicted(out, leapov, nonleap_only)
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


def _drop_cache_contradicted(out, leapov=None, nonleap_only=None):
    """Drop any cycle entry whose readings disagree with ground truth in a cached year of
    that year-type -- so the shipped tier is cache-consistent (no regression) while
    unobserved year-types stay best-effort. Returns the count dropped.

    Parity-aware: the common map is validated against the NON-leap cache years of an Easter
    date wherever a leap override exists for the day (else against all years), and each leap
    override is validated against the LEAP cache years. This lets the same Easter date ship
    a Peter (non-leap) and an Athanasius (leap) placement without either dropping the other.
    """
    leapov = leapov or {}
    nonleap_only = nonleap_only or {}
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
            # A day with a leap override -- or an explicit parity-split (source-winter) entry --
            # serves only the non-leap parity from the common map.
            years = common_years.get(easter_md, [])
            if md not in lov and md not in nonleap_only.get(easter_md, set()):
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
