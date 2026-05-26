"""Entry point invoked by the Alfred Script Filter to run an image search."""

from __future__ import annotations

import sys

from workflow import alfred, cache
from workflow.google import (
    ApiError,
    MissingConfigError,
    QuotaError,
    SearchConfig,
    search_images,
    validate_config,
)


def run(query, env):
    config = SearchConfig(
        api_key=(env.get("google_api_key") or "").strip(),
        cse_id=(env.get("google_cse_id") or "").strip(),
        num=_parse_int(env.get("result_count"), default=12),
        safe=(env.get("safe_search") or "off").strip() or "off",
    )

    try:
        validate_config(config)
    except MissingConfigError as exc:
        return [alfred.missing_config_item(_split_names(str(exc)))]

    query = (query or "").strip()
    if not query:
        return [alfred.error_item("Type a query", "Search Google Images")]

    try:
        results = search_images(query, config)
    except QuotaError as exc:
        return [alfred.quota_error_item(str(exc))]
    except ApiError as exc:
        return [alfred.api_error_item(str(exc))]

    if not results:
        return [alfred.empty_results_item(query)]

    cache_dir = cache.workflow_cache_dir()
    items = []
    for result in results:
        icon_path = cache.fetch_thumbnail(result.thumbnail_url, cache_dir=cache_dir)
        items.append(alfred.result_item(result, icon_path=icon_path))
    return items


def main(argv=None, env=None, stdout=None):
    argv = sys.argv if argv is None else argv
    env = dict(_os_environ() if env is None else env)
    stdout = sys.stdout if stdout is None else stdout

    query = argv[1] if len(argv) > 1 else ""
    items = run(query, env)
    stdout.write(alfred.render(items))


def _split_names(message):
    return [name.strip() for name in message.split(",") if name.strip()]


def _parse_int(value, *, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _os_environ():
    import os

    return os.environ


if __name__ == "__main__":
    main()
