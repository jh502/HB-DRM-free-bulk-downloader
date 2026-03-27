from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hb_downloader.api import (
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
            "# HB DRM-Free Downloader — links.txt\n"
            "# Replace the value on the next line with your _simpleauth_sess cookie:\n"
            "^paste_your_simpleauth_sess_cookie_here\n"
            "# Then add your Humble Bundle download URLs below, one per line:\n"
            "# https://www.humblebundle.com/downloads?key=YOUR_KEY_HERE\n"
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
