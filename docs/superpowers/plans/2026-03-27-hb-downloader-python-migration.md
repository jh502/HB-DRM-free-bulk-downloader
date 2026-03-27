# HB DRM-Free Downloader — Python Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the PowerShell HB DRM-Free bulk downloader to a cross-platform Python package with full feature parity and backwards-compatible `links.txt` support.

**Architecture:** Multi-file package under `hb_downloader/` with dedicated modules for config, API, downloading, and logging. Orchestrated by a CLI entry point. Runnable as `python -m hb_downloader`, installable via `pip install -e .`.

**Tech Stack:** Python 3.11+, `requests`, `rich` (optional), `tomllib` (stdlib), `pytest`, `pytest-mock`

---

## File Map

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Package metadata, dependencies, `hb-dl` script entry point |
| `config.toml.example` | Documented example config for users |
| `RUN.sh` | macOS/Linux launcher (new) |
| `RUN.bat` | Updated to call Python instead of PowerShell |
| `hb_downloader/__init__.py` | Empty package marker |
| `hb_downloader/__main__.py` | `python -m hb_downloader` entry point |
| `hb_downloader/config.py` | `Config` dataclass, `load_toml()`, `parse_directive()` |
| `hb_downloader/api.py` | `DownloadItem`, `fetch_bundle()`, `extract_downloads()`, `wait_for_connection()` |
| `hb_downloader/downloader.py` | `download_bundle()`, `md5_file()` |
| `hb_downloader/logger.py` | `Logger` class — manages LOG-all and LOG-error files |
| `hb_downloader/cli.py` | `parse_args()`, `main()` orchestration loop |
| `tests/__init__.py` | Empty |
| `tests/conftest.py` | Shared fixtures (mock bundle JSON, tmp paths) |
| `tests/test_config.py` | Config defaults, TOML loading, directive parsing |
| `tests/test_api.py` | `fetch_bundle()`, `extract_downloads()`, `_sanitise_title()` |
| `tests/test_downloader.py` | MD5, skip detection, download + move |
| `tests/test_logger.py` | Log file creation, log entry format |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `hb_downloader/__init__.py`
- Create: `hb_downloader/__main__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "hb-drm-free-downloader"
version = "0.5.0"
requires-python = ">=3.11"
dependencies = [
    "requests>=2.31",
]

[project.optional-dependencies]
pretty = ["rich>=13"]
dev = ["pytest>=7", "pytest-mock>=3", "requests-mock>=1.11"]

[project.scripts]
hb-dl = "hb_downloader.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create package files**

`hb_downloader/__init__.py` — empty file.

`hb_downloader/__main__.py`:
```python
from hb_downloader.cli import main

if __name__ == "__main__":
    main()
```

`tests/__init__.py` — empty file.

- [ ] **Step 3: Create `tests/conftest.py` with shared fixtures**

```python
import pytest
from pathlib import Path


MOCK_BUNDLE_JSON = {
    "product": {"human_name": "Test Bundle: Programming by O'Reilly"},
    "gamekey": "TESTKEY1234567A",
    "subproducts": [
        {
            "human_name": "Learning Python",
            "library_family_name": "",
            "downloads": [
                {
                    "platform": "ebook",
                    "download_struct": [
                        {
                            "name": "epub",
                            "url": {
                                "web": "https://dl.humble.com/learning_python.epub?ttl=99",
                                "bittorrent": "https://dl.humble.com/learning_python.epub.torrent",
                            },
                            "md5": "aabbccddeeff0011",
                        },
                        {
                            "name": "pdf",
                            "url": {
                                "web": "https://dl.humble.com/learning_python.pdf?ttl=99",
                                "bittorrent": "https://dl.humble.com/learning_python.pdf.torrent",
                            },
                            "md5": "1100ffeeddccbbaa",
                        },
                    ],
                }
            ],
        },
        {
            "human_name": "Hidden Item",
            "library_family_name": "hidden",
            "downloads": [
                {
                    "platform": "ebook",
                    "download_struct": [
                        {
                            "name": "pdf",
                            "url": {"web": "https://dl.humble.com/hidden.pdf?ttl=99", "bittorrent": ""},
                            "md5": "deadbeef",
                        }
                    ],
                }
            ],
        },
    ],
}


@pytest.fixture
def mock_bundle():
    import copy
    return copy.deepcopy(MOCK_BUNDLE_JSON)


@pytest.fixture
def tmp_download_dir(tmp_path):
    d = tmp_path / "downloads"
    d.mkdir()
    return d


@pytest.fixture
def tmp_links_file(tmp_path):
    f = tmp_path / "links.txt"
    f.write_text("")
    return f
```

- [ ] **Step 4: Install dev dependencies**

```bash
pip install -e ".[dev,pretty]"
```

Expected: installs `requests`, `rich`, `pytest`, `pytest-mock`, `requests-mock`.

- [ ] **Step 5: Verify pytest runs with no errors**

```bash
pytest --collect-only
```

Expected: `no tests ran` (0 errors, 0 failures).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml hb_downloader/ tests/
git commit -m "feat: scaffold Python package structure"
```

---

## Task 2: Config Dataclass + TOML Loading

**Files:**
- Create: `hb_downloader/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests for Config defaults**

`tests/test_config.py`:
```python
from pathlib import Path
from hb_downloader.config import Config, load_toml


def test_config_defaults():
    c = Config()
    assert c.cookie == "none"
    assert c.platforms == ["windows", "audio", "video", "ebook", "others"]
    assert c.exclude_platforms == []
    assert c.all_platforms is False
    assert c.formats == []
    assert c.strict is False
    assert c.pref_first is True
    assert c.method == "direct"
    assert c.md5_check is True
    assert c.md5_stored_check is True
    assert c.bundle_name == "full"
    assert c.shorten_if_title_over == 0
    assert c.shorten_filename_to == 0
    assert c.timestamped is False
    assert c.utc is False
    assert c.download_dir == Path("downloads")


def test_load_toml_partial(tmp_path):
    toml_file = tmp_path / "config.toml"
    toml_file.write_text("""
[auth]
cookie = "my_sess_cookie"

[download]
formats = ["pdf", "epub"]
strict = true
""")
    c = load_toml(toml_file)
    assert c.cookie == "my_sess_cookie"
    assert c.formats == ["pdf", "epub"]
    assert c.strict is True
    # non-specified values remain default
    assert c.md5_check is True
    assert c.platforms == ["windows", "audio", "video", "ebook", "others"]


def test_load_toml_missing_file():
    c = load_toml(Path("nonexistent.toml"))
    assert c.cookie == "none"  # returns defaults


