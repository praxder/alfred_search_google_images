"""Tests for thumbnail caching in workflow/cache.py."""

import io
import os
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

from workflow.cache import (
    cached_path,
    fetch_thumbnail,
    workflow_cache_dir,
)


class _FakeResponse:
    def __init__(self, body):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class WorkflowCacheDirTests(unittest.TestCase):
    def test_given_env_var_when_called_then_returns_path_and_creates_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "nested", "cache")
            with patch.dict(os.environ, {"alfred_workflow_cache": target}, clear=False):
                resolved = workflow_cache_dir()
            self.assertEqual(resolved, target)
            self.assertTrue(os.path.isdir(target))

    def test_given_missing_env_var_when_called_then_falls_back_to_temp_dir(self):
        env = {k: v for k, v in os.environ.items() if k != "alfred_workflow_cache"}
        with patch.dict(os.environ, env, clear=True):
            resolved = workflow_cache_dir()
        self.assertTrue(os.path.isdir(resolved))


class CachedPathTests(unittest.TestCase):
    def test_given_same_url_when_called_then_returns_same_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = cached_path("https://x/1.jpg", tmp)
            b = cached_path("https://x/1.jpg", tmp)
            self.assertEqual(a, b)

    def test_given_different_urls_when_called_then_returns_different_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = cached_path("https://x/1.jpg", tmp)
            b = cached_path("https://x/2.jpg", tmp)
            self.assertNotEqual(a, b)

    def test_given_url_when_called_then_path_is_inside_cache_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = cached_path("https://x/1.jpg", tmp)
            self.assertTrue(p.startswith(tmp + os.sep))


class FetchThumbnailTests(unittest.TestCase):
    def test_given_uncached_url_when_fetch_then_writes_file_and_returns_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "workflow.cache.urllib.request.urlopen",
                return_value=_FakeResponse(b"PNGBYTES"),
            ):
                path = fetch_thumbnail("https://x/img.png", cache_dir=tmp)
            self.assertIsNotNone(path)
            self.assertTrue(os.path.isfile(path))
            with open(path, "rb") as f:
                self.assertEqual(f.read(), b"PNGBYTES")

    def test_given_cached_file_when_fetch_then_skips_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            url = "https://x/img.png"
            existing = cached_path(url, tmp)
            os.makedirs(os.path.dirname(existing), exist_ok=True)
            with open(existing, "wb") as f:
                f.write(b"OLD")
            with patch("workflow.cache.urllib.request.urlopen") as opener:
                path = fetch_thumbnail(url, cache_dir=tmp)
            self.assertEqual(path, existing)
            opener.assert_not_called()

    def test_given_http_error_when_fetch_then_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            err = urllib.error.HTTPError("https://x", 503, "down", {}, io.BytesIO(b""))
            with patch("workflow.cache.urllib.request.urlopen", side_effect=err):
                path = fetch_thumbnail("https://x/img.png", cache_dir=tmp)
            self.assertIsNone(path)

    def test_given_network_error_when_fetch_then_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            err = urllib.error.URLError("offline")
            with patch("workflow.cache.urllib.request.urlopen", side_effect=err):
                path = fetch_thumbnail("https://x/img.png", cache_dir=tmp)
            self.assertIsNone(path)

    def test_given_empty_url_when_fetch_then_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = fetch_thumbnail("", cache_dir=tmp)
            self.assertIsNone(path)


if __name__ == "__main__":
    unittest.main()
