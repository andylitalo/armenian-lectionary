"""Armenian Church lectionary engine (Տօնացոյց / Ճաշոց).

Self-contained and OFFLINE. Public API:

    >>> import datetime, armenian_lectionary
    >>> armenian_lectionary.compute_armenian_lectionary(datetime.date(2026, 4, 5))
    >>> armenian_lectionary.calculate_liturgical_mode(datetime.date(2026, 4, 5))
    {'Tone': 'ԱՁ', 'Number': 1}

``compute_armenian_lectionary`` serves ``MIN_YEAR``-``MAX_YEAR`` (2001-2027) and raises
``ValueError`` outside it; ``calculate_liturgical_mode`` is pure arithmetic and takes any
date.

Internal helpers and constants remain importable from
``armenian_lectionary.engine``; the public surface is kept deliberately small.
"""

from .engine import (
    compute_armenian_lectionary,
    calculate_gregorian_easter,
    calculate_liturgical_mode,
    LITURGICAL_MODES,
    MAX_YEAR,
    MIN_YEAR,
    SUPPORTED_LANGUAGES,
)

__version__ = "1.2.3"
__all__ = [
    "compute_armenian_lectionary",
    "calculate_gregorian_easter",
    "calculate_liturgical_mode",
    "LITURGICAL_MODES",
    "MIN_YEAR",
    "MAX_YEAR",
    "SUPPORTED_LANGUAGES",
    "__version__",
]
