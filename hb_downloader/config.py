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
