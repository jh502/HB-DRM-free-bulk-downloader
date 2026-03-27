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
