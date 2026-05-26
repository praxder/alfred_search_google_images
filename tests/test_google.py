"""Tests for Google Custom Search response mapping in workflow/google.py."""

import io
import json
import unittest
import urllib.error
from unittest.mock import patch

from workflow.google import (
    ApiError,
    MissingConfigError,
    QuotaError,
    SearchConfig,
    SearchResult,
    map_response,
    search_images,
    validate_config,
)


def _sample_item(**overrides):
    item = {
        "title": "A photo of a cat",
        "link": "https://example.com/cat.jpg",
        "displayLink": "example.com",
        "mime": "image/jpeg",
        "image": {
            "contextLink": "https://example.com/cats",
            "thumbnailLink": "https://encrypted-tbn0.gstatic.com/cat-thumb",
            "width": 1920,
            "height": 1080,
            "thumbnailWidth": 160,
            "thumbnailHeight": 90,
            "byteSize": 100000,
        },
    }
    item.update(overrides)
    return item


class MapResponseTests(unittest.TestCase):
    def test_given_response_with_items_when_map_then_returns_search_results(self):
        payload = {"items": [_sample_item()]}

        results = map_response(payload)

        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertIsInstance(result, SearchResult)
        self.assertEqual(result.title, "A photo of a cat")
        self.assertEqual(result.image_url, "https://example.com/cat.jpg")
        self.assertEqual(result.thumbnail_url, "https://encrypted-tbn0.gstatic.com/cat-thumb")
        self.assertEqual(result.source_url, "https://example.com/cats")
        self.assertEqual(result.display_link, "example.com")
        self.assertEqual(result.mime, "image/jpeg")
        self.assertEqual(result.width, 1920)
        self.assertEqual(result.height, 1080)

    def test_given_response_with_no_items_key_when_map_then_returns_empty_list(self):
        results = map_response({})
        self.assertEqual(results, [])

    def test_given_response_with_empty_items_when_map_then_returns_empty_list(self):
        results = map_response({"items": []})
        self.assertEqual(results, [])

    def test_given_item_missing_image_section_when_map_then_uses_safe_defaults(self):
        item = _sample_item()
        del item["image"]

        results = map_response({"items": [item]})

        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result.image_url, "https://example.com/cat.jpg")
        self.assertEqual(result.thumbnail_url, "")
        self.assertEqual(result.source_url, "")
        self.assertEqual(result.width, 0)
        self.assertEqual(result.height, 0)

    def test_given_item_missing_link_when_map_then_skips_item(self):
        bad_item = _sample_item()
        del bad_item["link"]
        good_item = _sample_item(link="https://example.com/keep.jpg")

        results = map_response({"items": [bad_item, good_item]})

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].image_url, "https://example.com/keep.jpg")

    def test_given_multiple_items_when_map_then_preserves_order(self):
        items = [
            _sample_item(link="https://example.com/1.jpg", title="One"),
            _sample_item(link="https://example.com/2.jpg", title="Two"),
            _sample_item(link="https://example.com/3.jpg", title="Three"),
        ]

        results = map_response({"items": items})

        self.assertEqual([r.title for r in results], ["One", "Two", "Three"])

    def test_given_item_missing_optional_fields_when_map_then_uses_empty_strings(self):
        # Minimal item with only the required link.
        results = map_response({"items": [{"link": "https://example.com/x.jpg"}]})

        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result.title, "")
        self.assertEqual(result.display_link, "")
        self.assertEqual(result.mime, "")
        self.assertEqual(result.thumbnail_url, "")
        self.assertEqual(result.source_url, "")


class ValidateConfigTests(unittest.TestCase):
    def test_given_complete_config_when_validate_then_does_not_raise(self):
        validate_config(SearchConfig(api_key="k", cse_id="c"))

    def test_given_missing_api_key_when_validate_then_raises_with_name(self):
        with self.assertRaises(MissingConfigError) as cm:
            validate_config(SearchConfig(api_key="", cse_id="c"))
        self.assertIn("google_api_key", str(cm.exception))

    def test_given_missing_cse_id_when_validate_then_raises_with_name(self):
        with self.assertRaises(MissingConfigError) as cm:
            validate_config(SearchConfig(api_key="k", cse_id=""))
        self.assertIn("google_cse_id", str(cm.exception))

    def test_given_both_missing_when_validate_then_raises_with_both_names(self):
        with self.assertRaises(MissingConfigError) as cm:
            validate_config(SearchConfig(api_key="", cse_id=""))
        message = str(cm.exception)
        self.assertIn("google_api_key", message)
        self.assertIn("google_cse_id", message)


