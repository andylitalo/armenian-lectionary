"""The encoding of a day's name, tested at its own interface.

``ObservanceName`` holds what seven functions in ``engine.py`` each used to re-derive:
how a name splits into observances, which components a stage drops, where a new one
goes, and that operations do not mutate what they are given. None of that needed the
ground-truth cache to check, but before the module existed there was nowhere to check it
except end-to-end through the cache-gated name tests -- so in CI, where those skip, the
rules were unasserted.

These need nothing but the package, so they run everywhere.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary.observance_name import (                         # noqa: E402
    OBSERVANCE_SEP, ObservanceName)

FAST = "Sixth day of the Fast of Nativity"
SAINT = "Sts. Vahan of Goghtn, Gordius, Polyeuctus and Grigoris"
EVE = "Eve of Great Lent"
PLACEHOLDER = "(commemoration)"


def is_eve(component):
    return component.startswith("Eve of ")


class TestParse(unittest.TestCase):
    def test_splits_into_components(self):
        name = ObservanceName.parse(OBSERVANCE_SEP.join([FAST, SAINT, EVE]))
        self.assertEqual(name.parts, (FAST, SAINT, EVE))

    def test_a_single_component_is_a_name(self):
        self.assertEqual(ObservanceName.parse(SAINT).parts, (SAINT,))

    def test_empty_text_is_an_empty_name(self):
        for text in ("", None):
            name = ObservanceName.parse(text)
            self.assertEqual(name.parts, ())
            self.assertFalse(name)
            self.assertEqual(name.render(), "")

    def test_drops_nothing_by_default(self):
        """The default must not be 'drop placeholders' -- one caller relies on keeping
        them (the genocide re-anchor runs before the overlays that consume them)."""
        name = ObservanceName.parse(OBSERVANCE_SEP.join([PLACEHOLDER, SAINT]))
        self.assertEqual(name.parts, (PLACEHOLDER, SAINT))

    def test_drops_what_it_is_told_to(self):
        name = ObservanceName.parse(
            OBSERVANCE_SEP.join([PLACEHOLDER, SAINT, "Fast day"]),
            drop={PLACEHOLDER, "Fast day"})
        self.assertEqual(name.parts, (SAINT,))

    def test_dropping_everything_leaves_an_empty_name(self):
        """The module will not invent a name; the fallback is the caller's contract."""
        name = ObservanceName.parse(PLACEHOLDER, drop={PLACEHOLDER})
        self.assertEqual(name.render(), "")

    def test_round_trips(self):
        text = OBSERVANCE_SEP.join([FAST, SAINT, EVE])
        self.assertEqual(ObservanceName.parse(text).render(), text)


class TestQueries(unittest.TestCase):
    def setUp(self):
        self.name = ObservanceName.parse(OBSERVANCE_SEP.join([FAST, SAINT, EVE]))

    def test_find_returns_the_first_match(self):
        self.assertEqual(self.name.find(is_eve), EVE)

    def test_find_returns_none_when_absent(self):
        self.assertIsNone(ObservanceName.parse(SAINT).find(is_eve))

    def test_has_agrees_with_find(self):
        for name in (self.name, ObservanceName.parse(SAINT), ObservanceName()):
            self.assertEqual(name.has(is_eve), name.find(is_eve) is not None)

    def test_iterates_in_served_order(self):
        self.assertEqual(list(self.name), [FAST, SAINT, EVE])
        self.assertEqual(len(self.name), 3)


class TestOperations(unittest.TestCase):
    def setUp(self):
        self.name = ObservanceName.parse(OBSERVANCE_SEP.join([FAST, SAINT, EVE]))

    def test_operations_do_not_mutate(self):
        """Every overlay chains these; a mutating operation would corrupt the stage
        before it, which is exactly what list surgery on a shared list used to risk."""
        before = self.name.parts
        self.name.with_head("x")
        self.name.with_tail("x")
        self.name.without({SAINT})
        self.name.replace(is_eve, "x")
        self.name.map(str.upper)
        self.name.insert_after_head("x", lambda _: True)
        self.assertEqual(self.name.parts, before)

    def test_replace_swaps_every_match(self):
        renamed = self.name.replace(is_eve, "Eve of the Great Fast")
        self.assertEqual(renamed.parts, (FAST, SAINT, "Eve of the Great Fast"))

    def test_replace_is_a_no_op_when_nothing_matches(self):
        self.assertEqual(ObservanceName.parse(SAINT).replace(is_eve, "x").parts, (SAINT,))

    def test_map_applies_to_every_component(self):
        self.assertEqual(self.name.map(len).parts, (len(FAST), len(SAINT), len(EVE)))

    def test_without_removes_by_exact_text(self):
        self.assertEqual(self.name.without({SAINT}).parts, (FAST, EVE))
        self.assertEqual(self.name.without({"not present"}).parts, self.name.parts)

    def test_with_head_and_with_tail(self):
        self.assertEqual(ObservanceName.parse(SAINT).with_head(FAST).parts, (FAST, SAINT))
        self.assertEqual(ObservanceName.parse(SAINT).with_tail(EVE).parts, (SAINT, EVE))

    def test_with_tail_on_an_empty_name_is_the_whole_name(self):
        self.assertEqual(ObservanceName().with_tail(EVE).render(), EVE)


