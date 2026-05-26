# Google Image Search (Alfred Grid View)

An [Alfred](https://www.alfredapp.com/) workflow that searches Google Images
through the official Google Custom Search JSON API and renders results in
Alfred's Grid View. You bring your own Google API credentials.

## Features

- `gimg <query>` — Search Google Images and pick a result from a grid of
  thumbnails.
- **Enter** copies the selected image data to the macOS clipboard so you can
  paste it directly into another app.
- **Shift + Enter** opens the direct image URL in your default browser.
- **Cmd + Enter** copies the direct image URL as text.
- **Alt + Enter** opens the source page in your default browser.

## Requirements

- macOS with Alfred 5 and the Powerpack license (Grid View requires Alfred 5).
- The system `/usr/bin/python3` (ships with the Xcode Command Line Tools on
  macOS 12.3+). The first time Alfred runs the workflow, macOS may prompt
  you to install the command line tools.
- A Google Cloud project with the Custom Search JSON API enabled and a
  Programmable Search Engine configured for image search.

The workflow itself only uses the Python standard library at runtime, so
nothing needs to be installed with `pip`.

## Setting up Google credentials

The workflow uses Google's [Custom Search JSON API](https://developers.google.com/custom-search/v1/overview)
to query Google Images. You need two pieces of information:

1. **Google API key**
   1. Open the [Google Cloud Console](https://console.cloud.google.com/).
   2. Create or pick a project.
   3. In **APIs & Services → Library**, enable **Custom Search API**.
   4. In **APIs & Services → Credentials**, create an **API key**.
   5. Copy the key (it usually starts with `AIza`).

2. **Programmable Search Engine ID (`cx`)**
   1. Open the [Programmable Search Engine control panel](https://programmablesearchengine.google.com/controlpanel/all).
   2. Click **Add** and create a new search engine.
   3. Under **Sites to search**, choose **Search the entire web**.
   4. Open the engine's **Setup** page and enable **Image search**.
   5. Copy the **Search engine ID** value (the `cx`).

Keep both values handy for the next section.

## Installing the workflow

1. Build the distributable file:
   - In Finder, select the contents of this repository.
   - Compress the items into a `.zip` archive.
   - Rename the archive to `Google Image Search.alfredworkflow`.
2. Double-click the `.alfredworkflow` file. Alfred imports it.
3. Open Alfred Preferences → Workflows → **Google Image Search (Grid View)**.

## Configuring the workflow in Alfred

The workflow exposes configuration via Alfred's workflow configuration UI
(`[x]` button in the workflow header):

| Field | Variable | Required | Notes |
| --- | --- | --- | --- |
| Google API Key | `google_api_key` | yes | The API key from Google Cloud. Stored as a non-exported variable. |
| Programmable Search Engine ID | `google_cse_id` | yes | The `cx` value of your image-enabled search engine. |
| Result Count | `result_count` | no | Number of images to show, `1`–`100`. Each block of 10 uses one Custom Search API query (e.g. `12` = 2 queries). Default `12`. |
| SafeSearch | `safe_search` | no | `off` or `active`. Default `off`. |

The API key is set as non-exported in `info.plist` so child scripts (and
debug logs) only see it through the script filter, not through every action.

## Using the workflow

1. Trigger Alfred and type `gimg <query>`.
2. Wait for the grid to populate with image thumbnails.
3. Use the following actions:
   - **Enter** — Download the selected image and copy its data to the
     clipboard. You can paste it directly into other apps (e.g. Slack,
     Keynote, Mail). PNG, JPEG, and GIF are supported.
   - **Shift + Enter** — Open the direct image URL in your default browser.
   - **Cmd + Enter** — Copy the direct image URL as text.
   - **Alt + Enter** — Open the source page that hosts the image.
4. Press **⌘Y** while a result is highlighted for Quick Look (uses the image
   URL).

## Cache behaviour

- Thumbnails are downloaded once per image URL and stored in Alfred's
  per-workflow cache directory (`$alfred_workflow_cache`). They use a
  SHA-1-derived filename so repeat queries reuse the cached image.
- If a thumbnail cannot be downloaded, the result still appears with a
  fallback icon and remains selectable.
- Alfred manages the cache lifecycle. You can wipe it from Alfred Preferences
  if it grows too large, or delete `$alfred_workflow_cache/thumbnails`
  manually.

## API quota expectations

- Google's Custom Search JSON API free tier allows **100 search queries per
  day**. Each `gimg` query consumes one search call.
- Paid tiers are billed per 1,000 queries — see the Google Cloud pricing
  page for details.
- When the daily limit is exceeded, the workflow shows an error item titled
  "Google image search quota reached". Wait until the daily quota resets
  (Pacific time midnight) or upgrade your billing tier.

## Common setup failures

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| "Google image search is not configured" | API key or `cx` not entered. | Open the workflow configuration and fill in both fields. |
| "Google image search failed: API key not valid" | API key is wrong or the Custom Search API is not enabled in your Google Cloud project. | Re-check the key value and confirm the API is enabled. |
| "Google image search quota reached" | Daily query limit exceeded. | Wait for the quota to reset or upgrade your billing tier. |
| Results render with broken icons | Network blocked the thumbnail host (`encrypted-tbn0.gstatic.com`). | Allow that domain or rerun the search. Selection actions still work. |
| "Unsupported image format" notification after Enter | The selected image is something other than PNG, JPEG, or GIF (for example WebP). | Try a different result, or use Shift+Enter to open it in the browser. |
| "osascript binary not found" notification | macOS automation tooling is broken. | Reinstall macOS command line tools (`xcode-select --install`). |

## Development

The workflow is implemented as a small Python 3 package under `workflow/`.

```
workflow/
  __init__.py
  action.py     # Selected-result actions (Enter → clipboard copy)
  alfred.py     # Alfred Grid View JSON formatting
  cache.py      # Thumbnail download + on-disk cache
  google.py     # Google Custom Search API client + response mapping
  search.py     # Script Filter entry point
```

Run the tests with the standard-library test runner:

```
/usr/bin/python3 -m unittest discover -s tests
```

Format and lint with [Ruff](https://docs.astral.sh/ruff/):

```
ruff check .
ruff format --check .
```

## License

MIT.
