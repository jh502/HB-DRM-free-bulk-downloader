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

        if temp.exists():
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(temp), str(dest))
            bundle_dir = config.download_dir / item.bundle_title
            now = time.time()
            os.utime(bundle_dir, (now, now))

    shutil.rmtree(temp_dir, ignore_errors=True)
    return md5_errors, not_found_errors
