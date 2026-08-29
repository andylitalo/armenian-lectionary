"""The tier ladder's ORDER, which is the one thing about it nothing else asserts.

``_compute_lectionary`` used to be 13 sequential ``if``/``return`` blocks, so precedence
was the physical order of 25-line paragraphs: moving one was a conspicuous edit a reviewer
could not miss. It is now a tuple of thirteen names (``engine.TIERS``), and reordering it
is a one-token change that reads like tidying.

That would be fine if the suite defended it. It did not. Swapping the first two adapters
-- ``_tier_prelent_cohort`` above ``_tier_validated_table``, the precedence that adapter's
own comment argues for ("Checked first so the source proper is served consistently ...
rather than the cache-built table entry") -- changes what 117 days serve, under a
different ``Source``, and the whole suite stayed GREEN in CI. Swapping
``_tier_presentation_eve`` above ``_tier_first_volume_winter_continua`` changes one more.
Each is caught by a single ground-truth test, and ``dev/reference_data/`` is git-ignored,
so ``.github/workflows/ci.yml`` skips those (80 of 301 tests) on every push.

Worse, the tuple looks more forgiving than it is: 8 of its 12 adjacent swaps are silent
no-ops, because those tiers never claim the same date. Someone reordering it would get
away with it two times in three.

So this file states the ladder as an assertion instead of as a layout:

* every adapter is ON the ladder, once, in the order it is defined -- an adapter added but
  never wired into ``TIERS`` is dead code nothing else would notice, and definition order
  keeps the file readable top-to-bottom as the precedence it implements;
* the unconditional fallback is last, which is load-bearing in ``engine.py`` and was
  otherwise only a comment;
* each of the 21 real precedence relations is pinned to a date where BOTH tiers apply, so
  a pin fails on a reorder rather than merely restating coverage.

Needs no ground-truth cache; runs in CI. That is the point of it.
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary import engine                                     # noqa: E402


def _tier(bare_name):
    """``PRECEDENCE_PINS`` names adapters without their shared ``_tier_`` prefix."""
    return getattr(engine, "_tier_" + bare_name)


def _date(iso):
    return datetime.date(*(int(part) for part in iso.split("-")))


def _applicable(d):
    """Every tier that claims ``d``, in ladder order. The first one is what gets served."""
    return [tier for tier in engine.TIERS if tier(d) is not None]


# Every pair of tiers that actually contends for a date somewhere in the supported range,
# with a date on which they do. `winner` is the tier the ladder serves there; `loser`
# returns a TierResult for the same date and is passed over. A pin whose loser does NOT
# apply would assert nothing about precedence (test_every_pin_actually_contends), and only
# a pair that meets is worth pinning -- the other 57 pairs are date-disjoint, so their
# relative order in TIERS is unobservable.
#
# Derived by scanning all 9,861 days of MIN_YEAR-MAX_YEAR for dates with more than one
# applicable tier. `n` is how many dates back the relation; the four marked `adjacent` are
# the only swaps in TIERS that change any served day at all.
PRECEDENCE_PINS = (
    # (date, winner, loser, Source served)
    ("2001-02-10", "prelent_cohort", "validated_table",              # adjacent, n=117
     "first-volume-cohort"),
    ("2001-02-10", "prelent_cohort", "fallback", "first-volume-cohort"),
    ("2001-01-16", "validated_table", "cycle_saint", "validated-table"),
    ("2001-01-16", "validated_table", "generative_saint", "validated-table"),
    ("2001-07-25", "validated_table", "generative_continua", "validated-table"),
    ("2002-04-07", "validated_table", "annunciation", "validated-table"),
    ("2002-02-13", "validated_table", "presentation_eve", "validated-table"),
    ("2001-01-26", "validated_table", "first_volume_winter_continua", "validated-table"),
    ("2001-08-12", "validated_table", "first_volume_summer_continua", "validated-table"),
    ("2001-01-01", "validated_table", "fallback", "validated-table"),
    ("2001-09-08", "embedded_composite", "fallback", "validated-composite"),
    ("2002-07-30", "cycle_saint", "generative_saint",                # adjacent, n=69
     "second-volume-cycle"),
    ("2002-07-30", "cycle_saint", "fallback", "second-volume-cycle"),
    ("2008-07-23", "generative_continua", "fallback", "generative-continua"),
    ("2001-04-07", "annunciation", "fallback", "generative-composite"),
    ("2011-02-13", "presentation_eve", "first_volume_winter_continua",  # adjacent, n=1
     "generative-composite"),
    ("2001-02-13", "presentation_eve", "fallback", "generative-composite"),
    ("2011-02-04", "first_volume_winter_continua", "fallback",
     "first-volume-continua"),
    ("2008-07-20", "first_volume_summer_continua", "fallback",
     "first-volume-continua"),
    ("2008-01-19", "john_forerunner", "fallback", "validated-composite"),
    ("2008-01-13", "nativity_octave", "fallback",                    # adjacent, n=1
     "generative-composite"),
)

# The adjacencies that are contended, and so the only ones a swap could change output on.
CONTENDED_ADJACENCIES = (
    ("_tier_prelent_cohort", "_tier_validated_table"),
    ("_tier_cycle_saint", "_tier_generative_saint"),
    ("_tier_presentation_eve", "_tier_first_volume_winter_continua"),
    ("_tier_nativity_octave", "_tier_fallback"),
)


class TestTheLadderIsComplete(unittest.TestCase):
    """``TIERS`` is the ladder. An adapter missing from it is not a tier at all."""

    def setUp(self):
        self.adapters = sorted(
            (obj for name, obj in vars(engine).items()
             if name.startswith("_tier_") and callable(obj)),
            key=lambda f: f.__code__.co_firstlineno)

    def test_every_adapter_is_on_the_ladder_in_definition_order(self):
        """Defined-but-unwired is the failure mode: an adapter absent from TIERS never
        runs, and every other test passes exactly as it did before it was written.
        Definition order is asserted too, so reordering precedence means moving the
        adapter as well -- deliberate friction, and what the old branch chain gave for
        free."""
        self.assertEqual(list(engine.TIERS), self.adapters)

    def test_no_adapter_appears_twice(self):
        self.assertEqual(len(set(engine.TIERS)), len(engine.TIERS))

    def test_the_fallback_is_last(self):
        """``_tier_fallback``'s own comment says it "must stay last in TIERS" because it
        never returns None. Anything after it is unreachable; the comment was the only
        thing saying so."""
        self.assertIs(engine.TIERS[-1], engine._tier_fallback)

    def test_the_fallback_is_unconditional(self):
        """Which is what makes "last" load-bearing, and what lets ``_compute_lectionary``
        read the loop variable after the loop. Includes dates outside MIN_YEAR-MAX_YEAR:
        ``_compute_lectionary`` has no range guard, and ``dev/build_observance_catalog``
        reaches past the range through it."""
        for iso in ("1995-06-15", "2001-01-01", "2008-01-13", "2013-03-31",
                    "2027-12-31", "2040-02-29"):
            with self.subTest(date=iso):
                self.assertIsNotNone(engine._tier_fallback(_date(iso)))

    def test_a_tier_returns_a_TierResult_or_None(self):
        """The ladder's contract, and the reason ``_compute_lectionary`` has exactly one
        dict-construction site. A tier handing back a bare tuple or a dict -- shapes the
        resolvers underneath it still legitimately use -- would build a broken result
        rather than fail here."""
        for iso in {pin[0] for pin in PRECEDENCE_PINS}:
            for tier in engine.TIERS:
                result = tier(_date(iso))
                if result is not None:
                    with self.subTest(date=iso, tier=tier.__name__):
                        self.assertIsInstance(result, engine.TierResult)


class TestPrecedenceIsPinned(unittest.TestCase):
    """Each pin is a date where two tiers both answer and the ladder picks one."""

    def test_the_stated_winner_wins(self):
        for iso, winner, loser, _source in PRECEDENCE_PINS:
            with self.subTest(date=iso, winner=winner, loser=loser):
                self.assertIs(_applicable(_date(iso))[0], _tier(winner))
                self.assertLess(engine.TIERS.index(_tier(winner)),
                                engine.TIERS.index(_tier(loser)))

    def test_every_pin_actually_contends(self):
        """A pin whose loser does not apply on that date would pass however TIERS is
        ordered -- it would assert coverage, not precedence. This is what keeps the table
        above honest as the engine's data changes."""
        for iso, _winner, loser, _source in PRECEDENCE_PINS:
            with self.subTest(date=iso, loser=loser):
                self.assertIn(_tier(loser), _applicable(_date(iso)))

    def test_the_served_source_is_the_winners(self):
        """End to end through ``_compute_lectionary``: the ladder's choice is what a
        consumer gating on ``Source`` actually receives."""
        for iso, _winner, _loser, source in PRECEDENCE_PINS:
            with self.subTest(date=iso, source=source):
                self.assertEqual(engine._compute_lectionary(_date(iso))["Source"], source)

    def test_the_pins_cover_every_contended_adjacency(self):
        """If a future tier makes a fifth adjacency contended, this fails until it is
        pinned too -- otherwise the ladder grows a joint no test holds."""
        pinned = {("_tier_" + win, "_tier_" + lose)
                  for _d, win, lose, _s in PRECEDENCE_PINS}
        adjacent = [(engine.TIERS[i].__name__, engine.TIERS[i + 1].__name__)
                    for i in range(len(engine.TIERS) - 1)]
        self.assertEqual([pair for pair in adjacent if pair in pinned],
                         list(CONTENDED_ADJACENCIES))


if __name__ == "__main__":
    unittest.main()
