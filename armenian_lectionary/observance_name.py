"""The name of a liturgical day: an ordered list of observances, and how it is written.

A day's ``"Liturgical Day"`` is not one string with a delimiter in it. It is an ordered
list of the observances the day carries -- a calendar-position label at the head, one or
more commemorations, an ``Eve of ...`` note at the tail -- and CLAUDE.md's rule is that
each of those is one CANON, with its own catalog id, not one printed line. The engine
composes that list in stages: the table or a tier states the commemorations, then per-date
overlays add the components a table key shared by several civil years cannot hold.

Every one of those stages used to re-derive the list. Split on the separator, drop the
placeholders, find the component matching some predicate, replace or insert it, join back
up, and remember that a served name is never empty. Seven functions in ``engine.py`` did
that, four of them with a slightly different idea of which components to drop and three
with a different way of spelling the empty-name fallback.

This module holds the encoding, once. What it deliberately does NOT hold is the domain:
it has no opinion on what a position label looks like, which strings are placeholders, or
which observance outranks which. Those stay in ``engine.py`` and reach this module as
predicates and explicit ``drop`` sets, which is what keeps this importable from anywhere
in the package without a cycle -- and what keeps a rename or a new position family from
being a change to two files.

Instances are immutable; every operation returns a new name.
"""

# The join between components. THE mention of it: everything else asks this module.
#
# ``dev/`` still spells it out in places, and ``dev/fetch_reference.py`` and
# ``dev/fetch_translations.py`` must keep their own copy on purpose -- they collapse the
# source's ``<br>``-delimited HTML onto it before this package ever sees the text.
OBSERVANCE_SEP = " — "


class ObservanceName:
    """The components of a day's name, in served order.

    Construct with :meth:`parse` from text the engine already holds, or directly from
    components. ``render()`` writes it back out.

    A rendered name may be empty -- ``parse("")`` is a real thing, and so is a name whose
    every component was dropped -- so the "a served name is never empty" contract
    (``tests/test_observance_contract.py``) is the CALLER's, stated at each site as an
    explicit fallback. This module will not invent a name to satisfy it.
    """

    __slots__ = ("_parts",)

    def __init__(self, parts=()):
        self._parts = tuple(parts)

    @classmethod
    def parse(cls, text, drop=()):
        """Split ``text`` into components, dropping empties and anything in ``drop``.

        ``drop`` is explicit at every call site rather than defaulted, because the sites
        genuinely disagree: the position overlay drops the bare fast markers as well as
        the placeholders, the genocide re-anchor drops neither, and the language
        resolution drops nothing at all.
        """
        return cls(p for p in (text or "").split(OBSERVANCE_SEP) if p and p not in drop)

    @property
    def parts(self):
        """The components, in served order."""
        return self._parts

    def render(self):
        """The served string. Empty when there are no components -- see the class note."""
        return OBSERVANCE_SEP.join(self._parts)

    def __bool__(self):
        return bool(self._parts)

    def __len__(self):
        return len(self._parts)

    def __iter__(self):
        return iter(self._parts)

    def __eq__(self, other):
        return isinstance(other, ObservanceName) and self._parts == other._parts

    def __hash__(self):
        return hash(self._parts)

    def __repr__(self):
        return f"ObservanceName({list(self._parts)!r})"

    # ----------------------------------------------------------------- queries

    def find(self, predicate):
        """The first component satisfying ``predicate``, or ``None``."""
        return next((p for p in self._parts if predicate(p)), None)

    def has(self, predicate):
        """True if any component satisfies ``predicate``."""
        return any(predicate(p) for p in self._parts)

    # ------------------------------------------------------------ replacements

    def replace(self, predicate, text):
        """Every component satisfying ``predicate``, replaced by ``text``.

        Every replacement in the engine is of a component the day has exactly one of (a
        position label, an eve note), so "every" and "the first" coincide; this replaces
        all of them so a name that somehow carried two would not keep one of them.
        """
        return ObservanceName(text if predicate(p) else p for p in self._parts)

    def map(self, fn):
        """Every component through ``fn`` -- the language resolution's whole shape."""
        return ObservanceName(fn(p) for p in self._parts)

    def without(self, texts):
        """Every component except those in ``texts``."""
        return ObservanceName(p for p in self._parts if p not in texts)

    # --------------------------------------------------------------- placement
    #
    # Where a component goes is a liturgical fact, not a formatting one: the source prints
    # the calendar position first and the eve last, and a fixed civil-date observance
    # between the position and the commemoration. Each overlay names the placement it
    # means instead of doing its own list arithmetic.

    def with_head(self, text):
        """``text`` first, then everything else."""
        return ObservanceName((text,) + self._parts)

    def with_tail(self, text):
        """Everything else, then ``text`` last."""
        return ObservanceName(self._parts + (text,))

    def insert_after_head(self, text, is_head):
        """``text`` after a leading component satisfying ``is_head``; first if there is none.

        ``is_head=lambda _: True`` inserts after whatever leads, which is what the
        Annunciation collision wants (the day-count stays at the front, unconditionally).
        """
        keep = 1 if self._parts and is_head(self._parts[0]) else 0
        return ObservanceName(self._parts[:keep] + (text,) + self._parts[keep:])
