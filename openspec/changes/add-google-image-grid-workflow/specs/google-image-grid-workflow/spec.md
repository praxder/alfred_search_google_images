## ADDED Requirements

### Requirement: Configurable Google image search
The workflow SHALL search Google Images through user-provided Google Custom Search JSON API credentials.

#### Scenario: Search runs with configured credentials
- **WHEN** the user enters an image search query and the workflow has a Google API key and Programmable Search Engine ID configured
- **THEN** the workflow returns image results from the Google Custom Search JSON API image search endpoint

#### Scenario: Missing credentials are reported
- **WHEN** the user enters an image search query and required Google credentials are missing
- **THEN** the workflow returns an Alfred-visible error item that identifies the missing configuration

### Requirement: Alfred Grid View image results
The workflow SHALL render Google image results as Alfred Grid View items with local thumbnail icons and selected-result payloads.

#### Scenario: Search results are rendered for Alfred
- **WHEN** Google returns image results for a query
- **THEN** the workflow emits Alfred JSON items containing titles, subtitles, local thumbnail icon paths, direct image URLs, source page URLs, and quick look URLs

#### Scenario: Thumbnail cache is used
- **WHEN** a result includes a thumbnail URL
- **THEN** the workflow stores the thumbnail in Alfred's workflow cache directory and references the local cached path in the Alfred item icon

#### Scenario: Thumbnail failure keeps result usable
- **WHEN** a thumbnail cannot be downloaded or cached
- **THEN** the workflow still emits the result with a fallback icon or without a thumbnail while preserving its selection actions

### Requirement: Selected image clipboard action
The workflow SHALL copy the selected image data to the macOS clipboard when the user presses Enter on a grid result.

#### Scenario: Enter copies image data
- **WHEN** the user presses Enter on an image result
- **THEN** the workflow downloads the selected image and places the image data on the macOS clipboard

#### Scenario: Image copy failure is visible
- **WHEN** the selected image cannot be downloaded or copied to the clipboard
- **THEN** the workflow reports a clear Alfred-visible failure message

### Requirement: Modifier actions for selected results
The workflow SHALL provide modifier actions for opening and copying selected result URLs.

#### Scenario: Shift Enter opens direct image URL
- **WHEN** the user presses Shift+Enter on an image result
- **THEN** the workflow opens the direct image URL in the default browser

#### Scenario: Cmd Enter copies direct image URL
- **WHEN** the user presses Cmd+Enter on an image result
- **THEN** the workflow copies the direct image URL as text

#### Scenario: Alt Enter opens source page
- **WHEN** the user presses Alt+Enter on an image result
- **THEN** the workflow opens the result source page in the default browser

### Requirement: Distributable workflow setup
The workflow SHALL include setup documentation and packaged workflow metadata suitable for distribution to other Alfred users.

#### Scenario: User configures workflow after install
- **WHEN** a user installs the workflow
- **THEN** the workflow documentation explains how to configure the Google API key and Programmable Search Engine ID in Alfred

#### Scenario: User understands action behavior
- **WHEN** a user reads the workflow documentation
- **THEN** the documentation describes Enter, Shift+Enter, Cmd+Enter, and Alt+Enter behavior for image results
