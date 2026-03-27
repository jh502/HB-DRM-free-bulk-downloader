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
