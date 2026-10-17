"""Port: keep API keys in an OS-protected credential store instead of config.json."""

from __future__ import annotations

from typing import Protocol


class SecretStore(Protocol):
    def get(self, name: str) -> str | None:
        """The secret stored under `name`, or ``None`` if there is none.

        Raise :class:`sniplingo.domain.errors.SecretStoreError` if the store can't be read.
        """
        ...

    def set(self, name: str, value: str) -> None:
        """Store `value` under `name`, replacing any previous value.

        Raise :class:`sniplingo.domain.errors.SecretStoreError` on failure; the previous
        value (if any) must then be left untouched.
        """
        ...

    def delete(self, name: str) -> None:
        """Remove the secret under `name`. Deleting a missing secret is not an error.

        Raise :class:`sniplingo.domain.errors.SecretStoreError` on failure.
        """
        ...