def test_load_toml_all_sections(tmp_path):
    toml_file = tmp_path / "config.toml"
    toml_file.write_text("""
[auth]
cookie = "abc"

[download]
directory = "my_downloads"
platforms = ["linux", "ebook"]
exclude_platforms = ["windows"]
all_platforms = false
formats = ["pdf"]
strict = false
pref_first = false
method = "bittorrent"
md5_check = false
md5_stored_check = false

[paths]
bundle_name = "key"
shorten_if_title_over = 60
shorten_filename_to = 30

[logging]
timestamped = true
utc = true
""")
    c = load_toml(toml_file)
    assert c.cookie == "abc"
    assert c.download_dir == Path("my_downloads")
    assert c.platforms == ["linux", "ebook"]
    assert c.exclude_platforms == ["windows"]
    assert c.method == "bittorrent"
    assert c.md5_check is False
    assert c.bundle_name == "key"
    assert c.shorten_if_title_over == 60
    assert c.shorten_filename_to == 30
    assert c.timestamped is True
    assert c.utc is True
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_config.py -v
```

Expected: `ImportError: cannot import name 'Config'`

- [ ] **Step 3: Implement `hb_downloader/config.py`**

```python
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    # Auth
    cookie: str = "none"

    # Download
    download_dir: Path = field(default_factory=lambda: Path("downloads"))
    platforms: list[str] = field(
        default_factory=lambda: ["windows", "audio", "video", "ebook", "others"]
    )
    exclude_platforms: list[str] = field(default_factory=list)
    all_platforms: bool = False
    formats: list[str] = field(default_factory=list)  # empty = all formats
    strict: bool = False
    pref_first: bool = True
    method: str = "direct"  # "direct" or "bittorrent"
    md5_check: bool = True
    md5_stored_check: bool = True

    # Paths
    bundle_name: str = "full"  # "full" or "key"
    shorten_if_title_over: int = 0
    shorten_filename_to: int = 0

    # Logging
    timestamped: bool = False
    utc: bool = False

    # Internal — set once per run
    _log_time_applied: bool = field(default=False, repr=False)


def load_toml(path: Path) -> Config:
    """Load config.toml if it exists; return defaults otherwise."""
    if not path.exists():
        return Config()

    with open(path, "rb") as f:
        data = tomllib.load(f)

    c = Config()

    auth = data.get("auth", {})
    c.cookie = auth.get("cookie", c.cookie)

    dl = data.get("download", {})
    c.download_dir = Path(dl.get("directory", str(c.download_dir)))
    c.platforms = dl.get("platforms", c.platforms)
    c.exclude_platforms = dl.get("exclude_platforms", c.exclude_platforms)
    c.all_platforms = dl.get("all_platforms", c.all_platforms)
    c.formats = dl.get("formats", c.formats)
    c.strict = dl.get("strict", c.strict)
    c.pref_first = dl.get("pref_first", c.pref_first)
    c.method = dl.get("method", c.method)
    c.md5_check = dl.get("md5_check", c.md5_check)
    c.md5_stored_check = dl.get("md5_stored_check", c.md5_stored_check)

    paths = data.get("paths", {})
    c.bundle_name = paths.get("bundle_name", c.bundle_name)
    c.shorten_if_title_over = paths.get("shorten_if_title_over", c.shorten_if_title_over)
    c.shorten_filename_to = paths.get("shorten_filename_to", c.shorten_filename_to)

    logging = data.get("logging", {})
    c.timestamped = logging.get("timestamped", c.timestamped)
    c.utc = logging.get("utc", c.utc)

    return c
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_config.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add hb_downloader/config.py tests/test_config.py
git commit -m "feat: add Config dataclass and config.toml loading"
```

---

## Task 3: links.txt Directive Parsing

**Files:**
- Modify: `hb_downloader/config.py` — add `parse_directive()` and `iter_links_file()`
- Modify: `tests/test_config.py` — add directive tests

- [ ] **Step 1: Write failing tests**

Append to `tests/test_config.py`:
```python
from hb_downloader.config import parse_directive, iter_links_file
import copy


def _base_config():
    return Config()


def test_directive_cookie():
    c = _base_config()
    parse_directive("^my_secret_cookie", c)
    assert c.cookie == "my_secret_cookie"


def test_directive_formats_global():
    c = _base_config()
    parse_directive("#pdf,epub", c)
    assert c.formats == ["pdf", "epub"]


def test_directive_formats_none_resets():
    c = _base_config()
    c.formats = ["pdf"]
    parse_directive("#none", c)
    assert c.formats == []


def test_directive_platform_override():
    c = _base_config()
    parse_directive("@linux,mac", c)
    assert c.platforms == ["linux", "mac"]
    assert c.all_platforms is False


def test_directive_platform_add():
    c = _base_config()
    parse_directive("@+linux", c)
    assert "linux" in c.platforms
    assert "windows" in c.platforms  # default preserved


def test_directive_platform_exclude():
    c = _base_config()
    parse_directive("@-windows", c)
    assert c.exclude_platforms == ["windows"]


def test_directive_platform_all():
    c = _base_config()
    parse_directive("@all", c)
    assert c.all_platforms is True


def test_directive_platform_all_off():
    c = _base_config()
    c.all_platforms = True
    parse_directive("@all-", c)
    assert c.all_platforms is False


def test_directive_strict():
    c = _base_config()
    parse_directive("%strict", c)
    assert c.strict is True


def test_directive_normal():
    c = _base_config()
    c.strict = True
    parse_directive("%normal", c)
    assert c.strict is False


def test_directive_pref_all():
    c = _base_config()
    parse_directive("%all", c)
    assert c.pref_first is False


def test_directive_pref_pref():
    c = _base_config()
    c.pref_first = False
    parse_directive("%pref", c)
    assert c.pref_first is True


def test_directive_multiple_percent():
    c = _base_config()
    parse_directive("%strict,all", c)
    assert c.strict is True
    assert c.pref_first is False


def test_directive_md5_off():
    c = _base_config()
    parse_directive("!md5-", c)
    assert c.md5_check is False


def test_directive_md5s_off():
    c = _base_config()
    parse_directive("!md5s-", c)
    assert c.md5_stored_check is False


def test_directive_logtime():
    c = _base_config()
    parse_directive("!logtime", c)
    assert c.timestamped is True
    assert c.utc is False


def test_directive_logtimeutc():
    c = _base_config()
    parse_directive("!logtimeutc", c)
    assert c.timestamped is True
    assert c.utc is True


def test_directive_bittorrent():
    c = _base_config()
    parse_directive("*bittorrent", c)
    assert c.method == "bittorrent"


def test_directive_direct():
    c = _base_config()
    c.method = "bittorrent"
    parse_directive("*direct", c)
    assert c.method == "direct"


def test_directive_keybundle():
    c = _base_config()
    parse_directive("~keybundle", c)
    assert c.bundle_name == "key"


def test_directive_fullbundle():
    c = _base_config()
    c.bundle_name = "key"
    parse_directive("~fullbundle", c)
    assert c.bundle_name == "full"


def test_directive_path_shortening():
    c = _base_config()
    parse_directive("~if_title-60_file-30", c)
    assert c.shorten_if_title_over == 60
    assert c.shorten_filename_to == 30


def test_directive_path_shortening_reset():
    c = _base_config()
    c.shorten_if_title_over = 60
    c.shorten_filename_to = 30
    parse_directive("~if_title-0_file-0", c)
    assert c.shorten_if_title_over == 0
    assert c.shorten_filename_to == 0


def test_directive_comment_ignored():
    c = _base_config()
    original_cookie = c.cookie
    parse_directive("This is a comment line", c)
    assert c.cookie == original_cookie


def test_iter_links_file_yields_urls_and_applies_directives(tmp_path):
    links = tmp_path / "links.txt"
    links.write_text(
        "^test_cookie\n"
        "#pdf\n"
        "https://www.humblebundle.com/downloads?key=AAABBBCCC111222\n"
        "A comment line\n"
        "https://www.humblebundle.com/downloads?key=DDDEEEFFF333444#epub\n"
    )
    c = Config()
    results = list(iter_links_file(links, c))
    # Should yield 2 (url, inline_format, config_snapshot) tuples
    assert len(results) == 2
    url1, fmt1 = results[0]
    url2, fmt2 = results[1]
    assert "AAABBBCCC111222" in url1
    assert fmt1 == []  # no inline override
    assert "DDDEEEFFF333444" in url2
    assert fmt2 == ["epub"]  # inline override
    # Cookie was applied to config
    assert c.cookie == "test_cookie"
    assert c.formats == ["pdf"]