class _FakeResponse:
    def __init__(self, body):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class SearchImagesTests(unittest.TestCase):
    def test_given_missing_config_when_search_then_raises_missing_config(self):
        with self.assertRaises(MissingConfigError):
            search_images("cats", SearchConfig(api_key="", cse_id=""))

    def test_given_successful_response_when_search_then_returns_mapped_results(self):
        body = json.dumps({"items": [_sample_item()]}).encode("utf-8")
        with patch(
            "workflow.google.urllib.request.urlopen", return_value=_FakeResponse(body)
        ) as opener:
            results = search_images(
                "cats",
                SearchConfig(api_key="k", cse_id="c", num=5, safe="active"),
            )
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], SearchResult)
        called_url = opener.call_args.args[0]
        self.assertIn("searchType=image", called_url)
        self.assertIn("num=5", called_url)
        self.assertIn("safe=active", called_url)
        self.assertIn("q=cats", called_url)
        self.assertIn("key=k", called_url)
        self.assertIn("cx=c", called_url)

    def test_given_http_429_when_search_then_raises_quota_error(self):
        err = urllib.error.HTTPError("https://example", 429, "Too Many", {}, io.BytesIO(b""))
        with (
            patch("workflow.google.urllib.request.urlopen", side_effect=err),
            self.assertRaises(QuotaError),
        ):
            search_images("cats", SearchConfig(api_key="k", cse_id="c"))

    def test_given_quota_reason_in_body_when_search_then_raises_quota_error(self):
        body = json.dumps(
            {"error": {"message": "Quota exceeded", "errors": [{"reason": "dailyLimitExceeded"}]}}
        ).encode("utf-8")
        err = urllib.error.HTTPError("https://example", 403, "Forbidden", {}, io.BytesIO(body))
        err.read = lambda: body
        with (
            patch("workflow.google.urllib.request.urlopen", side_effect=err),
            self.assertRaises(QuotaError) as cm,
        ):
            search_images("cats", SearchConfig(api_key="k", cse_id="c"))
        self.assertIn("Quota exceeded", str(cm.exception))

    def test_given_http_400_when_search_then_raises_api_error(self):
        body = json.dumps(
            {"error": {"message": "Bad cx", "errors": [{"reason": "invalid"}]}}
        ).encode("utf-8")
        err = urllib.error.HTTPError("https://example", 400, "Bad Request", {}, io.BytesIO(body))
        err.read = lambda: body
        with (
            patch("workflow.google.urllib.request.urlopen", side_effect=err),
            self.assertRaises(ApiError) as cm,
        ):
            search_images("cats", SearchConfig(api_key="k", cse_id="c"))
        self.assertNotIsInstance(cm.exception, QuotaError)
        self.assertIn("Bad cx", str(cm.exception))

    def test_given_network_failure_when_search_then_raises_api_error(self):
        err = urllib.error.URLError("dns lookup failed")
        with (
            patch("workflow.google.urllib.request.urlopen", side_effect=err),
            self.assertRaises(ApiError),
        ):
            search_images("cats", SearchConfig(api_key="k", cse_id="c"))

    def test_given_invalid_json_response_when_search_then_raises_api_error(self):
        with (
            patch(
                "workflow.google.urllib.request.urlopen",
                return_value=_FakeResponse(b"not json"),
            ),
            self.assertRaises(ApiError),
        ):
            search_images("cats", SearchConfig(api_key="k", cse_id="c"))

    def test_given_num_out_of_range_when_search_then_clamps_to_one_to_ten(self):
        body = json.dumps({"items": []}).encode("utf-8")
        with patch(
            "workflow.google.urllib.request.urlopen", return_value=_FakeResponse(body)
        ) as opener:
            search_images("cats", SearchConfig(api_key="k", cse_id="c", num=42))
        self.assertIn("num=10", opener.call_args.args[0])

        with patch(
            "workflow.google.urllib.request.urlopen", return_value=_FakeResponse(body)
        ) as opener:
            search_images("cats", SearchConfig(api_key="k", cse_id="c", num=0))
        self.assertIn("num=1", opener.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
