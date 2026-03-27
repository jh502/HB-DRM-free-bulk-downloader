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


from hb_downloader.api import extract_downloads, _shorten_filename
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
    c = _config(all_platforms=True, formats=["pdf"], pref_first=True, strict=False)
    items = extract_downloads(mock_bundle, c)
    assert len(items) == 1
    assert items[0].label == "pdf"


def test_extract_format_all_matching(mock_bundle):
    c = _config(all_platforms=True, formats=["pdf", "epub"], pref_first=False, strict=False)
    items = extract_downloads(mock_bundle, c)
    assert len(items) == 2
    labels = {i.label for i in items}
    assert labels == {"pdf", "epub"}


def test_extract_strict_no_match_skips(mock_bundle):
    c = _config(all_platforms=True, formats=["mobi"], pref_first=True, strict=True)
    items = extract_downloads(mock_bundle, c)
    assert len(items) == 0


def test_extract_non_strict_fallback_to_last(mock_bundle):
    c = _config(all_platforms=True, formats=["mobi"], pref_first=True, strict=False)
    items = extract_downloads(mock_bundle, c)
    assert len(items) == 1  # falls back to last in download_struct


def test_extract_no_formats_downloads_all(mock_bundle):
    c = _config(all_platforms=True, formats=[], pref_first=False, strict=False)
    items = extract_downloads(mock_bundle, c)
    assert len(items) == 2


def test_extract_url_is_direct_by_default(mock_bundle):
    c = _config(all_platforms=True, formats=["pdf"], pref_first=True, method="direct")
    items = extract_downloads(mock_bundle, c)
    assert "ttl=" in items[0].url


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
    c = _config(
        all_platforms=True,
        formats=["pdf"],
        pref_first=True,
        shorten_if_title_over=5,
        shorten_filename_to=10,
    )
    items = extract_downloads(mock_bundle, c)
    assert len(items[0].filename) <= 10


def test_shorten_filename_extension_longer_than_target(base_config):
    """When shorten_filename_to < extension length, stem becomes empty string (clamped at 0)."""
    base_config.shorten_if_title_over = 1
    base_config.shorten_filename_to = 3
    # .epub is 5 chars, target is 3, so stem should be empty
    result = _shorten_filename("very_long_title.epub", "very long title", base_config)
    assert len(result) <= 5  # extension only at most
    assert result.endswith(".epub")
