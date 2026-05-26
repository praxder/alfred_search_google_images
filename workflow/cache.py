"""Thumbnail download and on-disk cache under Alfred's workflow cache directory."""

from __future__ import annotations

import contextlib
import hashlib
import os
import tempfile
import urllib.error
import urllib.request

DEFAULT_TIMEOUT = 4.0
_THUMBNAIL_SUBDIR = "thumbnails"


def workflow_cache_dir():
    base = os.environ.get("alfred_workflow_cache") or os.path.join(  # noqa: SIM112
        tempfile.gettempdir(), "alfred-google-image-search-cache"
    )
    os.makedirs(base, exist_ok=True)
    return base


def cached_path(url, cache_dir):
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()
    ext = _extension_for(url)
    return os.path.join(cache_dir, _THUMBNAIL_SUBDIR, f"{digest}{ext}")


def fetch_thumbnail(url, *, cache_dir, timeout=DEFAULT_TIMEOUT):
    if not url:
        return None
    path = cached_path(url, cache_dir)
    if os.path.isfile(path) and os.path.getsize(path) > 0:
        return path
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return None
    if not body:
        return None
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(prefix=".thumb-", dir=os.path.dirname(path))
    try:
        with os.fdopen(tmp_fd, "wb") as f:
            f.write(body)
        os.replace(tmp_path, path)
    except OSError:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        return None
    return path


def _extension_for(url):
    base = url.split("?", 1)[0].split("#", 1)[0]
    _, ext = os.path.splitext(base)
    ext = ext.lower()
    if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}:
        return ext
    return ".jpg"
