from __future__ import annotations

import re
import tomllib
from collections.abc import Generator
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


_BUNDLE_URL_PREFIX = "https://www.humblebundle.com/downloads?key="


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
        body = line[1:].strip()
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
