## Why

Alfred can show rich image results in Grid View, but this project does not yet provide a workflow that searches Google Images and turns those results into Alfred-native actions. A distributable workflow should let users search images quickly, copy the selected image itself, and open or copy image links without leaving Alfred.

## What Changes

- Add a Python 3 Alfred workflow that searches Google Images through the official Google Custom Search JSON API.
- Display image results in Alfred Grid View with local thumbnail icons, titles, source context, and quick look URLs.
- Add selection actions:
  - Enter copies the selected image data to the macOS clipboard.
  - Shift+Enter opens the direct image URL in the browser.
  - Cmd+Enter copies the direct image URL as text.
  - Alt+Enter opens the source page in the browser.
- Add workflow configuration for user-provided Google API key and Programmable Search Engine ID.
- Add cache behavior for thumbnails and result data where useful for performance and quota control.
- Add documentation for distributable setup and required Google API credentials.

## Capabilities

### New Capabilities

- `google-image-grid-workflow`: Covers Google image searching, Alfred Grid View result rendering, thumbnail caching, user configuration, and selected-image actions.

### Modified Capabilities

- None.

## Impact

- New Alfred workflow source, action scripts, and workflow metadata.
- New Python 3 scripts for search, result normalization, thumbnail caching, and image clipboard actions.
- New tests for JSON output, result mapping, modifier payloads, configuration validation, and clipboard/open action command behavior where practical.
- New user-facing setup documentation for Google API credentials and Alfred workflow configuration.