def test_iter_links_file_counts_only_bundle_urls(tmp_path):
    links = tmp_path / "links.txt"
    links.write_text(
        "^cookie\n"
        "#pdf\n"
        "https://www.humblebundle.com/downloads?key=AAA\n"
        "https://www.humblebundle.com/downloads?key=BBB\n"
    )
    c = Config()
    from hb_downloader.config import count_bundle_urls
    assert count_bundle_urls(links) == 2
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_config.py -v -k "directive or iter_links"
```

Expected: `ImportError: cannot import name 'parse_directive'`

- [ ] **Step 3: Implement `parse_directive()`, `iter_links_file()`, `count_bundle_urls()` in `hb_downloader/config.py`**

Add to the bottom of `hb_downloader/config.py`:
```python
import re
from collections.abc import Generator

_BUNDLE_URL_PREFIX = "https://www.humblebundle.com/downloads?key="
_DEFAULT_PLATFORMS = ["windows", "audio", "video", "ebook", "others"]


def parse_directive(line: str, config: Config) -> None:
    """Mutate config based on a links.txt directive line. Ignores comment lines."""
    line = line.rstrip("\n")

    if line.startswith("^"):
        config.cookie = line[1:].strip()

    elif line.startswith("#"):
        val = line[1:].strip()
        if val.lower() == "none":
            config.formats = []
        else:
            config.formats = [f.strip() for f in val.split(",")]

    elif line.startswith("@"):
        body = line[1:]
        if body.lower() == "all":
            config.all_platforms = True
        elif body.lower() == "all-":
            config.all_platforms = False
            config.exclude_platforms = []
        elif body.startswith("+"):
            extras = [p.strip() for p in body[1:].split(",")]
            for p in extras:
                if p and p not in config.platforms:
                    config.platforms.append(p)
        elif body.startswith("-"):
            config.exclude_platforms = [p.strip() for p in body[1:].split(",")]
        else:
            config.platforms = [p.strip() for p in body.split(",")]
            config.all_platforms = False

    elif line.startswith("%"):
        for token in line[1:].split(","):
            token = token.strip().lower()
            if token == "strict":
                config.strict = True
            elif token == "normal":
                config.strict = False
            elif token == "all":
                config.pref_first = False
            elif token == "pref":
                config.pref_first = True

    elif line.startswith("!"):
        for token in line[1:].split(","):
            token = token.strip().lower()
            if token == "md5+":
                config.md5_check = True
            elif token == "md5-":
                config.md5_check = False
                config.md5_stored_check = False
            elif token == "md5s+":
                config.md5_stored_check = True
            elif token == "md5s-":
                config.md5_stored_check = False
            elif token == "logtime" and not config._log_time_applied:
                config.timestamped = True
                config.utc = False
                config._log_time_applied = True
            elif token == "logtimeutc" and not config._log_time_applied:
                config.timestamped = True
                config.utc = True
                config._log_time_applied = True

    elif line.startswith("*"):
        for token in line[1:].split(","):
            token = token.strip().lower()
            if token == "direct":
                config.method = "direct"
            elif token == "bittorrent":
                config.method = "bittorrent"

    elif line.startswith("~"):
        for token in line[1:].split(","):
            token = token.strip().lower()
            if token == "fullbundle":
                config.bundle_name = "full"
            elif token == "keybundle":
                config.bundle_name = "key"
            else:
                m = re.match(r"if_title-(\d+)_file-(\d+)", token)
                if m:
                    config.shorten_if_title_over = int(m.group(1))
                    config.shorten_filename_to = int(m.group(2))
    # Any other line (comments, blank) — ignored


