"""Tests for selected-result actions in workflow/action.py."""

import unittest
from unittest.mock import MagicMock, patch

from workflow.action import (
    ClipboardError,
    DownloadError,
    UnsupportedFormatError,
    _fetch_image,
    copy_image,
    detect_format,
    main,
)

_PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
_JPEG_HEADER = b"\xff\xd8\xff\xe0" + b"\x00" * 8
_GIF_HEADER = b"GIF89a" + b"\x00" * 8
_WEBP_HEADER = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 4
_UNKNOWN_HEADER = b"\x00\x01\x02\x03"


class DetectFormatTests(unittest.TestCase):
    def test_given_png_bytes_when_detect_then_returns_pngf(self):
        self.assertEqual(detect_format(_PNG_HEADER), "PNGf")

    def test_given_jpeg_bytes_when_detect_then_returns_jpeg(self):
        self.assertEqual(detect_format(_JPEG_HEADER), "JPEG")

    def test_given_gif_bytes_when_detect_then_returns_gifs(self):
        self.assertEqual(detect_format(_GIF_HEADER), "GIFf")

    def test_given_webp_bytes_when_detect_then_returns_webp(self):
        self.assertEqual(detect_format(_WEBP_HEADER), "WEBP")

    def test_given_unknown_bytes_when_detect_then_returns_empty_string(self):
        self.assertEqual(detect_format(_UNKNOWN_HEADER), "")

    def test_given_empty_bytes_when_detect_then_returns_empty_string(self):
        self.assertEqual(detect_format(b""), "")


class CopyImageTests(unittest.TestCase):
    def test_given_png_url_when_copy_then_clipboard_called_with_pngf_class(self):
        fetcher = MagicMock(return_value=_PNG_HEADER)
        clipboard = MagicMock()
        notifier = MagicMock()

        rc = copy_image(
            "https://example.com/img.png",
            fetcher=fetcher,
            clipboard=clipboard,
            notifier=notifier,
        )

        self.assertEqual(rc, 0)
        fetcher.assert_called_once_with("https://example.com/img.png")
        clipboard.assert_called_once_with(_PNG_HEADER, "PNGf")
        notifier.assert_not_called()

    def test_given_jpeg_url_when_copy_then_clipboard_called_with_jpeg_class(self):
        fetcher = MagicMock(return_value=_JPEG_HEADER)
        clipboard = MagicMock()
        notifier = MagicMock()

        rc = copy_image(
            "https://example.com/img.jpg",
            fetcher=fetcher,
            clipboard=clipboard,
            notifier=notifier,
        )

        self.assertEqual(rc, 0)
        clipboard.assert_called_once_with(_JPEG_HEADER, "JPEG")

    def test_given_webp_url_when_copy_then_converts_then_clipboard_called_with_pngf(self):
        fetcher = MagicMock(return_value=_WEBP_HEADER)
        converter = MagicMock(return_value=_PNG_HEADER)
        clipboard = MagicMock()
        notifier = MagicMock()

        rc = copy_image(
            "https://example.com/img.webp",
            fetcher=fetcher,
            clipboard=clipboard,
            notifier=notifier,
            converter=converter,
        )

        self.assertEqual(rc, 0)
        converter.assert_called_once_with(_WEBP_HEADER)
        clipboard.assert_called_once_with(_PNG_HEADER, "PNGf")
        notifier.assert_not_called()

    def test_given_webp_conversion_fails_when_copy_then_notifies_and_returns_nonzero(self):
        fetcher = MagicMock(return_value=_WEBP_HEADER)
        converter = MagicMock(side_effect=ClipboardError("sips not found"))
        clipboard = MagicMock()
        notifier = MagicMock()

        rc = copy_image(
            "https://example.com/img.webp",
            fetcher=fetcher,
            clipboard=clipboard,
            notifier=notifier,
            converter=converter,
        )

        self.assertNotEqual(rc, 0)
        clipboard.assert_not_called()
        notifier.assert_called_once()

    def test_given_empty_url_when_copy_then_notifies_and_returns_nonzero(self):
        fetcher = MagicMock()
        clipboard = MagicMock()
        notifier = MagicMock()

        rc = copy_image("", fetcher=fetcher, clipboard=clipboard, notifier=notifier)

        self.assertNotEqual(rc, 0)
        fetcher.assert_not_called()
        clipboard.assert_not_called()
        notifier.assert_called_once()

    def test_given_download_failure_when_copy_then_notifies_and_returns_nonzero(self):
        fetcher = MagicMock(side_effect=DownloadError("404 Not Found"))
        clipboard = MagicMock()
        notifier = MagicMock()

        rc = copy_image(
            "https://example.com/x.png",
            fetcher=fetcher,
            clipboard=clipboard,
            notifier=notifier,
        )

        self.assertNotEqual(rc, 0)
        clipboard.assert_not_called()
        notifier.assert_called_once()
        title, message = notifier.call_args.args
        self.assertIn("404", message)

    def test_given_empty_body_when_copy_then_notifies_and_returns_nonzero(self):
        fetcher = MagicMock(return_value=b"")
        clipboard = MagicMock()
        notifier = MagicMock()

        rc = copy_image(
            "https://example.com/x.png",
            fetcher=fetcher,
            clipboard=clipboard,
            notifier=notifier,
        )

        self.assertNotEqual(rc, 0)
        clipboard.assert_not_called()
        notifier.assert_called_once()

    def test_given_unsupported_format_when_copy_then_notifies_and_returns_nonzero(self):
        fetcher = MagicMock(return_value=_UNKNOWN_HEADER)
        clipboard = MagicMock()
        notifier = MagicMock()

        rc = copy_image(
            "https://example.com/x.bin",
            fetcher=fetcher,
            clipboard=clipboard,
            notifier=notifier,
        )

        self.assertNotEqual(rc, 0)
        clipboard.assert_not_called()
        notifier.assert_called_once()

    def test_given_clipboard_failure_when_copy_then_notifies_and_returns_nonzero(self):
        fetcher = MagicMock(return_value=_PNG_HEADER)
        clipboard = MagicMock(side_effect=ClipboardError("osascript exited 1"))
        notifier = MagicMock()

        rc = copy_image(
            "https://example.com/x.png",
            fetcher=fetcher,
            clipboard=clipboard,
            notifier=notifier,
        )

        self.assertNotEqual(rc, 0)
        notifier.assert_called_once()
        title, message = notifier.call_args.args
        self.assertIn("osascript", message)


