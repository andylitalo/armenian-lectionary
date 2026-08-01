"""Armenian Church lectionary engine (Տօնացոյց / Ճաշոց).

Self-contained and OFFLINE. Public API:

    >>> import datetime, armenian_lectionary
    >>> armenian_lectionary.compute_armenian_lectionary(datetime.date(2026, 4, 5))
    >>> armenian_lectionary.calculate_liturgical_mode(datetime.date(2026, 4, 5))
    {'Tone': 'ԱՁ', 'Number': 1}

Internal helpers and constants remain importable from
``armenian_lectionary.engine``; the public surface is kept deliberately small.
"""

from .engine import (
    compute_armenian_lectionary,
    calculate_gregorian_easter,
    calculate_liturgical_mode,
    LITURGICAL_MODES,
    SUPPORTED_LANGUAGES,
)

__version__ = "1.2.3"
__all__ = [
    "compute_armenian_lectionary",
    "calculate_gregorian_easter",
    "calculate_liturgical_mode",
    "LITURGICAL_MODES",
    "SUPPORTED_LANGUAGES",
    "__version__",
]
