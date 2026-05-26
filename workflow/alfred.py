"""Alfred Grid View JSON output formatting."""

from __future__ import annotations

import hashlib
import json
import os

_FALLBACK_ICON = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "icons", "fallback.png")
)


def render(items):
    payload = {"items": list(items)}
    return json.dumps(payload, ensure_ascii=False)


def result_item(result, *, icon_path):
    title = result.title or result.display_link or result.image_url
    subtitle = _format_subtitle(result)
    item = {
        "uid": _uid_for(result.image_url),
        "type": "default",
        "title": title,
        "subtitle": subtitle,
        "arg": result.image_url,
        "quicklookurl": result.image_url,
        "icon": {"path": icon_path or _FALLBACK_ICON},
        "mods": {
            "shift": {"arg": result.image_url, "subtitle": "Open image URL in browser"},
            "cmd": {"arg": result.image_url, "subtitle": "Copy image URL"},
            "alt": {
                "arg": result.source_url or result.image_url,
                "subtitle": "Open source page",
            },
        },
    }
    return item


def error_item(title, subtitle="", *, icon_path=None):
    return {
        "title": title,
        "subtitle": subtitle,
        "valid": False,
        "icon": {"path": icon_path or _FALLBACK_ICON},
    }


def missing_config_item(missing):
    names = ", ".join(missing) if missing else "configuration"
    return error_item(
        "Google image search is not configured",
        f"Set {names} in the workflow configuration",
    )


def api_error_item(message):
    return error_item("Google image search failed", message or "Unknown API error")


def quota_error_item(message):
    return error_item(
        "Google image search quota reached",
        message or "Daily or rate limit exceeded — try again later",
    )


def empty_results_item(query):
    q = query.strip() if isinstance(query, str) else ""
    subtitle = f"No image results for “{q}”" if q else "No image results"
    return error_item("No results", subtitle)


def _format_subtitle(result):
    parts = []
    if result.width and result.height:
        parts.append(f"{result.width}×{result.height}")
    if result.display_link:
        parts.append(result.display_link)
    return " · ".join(parts)


def _uid_for(image_url):
    return hashlib.sha1(image_url.encode("utf-8")).hexdigest()
