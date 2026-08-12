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
