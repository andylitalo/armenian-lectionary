"""Decode the legacy Armenian font encoding used by the 2013 Oratsouyts.

The 2013 PDF has a complete text layer, but Armenian letters occupy Latin-1
glyph code points.  Decoding must happen exactly once: some output punctuation
characters are also legacy input code points, so the operation is intentionally
not idempotent.
"""

from __future__ import annotations

import unicodedata


# The legacy font places the 38 uppercase and lowercase Armenian letters at
# alternating Latin-1 code points.  Keeping the regular portion generated makes
# the relationship auditable and avoids a hand-maintained 76-item table.
_LEGACY_GLYPHS = {
    **{
        chr(0xB2 + 2 * index): chr(0x0531 + index)
        for index in range(38)
    },
    **{
        chr(0xB3 + 2 * index): chr(0x0561 + index)
        for index in range(38)
    },
    # Alternate glyphs emitted by different PDF text extractors.
    "•": "գ",
    "μ": "բ",
    "β": "բ",
    # Legacy punctuation.
    "°": "՛",
    "¯": "՜",
    "ª": "՝",
    "±": "՞",
    "£": "։",
    "«": ",",
    "§": "«",
    "¦": "»",
    "®": "…",
    "©": ".",
    "¨": "և",
    # Additional characters observed in the 2013 edition.
    "¥": "(",
    "¤": ")",
    "¬": "-",
}

_TRANSLATION = str.maketrans(_LEGACY_GLYPHS)


def decode_legacy_armenian(raw: str) -> str:
    """Return NFC Unicode text for one legacy-encoded source string."""

    return unicodedata.normalize("NFC", raw.translate(_TRANSLATION))
