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
            if isinstance(dl_struct, dict):
                dl_struct = [dl_struct]
            if not dl_struct:
                continue

            dl_struct = [d for d in dl_struct if d.get("url", {}).get("web")]
            if not dl_struct:
                continue

            eff_formats = config.formats

            if not eff_formats:
                for entry in dl_struct:
                    items.append(_make_item(entry, bundle_title, item_title, config))
                continue

            matched: list[DownloadItem] = []
            for pref in eff_formats:
                for entry in reversed(dl_struct):
                    if entry.get("name", "").lower() == pref.lower():
                        matched.append(_make_item(entry, bundle_title, item_title, config))
                        if config.pref_first:
                            break
                if matched and config.pref_first:
                    break

            if matched:
                items.extend(matched)
            elif not config.strict:
                items.append(_make_item(dl_struct[-1], bundle_title, item_title, config))

    return items


def _make_item(
    entry: dict, bundle_title: str, item_title: str, config: Config
) -> DownloadItem:
    """Build a DownloadItem from a download_struct entry."""
    url_obj = entry.get("url", {})
    url = url_obj.get("web") if config.method == "direct" else url_obj.get("bittorrent", url_obj.get("web"))
    md5 = (entry.get("md5") or "").strip()
    label = entry.get("name", "")
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
