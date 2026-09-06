"""HTTP/JSON contract tests for the Flask service."""

import unittest

try:
    from app import app
except ModuleNotFoundError as exc:
    if exc.name in {"flask", "flask_limiter"}:
        raise unittest.SkipTest("Flask web dependencies are not installed") from exc
    raise


class TestReadingsAPI(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, RATELIMIT_ENABLED=False)
        self.client = app.test_client()

    def test_mode_object_survives_json_boundary_in_both_languages(self):
        expected = {"Tone": "ԱՁ", "Number": 1}
        for language in ("en", "hy"):
            with self.subTest(language=language):
                response = self.client.get(
                    "/readings?date=2026-04-05&language=" + language
                )
                self.assertEqual(response.status_code, 200)
                mode = response.get_json()["Mode"]
                self.assertEqual(mode, expected)
                self.assertIs(type(mode["Number"]), int)

    def test_observance_ids_survive_json_boundary_and_do_not_vary_by_language(self):
        expected = [
            "eleventh_sunday_of_the_holy_cross", "presentation_of_the_holy_mother",
            "eve_of_fast_of_advent",
        ]
        ids_by_language = {}
        for language in ("en", "hy"):
            with self.subTest(language=language):
                response = self.client.get(
                    "/readings?date=2004-11-21&language=" + language
                )
                self.assertEqual(response.status_code, 200)
                ids = response.get_json()["ObservanceIds"]
                self.assertEqual(ids, expected)
                ids_by_language[language] = ids
        self.assertEqual(ids_by_language["en"], ids_by_language["hy"])

    def test_observances_survive_json_boundary_with_only_the_name_localized(self):
        """The wire is where an attribute could silently become ``null``: the engine
        coerces to bool precisely so JSON carries `false`, not a missing third value.
        Also pins that the names still join back to the served day over HTTP, which is
        what lets a consumer stop splitting `Liturgical Day` on the separator."""
        by_language = {}
        for language in ("en", "hy"):
            with self.subTest(language=language):
                response = self.client.get(
                    "/readings?date=2026-04-03&language=" + language
                )
                self.assertEqual(response.status_code, 200)
                payload = response.get_json()
                observances = payload["Observances"]
                self.assertEqual([o["id"] for o in observances],
                                 ["great_friday", "passion_crucifixion_burial"])
                for o in observances:
                    self.assertIs(type(o["is_fast"]), bool)
                    self.assertIs(type(o["is_comm"]), bool)
                self.assertEqual(
                    " — ".join(o["name"] for o in observances),
                    payload["Liturgical Day"])
                by_language[language] = observances

        self.assertNotEqual([o["name"] for o in by_language["en"]],
                            [o["name"] for o in by_language["hy"]])
        for a, b in zip(by_language["en"], by_language["hy"]):
            self.assertEqual({k: v for k, v in a.items() if k != "name"},
                             {k: v for k, v in b.items() if k != "name"})

    def test_season_is_not_served(self):
        """Season is an internal tier-provenance label, not a liturgical fact, and no
        consumer relies on it -- it must not leak onto the wire even though the
        package-level compute_armenian_lectionary() still carries it internally.
        """
        response = self.client.get("/readings?date=2026-08-05")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Season", response.get_json())

    def test_out_of_range_date_is_a_400_not_a_500(self):
        """The endpoint answers the range question itself, before the engine raises.

        Both layers now enforce the same bound, and that is deliberate -- but only this one
        can turn it into a useful HTTP response. If the endpoint check were ever dropped on
        the grounds that "the engine handles it", the engine's ValueError would surface as a
        500 with no explanation of the supported window.
        """
        response = self.client.get("/readings?date=2038-02-28")
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertIn("supported_range", payload)
        self.assertEqual(payload["supported_range"], {"min_year": 2001, "max_year": 2027})

    def test_the_endpoint_and_the_engine_agree_on_the_boundary(self):
        """One definition, imported -- not two copies that can drift apart."""
        import app as app_module
        from armenian_lectionary import MAX_YEAR, MIN_YEAR
        self.assertEqual((app_module.MIN_YEAR, app_module.MAX_YEAR),
                         (MIN_YEAR, MAX_YEAR))
        self.assertEqual(
            self.client.get(f"/readings?date={MAX_YEAR}-12-31").status_code, 200)
        self.assertEqual(
            self.client.get(f"/readings?date={MAX_YEAR + 1}-01-01").status_code, 400)

    def test_readings_refs_survives_json_boundary_in_both_languages(self):
        for language in ("en", "hy"):
            with self.subTest(language=language):
                response = self.client.get(
                    "/readings?date=2026-04-05&language=" + language
                )
                self.assertEqual(response.status_code, 200)
                body = response.get_json()
                refs = body["ReadingsRefs"]
                self.assertTrue(refs)
                first = refs[0]
                self.assertEqual(first["book"], "John")
                self.assertEqual(first["citation"], "John 20.1-18")
                self.assertIs(type(first["start_chapter"]), int)


if __name__ == "__main__":
    unittest.main()
