"""Move API keys between :class:`AppConfig` and the OS credential store.

``config.json`` never holds keys (see :func:`core.config.save_config`); the
:class:`~sniplingo.ports.secret_store.SecretStore` does. Invariant: after every sync the
keys in the returned config are exactly what the store holds. A key the store could not
accept is **not** kept in memory — the user gets the reason and re-enters it.

- :func:`load_secrets` (startup) reads keys from the store. A key still present in the
  loaded config is a legacy plaintext value from ``config.json``: it is moved into the
  store (and wins over any stored value, since older versions only wrote the file).
- :func:`persist_secrets` (settings saved) writes changed keys and deletes cleared ones.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from sniplingo.core.config import SECRET_FIELDS, AppConfig
from sniplingo.domain.errors import SecretStoreError
from sniplingo.ports.secret_store import SecretStore

SECRET_LABELS: dict[str, str] = {
    "google_cloud_api_key": "Google Cloud APIキー",
    "deepl_api_key": "DeepL APIキー",
    "gemini_api_key": "Gemini APIキー",
}


@dataclass(frozen=True)
class SecretSync:
    """Outcome of a sync. `errors` are user-facing reasons and never contain a key."""

    config: AppConfig
    stored: frozenset[str] = frozenset()  # fields written to / deleted from the store
    failed: frozenset[str] = frozenset()  # fields whose store operation failed
    errors: tuple[str, ...] = ()


def load_secrets(config: AppConfig, store: SecretStore) -> SecretSync:
    """Fill `config`'s keys from `store`, migrating legacy plaintext keys into it."""
    values: dict[str, str | None] = {}
    stored: set[str] = set()
    failed: set[str] = set()
    errors: list[str] = []
    for name in SECRET_FIELDS:
        label = SECRET_LABELS[name]
        legacy = getattr(config, name)
        try:
            if legacy:
                store.set(name, legacy)
                stored.add(name)
                values[name] = legacy
            else:
                values[name] = store.get(name)
        except SecretStoreError as exc:
            values[name] = None
            failed.add(name)
            if legacy:
                errors.append(
                    f"{label}を安全な保管先へ移行できませんでした"
                    f"（config.json に残しています）: {exc}"
                )
            else:
                errors.append(f"{label}を読み込めませんでした: {exc}")
    return SecretSync(
        replace(config, **values), frozenset(stored), frozenset(failed), tuple(errors)
    )


def persist_secrets(current: AppConfig, updated: AppConfig, store: SecretStore) -> SecretSync:
    """Store `updated`'s changed keys; a failed key keeps its `current` value."""
    values: dict[str, str | None] = {}
    stored: set[str] = set()
    failed: set[str] = set()
    errors: list[str] = []
    for name in SECRET_FIELDS:
        old, new = getattr(current, name), getattr(updated, name)
        if old == new:
            continue
        label = SECRET_LABELS[name]
        try:
            if new:
                store.set(name, new)
            else:
                store.delete(name)
        except SecretStoreError as exc:
            values[name] = old
            failed.add(name)
            action = "保存" if new else "削除"
            errors.append(f"{label}を{action}できませんでした: {exc}")
        else:
            stored.add(name)
    return SecretSync(
        replace(updated, **values), frozenset(stored), frozenset(failed), tuple(errors)
    )