def iter_links_file(
    path: Path, config: Config
) -> Generator[tuple[str, list[str]], None, None]:
    """Yield (url, inline_formats) for each bundle URL in links.txt.
    Applies directive lines to config as they are encountered."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(_BUNDLE_URL_PREFIX):
            parts = line.split("#", 1)
            url = parts[0].strip()
            inline_formats = (
                [f.strip() for f in parts[1].split(",")]
                if len(parts) > 1 and parts[1].strip()
                else []
            )
            yield url, inline_formats
        else:
            parse_directive(line, config)


def count_bundle_urls(path: Path) -> int:
    """Count bundle URLs in links.txt without mutating config."""
    if not path.exists():
        return 0
    return sum(
        1
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip().startswith(_BUNDLE_URL_PREFIX)
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_config.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add hb_downloader/config.py tests/test_config.py
git commit -m "feat: add links.txt directive parsing"
```

---

## Task 4: Logger

**Files:**
- Create: `hb_downloader/logger.py`
- Create: `tests/test_logger.py`

- [ ] **Step 1: Write failing tests**

`tests/test_logger.py`:
```python
from pathlib import Path
from hb_downloader.logger import Logger


def test_logger_creates_log_files(tmp_path):
    log_all = tmp_path / "LOG-all.txt"
    log_err = tmp_path / "LOG-error.txt"
    Logger(log_all, log_err)
    assert log_all.exists()
    assert log_err.exists()


def test_logger_writes_bundle_header(tmp_path):
    log_all = tmp_path / "LOG-all.txt"
    log_err = tmp_path / "LOG-error.txt"
    lg = Logger(log_all, log_err)
    lg.log_bundle_header(1, 3, "My Bundle", "https://www.humblebundle.com/downloads?key=ABC")
    content = log_all.read_text()
    assert "My Bundle" in content
    assert "https://www.humblebundle.com/downloads?key=ABC" in content


def test_logger_item_ok_writes_to_all_only(tmp_path):
    log_all = tmp_path / "LOG-all.txt"
    log_err = tmp_path / "LOG-error.txt"
    lg = Logger(log_all, log_err)
    lg.log_bundle_header(1, 1, "Bundle", "https://example.com")
    lg.log_item_ok("My Book", "my_book.pdf", "pdf", "abc123")
    all_content = log_all.read_text()
    err_content = log_err.read_text()
    assert "my_book.pdf" in all_content
    assert "OK" in all_content
    assert "my_book.pdf" not in err_content


def test_logger_item_fail_writes_to_both(tmp_path):
    log_all = tmp_path / "LOG-all.txt"
    log_err = tmp_path / "LOG-error.txt"
    lg = Logger(log_all, log_err)
    lg.log_bundle_header(1, 1, "Bundle", "https://example.com")
    lg.log_item_fail("My Book", "my_book.pdf", "pdf", "aabbcc", "ddeeff", "MD5 mismatch")
    all_content = log_all.read_text()
    err_content = log_err.read_text()
    assert "FAIL" in all_content
    assert "FAIL" in err_content
    assert "aabbcc" in err_content


def test_logger_item_skipped_ok_writes_to_all(tmp_path):
    log_all = tmp_path / "LOG-all.txt"
    log_err = tmp_path / "LOG-error.txt"
    lg = Logger(log_all, log_err)
    lg.log_bundle_header(1, 1, "Bundle", "https://example.com")
    lg.log_item_skipped("My Book", "my_book.pdf", "pdf", "abc123", ok=True)
    content = log_all.read_text()
    assert "skipping" in content.lower()
    assert "OK" in content


def test_logger_summary(tmp_path):
    log_all = tmp_path / "LOG-all.txt"
    log_err = tmp_path / "LOG-error.txt"
    lg = Logger(log_all, log_err)
    lg.log_summary(md5_errors=2, not_found_errors=1)
    content = log_all.read_text()
    assert "Error Summary" in content
    assert "1" in content  # not_found_errors


def test_logger_timestamped_paths(tmp_path):
    from hb_downloader.logger import make_log_paths
    log_all, log_err = make_log_paths(base_dir=tmp_path, timestamped=True, utc=False)
    assert "LOG-all-" in log_all.name
    assert log_all.suffix == ".txt"
    assert "LOG-error-" in log_err.name


def test_logger_timestamped_utc_paths(tmp_path):
    from hb_downloader.logger import make_log_paths
    log_all, log_err = make_log_paths(base_dir=tmp_path, timestamped=True, utc=True)
    assert log_all.name.endswith("Z.txt")
    assert log_err.name.endswith("Z.txt")
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_logger.py -v
```

Expected: `ImportError: cannot import name 'Logger'`

- [ ] **Step 3: Implement `hb_downloader/logger.py`**

```python
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def make_log_paths(
    base_dir: Path, timestamped: bool = False, utc: bool = False
) -> tuple[Path, Path]:
    """Return (log_all_path, log_error_path) based on timestamped setting."""
    if timestamped:
        logs_dir = base_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        if utc:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S") + "Z"
        else:
            ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        return logs_dir / f"LOG-all-{ts}.txt", logs_dir / f"LOG-error-{ts}.txt"
    return base_dir / "LOG-all.txt", base_dir / "LOG-error.txt"


class Logger:
    def __init__(self, log_all: Path, log_error: Path) -> None:
        self._all = log_all
        self._err = log_error
        now = datetime.now().strftime("%Y-%m-%d %A %H:%M:%S")
        for path in (self._all, self._err):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"{now}\n", encoding="utf-8")

    def _write(self, path: Path, text: str) -> None:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text)

    def _write_all(self, text: str) -> None:
        self._write(self._all, text)

    def _write_err(self, text: str) -> None:
        self._write(self._err, text)

    def log_bundle_header(
        self, bundle_num: int, total: int, title: str, url: str
    ) -> None:
        block = (
            "\n==============================================================\n"
            f"{bundle_num} / {total} - {title}\n"
            f"{url}\n"
            "--------------------------------------------------------------\n"
        )
        self._write_all(block)
        self._write_err(block)

    def log_item_title(self, chunk_num: int, chunk_total: int, item_title: str) -> None:
        self._write_all(f"\n{chunk_num} / {chunk_total} - {item_title}\n")

    def log_item_error_title(
        self, chunk_num: int, chunk_total: int, item_title: str
    ) -> None:
        self._write_err(f"\n{chunk_num} / {chunk_total} - {item_title}\n")

    def log_item_ok(
        self, item_title: str, filename: str, label: str, md5: str
    ) -> None:
        self._write_all(
            f"{label} - {filename}\n"
            "   OK - File integrity (MD5) verified.\n"
            f"   MD5: {md5}\n"
        )

    def log_item_fail(
        self,
        item_title: str,
        filename: str,
        label: str,
        md5_file: str,
        md5_expected: str,
        reason: str,
    ) -> None:
        entry = (
            f"{label} - {filename}\n"
            f"   FAIL - {reason}\n"
            f"   File MD5: {md5_file}\n"
            f"   HB   MD5: {md5_expected}\n"
        )
        self._write_all(entry)
        self._write_err(entry)

    def log_item_skipped(
        self,
        item_title: str,
        filename: str,
        label: str,
        md5: str,
        ok: bool,
    ) -> None:
        self._write_all(
            f"{label} - {filename}\n"
            "   File downloaded already, skipping...\n"
        )
        if ok:
            self._write_all(
                "   OK - File integrity (MD5) verified.\n"
                f"   MD5: {md5}\n"
            )
        else:
            entry = (
                "   FAIL - File integrity (MD5) failed.\n"
                f"   MD5: {md5}\n"
            )
            self._write_all(entry)
            self._write_err(f"{label} - {filename}\n   File downloaded already, skipping...\n{entry}")

    def log_summary(self, md5_errors: int, not_found_errors: int) -> None:
        summary = (
            "\nError Summary:\n"
            "----------------------\n"
            f"Failed file integrity (MD5) checks: {md5_errors - not_found_errors}\n"
            f"Unsuccessful downloads (file not found): {not_found_errors}\n"
            f"Total: {md5_errors}\n"
        )
        self._write_all(summary)
        self._write_err(summary)

    def log_separator(self) -> None:
        sep = "==============================================================\n"
        self._write_all(sep)
        self._write_err(sep)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_logger.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add hb_downloader/logger.py tests/test_logger.py
git commit -m "feat: add Logger for LOG-all and LOG-error files"
```

---

## Task 5: API — Connectivity, fetch_bundle, Title Sanitisation

**Files:**
- Create: `hb_downloader/api.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Write failing tests**

`tests/test_api.py`:
```python
import pytest
import requests_mock as req_mock
from hb_downloader.api import (
    fetch_bundle,
    HBAuthError,
    HBNotFoundError,
    HBAPIError,
    _sanitise_title,
)


def test_sanitise_title_strips_special_chars():
    assert _sanitise_title("Hello: World!") == "Hello_ World_"


def test_sanitise_title_preserves_allowed():
    assert _sanitise_title("My-Book_Title 2") == "My-Book_Title 2"


def test_sanitise_title_replaces_slash():
    assert _sanitise_title("A/B") == "A_B"


def test_sanitise_title_trims_whitespace():
    assert _sanitise_title("  Hello  ") == "Hello"


def test_sanitise_title_non_ascii():
    # Non-ASCII chars replaced with ? then stripped to _
    result = _sanitise_title("Привет")
    assert all(c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_ '" for c in result)


def test_fetch_bundle_success(mock_bundle):
    with req_mock.Mocker() as m:
        m.get(
            "https://www.humblebundle.com/api/v1/order/TESTKEY1234567A",
            json=mock_bundle,
        )
        result = fetch_bundle("TESTKEY1234567A", "test_cookie")
    assert result["gamekey"] == "TESTKEY1234567A"


def test_fetch_bundle_401_raises_auth_error():
    with req_mock.Mocker() as m:
        m.get(
            "https://www.humblebundle.com/api/v1/order/BADKEY",
            status_code=401,
        )
        with pytest.raises(HBAuthError):
            fetch_bundle("BADKEY", "bad_cookie")


def test_fetch_bundle_404_raises_not_found():
    with req_mock.Mocker() as m:
        m.get(
            "https://www.humblebundle.com/api/v1/order/MISSINGKEY",
            status_code=404,
        )
        with pytest.raises(HBNotFoundError):
            fetch_bundle("MISSINGKEY", "cookie")


def test_fetch_bundle_500_raises_api_error():
    with req_mock.Mocker() as m:
        m.get(
            "https://www.humblebundle.com/api/v1/order/ERRKEY",
            status_code=500,
        )
        with pytest.raises(HBAPIError):
            fetch_bundle("ERRKEY", "cookie")
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_api.py -v
```

Expected: `ImportError: cannot import name 'fetch_bundle'`

- [ ] **Step 3: Implement `hb_downloader/api.py` (fetch + sanitise; extract_downloads in Task 6)**

```python
from __future__ import annotations

import re
import socket
import time
from dataclasses import dataclass

import requests

from hb_downloader.config import Config


class HBAuthError(Exception):
    pass


class HBNotFoundError(Exception):
    pass


class HBAPIError(Exception):
    pass


@dataclass
class DownloadItem:
    bundle_title: str
    item_title: str
    filename: str
    url: str
    md5: str
    label: str


def _sanitise_title(name: str) -> str:
    """Replicate PS1 ASCII conversion + special char stripping."""
    name = name.encode("ascii", errors="replace").decode("ascii")
    name = re.sub(r"[^a-zA-Z0-9/_'\- ]", "_", name)
    name = name.replace("/", "_")
    return name.strip()


def wait_for_connection(
    host: str = "humblebundle.com",
    max_attempts: int = 12,
    interval: int = 10,
) -> bool:
    """Wait for network connectivity. Returns False if never connected."""
    for attempt in range(max_attempts):
        try:
            socket.create_connection((host, 443), timeout=5)
            return True
        except OSError:
            print(
                f"\033[31mWaiting for internet connection to continue... "
                f"({attempt + 1}/{max_attempts})\033[0m"
            )
            time.sleep(interval)
    return False


def fetch_bundle(key: str, cookie: str) -> dict:
    """Fetch bundle JSON from HB API. Raises HBAuthError, HBNotFoundError, HBAPIError."""
    url = f"https://www.humblebundle.com/api/v1/order/{key}"
    session = requests.Session()
    session.cookies.set("_simpleauth_sess", cookie, domain="humblebundle.com")
    resp = session.get(url, timeout=900)
    if resp.status_code == 401:
        raise HBAuthError("Invalid or missing _simpleauth_sess cookie (401)")
    if resp.status_code == 404:
        raise HBNotFoundError("Bundle key not found — check for typos (404)")
    if resp.status_code != 200:
        raise HBAPIError(f"Unexpected API response: {resp.status_code}")
    return resp.json()


def extract_downloads(bundle_json: dict, config: Config) -> list[DownloadItem]:
    """Apply platform/format/strict/pref filters. Returns flat list of DownloadItem."""
    # Implemented in Task 6
    raise NotImplementedError
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_api.py -v
```

Expected: all 9 tests PASS (extract_downloads tests are in Task 6).

- [ ] **Step 5: Commit**

```bash
git add hb_downloader/api.py tests/test_api.py
git commit -m "feat: add HB API fetch_bundle and title sanitisation"
```

---

## Task 6: API — extract_downloads

**Files:**
- Modify: `hb_downloader/api.py` — implement `extract_downloads()`
- Modify: `tests/test_api.py` — add extract_downloads tests

- [ ] **Step 1: Write failing tests**

Append to `tests/test_api.py`:
```python
from hb_downloader.api import extract_downloads
from hb_downloader.config import Config


def _config(**kwargs) -> Config:
    c = Config()
    for k, v in kwargs.items():
        setattr(c, k, v)
    return c


def test_extract_skips_hidden_entries(mock_bundle):
    c = _config(all_platforms=True, formats=[])
    items = extract_downloads(mock_bundle, c)
    titles = [i.item_title for i in items]
    assert "Hidden Item" not in titles


def test_extract_all_platforms_returns_all(mock_bundle):
    c = _config(all_platforms=True, formats=[], pref_first=False)
    items = extract_downloads(mock_bundle, c)
    assert len(items) == 2  # epub + pdf for Learning Python


def test_extract_platform_filter_excludes_non_matching(mock_bundle):
    c = _config(platforms=["windows"], formats=[])
    items = extract_downloads(mock_bundle, c)
    assert len(items) == 0  # mock bundle only has ebook platform


def test_extract_format_pref_first(mock_bundle):
    # pref_first=True: return first matching format only
    c = _config(all_platforms=True, formats=["pdf"], pref_first=True, strict=False)
    items = extract_downloads(mock_bundle, c)
    assert len(items) == 1
    assert items[0].label == "pdf"


def test_extract_format_all_matching(mock_bundle):
    # pref_first=False: return all matching formats
    c = _config(all_platforms=True, formats=["pdf", "epub"], pref_first=False, strict=False)
    items = extract_downloads(mock_bundle, c)
    assert len(items) == 2
    labels = {i.label for i in items}
    assert labels == {"pdf", "epub"}


def test_extract_strict_no_match_skips(mock_bundle):
    # strict=True + preferred format not present → skip item
    c = _config(all_platforms=True, formats=["mobi"], pref_first=True, strict=True)
    items = extract_downloads(mock_bundle, c)
    assert len(items) == 0


def test_extract_non_strict_fallback_to_last(mock_bundle):
    # strict=False + preferred not found → fall back to last format in struct
    c = _config(all_platforms=True, formats=["mobi"], pref_first=True, strict=False)
    items = extract_downloads(mock_bundle, c)
    assert len(items) == 1  # falls back to last in download_struct


def test_extract_no_formats_downloads_all(mock_bundle):
    # formats=[] means download all
    c = _config(all_platforms=True, formats=[], pref_first=False, strict=False)
    items = extract_downloads(mock_bundle, c)
    assert len(items) == 2


def test_extract_url_is_direct_by_default(mock_bundle):
    c = _config(all_platforms=True, formats=["pdf"], pref_first=True, method="direct")
    items = extract_downloads(mock_bundle, c)
    assert "ttl=" in items[0].url  # direct URL has query params


def test_extract_url_is_bittorrent(mock_bundle):
    c = _config(all_platforms=True, formats=["pdf"], pref_first=True, method="bittorrent")
    items = extract_downloads(mock_bundle, c)
    assert "torrent" in items[0].url


def test_extract_bundle_title_uses_key_when_configured(mock_bundle):
    c = _config(all_platforms=True, formats=[], bundle_name="key")
    items = extract_downloads(mock_bundle, c)
    assert items[0].bundle_title == "TESTKEY1234567A"


def test_extract_filename_strips_query_params(mock_bundle):
    c = _config(all_platforms=True, formats=["pdf"], pref_first=True)
    items = extract_downloads(mock_bundle, c)
    assert "?" not in items[0].filename
    assert items[0].filename == "learning_python.pdf"


def test_extract_filename_shortened(mock_bundle):
    # shorten_if_title_over=5 (very short threshold to trigger), shorten_filename_to=10
    c = _config(
        all_platforms=True,
        formats=["pdf"],
        pref_first=True,
        shorten_if_title_over=5,
        shorten_filename_to=10,
    )
    items = extract_downloads(mock_bundle, c)
    assert len(items[0].filename) <= 10
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_api.py -v -k "extract"
```

Expected: all extract tests FAIL with `NotImplementedError`.

- [ ] **Step 3: Implement `extract_downloads()` in `hb_downloader/api.py`**

Replace the `extract_downloads` stub with:
```python
def extract_downloads(bundle_json: dict, config: Config) -> list[DownloadItem]:
    """Apply platform/format/strict/pref filters. Returns flat list of DownloadItem."""
    subproducts = bundle_json.get("subproducts", [])
    if not subproducts:
        return []

    # Bundle title
    if config.bundle_name == "key":
        bundle_title = bundle_json.get("gamekey", "unknown")
    else:
        raw = bundle_json.get("product", {}).get("human_name", "unknown")
        bundle_title = _sanitise_title(raw)

    items: list[DownloadItem] = []

    for product in subproducts:
        if product.get("library_family_name") == "hidden":
            continue

        item_title = _sanitise_title(product.get("human_name", "unknown"))
        downloads = product.get("downloads", [])

        for dl in downloads:
            platform = dl.get("platform", "")
            if not config.all_platforms:
                if platform not in config.platforms:
                    continue
                if platform in config.exclude_platforms:
                    continue

            dl_struct = dl.get("download_struct", [])
            # Normalise to list
            if isinstance(dl_struct, dict):
                dl_struct = [dl_struct]
            if not dl_struct:
                continue

            # Only process entries that have a web URL
            dl_struct = [d for d in dl_struct if d.get("url", {}).get("web")]
            if not dl_struct:
                continue

            # Determine effective formats (empty = all)
            eff_formats = config.formats  # may be overridden externally per URL

            if not eff_formats:
                # Download all
                for entry in dl_struct:
                    items.append(
                        _make_item(entry, bundle_title, item_title, config)
                    )
                continue

            # Match preferred formats
            matched: list[DownloadItem] = []
            for pref in eff_formats:
                for entry in reversed(dl_struct):
                    if entry.get("name", "").lower() == pref.lower():
                        matched.append(
                            _make_item(entry, bundle_title, item_title, config)
                        )
                        if config.pref_first:
                            break
                if matched and config.pref_first:
                    break

            if matched:
                items.extend(matched)
            elif not config.strict:
                # Fall back to last entry in struct
                items.append(
                    _make_item(dl_struct[-1], bundle_title, item_title, config)
                )

    return items


def _make_item(
    entry: dict, bundle_title: str, item_title: str, config: Config
) -> DownloadItem:
    """Build a DownloadItem from a download_struct entry."""
    url_obj = entry.get("url", {})
    url = url_obj.get("web") if config.method == "direct" else url_obj.get("bittorrent", url_obj.get("web"))
    md5 = (entry.get("md5") or "").strip()
    label = entry.get("name", "")

    # Filename: strip query params, take last path segment
    raw_filename = (url or "").split("?")[0].rstrip("/").split("/")[-1].strip()
    filename = _shorten_filename(raw_filename, item_title, config)

    return DownloadItem(
        bundle_title=bundle_title,
        item_title=item_title,
        filename=filename,
        url=url or "",
        md5=md5,
        label=label,
    )


def _shorten_filename(filename: str, item_title: str, config: Config) -> str:
    """Apply conditional filename shortening if configured."""
    if (
        config.shorten_if_title_over > 0
        and len(item_title) > config.shorten_if_title_over
        and config.shorten_filename_to > 0
    ):
        ext_idx = filename.rfind(".")
        if ext_idx > 0:
            ext = filename[ext_idx:]
            stem = filename[:ext_idx]
            max_stem = config.shorten_filename_to - len(ext)
            if len(filename) > config.shorten_filename_to:
                filename = stem[:max_stem] + ext
    return filename
```

- [ ] **Step 4: Run all API tests**

```bash
pytest tests/test_api.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add hb_downloader/api.py tests/test_api.py
git commit -m "feat: implement extract_downloads with platform/format filtering"
```

---

## Task 7: Downloader — MD5, Skip Detection, Download & Move

**Files:**
- Create: `hb_downloader/downloader.py`
- Create: `tests/test_downloader.py`

- [ ] **Step 1: Write failing tests**

`tests/test_downloader.py`:
```python
import hashlib
import shutil
from pathlib import Path

import pytest

from hb_downloader.api import DownloadItem
from hb_downloader.config import Config
from hb_downloader.downloader import md5_file, download_bundle
from hb_downloader.logger import Logger, make_log_paths


def _make_item(**kwargs) -> DownloadItem:
    defaults = dict(
        bundle_title="Test_Bundle",
        item_title="Test_Book",
        filename="test_book.pdf",
        url="https://dl.humble.com/test_book.pdf?ttl=1",
        md5="",
        label="pdf",
    )
    defaults.update(kwargs)
    return DownloadItem(**defaults)


def _make_logger(tmp_path) -> Logger:
    log_all, log_err = make_log_paths(tmp_path)
    return Logger(log_all, log_err)


def test_md5_file_correct_hash(tmp_path):
    f = tmp_path / "test.txt"
    f.write_bytes(b"hello world")
    expected = hashlib.md5(b"hello world").hexdigest()
    assert md5_file(f) == expected


def test_md5_file_missing_returns_none(tmp_path):
    assert md5_file(tmp_path / "nonexistent.txt") is None


def test_download_bundle_skips_existing(tmp_path, requests_mock):
    config = Config()
    config.download_dir = tmp_path / "downloads"
    item = _make_item()
    # Pre-create destination file
    dest = config.download_dir / item.bundle_title / item.item_title / item.filename
    dest.parent.mkdir(parents=True)
    dest.write_bytes(b"already here")

    lg = _make_logger(tmp_path)
    download_bundle([item], config, lg)
    # requests_mock has no registered URLs — would raise if download was attempted
    assert dest.read_bytes() == b"already here"


def test_download_bundle_downloads_new_file(tmp_path, requests_mock):
    file_content = b"PDF file content here"
    md5_expected = hashlib.md5(file_content).hexdigest()

    item = _make_item(
        url="https://dl.humble.com/test_book.pdf?ttl=1",
        md5=md5_expected,
    )
    requests_mock.get(item.url, content=file_content)

    config = Config()
    config.download_dir = tmp_path / "downloads"
    lg = _make_logger(tmp_path)
    download_bundle([item], config, lg)

    dest = config.download_dir / item.bundle_title / item.item_title / item.filename
    assert dest.exists()
    assert dest.read_bytes() == file_content


def test_download_bundle_md5_mismatch_logs_fail(tmp_path, requests_mock):
    file_content = b"PDF file content here"
    item = _make_item(
        url="https://dl.humble.com/test_book.pdf?ttl=1",
        md5="wrongmd5value",
    )
    requests_mock.get(item.url, content=file_content)

    config = Config()
    config.download_dir = tmp_path / "downloads"
    config.md5_check = True
    log_all, log_err = make_log_paths(tmp_path)
    lg = Logger(log_all, log_err)
    download_bundle([item], config, lg)

    err_content = log_err.read_text()
    assert "FAIL" in err_content


def test_download_bundle_dry_run_does_not_download(tmp_path, requests_mock):
    item = _make_item(url="https://dl.humble.com/test_book.pdf?ttl=1")
    config = Config()
    config.download_dir = tmp_path / "downloads"
    lg = _make_logger(tmp_path)
    download_bundle([item], config, lg, dry_run=True)

    dest = config.download_dir / item.bundle_title / item.item_title / item.filename
    assert not dest.exists()


def test_download_bundle_updates_bundle_dir_mtime(tmp_path, requests_mock):
    import time
    file_content = b"content"
    item = _make_item(url="https://dl.humble.com/test_book.pdf?ttl=1", md5="")
    requests_mock.get(item.url, content=file_content)

    config = Config()
    config.download_dir = tmp_path / "downloads"
    config.md5_check = False
    lg = _make_logger(tmp_path)

    before = time.time() - 1
    download_bundle([item], config, lg)
    bundle_dir = config.download_dir / item.bundle_title
    assert bundle_dir.stat().st_mtime >= before
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_downloader.py -v
```

Expected: `ImportError: cannot import name 'md5_file'`

- [ ] **Step 3: Implement `hb_downloader/downloader.py`**

```python
from __future__ import annotations

import hashlib
import os
import shutil
import time
from pathlib import Path

import requests

from hb_downloader.api import DownloadItem
from hb_downloader.config import Config
from hb_downloader.logger import Logger

try:
    from rich.progress import (
        BarColumn,
        DownloadColumn,
        Progress,
        TextColumn,
        TimeRemainingColumn,
        TransferSpeedColumn,
    )
    _RICH = True
except ImportError:
    _RICH = False


def md5_file(path: Path) -> str | None:
    """Return hex MD5 of file, or None if file does not exist."""
    if not path.exists():
        return None
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _download_file(url: str, dest: Path) -> None:
    """Stream-download url to dest, showing a rich progress bar if available."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, stream=True, timeout=900)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0))

    if _RICH:
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
        ) as progress:
            task = progress.add_task(dest.name, total=total or None)
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)
                    progress.update(task, advance=len(chunk))
    else:
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)


