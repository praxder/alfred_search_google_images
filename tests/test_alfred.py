"""Tests for Alfred Grid JSON output in workflow/alfred.py."""

import json
import unittest

from workflow.alfred import (
    api_error_item,
    empty_results_item,
    error_item,
    missing_config_item,
    quota_error_item,
    render,
    result_item,
)
from workflow.google import SearchResult


def _sample_result(**overrides):
    defaults = {
        "title": "A photo of a cat",
        "image_url": "https://example.com/cat.jpg",
        "thumbnail_url": "https://encrypted-tbn0.gstatic.com/cat-thumb",
        "source_url": "https://example.com/cats",
        "display_link": "example.com",
        "mime": "image/jpeg",
        "width": 1920,
        "height": 1080,
    }
    defaults.update(overrides)
    return SearchResult(**defaults)


class ResultItemTests(unittest.TestCase):
    def test_given_result_with_thumb_when_render_then_uses_local_icon_path(self):
        item = result_item(_sample_result(), icon_path="/cache/thumb.jpg")

        self.assertEqual(item["icon"], {"path": "/cache/thumb.jpg"})

    def test_given_result_when_render_then_arg_is_direct_image_url(self):
        item = result_item(_sample_result(), icon_path="/cache/x.jpg")
        self.assertEqual(item["arg"], "https://example.com/cat.jpg")

    def test_given_result_when_render_then_quicklook_is_direct_image_url(self):
        item = result_item(_sample_result(), icon_path="/cache/x.jpg")
        self.assertEqual(item["quicklookurl"], "https://example.com/cat.jpg")

    def test_given_result_with_dimensions_when_render_then_subtitle_shows_size_and_host(self):
        item = result_item(_sample_result(), icon_path="/cache/x.jpg")
        self.assertEqual(item["subtitle"], "1920×1080 · example.com")

    def test_given_result_without_dimensions_when_render_then_subtitle_falls_back_to_host(self):
        item = result_item(_sample_result(width=0, height=0), icon_path="/cache/x.jpg")
        self.assertEqual(item["subtitle"], "example.com")

    def test_given_result_when_render_then_modifier_payloads_are_present(self):
        item = result_item(_sample_result(), icon_path="/cache/x.jpg")
        mods = item["mods"]
        self.assertEqual(mods["shift"]["arg"], "https://example.com/cat.jpg")
        self.assertEqual(mods["cmd"]["arg"], "https://example.com/cat.jpg")
        self.assertEqual(mods["alt"]["arg"], "https://example.com/cats")
        for mod in ("shift", "cmd", "alt"):
            self.assertTrue(mods[mod]["subtitle"], f"{mod} subtitle should be non-empty")

    def test_given_no_icon_path_when_render_then_uses_fallback_icon_key(self):
        item = result_item(_sample_result(), icon_path=None)
        # Either no icon key, or icon dict pointing at a fallback path.
        if "icon" in item:
            self.assertIn("path", item["icon"])
            self.assertNotEqual(item["icon"]["path"], "")

    def test_given_result_when_render_then_title_matches_result_title(self):
        item = result_item(_sample_result(title="My title"), icon_path="/cache/x.jpg")
        self.assertEqual(item["title"], "My title")

    def test_given_blank_title_when_render_then_falls_back_to_display_link(self):
        item = result_item(_sample_result(title=""), icon_path="/cache/x.jpg")
        self.assertEqual(item["title"], "example.com")

    def test_given_result_when_render_then_uid_is_stable_for_same_image_url(self):
        a = result_item(_sample_result(), icon_path="/cache/x.jpg")
        b = result_item(_sample_result(), icon_path="/cache/y.jpg")
        self.assertEqual(a["uid"], b["uid"])

    def test_given_different_image_urls_when_render_then_uids_differ(self):
        a = result_item(_sample_result(image_url="https://example.com/a.jpg"), icon_path="/x")
        b = result_item(_sample_result(image_url="https://example.com/b.jpg"), icon_path="/x")
        self.assertNotEqual(a["uid"], b["uid"])


class RenderTests(unittest.TestCase):
    def test_given_items_when_render_then_returns_valid_json_string(self):
        rendered = render([{"title": "x", "valid": False}])
        payload = json.loads(rendered)
        self.assertEqual(payload["view"], "grid")
        self.assertEqual(payload["items"], [{"title": "x", "valid": False}])

    def test_given_empty_items_when_render_then_returns_empty_items_array(self):
        rendered = render([])
        payload = json.loads(rendered)
        self.assertEqual(payload["items"], [])


class ErrorItemTests(unittest.TestCase):
    def test_given_title_and_subtitle_when_error_item_then_invalid_with_message(self):
        item = error_item("Something failed", "Try again later")

        self.assertEqual(item["title"], "Something failed")
        self.assertEqual(item["subtitle"], "Try again later")
        self.assertFalse(item["valid"])

    def test_missing_config_item_lists_missing_variable_names(self):
        item = missing_config_item(["google_api_key", "google_cse_id"])

        self.assertIn("google_api_key", item["subtitle"])
        self.assertIn("google_cse_id", item["subtitle"])
        self.assertFalse(item["valid"])

    def test_api_error_item_includes_message(self):
        item = api_error_item("Bad cx")
        self.assertIn("Bad cx", item["subtitle"])
        self.assertFalse(item["valid"])

    def test_quota_error_item_mentions_quota(self):
        item = quota_error_item("Daily limit exceeded")
        self.assertIn("Daily limit exceeded", item["subtitle"])
        self.assertFalse(item["valid"])
        # Title should make it clear this is a quota issue.
        self.assertTrue(any(token in item["title"].lower() for token in ("quota", "limit")))

    def test_empty_results_item_mentions_query(self):
        item = empty_results_item("flying squirrel")
        self.assertIn("flying squirrel", item["subtitle"] + item["title"])
        self.assertFalse(item["valid"])


if __name__ == "__main__":
    unittest.main()
