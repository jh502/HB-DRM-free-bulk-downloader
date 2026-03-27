# HB DRM-Free Bulk Downloader — Python Migration Design

**Date:** 2026-03-27
**Version:** 0.5.0 (target)
**Original:** PowerShell script `HB-DRM-Free_download.ps1` v0.4.3

## Goals

- Migrate the existing PowerShell bulk downloader to a cross-platform Python implementation
- Preserve 100% feature parity with the original script
- Maintain full backwards compatibility with existing `links.txt` files
- Add small quality-of-life improvements (progress bars, coloured output, `--dry-run`)
- Structure the code so it can be run as a script today and packaged via `pip` later
- Defer significant new features (concurrent downloads, GUI, etc.) to post-migration

## Non-Goals

- Concurrent/parallel downloads (future)
- GUI or web interface (future)
- Resume partial downloads via HTTP range requests (future)
- Any changes to the Humble Bundle API interaction beyond what the original does

---

## Architecture

Multi-file Python package under `hb_downloader/`, runnable as `python -m hb_downloader` and installable via `pip install -e .`.

```
hb_downloader/
├── __main__.py          # python -m entry point → calls cli.main()
├── cli.py               # argparse, top-level orchestration loop
├── config.py            # config.toml + links.txt parsing, settings state
├── api.py               # Humble Bundle API calls, data models
├── downloader.py        # file download, MD5 verification, skip logic
└── logger.py            # log file management (LOG-all + LOG-error)

pyproject.toml           # packaging metadata
config.toml              # new-format user config (optional)
links.txt                # legacy format (fully supported)
```

**Data flow:**
1. `cli.py` parses CLI args → loads `config.toml` → reads `links.txt` line by line
2. Non-URL lines mutate the active `Config` state (legacy directives)
3. For each bundle URL: `api.py` fetches metadata and filters to a `list[DownloadItem]`
4. `downloader.py` skips already-downloaded files, downloads to `temp/`, verifies MD5, moves to `downloads/`
5. `logger.py` writes results to `LOG-all.txt` and `LOG-error.txt` throughout

---

## Module Designs

### `config.py`

Owns all configuration state. Two input sources:

**`config.toml` (new format — takes precedence):**
```toml
[auth]
cookie = "_simpleauth_sess value here"

[download]
directory = "downloads"
platforms = ["windows", "audio", "video", "ebook", "others"]
exclude_platforms = []
all_platforms = false
formats = []          # empty = all formats
strict = false        # never fall back to first format if preferred not found
pref_first = true     # download first matching format only (not all matches)
method = "direct"     # "direct" or "bittorrent"
md5_check = true
md5_stored_check = true

[paths]
bundle_name = "full"        # "full" or "key"
shorten_if_title_over = 0   # 0 = disabled
shorten_filename_to = 0

[logging]
timestamped = false   # true = per-run log files in logs/ subfolder
utc = false
```

**`links.txt` legacy directives (fully supported, parsed in order):**

| Prefix | Behaviour |
|--------|-----------|
| `^value` | Set auth cookie |
| `#pdf,epub` | Set preferred formats (global) |
| `@linux,mac` | Override included platforms |
| `@+linux` | Add to included platforms |
| `@-windows` | Add to excluded platforms |
| `@all` / `@all-` | Disable / re-enable platform filtering |
| `%strict` / `%normal` | Enable / disable strict format mode |
| `%all` / `%pref` | Download all matching formats / first match only |
| `!md5+` / `!md5-` | Enable / disable MD5 checking |
| `!md5s+` / `!md5s-` | Enable / disable MD5 check on stored files |
| `!logtime` / `!logtimeutc` | Timestamped logs (applied once per run) |
| `*direct` / `*bittorrent` | Download method |
| `~fullbundle` / `~keybundle` | Bundle folder naming |
| `~if_title-N_file-M` | Conditional filename shortening |
| `https://...?key=XXXX` | Bundle URL to process |
| `https://...?key=XXXX#pdf` | Bundle URL with inline format override |
| Any other line | Ignored (comment) |

Multiple `^cookie` lines are supported — the active cookie switches mid-file (same as original).

**Precedence:** CLI args > `config.toml` > `links.txt` directives > hardcoded defaults.

Key class: `Config` dataclass holding all current settings. `links.txt` parsing mutates a `Config` instance as it processes each line.

---

### `api.py`

Single responsibility: HTTP communication with the Humble Bundle API.