def download_bundle(
    items: list[DownloadItem],
    config: Config,
    logger: Logger,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Download all items. Returns (md5_errors, not_found_errors)."""
    temp_dir = config.download_dir / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    md5_errors = 0
    not_found_errors = 0

    for item in items:
        dest_dir = config.download_dir / item.bundle_title / item.item_title
        dest = dest_dir / item.filename
        temp = temp_dir / item.bundle_title / item.item_title / item.filename

        if dry_run:
            print(f"  [dry-run] {item.label} - {item.filename}")
            continue

        if dest.exists():
            # Skip — already downloaded
            print(f"   File downloaded already, skipping...")
            if config.md5_check and config.md5_stored_check:
                actual = md5_file(dest)
                ok = actual == item.md5
                logger.log_item_skipped(item.item_title, item.filename, item.label, item.md5, ok=ok)
                if not ok:
                    md5_errors += 1
                    if actual is None:
                        not_found_errors += 1
            continue

        # Download to temp
        print(f"   {item.label} - {item.filename}")
        try:
            _download_file(item.url, temp)
        except Exception as e:
            print(f"   Cannot download {item.url}: {e}")
            logger.log_item_fail(
                item.item_title, item.filename, item.label,
                "none", item.md5, "Unsuccessful download (file not found)."
            )
            md5_errors += 1
            not_found_errors += 1
            continue

        # MD5 verify
        if config.md5_check:
            actual = md5_file(temp)
            if actual == item.md5:
                print("    OK - File integrity (MD5) verified.")
                logger.log_item_ok(item.item_title, item.filename, item.label, item.md5)
            else:
                if actual is None:
                    reason = "Unsuccessful download (file not found)."
                    not_found_errors += 1
                else:
                    reason = "File integrity (MD5) failed."
                md5_errors += 1
                print(f"    FAIL - {reason}")
                logger.log_item_fail(
                    item.item_title, item.filename, item.label,
                    actual or "none", item.md5, reason
                )

        # Move temp → final destination
        if temp.exists():
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(temp), str(dest))
            # Update bundle dir mtime (mirrors PS1 LastWriteTime update)
            bundle_dir = config.download_dir / item.bundle_title
            now = time.time()
            os.utime(bundle_dir, (now, now))

    # Clean up temp
    shutil.rmtree(temp_dir, ignore_errors=True)
    return md5_errors, not_found_errors
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_downloader.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add hb_downloader/downloader.py tests/test_downloader.py
git commit -m "feat: implement downloader with MD5 verification and skip logic"
```

---

## Task 8: CLI — Arg Parsing + Orchestration Loop

**Files:**
- Create: `hb_downloader/cli.py`
- Create: `tests/test_cli.py` (integration smoke test)

- [ ] **Step 1: Write failing tests**

`tests/test_cli.py`:
```python
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from hb_downloader.cli import parse_args


def test_parse_args_defaults():
    args = parse_args([])
    assert args.links == Path("links.txt")
    assert args.config == Path("config.toml")
    assert args.output is None
    assert args.cookie is None
    assert args.format is None
    assert args.platforms is None
    assert args.dry_run is False


def test_parse_args_all_options():
    args = parse_args([
        "--cookie", "abc",
        "--links", "my_links.txt",
        "--config", "my_config.toml",
        "--output", "my_downloads",
        "--format", "pdf,epub",
        "--platforms", "linux,ebook",
        "--dry-run",
    ])
    assert args.cookie == "abc"
    assert args.links == Path("my_links.txt")
    assert args.config == Path("my_config.toml")
    assert args.output == Path("my_downloads")
    assert args.format == "pdf,epub"
    assert args.platforms == "linux,ebook"
    assert args.dry_run is True


def test_main_creates_downloads_dir(tmp_path, requests_mock):
    links = tmp_path / "links.txt"
    links.write_text(
        "^test_cookie\n"
        f"https://www.humblebundle.com/downloads?key=TESTKEY1234567A\n"
    )
    requests_mock.get(
        "https://www.humblebundle.com/api/v1/order/TESTKEY1234567A",
        json={
            "product": {"human_name": "Empty Bundle"},
            "gamekey": "TESTKEY1234567A",
            "subproducts": [],
        },
    )
    from hb_downloader.cli import main
    with patch("sys.argv", [
        "hb-dl",
        "--links", str(links),
        "--config", str(tmp_path / "nonexistent.toml"),
        "--output", str(tmp_path / "downloads"),
    ]):
        main()
    assert (tmp_path / "downloads").exists()
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_cli.py -v
```

Expected: `ImportError: cannot import name 'parse_args'`

- [ ] **Step 3: Implement `hb_downloader/cli.py`**

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hb_downloader.api import (
    DownloadItem,
    HBAuthError,
    HBNotFoundError,
    HBAPIError,
    extract_downloads,
    fetch_bundle,
    wait_for_connection,
)
from hb_downloader.config import Config, count_bundle_urls, iter_links_file, load_toml
from hb_downloader.downloader import download_bundle
from hb_downloader.logger import Logger, make_log_paths


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="hb-dl",
        description="HB DRM-Free bulk downloader — cross-platform Python edition",
    )
    parser.add_argument("--cookie", help="_simpleauth_sess cookie value")
    parser.add_argument("--links", type=Path, default=Path("links.txt"), metavar="FILE")
    parser.add_argument("--config", type=Path, default=Path("config.toml"), metavar="FILE")
    parser.add_argument("--output", type=Path, default=None, metavar="DIR")
    parser.add_argument("--format", metavar="TEXT", help="Preferred format(s), e.g. pdf,epub")
    parser.add_argument("--platforms", metavar="TEXT", help="Platforms to include, e.g. windows,ebook")
    parser.add_argument("--dry-run", action="store_true", default=False)
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()

    # Load config: toml → CLI overrides
    config = load_toml(args.config)
    if args.cookie:
        config.cookie = args.cookie
    if args.output:
        config.download_dir = args.output
    if args.format:
        config.formats = [f.strip() for f in args.format.split(",")]
    if args.platforms:
        config.platforms = [p.strip() for p in args.platforms.split(",")]

    print(f"HB DRM-Free bulk downloader 0.5.0")
    print(f"Download directory: {config.download_dir}\n")

    # Ensure output directories exist
    config.download_dir.mkdir(parents=True, exist_ok=True)

    # Connectivity check
    if not wait_for_connection():
        print("\033[31mScript terminated: no internet connection after 120 seconds.\033[0m")
        sys.exit(1)

    # Ensure links.txt exists
    if not args.links.exists():
        args.links.write_text(
            "^<Override this with your '_simpleauth_sess' cookie from your browser. "
            "More info in README.>\n"
        )

    # Set up log files (respects config.timestamped / config.utc)
    base_dir = Path(".")
    log_all_path, log_err_path = make_log_paths(base_dir, config.timestamped, config.utc)
    logger = Logger(log_all_path, log_err_path)

    total_bundles = count_bundle_urls(args.links)
    current = 0
    total_md5_errors = 0
    total_not_found = 0

    for url, inline_formats in iter_links_file(args.links, config):
        current += 1

        # Apply inline format override for this URL only
        active_config = config
        if inline_formats:
            import copy
            active_config = copy.copy(config)
            active_config.formats = inline_formats

        key = url.split("?key=")[-1].strip()
        print(f"\n{'='*62}")
        print(f"{current} / {total_bundles}")
        print(f"{url}")
        print(f"{'-'*62}")

        try:
            bundle_json = fetch_bundle(key, active_config.cookie)
        except HBAuthError as e:
            print(f"\033[31m{e}\033[0m")
            print("Add your _simpleauth_sess cookie to links.txt as: ^your_cookie_value")
            continue
        except HBNotFoundError as e:
            print(f"\033[31m{e}\033[0m")
            continue
        except HBAPIError as e:
            print(f"\033[31m{e}\033[0m")
            continue

        items = extract_downloads(bundle_json, active_config)

        if not items:
            print("\nNo DRM-Free content detected for this bundle.\n")
            continue

        # Group items by item_title for display
        seen_titles: set[str] = set()
        chunk_map: dict[str, int] = {}
        ordered_titles: list[str] = []
        for item in items:
            if item.item_title not in seen_titles:
                seen_titles.add(item.item_title)
                ordered_titles.append(item.item_title)
        total_items = len(ordered_titles)
        for idx, title in enumerate(ordered_titles, 1):
            chunk_map[title] = idx

        bundle_display = items[0].bundle_title if items else key
        logger.log_bundle_header(current, total_bundles, bundle_display, url)

        # Print per-item progress and download
        for idx, title in enumerate(ordered_titles, 1):
            print(f"\n{idx} / {total_items} - {title}")
            logger.log_item_title(idx, total_items, title)
            title_items = [i for i in items if i.item_title == title]
            md5_errs, not_found = download_bundle(title_items, active_config, logger, args.dry_run)
            total_md5_errors += md5_errs
            total_not_found += not_found

        logger.log_separator()
        print(f"{'='*62}")

    # Final summary
    summary = (
        f"\nError Summary:\n"
        f"----------------------\n"
        f"Failed file integrity (MD5) checks: {total_md5_errors - total_not_found}\n"
        f"Unsuccessful downloads (file not found): {total_not_found}\n"
        f"Total: {total_md5_errors}"
    )
    print(summary)
    logger.log_summary(total_md5_errors, total_not_found)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_cli.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add hb_downloader/cli.py tests/test_cli.py
git commit -m "feat: add CLI entry point and orchestration loop"
```

---

## Task 9: Launchers, config.toml.example, and RUN.bat Update

**Files:**
- Create: `RUN.sh`
- Create: `config.toml.example`
- Modify: `RUN.bat`

- [ ] **Step 1: Create `RUN.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 -m hb_downloader \
  --links "$SCRIPT_DIR/links.txt" \
  --config "$SCRIPT_DIR/config.toml" \
  --output "$SCRIPT_DIR/downloads"
```

Make it executable:
```bash
chmod +x RUN.sh
```

- [ ] **Step 2: Create `config.toml.example`**

```toml
# HB DRM-Free Downloader — example config
# Copy to config.toml and fill in your values.
# CLI args override these settings.
# links.txt directives also override these (processed line-by-line).

[auth]
# Your _simpleauth_sess cookie from humblebundle.com
# See README for how to find it.
cookie = "paste_your_cookie_here"

[download]
# Where to save files (relative to script directory, or absolute)
directory = "downloads"

# Platforms to include. Known values: windows, linux, mac, android, audio, video, ebook, others
platforms = ["windows", "audio", "video", "ebook", "others"]

# Platforms to exclude (takes precedence over platforms list)
exclude_platforms = []

# Set to true to download all platforms regardless of above lists
all_platforms = false

# Preferred formats (e.g. ["pdf", "epub"]). Empty list = download all formats.
formats = []

# strict = true: skip items that don't have your preferred format (no fallback)
strict = false

# pref_first = true: download first matching format only
# pref_first = false: download all matching formats
pref_first = true

# method = "direct" or "bittorrent"
method = "direct"

# MD5 file integrity checking
md5_check = true
md5_stored_check = true

[paths]
# bundle_name = "full" uses the bundle's human name as the folder
# bundle_name = "key" uses the purchase key (shorter, avoids path length issues)
bundle_name = "full"

# Conditional filename shortening:
# If item title length > shorten_if_title_over, truncate filename to shorten_filename_to chars
# Set shorten_if_title_over = 0 to disable
shorten_if_title_over = 0
shorten_filename_to = 0

[logging]
# timestamped = true saves logs with date/time in a logs/ subfolder (not overwritten each run)
timestamped = false
utc = false
```

- [ ] **Step 3: Update `RUN.bat`**

Read the current content first, then replace:
```bat
@echo off
python -m hb_downloader --links "%~dp0links.txt" --config "%~dp0config.toml" --output "%~dp0downloads"
pause
```

- [ ] **Step 4: Verify end-to-end on a dry run**

Create a minimal `links.txt` in the repo root with a placeholder, then run:
```bash
python -m hb_downloader --dry-run --links links.txt --output /tmp/hb_test
```

Expected: prints version banner and "Download directory", then exits cleanly (no crash).

- [ ] **Step 5: Commit**

```bash
git add RUN.sh config.toml.example RUN.bat
git commit -m "feat: add RUN.sh launcher, config.toml.example, update RUN.bat for Python"
```

---

## Self-Review

Spec coverage check:

| Spec requirement | Task |
|-----------------|------|
| `Config` dataclass + defaults | Task 2 |
| `config.toml` loading | Task 2 |
| All `links.txt` directives (`^#@%!*~`) | Task 3 |
| Backwards compatible `links.txt` | Task 3 |
| CLI args + precedence | Task 8 |
| `fetch_bundle()` + error types | Task 5 |
| Title sanitisation (ASCII/Cyrillic) | Task 5 |
| Hidden subproduct filtering | Task 6 |
| Platform filtering (`all_platforms`, include/exclude) | Task 6 |
| Format preference + strict + pref_first | Task 6 |
| BitTorrent vs direct URL selection | Task 6 |
| Filename from URL (strip query params) | Task 6 |
| Conditional filename shortening | Task 6 |
| bundle_name full vs key | Task 6 |
| `md5_file()` | Task 7 |
| Skip already-downloaded files | Task 7 |
| Two-stage download (temp → downloads) | Task 7 |
| MD5 verification (new + stored) | Task 7 |
| Bundle dir mtime update | Task 7 |
| `--dry-run` | Task 7 + Task 8 |
| Progress bar via `rich` (fallback) | Task 7 |
| Coloured console output (errors red) | Task 5 (wait_for_connection) + Task 8 |
| Logger — LOG-all + LOG-error | Task 4 |
| Timestamped log files | Task 4 |
| Internet connectivity check + retry | Task 5 |
| Error summary on exit | Task 8 |
| `python -m hb_downloader` entry | Task 1 |
| `pip install -e .` packaging | Task 1 |
| `RUN.sh` for macOS/Linux | Task 9 |
| `RUN.bat` updated | Task 9 |
| `config.toml.example` | Task 9 |

All spec requirements are covered. No placeholders remain. Type/method names are consistent across tasks.

---

**Plan complete and saved to `docs/superpowers/plans/2026-03-27-hb-downloader-python-migration.md`.**

Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
