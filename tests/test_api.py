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
