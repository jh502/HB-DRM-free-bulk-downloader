import pytest
from pathlib import Path


MOCK_BUNDLE_JSON = {
    "product": {"human_name": "Test Bundle: Programming by O'Reilly"},
    "gamekey": "TESTKEY1234567A",
    "subproducts": [
        {
            "human_name": "Learning Python",
            "library_family_name": "",
            "downloads": [
                {
                    "platform": "ebook",
                    "download_struct": [
                        {
                            "name": "epub",
                            "url": {
                                "web": "https://dl.humble.com/learning_python.epub?ttl=99",
                                "bittorrent": "https://dl.humble.com/learning_python.epub.torrent",
                            },
                            "md5": "aabbccddeeff0011",
                        },
                        {
                            "name": "pdf",
                            "url": {
                                "web": "https://dl.humble.com/learning_python.pdf?ttl=99",
                                "bittorrent": "https://dl.humble.com/learning_python.pdf.torrent",
                            },
                            "md5": "1100ffeeddccbbaa",
                        },
                    ],
                }
            ],
        },
        {
            "human_name": "Hidden Item",
            "library_family_name": "hidden",
            "downloads": [
                {
                    "platform": "ebook",
                    "download_struct": [
                        {
                            "name": "pdf",
                            "url": {"web": "https://dl.humble.com/hidden.pdf?ttl=99", "bittorrent": ""},
                            "md5": "deadbeef",
                        }
                    ],
                }
            ],
        },
    ],
}


@pytest.fixture
def mock_bundle():
    import copy
    return copy.deepcopy(MOCK_BUNDLE_JSON)


@pytest.fixture
def tmp_download_dir(tmp_path):
    d = tmp_path / "downloads"
    d.mkdir()
    return d


@pytest.fixture
def tmp_links_file(tmp_path):
    f = tmp_path / "links.txt"
    f.write_text("")
    return f
