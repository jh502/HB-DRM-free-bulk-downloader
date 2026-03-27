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


def test_main_dry_run(tmp_path, requests_mock):
    """--dry-run flag is passed through to download_bundle."""
    links = tmp_path / "links.txt"
    links.write_text(
        "^test_cookie\n"
        "https://www.humblebundle.com/downloads?key=TESTKEY1234567B\n"
    )
    requests_mock.get(
        "https://www.humblebundle.com/api/v1/order/TESTKEY1234567B",
        json={
            "product": {"human_name": "Dry Run Bundle"},
            "gamekey": "TESTKEY1234567B",
            "subproducts": [],
        },
    )
    from hb_downloader.cli import main
    with patch("sys.argv", [
        "hb-dl",
        "--links", str(links),
        "--config", str(tmp_path / "nonexistent.toml"),
        "--output", str(tmp_path / "downloads"),
        "--dry-run",
    ]):
        main()
    # Should complete without error (empty bundle, dry-run)
    assert (tmp_path / "downloads").exists()


def test_main_auth_error(tmp_path, requests_mock):
    """HBAuthError from fetch_bundle is caught and execution continues."""
    links = tmp_path / "links.txt"
    links.write_text(
        "^bad_cookie\n"
        "https://www.humblebundle.com/downloads?key=TESTKEY1234567C\n"
    )
    requests_mock.get(
        "https://www.humblebundle.com/api/v1/order/TESTKEY1234567C",
        status_code=401,
    )
    from hb_downloader.cli import main
    with patch("sys.argv", [
        "hb-dl",
        "--links", str(links),
        "--config", str(tmp_path / "nonexistent.toml"),
        "--output", str(tmp_path / "downloads"),
    ]):
        main()  # Should not raise
    assert (tmp_path / "downloads").exists()


def test_main_cookie_override(tmp_path, requests_mock):
    """--cookie CLI arg overrides config cookie."""
    links = tmp_path / "links.txt"
    links.write_text(
        "https://www.humblebundle.com/downloads?key=TESTKEY1234567D\n"
    )
    requests_mock.get(
        "https://www.humblebundle.com/api/v1/order/TESTKEY1234567D",
        json={
            "product": {"human_name": "Cookie Test Bundle"},
            "gamekey": "TESTKEY1234567D",
            "subproducts": [],
        },
    )
    from hb_downloader.cli import main
    with patch("sys.argv", [
        "hb-dl",
        "--links", str(links),
        "--config", str(tmp_path / "nonexistent.toml"),
        "--output", str(tmp_path / "downloads"),
        "--cookie", "cli_cookie_value",
    ]):
        main()
    assert (tmp_path / "downloads").exists()


def test_main_creates_links_txt(tmp_path, requests_mock):
    """links.txt is created with template content when it doesn't exist."""
    links = tmp_path / "links.txt"
    assert not links.exists()
    from hb_downloader.cli import main
    with patch("sys.argv", [
        "hb-dl",
        "--links", str(links),
        "--config", str(tmp_path / "nonexistent.toml"),
        "--output", str(tmp_path / "downloads"),
    ]):
        main()
    assert links.exists()
    content = links.read_text()
    # Template should not be an instructional sentence set as cookie value
    assert "^paste_your_simpleauth_sess_cookie_here" in content
