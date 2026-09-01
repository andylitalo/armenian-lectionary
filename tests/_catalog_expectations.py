"""Read a test's expected observance text from the live catalog, by id, instead of
copy-pasting ``approved_en``/``approved_hy`` as a literal string.

A hardcoded literal in a test breaks on every reviewed rename in
dev/observance_name_review.tsv for no reason -- the test isn't checking that the wording
is a specific string, it's checking that the RIGHT DAY/FAMILY/COLLISION-WINNER is served.
Reading the expectation from ``engine._OBSERVANCE_CATALOG`` by id keeps that check and
drops the wording pin, so a rename plus a rebuild needs no test edit.

Not for every test: a handful (``TestGeneratedLabelsResolveThroughTheCatalog`` and
siblings in tests/test_language.py, tests/test_observance_name_review.py, the
dev/verify_*.py scripts) are already independently rename-safe by construction -- they
read the live catalog or a monkeypatched synthetic value themselves -- and don't need
this helper.
"""

import re

from armenian_lectionary import engine

_ORD_EN_RE = re.compile(r"^\w+ day of (.+)$")
_ORD_HY_RE = re.compile(r"^[Ա-Ֆ]+ օր (.+)$")


def text(sid, lang="en"):
    """The catalog's current text for ``sid``."""
    return engine._OBSERVANCE_CATALOG[sid][lang]


def bare_en(sid):
    """The family name behind an "{ordinal} day of X" catalog entry, current as of the
    live catalog -- for a test asserting an ordinal-day sentence without hardcoding X."""
    m = _ORD_EN_RE.match(text(sid))
    return m.group(1) if m else text(sid)


def bare_hy(sid):
    """The Armenian sibling of :func:`bare_en`."""
    m = _ORD_HY_RE.match(text(sid, "hy"))
    return m.group(1) if m else text(sid, "hy")
