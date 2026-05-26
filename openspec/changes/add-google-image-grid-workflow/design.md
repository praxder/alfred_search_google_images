## Context

The project currently contains only an OpenSpec scaffold. The change introduces a distributable Alfred workflow that searches Google Images, renders results in Alfred Grid View, and provides selected-result actions for copying or opening images.

The workflow will target Python 3 because Alfred users can run it without bundling a large runtime. Google Images data will come from the official Google Custom Search JSON API with image search enabled. Users must provide their own Google API key and Programmable Search Engine ID through Alfred workflow configuration.

Alfred Grid View needs local image paths for reliable result thumbnails, so the workflow will cache thumbnails under Alfred's workflow cache directory. The selected image copy action needs to put image data on the macOS pasteboard, not just copy a URL as text.

## Goals / Non-Goals

**Goals:**

- Provide a distributable Alfred workflow for searching Google Images from a keyword.
- Render results in Alfred Grid View with cached thumbnails and useful metadata.
- Copy the selected image data to the clipboard on Enter.
- Support modifier actions for opening the image URL, copying the image URL, and opening the source page.
- Keep implementation small, testable, and Python 3 based.
- Document user setup for Google credentials and Alfred workflow configuration.

**Non-Goals:**

- Scrape Google Images web pages.
- Bundle or provision Google API credentials.
- Provide account sync, cloud caching, or hosted services.
- Build a general-purpose image downloader outside the Alfred workflow.
- Support non-macOS clipboard behavior.

## Decisions

### Use Google Custom Search JSON API

The workflow will use the Google Custom Search JSON API with image search parameters instead of scraping Google Images pages.

Rationale: the official API provides stable JSON, avoids brittle HTML parsing, and is appropriate for a distributable workflow. Users can supply their own API key and Programmable Search Engine ID.

Alternative considered: scrape Google Images results. This was rejected because page structure and anti-automation behavior are unstable, and distribution would be fragile.

### Use Python 3 scripts with standard-library-first implementation

The workflow will use Python 3 for search, JSON output, thumbnail caching, and selected-result actions.

Rationale: the user requested Python 3, Alfred can invoke Python scripts directly, and a standard-library-first implementation keeps distribution simple.

Alternative considered: Node or Swift. Node adds runtime/package distribution concerns, and Swift adds build/signing complexity for a small workflow.

### Cache thumbnails in Alfred workflow cache

The search script will download and cache thumbnail images using stable filenames derived from result URLs or thumbnail URLs.

Rationale: Alfred Grid View renders local image icons reliably, and caching reduces repeated network requests when a query is repeated.

Alternative considered: point icons directly at remote URLs. This is less reliable in Alfred and gives less control over failures.

### Use dedicated action scripts for selected-result behavior

The grid item payload will preserve the direct image URL and source page URL. Alfred actions will route to small Python scripts or native commands:

- Enter: download the selected image and copy image data to macOS pasteboard.
- Shift+Enter: open the direct image URL.
- Cmd+Enter: copy the direct image URL as text.
- Alt+Enter: open the source page.

Rationale: result rendering and selected-result side effects have different failure modes. Separate scripts keep each path simple and easier to test.

Alternative considered: perform all actions in one script based on flags. This saves files but makes behavior and tests less clear.

### Validate configuration before search

The search script will fail fast with an Alfred-visible error item when required configuration is missing or invalid.

Rationale: distributable workflows need clear setup failures. Silent empty results would make credential problems hard to diagnose.

Alternative considered: return no results on configuration failure. This was rejected because it hides setup errors.

## Risks / Trade-offs

- API quota exhaustion -> Show an Alfred-visible error item and document quota behavior.
- Image download failures -> Keep the search result visible, use fallback icons, and show copy failures clearly when selected.
- Pasteboard image compatibility -> Use macOS-native pasteboard behavior and verify with real image data during implementation.
- Large or unsupported images -> Download with size and timeout limits before attempting clipboard copy.
- Distributable credential setup friction -> Document required Google API key and Programmable Search Engine ID fields in the workflow README.
