from pathlib import Path
from hb_downloader.config import Config, load_toml, parse_directive, iter_links_file, count_bundle_urls


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


def _base_config():
    return Config()


def test_directive_cookie():
    c = _base_config()
    parse_directive("^my_secret_cookie", c)
    assert c.cookie == "my_secret_cookie"


def test_directive_formats_global():
    c = _base_config()
    parse_directive("#pdf,epub", c)
    assert c.formats == ["pdf", "epub"]


def test_directive_formats_none_resets():
    c = _base_config()
    c.formats = ["pdf"]
    parse_directive("#none", c)
    assert c.formats == []


def test_directive_platform_override():
    c = _base_config()
    parse_directive("@linux,mac", c)
    assert c.platforms == ["linux", "mac"]
    assert c.all_platforms is False


def test_directive_platform_add():
    c = _base_config()
    parse_directive("@+linux", c)
    assert "linux" in c.platforms
    assert "windows" in c.platforms  # default preserved


def test_directive_platform_exclude():
    c = _base_config()
    parse_directive("@-windows", c)
    assert c.exclude_platforms == ["windows"]


def test_directive_platform_all():
    c = _base_config()
    parse_directive("@all", c)
    assert c.all_platforms is True


def test_directive_platform_all_off():
    c = _base_config()
    c.all_platforms = True
    parse_directive("@all-", c)
    assert c.all_platforms is False


def test_directive_strict():
    c = _base_config()
    parse_directive("%strict", c)
    assert c.strict is True


def test_directive_normal():
    c = _base_config()
    c.strict = True
    parse_directive("%normal", c)
    assert c.strict is False


def test_directive_pref_all():
    c = _base_config()
    parse_directive("%all", c)
    assert c.pref_first is False


def test_directive_pref_pref():
    c = _base_config()
    c.pref_first = False
    parse_directive("%pref", c)
    assert c.pref_first is True


def test_directive_multiple_percent():
    c = _base_config()
    parse_directive("%strict,all", c)
    assert c.strict is True
    assert c.pref_first is False


def test_directive_md5_off():
    c = _base_config()
    parse_directive("!md5-", c)
    assert c.md5_check is False


def test_directive_md5s_off():
    c = _base_config()
    parse_directive("!md5s-", c)
    assert c.md5_stored_check is False


def test_directive_logtime():
    c = _base_config()
    parse_directive("!logtime", c)
    assert c.timestamped is True
    assert c.utc is False


def test_directive_logtimeutc():
    c = _base_config()
    parse_directive("!logtimeutc", c)
    assert c.timestamped is True
    assert c.utc is True


def test_directive_bittorrent():
    c = _base_config()
    parse_directive("*bittorrent", c)
    assert c.method == "bittorrent"


def test_directive_direct():
    c = _base_config()
    c.method = "bittorrent"
    parse_directive("*direct", c)
    assert c.method == "direct"


def test_directive_keybundle():
    c = _base_config()
    parse_directive("~keybundle", c)
    assert c.bundle_name == "key"


def test_directive_fullbundle():
    c = _base_config()
    c.bundle_name = "key"
    parse_directive("~fullbundle", c)
    assert c.bundle_name == "full"


def test_directive_path_shortening():
    c = _base_config()
    parse_directive("~if_title-60_file-30", c)
    assert c.shorten_if_title_over == 60
    assert c.shorten_filename_to == 30


def test_directive_path_shortening_reset():
    c = _base_config()
    c.shorten_if_title_over = 60
    c.shorten_filename_to = 30
    parse_directive("~if_title-0_file-0", c)
    assert c.shorten_if_title_over == 0
    assert c.shorten_filename_to == 0


def test_directive_comment_ignored():
    c = _base_config()
    original_cookie = c.cookie
    parse_directive("This is a comment line", c)
    assert c.cookie == original_cookie


def test_iter_links_file_yields_urls_and_applies_directives(tmp_path):
    links = tmp_path / "links.txt"
    links.write_text(
        "^test_cookie\n"
        "#pdf\n"
        "https://www.humblebundle.com/downloads?key=AAABBBCCC111222\n"
        "A comment line\n"
        "https://www.humblebundle.com/downloads?key=DDDEEEFFF333444#epub\n"
    )
    c = Config()
    results = list(iter_links_file(links, c))
    assert len(results) == 2
    url1, fmt1 = results[0]
    url2, fmt2 = results[1]
    assert "AAABBBCCC111222" in url1
    assert fmt1 == []
    assert "DDDEEEFFF333444" in url2
    assert fmt2 == ["epub"]
    assert c.cookie == "test_cookie"
    assert c.formats == ["pdf"]


def test_iter_links_file_counts_only_bundle_urls(tmp_path):
    links = tmp_path / "links.txt"
    links.write_text(
        "^cookie\n"
        "#pdf\n"
        "https://www.humblebundle.com/downloads?key=AAA\n"
        "https://www.humblebundle.com/downloads?key=BBB\n"
    )
    c = Config()
    assert count_bundle_urls(links) == 2