class FetchImageTests(unittest.TestCase):
    def test_given_non_http_scheme_when_fetch_then_raises_download_error(self):
        with patch("workflow.action.urllib.request.urlopen") as opener:
            with self.assertRaises(DownloadError):
                _fetch_image("file:///etc/passwd")
            opener.assert_not_called()


class ApplescriptStringTests(unittest.TestCase):
    def test_given_quote_when_escaped_then_backslash_quote(self):
        from workflow.action import _applescript_string

        self.assertEqual(_applescript_string('a "b"'), 'a \\"b\\"')

    def test_given_backslash_when_escaped_then_doubled(self):
        from workflow.action import _applescript_string

        self.assertEqual(_applescript_string("a\\b"), "a\\\\b")


class MainTests(unittest.TestCase):
    def test_given_missing_args_when_main_then_returns_nonzero(self):
        with patch("workflow.action._notify") as notify:
            rc = main(["action.py"])
        self.assertNotEqual(rc, 0)
        notify.assert_called_once()

    def test_given_unknown_mode_when_main_then_returns_nonzero(self):
        with patch("workflow.action._notify") as notify:
            rc = main(["action.py", "weird-mode", "https://example.com/x.png"])
        self.assertNotEqual(rc, 0)
        notify.assert_called_once()

    def test_given_copy_image_mode_when_main_then_delegates_to_copy_image(self):
        import workflow.action as action_module

        called = {}

        def fake_copy_image(url, **_kwargs):
            called["url"] = url
            return 0

        original = action_module.copy_image
        action_module.copy_image = fake_copy_image
        try:
            rc = main(["action.py", "copy-image", "https://example.com/cat.png"])
        finally:
            action_module.copy_image = original

        self.assertEqual(rc, 0)
        self.assertEqual(called["url"], "https://example.com/cat.png")


class ExceptionTypeTests(unittest.TestCase):
    def test_download_error_is_exception(self):
        self.assertTrue(issubclass(DownloadError, Exception))

    def test_clipboard_error_is_exception(self):
        self.assertTrue(issubclass(ClipboardError, Exception))

    def test_unsupported_format_error_is_exception(self):
        self.assertTrue(issubclass(UnsupportedFormatError, Exception))


if __name__ == "__main__":
    unittest.main()
