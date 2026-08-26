"""The observance catalog: ``id -> {en, hy}``, and the indexes that read it backwards.

An observance's id is what a consumer is meant to store instead of display text, and the
catalog is where the two meet. Three questions get asked of it at runtime, and each used
to have its own module-level global in ``engine.py``:

    what is this id called?          _OBSERVANCE_CATALOG
    which observance is this text?   _TEXT_TO_OBSERVANCE_ID
    what are this text's names?      _TEXT_TO_OBSERVANCE_NAMES

The reverse indexes are derived from the forward one, so they can go stale -- and they
did, structurally: tests substitute a small catalog to exercise resolution, which meant
an index built at import would keep answering from the shipped one. ``engine.py`` grew a
fourth global (``_OBSERVANCE_INDEX_FOR``) and two accessors that compared it by identity
on every call and rebuilt when it had moved, plus a ``cache_clear()`` on an unrelated
``lru_cache`` that happened to memoize a scan resolved through the index.

None of that was about observances. It was about a dependency being created rather than
accepted. Here the indexes are built in ``__init__`` from the entries the instance was
constructed with, so there is no moment at which they can disagree with it: swapping the
catalog means constructing another one, and its indexes come with it. The staleness
machinery does not move -- it stops existing.

:attr:`ObservanceCatalog.own_day_cache` is the same idea applied to the one cache the
engine keeps against a catalog. It lives on the instance rather than on the function, so
a different catalog is a different cache by construction, and nothing has to remember to
invalidate anything.

Read access is dict-like on purpose (``catalog[sid]``, ``.get``, ``.items()``, ``in``,
truthiness): a good deal of dev tooling and several tests read entries by id, and that is
a fair thing to do with a catalog. What is NOT dict-like is writing -- an instance is
built complete or not at all.
"""

import json


class ObservanceCatalog:
    """``id -> {"en": ..., "hy": ...}``, with the text indexes built alongside."""

    __slots__ = ("_entries", "_by_text", "_ids_by_text", "own_day_cache")

    def __init__(self, entries=()):
        self._entries = dict(entries)
        # One key set for both indexes, because one observance is one CANON: where the
        # source prints a longer or shorter companion list for the same liturgical day,
        # that is the Tōnats'oyts packing several First Volume canons onto one line, not
        # one observance under two names. The packed line's components each resolve here
        # on their own (docs/observance-name-corrections.md section 7).
        self._by_text = {entry["en"]: entry for entry in self._entries.values()}
        self._ids_by_text = {entry["en"]: sid for sid, entry in self._entries.items()}
        # Scratch space for the engine's per-liturgical-year own-day scan. Here rather
        # than on the function so that swapping the catalog swaps the cache with it; see
        # engine._canons_with_own_day.
        self.own_day_cache = {}

    @classmethod
    def load(cls, path):
        """The catalog at ``path``, or an empty one if the file is absent.

        Absent is a thin checkout and degrades to English/literal text everywhere, the
        convention every other shipped data file uses. Malformed is NOT swallowed -- that
        is a build error, and failing at import beats serving half a corpus.
        """
        try:
            with open(path, encoding="utf-8") as fh:
                return cls(json.load(fh))
        except FileNotFoundError:
            return cls()

    # ------------------------------------------------------------- the questions

    def id_of(self, text):
        """The observance a served English component names, or ``None``.

        ``None`` rather than raising: this is the serving path, which must never fail on
        a name. ``dev/observance_ids.ids_for_text`` is the one that raises, because a
        build may not ship a component it cannot identify.
        """
        return self._ids_by_text.get(text)

    def names_for(self, text):
        """``{"en": ..., "hy": ...}`` for a served English component, or ``None``."""
        return self._by_text.get(text)

    def text_of(self, sid, default, lang="en"):
        """``sid``'s current text, or ``default`` if the catalog or the id is absent.

        Lets a hand-written literal stay a correct fallback for a thin install while a
        full checkout always serves the live, renamed text: a TSV rename of one of the
        literal-served observances (the pre-Lent cohort, a fixed civil date, an
        extreme-early-Easter composite) reaches this call with no engine.py edit.
        """
        entry = self._entries.get(sid)
        return entry.get(lang, default) if entry else default

    def replacing(self, sid, **fields):
        """A new catalog with ``sid``'s named fields overridden.

        Renaming one observance and asking what the engine then serves is the whole shape
        of the rename tests, and each of them used to spell it as a dict spread that also
        had to remember to rebuild the reverse index by hand. Here the new catalog indexes
        itself, so the two cannot disagree.
        """
        if sid not in self._entries:
            raise KeyError(sid)
        return ObservanceCatalog(
            {**self._entries, sid: {**self._entries[sid], **fields}})

    # ----------------------------------------------------------- dict-like reads

    def __bool__(self):
        return bool(self._entries)

    def __len__(self):
        return len(self._entries)

    def __iter__(self):
        return iter(self._entries)

    def __contains__(self, sid):
        return sid in self._entries

    def __getitem__(self, sid):
        return self._entries[sid]

    def get(self, sid, default=None):
        return self._entries.get(sid, default)

    def items(self):
        return self._entries.items()

    def keys(self):
        return self._entries.keys()

    def values(self):
        return self._entries.values()

    def __repr__(self):
        return f"ObservanceCatalog({len(self._entries)} observances)"
