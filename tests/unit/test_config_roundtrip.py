import json

from sniplingo.core.config import AppConfig, default_config_path, load_config, save_config
from sniplingo.domain.models import Region


def test_defaults():
    c = AppConfig()
    assert c.source_lang == "en"
    assert c.target_lang == "ja"
    assert c.select_region_hotkey == "<ctrl>+<alt>+r"
    assert c.default_backend == "google_free"
    assert c.overlay_position is None
    assert c.enable_offline_fallback is True
    assert c.deepl_api_key is None
    assert c.region is None
    assert c.has_deepl is False


def test_to_from_dict_roundtrip():
    c = AppConfig(
        source_lang="en",
        target_lang="ja",
        select_region_hotkey="<ctrl>+<shift>+r",
        default_backend="deepl",
        deepl_api_key="secret-key",
        region=Region(10, 20, 30, 40),
        overlay_position=(120, 80),
    )
    assert AppConfig.from_dict(c.to_dict()) == c


def test_overlay_position_parsing():
    assert AppConfig.from_dict({"overlay_position": [120, 80]}).overlay_position == (120, 80)
    assert AppConfig.from_dict({"overlay_position": None}).overlay_position is None
    assert AppConfig.from_dict({"overlay_position": "nope"}).overlay_position is None
    assert AppConfig.from_dict({"overlay_position": [1]}).overlay_position is None  # wrong length


def test_save_load_roundtrip_creates_parent_dirs(tmp_path):
    path = tmp_path / "sniplingo" / "config.json"
    c = AppConfig(target_lang="ja", region=Region(1, 2, 3, 4), deepl_api_key="k")
    save_config(c, path)
    assert path.exists()
    assert load_config(path) == c


def test_load_missing_returns_defaults(tmp_path):
    assert load_config(tmp_path / "nope.json") == AppConfig()


def test_load_corrupt_json_returns_defaults(tmp_path):
    p = tmp_path / "config.json"
    p.write_text("{ this is not valid json", encoding="utf-8")
    assert load_config(p) == AppConfig()


def test_from_dict_ignores_unknown_keys():
    c = AppConfig.from_dict({"target_lang": "fr", "totally_unknown": 999})
    assert c.target_lang == "fr"
    assert not hasattr(c, "totally_unknown")


def test_from_dict_wrong_types_fall_back_to_defaults():
    c = AppConfig.from_dict({"target_lang": 123, "enable_offline_fallback": "yes"})
    assert c.target_lang == "ja"
    assert c.enable_offline_fallback is True


def test_from_dict_bad_region_becomes_none():
    assert AppConfig.from_dict({"region": "nope"}).region is None
    assert AppConfig.from_dict({"region": {"left": 1}}).region is None  # incomplete


def test_from_dict_non_dict_returns_defaults():
    assert AppConfig.from_dict(["not", "a", "dict"]) == AppConfig()


def test_has_deepl():
    assert AppConfig(deepl_api_key="x").has_deepl is True
    assert AppConfig(deepl_api_key="").has_deepl is False
    assert AppConfig(deepl_api_key=None).has_deepl is False


def test_redacted_masks_key():
    c = AppConfig(deepl_api_key="super-secret")
    red = c.redacted()
    assert "super-secret" not in json.dumps(red)
    assert red["deepl_api_key"] == "****"


def test_redacted_without_key_is_none():
    assert AppConfig().redacted()["deepl_api_key"] is None


def test_default_config_path_uses_appdata(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert default_config_path() == tmp_path / "SnipLingo" / "config.json"
