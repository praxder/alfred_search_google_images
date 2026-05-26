"""Google Custom Search JSON API image search and response mapping."""

from __future__ import annotations

import contextlib
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

API_URL = "https://www.googleapis.com/customsearch/v1"
DEFAULT_TIMEOUT = 8.0
DEFAULT_NUM_RESULTS = 12
MAX_NUM_RESULTS = 100
MAX_PAGE_SIZE = 10
QUOTA_REASONS = frozenset(
    {
        "quotaExceeded",
        "dailyLimitExceeded",
        "rateLimitExceeded",
        "userRateLimitExceeded",
    }
)


@dataclass(frozen=True)
class SearchResult:
    title: str
    image_url: str
    thumbnail_url: str
    source_url: str
    display_link: str
    mime: str
    width: int
    height: int


@dataclass(frozen=True)
class SearchConfig:
    api_key: str
    cse_id: str
    num: int = DEFAULT_NUM_RESULTS
    safe: str = "off"


class MissingConfigError(Exception):
    """Raised when required workflow configuration is missing."""


class ApiError(Exception):
    """Raised when the Google Custom Search API returns an error."""

    def __init__(self, message, *, status=None, reason=None):
        super().__init__(message)
        self.status = status
        self.reason = reason


class QuotaError(ApiError):
    """Raised when the Google Custom Search API reports a quota or rate limit."""


def validate_config(config):
    missing = []
    if not config.api_key:
        missing.append("google_api_key")
    if not config.cse_id:
        missing.append("google_cse_id")
    if missing:
        raise MissingConfigError(", ".join(missing))


def map_response(payload):
    results = []
    for item in payload.get("items") or []:
        link = item.get("link")
        if not link:
            continue
        image = item.get("image") or {}
        results.append(
            SearchResult(
                title=item.get("title") or "",
                image_url=link,
                thumbnail_url=image.get("thumbnailLink") or "",
                source_url=image.get("contextLink") or "",
                display_link=item.get("displayLink") or "",
                mime=item.get("mime") or "",
                width=_safe_int(image.get("width")),
                height=_safe_int(image.get("height")),
            )
        )
    return results


def search_images(query, config, *, timeout=DEFAULT_TIMEOUT):
    validate_config(config)
    target = _clamp_num(config.num)
    results = []
    start = 1
    while len(results) < target:
        page_size = min(MAX_PAGE_SIZE, target - len(results))
        page = _fetch_page(query, config, start=start, num=page_size, timeout=timeout)
        if not page:
            break
        results.extend(page)
        if len(page) < page_size:
            break
        start += page_size
    return results[:target]


def _fetch_page(query, config, *, start, num, timeout):
    params = {
        "key": config.api_key,
        "cx": config.cse_id,
        "q": query,
        "searchType": "image",
        "num": str(num),
        "start": str(start),
        "safe": config.safe or "off",
    }
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read()
    except urllib.error.HTTPError as exc:
        _raise_for_http_error(exc)
    except urllib.error.URLError as exc:
        raise ApiError(f"Network error: {exc.reason}") from exc
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ApiError("Invalid JSON response from Google API") from exc
    return map_response(payload)


def _clamp_num(num):
    try:
        n = int(num)
    except (TypeError, ValueError):
        n = DEFAULT_NUM_RESULTS
    return max(1, min(MAX_NUM_RESULTS, n))


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _raise_for_http_error(exc):
    body = b""
    with contextlib.suppress(Exception):
        body = exc.read()
    message = exc.reason if isinstance(exc.reason, str) else str(exc.reason)
    reason = None
    if body:
        try:
            err_payload = json.loads(body)
            err = err_payload.get("error") or {}
            message = err.get("message") or message
            errors = err.get("errors") or []
            if errors:
                reason = (errors[0] or {}).get("reason")
        except json.JSONDecodeError:
            pass
    if exc.code == 429 or reason in QUOTA_REASONS:
        raise QuotaError(
            message or "Google API quota exceeded", status=exc.code, reason=reason
        ) from exc
    raise ApiError(message or "Google API error", status=exc.code, reason=reason) from exc
