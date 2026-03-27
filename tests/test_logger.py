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
