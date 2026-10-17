"""Tests for moving API keys between AppConfig and the OS credential store (fake store)."""

from tests.fakes import FakeSecretStore

from sniplingo.core.config import SECRET_FIELDS, AppConfig
from sniplingo.core.secret_sync import SECRET_LABELS, load_secrets, persist_secrets
from sniplingo.domain.models import BackendName

# --- load_secrets (startup) ----------------------------------------------------------


def test_load_reads_every_key_from_the_store():
    store = FakeSecretStore(
        {"google_cloud_api_key": "c", "deepl_api_key": "d", "gemini_api_key": "g"}
    )
    sync = load_secrets(AppConfig(target_lang="fr"), store)
    assert sync.config == AppConfig(
        target_lang="fr", google_cloud_api_key="c", deepl_api_key="d", gemini_api_key="g"
    )
    assert sync.errors == ()
    assert sync.stored == frozenset()
    assert sync.failed == frozenset()


def test_load_with_empty_store_yields_no_keys():
    sync = load_secrets(AppConfig(), FakeSecretStore())
    assert sync.config.secrets() == []
    assert sync.errors == ()


def test_load_migrates_legacy_plaintext_key_into_the_store():
    store = FakeSecretStore()
    sync = load_secrets(AppConfig(deepl_api_key="legacy-d"), store)
    assert store.secrets == {"deepl_api_key": "legacy-d"}
    assert sync.config.deepl_api_key == "legacy-d"
    assert sync.stored == frozenset({"deepl_api_key"})
    assert sync.errors == ()


def test_load_legacy_key_wins_over_the_stored_one():
    store = FakeSecretStore({"deepl_api_key": "stored"})
    sync = load_secrets(AppConfig(deepl_api_key="legacy"), store)
    assert store.secrets["deepl_api_key"] == "legacy"
    assert sync.config.deepl_api_key == "legacy"


def test_load_failed_migration_drops_the_key_and_reports_why():
    store = FakeSecretStore(fail_on={("set", "deepl_api_key")}, reason="access denied")
    sync = load_secrets(AppConfig(deepl_api_key="legacy-d"), store)
    assert sync.config.deepl_api_key is None  # not kept in memory
    assert sync.failed == frozenset({"deepl_api_key"})
    assert sync.stored == frozenset()
    (error,) = sync.errors
    assert "DeepL" in error and "access denied" in error and "config.json" in error
    assert "legacy-d" not in error


def test_load_read_failure_drops_the_key_and_reports_why():
    store = FakeSecretStore(fail_on={("get", "gemini_api_key")}, reason="service stopped")
    sync = load_secrets(AppConfig(), store)
    assert sync.config.gemini_api_key is None
    assert sync.failed == frozenset({"gemini_api_key"})
    (error,) = sync.errors
    assert "Gemini" in error and "service stopped" in error


def test_load_one_failure_does_not_stop_the_other_keys():
    store = FakeSecretStore(
        {"google_cloud_api_key": "c", "gemini_api_key": "g"},
        fail_on={("get", "google_cloud_api_key")},
    )
    sync = load_secrets(AppConfig(deepl_api_key="legacy-d"), store)
    assert sync.config.google_cloud_api_key is None
    assert sync.config.deepl_api_key == "legacy-d"
    assert sync.config.gemini_api_key == "g"
    assert sync.failed == frozenset({"google_cloud_api_key"})
    assert sync.stored == frozenset({"deepl_api_key"})


def test_load_touches_only_secret_fields():
    store = FakeSecretStore()
    load_secrets(AppConfig(), store)
    assert {name for _, name in store.calls} == set(SECRET_FIELDS)


# --- persist_secrets (settings dialog saved) ------------------------------------------


def test_persist_unchanged_keys_does_not_touch_the_store():
    current = AppConfig(deepl_api_key="d")
    store = FakeSecretStore({"deepl_api_key": "d"})
    sync = persist_secrets(current, current, store)
    assert store.calls == []
    assert sync.config == current
    assert sync.errors == ()


def test_persist_writes_a_new_key():
    store = FakeSecretStore()
    sync = persist_secrets(AppConfig(), AppConfig(google_cloud_api_key="new"), store)
    assert store.secrets == {"google_cloud_api_key": "new"}
    assert sync.config.google_cloud_api_key == "new"
    assert sync.stored == frozenset({"google_cloud_api_key"})


def test_persist_deletes_a_cleared_key():
    store = FakeSecretStore({"gemini_api_key": "old"})
    sync = persist_secrets(AppConfig(gemini_api_key="old"), AppConfig(), store)
    assert store.secrets == {}
    assert sync.config.gemini_api_key is None
    assert sync.stored == frozenset({"gemini_api_key"})


def test_persist_write_failure_keeps_the_previous_key_and_reports_why():
    """The new key is not held in memory: config keeps what the store still has."""
    store = FakeSecretStore(
        {"deepl_api_key": "old"}, fail_on={("set", "deepl_api_key")}, reason="access denied"
    )
    sync = persist_secrets(
        AppConfig(deepl_api_key="old"), AppConfig(deepl_api_key="new-deepl-secret"), store
    )
    assert sync.config.deepl_api_key == "old"
    assert sync.failed == frozenset({"deepl_api_key"})
    assert sync.stored == frozenset()
    (error,) = sync.errors
    assert "DeepL" in error and "access denied" in error
    assert "new-deepl-secret" not in error


def test_persist_write_failure_without_previous_key_leaves_none():
    store = FakeSecretStore(fail_on={("set", "google_cloud_api_key")})
    sync = persist_secrets(AppConfig(), AppConfig(google_cloud_api_key="new"), store)
    assert sync.config.google_cloud_api_key is None


def test_persist_delete_failure_keeps_the_key_and_reports_why():
    store = FakeSecretStore(
        {"gemini_api_key": "old"}, fail_on={("delete", "gemini_api_key")}, reason="locked"
    )
    sync = persist_secrets(AppConfig(gemini_api_key="old"), AppConfig(), store)
    assert sync.config.gemini_api_key == "old"
    (error,) = sync.errors
    assert "Gemini" in error and "locked" in error


def test_persist_keeps_non_secret_changes_even_when_a_key_fails():
    store = FakeSecretStore(fail_on={("set", "deepl_api_key")})
    sync = persist_secrets(
        AppConfig(),
        AppConfig(default_backend=BackendName.DEEPL, deepl_api_key="d", gemini_api_key="g"),
        store,
    )
    assert sync.config.default_backend is BackendName.DEEPL
    assert sync.config.deepl_api_key is None
    assert sync.config.gemini_api_key == "g"
    assert sync.stored == frozenset({"gemini_api_key"})
    assert sync.failed == frozenset({"deepl_api_key"})


def test_every_secret_field_has_a_user_facing_label():
    assert set(SECRET_LABELS) == set(SECRET_FIELDS)
