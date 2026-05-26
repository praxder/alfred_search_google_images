"""Tests for the search orchestration entry point in workflow/search.py."""

import io
import json
import unittest
from unittest.mock import patch

from workflow.google import ApiError, QuotaError, SearchResult
from workflow.search import main, run


def _result(**overrides):
    defaults = {
        "title": "Cat",
        "image_url": "https://example.com/cat.jpg",
        "thumbnail_url": "https://t/cat",
        "source_url": "https://example.com/cats",
        "display_link": "example.com",
        "mime": "image/jpeg",
        "width": 800,
        "height": 600,
    }
    defaults.update(overrides)
    return SearchResult(**defaults)


def _full_env(**overrides):
    env = {"google_api_key": "k", "google_cse_id": "c", "result_count": "5", "safe_search": "off"}
    env.update(overrides)
    return env


class RunTests(unittest.TestCase):
    def test_given_missing_creds_when_run_then_returns_missing_config_item(self):
        items = run("cats", {"google_api_key": "", "google_cse_id": ""})
        self.assertEqual(len(items), 1)
        self.assertFalse(items[0]["valid"])
        self.assertIn("google_api_key", items[0]["subtitle"])

    def test_given_empty_query_when_run_then_returns_prompt_item(self):
        items = run("", _full_env())
        self.assertEqual(len(items), 1)
        self.assertFalse(items[0]["valid"])

    def test_given_quota_error_when_run_then_returns_quota_item(self):
        with patch("workflow.search.search_images", side_effect=QuotaError("Daily limit")):
            items = run("cats", _full_env())
        self.assertEqual(len(items), 1)
        self.assertIn("Daily limit", items[0]["subtitle"])

    def test_given_api_error_when_run_then_returns_api_error_item(self):
        with patch("workflow.search.search_images", side_effect=ApiError("Bad cx")):
            items = run("cats", _full_env())
        self.assertEqual(len(items), 1)
        self.assertIn("Bad cx", items[0]["subtitle"])

    def test_given_empty_results_when_run_then_returns_empty_results_item(self):
        with patch("workflow.search.search_images", return_value=[]):
            items = run("flying squirrel", _full_env())
        self.assertEqual(len(items), 1)
        self.assertIn("flying squirrel", items[0]["subtitle"])

    def test_given_results_when_run_then_returns_grid_items_with_cached_icons(self):
        with (
            patch(
                "workflow.search.search_images",
                return_value=[_result(), _result(image_url="https://example.com/2.jpg")],
            ),
            patch("workflow.search.cache.workflow_cache_dir", return_value="/cache"),
            patch(
                "workflow.search.cache.fetch_thumbnail",
                side_effect=["/cache/a.jpg", "/cache/b.jpg"],
            ),
        ):
            items = run("cats", _full_env())
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["icon"]["path"], "/cache/a.jpg")
        self.assertEqual(items[1]["icon"]["path"], "/cache/b.jpg")
        self.assertEqual(items[0]["arg"], "https://example.com/cat.jpg")

    def test_given_thumbnail_fetch_fails_when_run_then_item_still_emitted_with_fallback(self):
        with (
            patch("workflow.search.search_images", return_value=[_result()]),
            patch("workflow.search.cache.workflow_cache_dir", return_value="/cache"),
            patch("workflow.search.cache.fetch_thumbnail", return_value=None),
        ):
            items = run("cats", _full_env())
        self.assertEqual(len(items), 1)
        # Fallback: item still has an icon path that is non-empty.
        self.assertTrue(items[0]["icon"]["path"])
        self.assertEqual(items[0]["arg"], "https://example.com/cat.jpg")


class MainTests(unittest.TestCase):
    def test_given_args_when_main_then_writes_grid_json_to_stdout(self):
        out = io.StringIO()
        with patch("workflow.search.search_images", return_value=[]):
            main(argv=["search.py", "cats"], env=_full_env(), stdout=out)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["view"], "grid")
        self.assertEqual(len(payload["items"]), 1)


if __name__ == "__main__":
    unittest.main()
