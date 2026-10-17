"""Integration: WindowsCredentialStore against the real Windows Credential Manager.

Uses a unique per-run target prefix and deletes everything it wrote.
Run: pytest tests/integration/test_windows_credential_store_real.py -m windows_credential
"""

from __future__ import annotations

import uuid

import pytest

from sniplingo.domain.errors import SecretStoreError

pytestmark = pytest.mark.windows_credential

NAME = "deepl_api_key"


@pytest.fixture
def store():
    from sniplingo.adapters.windows_credential_store import WindowsCredentialStore

    s = WindowsCredentialStore(prefix=f"SnipLingo-test-{uuid.uuid4().hex}")
    yield s
    s.delete(NAME)


def test_missing_secret_reads_as_none(store):
    assert store.get(NAME) is None


def test_set_then_get_roundtrips(store):
    store.set(NAME, "dummy-value-ä日本")
    assert store.get(NAME) == "dummy-value-ä日本"


def test_set_replaces_previous_value(store):
    store.set(NAME, "first")
    store.set(NAME, "second")
    assert store.get(NAME) == "second"


def test_delete_removes_and_tolerates_missing(store):
    store.set(NAME, "value")
    store.delete(NAME)
    assert store.get(NAME) is None
    store.delete(NAME)  # already gone: no error


def test_oversized_value_is_rejected_without_writing(store):
    with pytest.raises(SecretStoreError) as info:
        store.set(NAME, "x" * 5000)
    assert "x" * 50 not in str(info.value)
    assert store.get(NAME) is None


def test_target_names_are_namespaced(store):
    assert store.target(NAME).endswith(f":{NAME}")


def test_win32_failure_raises_with_the_reason():
    from sniplingo.adapters.windows_credential_store import WindowsCredentialStore

    too_long = WindowsCredentialStore(prefix="x" * 40000)  # > CRED_MAX_GENERIC_TARGET_NAME
    with pytest.raises(SecretStoreError) as info:
        too_long.set(NAME, "secret-value")
    assert "Win32" in str(info.value)
    assert "secret-value" not in str(info.value)
