"""Entry point invoked by Alfred for selected-result actions (e.g. copy-image)."""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_TIMEOUT = 10.0
MAX_IMAGE_BYTES = 25 * 1024 * 1024  # 25 MiB safety cap


class DownloadError(Exception):
    """Raised when the selected image cannot be downloaded."""


class ClipboardError(Exception):
    """Raised when the image cannot be placed on the macOS clipboard."""


class UnsupportedFormatError(Exception):
    """Raised when the downloaded image format cannot be placed on the clipboard."""


def detect_format(body):
    if not body:
        return ""
    if body.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNGf"
    if body.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if body.startswith(b"GIF87a") or body.startswith(b"GIF89a"):
        return "GIFf"
    if body[:4] == b"RIFF" and body[8:12] == b"WEBP":
        return "WEBP"
    return ""


def copy_image(url, *, fetcher=None, clipboard=None, notifier=None, converter=None):
    fetcher = fetcher or _fetch_image
    clipboard = clipboard or _copy_to_clipboard
    notifier = notifier or _notify
    converter = converter or _convert_webp_to_png

    if not url:
        notifier("Cannot copy image", "No image URL was provided.")
        return 1

    try:
        body = fetcher(url)
    except DownloadError as exc:
        notifier("Image download failed", str(exc))
        return 1

    if not body:
        notifier("Image download failed", "Empty response from image URL.")
        return 1

    fmt = detect_format(body)
    if not fmt:
        notifier(
            "Unsupported image format",
            "Only PNG, JPEG, GIF, and WebP images can be copied to the clipboard.",
        )
        return 1

    if fmt == "WEBP":
        try:
            body = converter(body)
        except ClipboardError as exc:
            notifier("Clipboard copy failed", str(exc))
            return 1
        fmt = "PNGf"

    try:
        clipboard(body, fmt)
    except ClipboardError as exc:
        notifier("Clipboard copy failed", str(exc))
        return 1

    return 0


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    if len(argv) < 3:
        _notify("Action failed", "Missing arguments. Expected: action <mode> <url>")
        return 1

    mode = argv[1]
    url = argv[2]

    if mode == "copy-image":
        return copy_image(url)

    _notify("Action failed", f"Unknown action mode: {mode}")
    return 1


def _fetch_image(url, *, timeout=DEFAULT_TIMEOUT):
    if urllib.parse.urlsplit(url).scheme not in ("http", "https"):
        raise DownloadError("Only http and https image URLs are supported.")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read(MAX_IMAGE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise DownloadError(f"HTTP {exc.code} {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise DownloadError(f"Network error: {exc.reason}") from exc
    except (TimeoutError, OSError) as exc:
        raise DownloadError(f"Download error: {exc}") from exc
    if len(body) > MAX_IMAGE_BYTES:
        raise DownloadError("Image exceeds maximum supported size.")
    return body


def _convert_webp_to_png(body):
    in_fd, in_path = tempfile.mkstemp(prefix="alfred-img-", suffix=".webp")
    out_path = f"{in_path[: -len('.webp')]}.png"
    try:
        with os.fdopen(in_fd, "wb") as f:
            f.write(body)
        try:
            subprocess.run(
                ["/usr/bin/sips", "-s", "format", "png", in_path, "--out", out_path],
                check=True,
                capture_output=True,
            )
        except FileNotFoundError as exc:
            raise ClipboardError("sips binary not found") from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or b"").decode("utf-8", errors="replace").strip()
            raise ClipboardError(stderr or f"sips exited {exc.returncode}") from exc
        with open(out_path, "rb") as f:
            return f.read()
    finally:
        for path in (in_path, out_path):
            with contextlib.suppress(OSError):
                os.unlink(path)


_EXT_BY_FORMAT = {"PNGf": ".png", "JPEG": ".jpg", "GIFf": ".gif"}


def _copy_to_clipboard(body, fmt):
    ext = _EXT_BY_FORMAT.get(fmt)
    if ext is None:
        raise UnsupportedFormatError(f"Unknown format: {fmt}")
    fd, path = tempfile.mkstemp(prefix="alfred-img-", suffix=ext)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(body)
        script = f'set the clipboard to (read (POSIX file "{path}") as «class {fmt}»)'
        try:
            subprocess.run(
                ["/usr/bin/osascript", "-e", script],
                check=True,
                capture_output=True,
            )
        except FileNotFoundError as exc:
            raise ClipboardError("osascript binary not found") from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or b"").decode("utf-8", errors="replace").strip()
            raise ClipboardError(stderr or f"osascript exited {exc.returncode}") from exc
    finally:
        with contextlib.suppress(OSError):
            os.unlink(path)


def _applescript_string(text):
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _notify(title, message):
    safe_title = _applescript_string(title or "Google Image Search")
    safe_message = _applescript_string(message or "")
    script = f'display notification "{safe_message}" with title "{safe_title}"'
    with contextlib.suppress(FileNotFoundError, subprocess.TimeoutExpired, OSError):
        subprocess.run(
            ["/usr/bin/osascript", "-e", script],
            check=False,
            capture_output=True,
            timeout=5,
        )
    print(f"{title}: {message}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
