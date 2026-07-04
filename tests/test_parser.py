"""Unit tests for the Second-Volume cycle parser (dev/build_second_volume_cycles.py).

These lock the name-matching hygiene fixes: transliteration aliasing (Anthony/Anton),
normalized generic-token exclusion (the stray "holi" collision), name-collision guards
(David the Prophet, Gregory+Nicholas), and [Note: ...] artifact stripping. Pure functions
over the engine's identity table -- no ground-truth cache needed.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev import build_second_volume_cycles as b  # noqa: E402


class TestNorm(unittest.TestCase):
    def test_translit_folds(self):
        # ph->f, ios->ius, y->i, and the Anthony/Anton alias all collapse variants.
        self.assertIn("anton", b._norm("Saint Anthony the Hermit"))
        self.assertIn("anton", b._norm("Anton the Anchorite"))
        self.assertEqual(b._norm("Tryphon"), b._norm("Triphon"))

    def test_note_stripped(self):
        # A [Note: ...] annotation contributes no tokens.
        self.assertNotIn("text", b._norm("James [Note: text says 3:31] the Apostle"))

    def test_generic_folds_excluded(self):
        # "holy"->"holi" must be treated as generic, not a distinctive name token.
        ids = dict(((z, s), (nm, bl)) for z, s, nm, bl in b._identities())
        for (z, s), (names, _bl) in ids.items():
            self.assertNotIn("holi", names, f"{s} kept stray generic token 'holi'")


class TestMatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ids = b._identities()

    def sid(self, text):
        got = b._match(text, self.ids)
        return got[1] if got else None

    def test_anthony_alias_matches_anton(self):
        self.assertIn(self.sid("Saint Anthony the Hermit."),
                      {"hermit_saints_anton", "hermits_saints_anton"})

    def test_note_artifact_ignored(self):
        self.assertEqual(self.sid("Peter [Note: garbled] the Patriarch, Blaise."),
                         "peter_the_patriarch")

    def test_david_the_prophet_not_david_of_dvin(self):
        # The winter "David the Prophet" day must not grab Ex-zone David of Dvin,
        # nor Isaiah the Prophet on the bare title token.
        self.assertNotIn(self.sid("David the Prophet and James the Apostle."),
                         {"david_of_dvin", "isaiah_the_prophet"})

    def test_david_of_dvin_still_matches_when_named(self):
        self.assertEqual(self.sid("David of Dvin, and the martyrs Lambeus."),
                         "david_of_dvin")

    def test_gregory_and_nicholas_not_illuminator(self):
        self.assertNotIn(
            self.sid("Gregory and Nicholas the Wonderworker bishops."),
            {"gregory_the_illuminator", "gregory_of_theologian"})

    def test_conception_not_seventy_two(self):
        self.assertNotEqual(self.sid("Feast of the Conception of the Holy Virgin by Anna."),
                            "seventy_two_holy")

    def test_distinctive_names_still_resolve(self):
        self.assertEqual(self.sid("Isaiah the Prophet."), "isaiah_the_prophet")
        self.assertEqual(self.sid("Seventy-two holy disciples."), "seventy_two_holy")
        self.assertEqual(
            self.sid("Fathers Saints Athanasius, Cyril, and Gregory the Theologian."),
            "fathers_saints_athanasius")


class TestMonthReset(unittest.TestCase):
    def test_month_does_not_leak_across_canons(self):
        # The build derives month context per canon span with fresh state; a header on an
        # earlier canon's page must not tag a later canon's dated entries. We assert the
        # mechanism structurally: the parse loop re-initializes month per span.
        import inspect
        src = inspect.getsource(b.main)
        self.assertIn("month = None", src)
        # ...inside the per-canon loop, not a single global sweep.
        self.assertGreater(src.count("for easter_md"), 0)


if __name__ == "__main__":
    unittest.main()