```python
@dataclass
class DownloadItem:
    bundle_title: str   # sanitised
    item_title: str     # sanitised
    filename: str       # possibly shortened per path config
    url: str            # direct download or bittorrent URL
    md5: str
    label: str          # e.g. "pdf", "epub", "mp3"

def fetch_bundle(key: str, cookie: str) -> dict:
    """GET https://www.humblebundle.com/api/v1/order/{key}
    Raises: HBAuthError (401), HBNotFoundError (404), HBAPIError (other)"""

def extract_downloads(bundle_json: dict, config: Config) -> list[DownloadItem]:
    """Apply platform/format/strict/pref filters. Returns flat download list."""
```

- Title sanitisation: ASCII conversion (Cyrillic transliteration) + strip chars not in `[a-zA-Z0-9/_'\\-\\ ]` + trim — identical to original
- `hidden` library_family_name entries are skipped (same as original)
- Internet connectivity check: retries up to 12 × 10s before aborting

---

### `downloader.py`

Single responsibility: download files and verify integrity.

```python
def download_bundle(
    items: list[DownloadItem],
    config: Config,
    logger: Logger,
    dry_run: bool = False,
) -> None:
    """For each DownloadItem:
    - If dry_run: print what would be downloaded, return
    - Skip if downloads/bundle/item/filename already exists
    - Download to temp/bundle/item/filename via requests (streaming)
    - Show rich progress bar if rich is installed, plain output otherwise
    - Verify MD5 if config.md5_check
    - Move temp → downloads/ on completion
    - Log result
    """
```

- Two-stage download: `temp/` → `downloads/` (same as original)
- `temp/` is cleared at script start and after each bundle
- MD5: `hashlib.md5()` streaming read
- Path shortening applied when constructing destination paths
- Bundle folder `LastWriteTime` update equivalent: `os.utime()` on the bundle dir after new content is moved in

---

### `logger.py`

Manages `LOG-all.txt` and `LOG-error.txt`. Created fresh each run (or timestamped in `logs/` subfolder).

```python
class Logger:
    def log_bundle_header(self, bundle_num, total, title, url): ...
    def log_item_ok(self, item_title, filename, label, md5): ...
    def log_item_fail(self, item_title, filename, label, md5_file, md5_expected, reason): ...
    def log_item_skipped(self, item_title, filename, label, md5, ok: bool): ...
    def log_summary(self, md5_errors, not_found_errors): ...
```

No third-party dependencies.

---

### `cli.py`

Entry point and orchestration.

```
usage: python -m hb_downloader [OPTIONS]

  --cookie TEXT        _simpleauth_sess cookie (overrides config/links.txt)
  --links FILE         Path to links.txt (default: ./links.txt)
  --config FILE        Path to config.toml (default: ./config.toml)
  --output DIR         Download directory (default: ./downloads)
  --format TEXT        Preferred format(s), comma-separated e.g. pdf,epub
  --platforms TEXT     Platforms to include e.g. windows,ebook
  --dry-run            Print what would be downloaded, no actual downloads
```

Orchestration loop:
1. Initialise `Config` from `config.toml` + CLI args
2. Scan `links.txt` to count bundle URLs (for progress display)
3. Process `links.txt` line by line — mutate `Config` on directives, call `api` + `downloader` on URLs
4. Print error summary on exit

---

## Dependencies

| Package | Use | Required |
|---------|-----|----------|
| `requests` | HTTP downloads and API calls | Yes |
| `rich` | Progress bars, coloured output | No (graceful fallback) |
| `tomllib` (stdlib, Python 3.11+) or `tomli` | Parse `config.toml` | Yes (bundled in 3.11+) |

Python version requirement: **3.11+** (for `tomllib` in stdlib). Earlier versions require `pip install tomli`.

---

## Compatibility Notes

- `links.txt` files from v0.4.x work without any changes
- Download folder structure is identical: `downloads/bundleName/itemName/filename`
- Log file format is identical
- `RUN.bat` can be updated to call `python hb_downloader` instead of the `.ps1`
- A `RUN.sh` launcher will be added for macOS/Linux

---

## Small Targeted Improvements (in scope for this migration)

1. **Progress bars** — per-file download progress via `rich` (falls back to plain text)
2. **Coloured console output** — errors in red, success in green, info in default — via `rich` with fallback
3. **`--dry-run` flag** — preview downloads without fetching anything
4. **Better error messages** — HTTP status codes and reasons shown clearly rather than raw exceptions

## Out of Scope (post-migration)

- Concurrent/parallel downloads
- Resume partial downloads (HTTP range requests)
- GUI
- Generating a list of all owned bundles automatically