class TestInsertAfterHead(unittest.TestCase):
    """Where a fixed civil-date observance goes: after the position label if there is
    one, ahead of the commemoration either way."""

    NEW_YEAR = "Blessing of the Pomegranates"

    def test_inserts_after_a_matching_head(self):
        name = ObservanceName.parse(OBSERVANCE_SEP.join([FAST, SAINT]))
        self.assertEqual(
            name.insert_after_head(self.NEW_YEAR, lambda p: p == FAST).parts,
            (FAST, self.NEW_YEAR, SAINT))

    def test_inserts_first_when_the_head_does_not_match(self):
        name = ObservanceName.parse(SAINT)
        self.assertEqual(
            name.insert_after_head(self.NEW_YEAR, lambda p: p == FAST).parts,
            (self.NEW_YEAR, SAINT))

    def test_inserts_first_into_an_empty_name(self):
        self.assertEqual(
            ObservanceName().insert_after_head(self.NEW_YEAR, lambda _: True).parts,
            (self.NEW_YEAR,))

    def test_an_always_true_predicate_inserts_after_whatever_leads(self):
        """The Annunciation collision's rule: the day-count stays at the front
        unconditionally, and the Annunciation goes directly behind it."""
        name = ObservanceName.parse(OBSERVANCE_SEP.join([FAST, SAINT]))
        self.assertEqual(
            name.insert_after_head("Annunciation", lambda _: True).parts,
            (FAST, "Annunciation", SAINT))


class TestValueSemantics(unittest.TestCase):
    def test_equal_by_components(self):
        self.assertEqual(ObservanceName.parse(SAINT), ObservanceName([SAINT]))
        self.assertNotEqual(ObservanceName.parse(SAINT), ObservanceName([FAST]))

    def test_not_equal_to_its_own_text(self):
        """A name is a list of observances, not the string it renders to. Comparing one
        to a string is the confusion this module exists to end, so it must not be true
        by accident."""
        self.assertNotEqual(ObservanceName.parse(SAINT), SAINT)

    def test_hashable(self):
        self.assertEqual(len({ObservanceName([SAINT]), ObservanceName([SAINT])}), 1)


class TestTheEngineDoesNotReDeriveTheEncoding(unittest.TestCase):
    """The deepening, asserted rather than trusted to survive the next overlay.

    ``engine.py`` had 21 places that split or joined on the separator. The point of the
    module is that it now has none: a stage that needs the components asks for them.
    Nothing stops the next one from reaching for ``.split()`` again, so this notices.

    ``_OBSERVANCE_SEP`` itself stays in ``engine.py`` as a re-export -- dev tooling and
    tests import it from there -- so this looks for the surgery, not the name.
    """

    def test_engine_never_splits_or_joins_a_name_itself(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "armenian_lectionary", "engine.py")
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
        # Comments and docstrings still discuss the separator by name; only code that
        # takes a name apart or puts one back together is a finding.
        offenders = [line.strip() for line in source.splitlines()
                     if re.search(r"(?:_?OBSERVANCE_SEP\s*\.\s*join"
                                  r"|\.split\(\s*_?OBSERVANCE_SEP)", line)
                     and not line.lstrip().startswith("#")]
        self.assertEqual(
            [], offenders,
            "engine.py takes an observance name apart by hand; use "
            "armenian_lectionary.observance_name.ObservanceName instead:\n  "
            + "\n  ".join(offenders))


if __name__ == "__main__":
    unittest.main()
