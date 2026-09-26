import dataclasses
import json

import pytest

from sniplingo.core.config import AppConfig, default_config_path, load_config, save_config
from sniplingo.domain.models import BackendName, Region


def test_defaults():
    c = AppConfig()
    assert c.source_lang == "en"
    assert c.target_lang == "ja"
    assert c.select_region_hotkey == "<ctrl>+<alt>+r"
    assert c.default_backend is BackendName.GOOGLE_FREE
    assert c.overlay_position is None
    assert c.deepl_api_key is None
    assert c.gemini_api_key is None
    assert c.gemini_model == "gemini-2.5-flash"
    assert c.region is None
    assert c.has_deepl is False
    assert c.has_gemini is False
    assert c.capture_padding == 8
    assert c.ocr_scale == 2


def test_to_from_dict_roundtrip():
    c = AppConfig(
        source_lang="en",
        target_lang="ja",
        select_region_hotkey="<ctrl>+<shift>+r",
        default_backend="gemini",
        deepl_api_key="secret-key",
        gemini_api_key="gemini-secret",
        gemini_model="gemini-2.5-flash-lite",
        region=Region(10, 20, 30, 40),
        overlay_position=(120, 80),
    )
    assert AppConfig.from_dict(c.to_dict()) == c


def test_capture_padding_roundtrips():
    c = AppConfig(capture_padding=12)
    assert AppConfig.from_dict(c.to_dict()).capture_padding == 12


def test_capture_padding_wrong_type_falls_back_to_default():
    assert AppConfig.from_dict({"capture_padding": "lots"}).capture_padding == 8
    # bool is an int subclass but must not be accepted as a padding value
    assert AppConfig.from_dict({"capture_padding": True}).capture_padding == 8


def test_ocr_scale_roundtrips():
    c = AppConfig(ocr_scale=3)
    assert AppConfig.from_dict(c.to_dict()).ocr_scale == 3


def test_ocr_scale_wrong_type_falls_back_to_default():
    assert AppConfig.from_dict({"ocr_scale": "big"}).ocr_scale == 2
    assert AppConfig.from_dict({"ocr_scale": True}).ocr_scale == 2


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
    c = AppConfig.from_dict({"target_lang": 123, "overlay_opacity": "opaque"})
    assert c.target_lang == "ja"
    assert c.overlay_opacity == 0.85


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


def test_has_gemini():
    assert AppConfig(gemini_api_key="x").has_gemini is True
    assert AppConfig(gemini_api_key="").has_gemini is False
    assert AppConfig(gemini_api_key=None).has_gemini is False


def test_redacted_masks_gemini_key():
    c = AppConfig(gemini_api_key="super-gemini-secret")
    red = c.redacted()
    assert "super-gemini-secret" not in json.dumps(red)
    assert red["gemini_api_key"] == "****"


def test_redacted_without_gemini_key_is_none():
    assert AppConfig().redacted()["gemini_api_key"] is None


def test_gemini_model_default_when_blank():
    """A blank/invalid model string in config falls back to the default."""
    c = AppConfig.from_dict({"gemini_model": ""})
    assert c.gemini_model == "gemini-2.5-flash"
    c2 = AppConfig.from_dict({"gemini_model": 123})
    assert c2.gemini_model == "gemini-2.5-flash"


def test_default_config_path_uses_appdata(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert default_config_path() == tmp_path / "SnipLingo" / "config.json"


# --- immutability / generic field handling -------------------------------------------


def test_config_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        AppConfig().region = Region(0, 0, 1, 1)  # type: ignore[misc]


def test_to_dict_covers_every_field():
    """Adding a dataclass field must be enough — no hand-maintained key list."""
    assert set(AppConfig().to_dict()) == {f.name for f in dataclasses.fields(AppConfig)}


def test_to_dict_is_json_serializable_with_enum_backend():
    data = json.loads(json.dumps(AppConfig(default_backend=BackendName.GEMINI).to_dict()))
    assert data["default_backend"] == "gemini"
    assert AppConfig.from_dict(data).default_backend is BackendName.GEMINI


def test_redacted_masks_every_secret_and_keeps_the_rest():
    c = AppConfig(deepl_api_key="d-secret", gemini_api_key="g-secret", target_lang="fr")
    red = c.redacted()
    assert red["deepl_api_key"] == "****" and red["gemini_api_key"] == "****"
    assert red["target_lang"] == "fr"


# --- validation: values of the right type but out of range fall back to defaults ---


def test_removed_argos_backend_falls_back_to_google_free():
    assert AppConfig.from_dict({"default_backend": "argos"}).default_backend is (
        BackendName.GOOGLE_FREE
    )


def test_legacy_offline_fallback_key_is_ignored():
    c = AppConfig.from_dict({"enable_offline_fallback": True})
    assert not hasattr(c, "enable_offline_fallback")


@pytest.mark.parametrize(
    "key,value",
    [
        ("overlay_opacity", 5.0),
        ("overlay_opacity", 0.0),
        ("capture_padding", -3),
        ("capture_padding", 1000),
        ("ocr_scale", 0),
        ("ocr_scale", 9),
        ("source_lang", "  "),
        ("target_lang", ""),
        ("select_region_hotkey", "nope"),
    ],
)
def test_out_of_range_values_fall_back_to_default(key, value):
    assert getattr(AppConfig.from_dict({key: value}), key) == getattr(AppConfig(), key)


@pytest.mark.parametrize(
    "key,value",
    [("overlay_opacity", 0.3), ("capture_padding", 0), ("ocr_scale", 4), ("ocr_scale", 1)],
)
def test_in_range_values_are_kept(key, value):
    assert getattr(AppConfig.from_dict({key: value}), key) == value


def test_empty_region_is_dropped():
    assert (
        AppConfig.from_dict({"region": {"left": 0, "top": 0, "width": 0, "height": 5}}).region
        is None
    )


def test_secrets_lists_only_configured_keys():
    assert AppConfig().secrets() == []
    assert AppConfig(deepl_api_key="d", gemini_api_key="g").secrets() == ["d", "g"]
