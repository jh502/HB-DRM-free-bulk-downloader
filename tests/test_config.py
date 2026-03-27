from pathlib import Path
from hb_downloader.config import Config, load_toml


def test_config_defaults():
    c = Config()
    assert c.cookie == "none"
    assert c.platforms == ["windows", "audio", "video", "ebook", "others"]
    assert c.exclude_platforms == []
    assert c.all_platforms is False
    assert c.formats == []
    assert c.strict is False
    assert c.pref_first is True
    assert c.method == "direct"
    assert c.md5_check is True
    assert c.md5_stored_check is True
    assert c.bundle_name == "full"
    assert c.shorten_if_title_over == 0
    assert c.shorten_filename_to == 0
    assert c.timestamped is False
    assert c.utc is False
    assert c.download_dir == Path("downloads")


def test_load_toml_partial(tmp_path):
    toml_file = tmp_path / "config.toml"
    toml_file.write_text("""
[auth]
cookie = "my_sess_cookie"

[download]
formats = ["pdf", "epub"]
strict = true
""")
    c = load_toml(toml_file)
    assert c.cookie == "my_sess_cookie"
    assert c.formats == ["pdf", "epub"]
    assert c.strict is True
    assert c.md5_check is True
    assert c.platforms == ["windows", "audio", "video", "ebook", "others"]


def test_load_toml_missing_file():
    c = load_toml(Path("nonexistent.toml"))
    assert c.cookie == "none"


def test_load_toml_all_sections(tmp_path):
    toml_file = tmp_path / "config.toml"
    toml_file.write_text("""
[auth]
cookie = "abc"

[download]
directory = "my_downloads"
platforms = ["linux", "ebook"]
exclude_platforms = ["windows"]
all_platforms = false
formats = ["pdf"]
strict = false
pref_first = false
method = "bittorrent"
md5_check = false
md5_stored_check = false

[paths]
bundle_name = "key"
shorten_if_title_over = 60
shorten_filename_to = 30

[logging]
timestamped = true
utc = true
""")
    c = load_toml(toml_file)
    assert c.cookie == "abc"
    assert c.download_dir == Path("my_downloads")
    assert c.platforms == ["linux", "ebook"]
    assert c.exclude_platforms == ["windows"]
    assert c.method == "bittorrent"
    assert c.md5_check is False
    assert c.bundle_name == "key"
    assert c.shorten_if_title_over == 60
    assert c.shorten_filename_to == 30
    assert c.timestamped is True
    assert c.utc is True
