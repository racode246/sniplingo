"""SecretStore backed by the Windows Credential Manager (``advapi32`` Cred* API via ctypes).

Each key is a *generic* credential named ``SnipLingo:<field>`` (visible and removable in
Control Panel > Credential Manager > Windows Credentials). Windows encrypts the blob with
DPAPI for the logged-on user, so a copied file or another account can't read it.
``CRED_PERSIST_LOCAL_MACHINE`` keeps it on this PC (it does not roam with the profile).

Errors become :class:`SecretStoreError` with the Win32 reason (never the value).
"""

from __future__ import annotations

import ctypes
import functools
from ctypes import wintypes

from sniplingo.domain.errors import SecretStoreError

_CRED_TYPE_GENERIC = 1
_CRED_PERSIST_LOCAL_MACHINE = 2
_CRED_MAX_CREDENTIAL_BLOB_SIZE = 5 * 512
_ERROR_NOT_FOUND = 1168
_ENCODING = "utf-16-le"  # what cmdkey / other Windows tools use for generic blobs


class _CREDENTIALW(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


_PCREDENTIALW = ctypes.POINTER(_CREDENTIALW)


@functools.cache
def _advapi32() -> ctypes.WinDLL:
    """Load and type the Cred* functions once (lazily, so importing never fails)."""
    dll = ctypes.WinDLL("advapi32", use_last_error=True)
    dll.CredWriteW.argtypes = [_PCREDENTIALW, wintypes.DWORD]
    dll.CredWriteW.restype = wintypes.BOOL
    dll.CredReadW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(_PCREDENTIALW),
    ]
    dll.CredReadW.restype = wintypes.BOOL
    dll.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    dll.CredDeleteW.restype = wintypes.BOOL
    dll.CredFree.argtypes = [ctypes.c_void_p]
    dll.CredFree.restype = None
    return dll


def _win_error(code: int) -> SecretStoreError:
    return SecretStoreError(
        f"資格情報マネージャー: {ctypes.FormatError(code).strip()} (Win32 {code})"
    )


class WindowsCredentialStore:
    def __init__(self, prefix: str = "SnipLingo") -> None:
        self._prefix = prefix

    def target(self, name: str) -> str:
        """The Credential Manager target name used for `name`."""
        return f"{self._prefix}:{name}"

    def get(self, name: str) -> str | None:
        api = _advapi32()
        pcred = _PCREDENTIALW()
        if not api.CredReadW(self.target(name), _CRED_TYPE_GENERIC, 0, ctypes.byref(pcred)):
            code = ctypes.get_last_error()
            if code == _ERROR_NOT_FOUND:
                return None
            raise _win_error(code)
        try:
            cred = pcred.contents
            if not cred.CredentialBlobSize:
                return None
            blob = ctypes.string_at(cred.CredentialBlob, cred.CredentialBlobSize)
            return blob.decode(_ENCODING)
        except UnicodeDecodeError:
            raise SecretStoreError("資格情報マネージャー: 保存された値を読み取れません") from None
        finally:
            api.CredFree(pcred)

    def set(self, name: str, value: str) -> None:
        blob = value.encode(_ENCODING)
        if len(blob) > _CRED_MAX_CREDENTIAL_BLOB_SIZE:
            raise SecretStoreError(
                f"資格情報マネージャー: 値が長すぎます"
                f"（{len(blob)} バイト、上限 {_CRED_MAX_CREDENTIAL_BLOB_SIZE} バイト）"
            )
        buffer = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
        cred = _CREDENTIALW()
        cred.Type = _CRED_TYPE_GENERIC
        cred.TargetName = self.target(name)
        cred.Comment = "SnipLingo API key"
        cred.CredentialBlobSize = len(blob)
        cred.CredentialBlob = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))
        cred.Persist = _CRED_PERSIST_LOCAL_MACHINE
        cred.UserName = self._prefix
        try:
            if not _advapi32().CredWriteW(ctypes.byref(cred), 0):
                raise _win_error(ctypes.get_last_error())
        finally:
            ctypes.memset(buffer, 0, len(blob))  # don't leave a copy in our heap

    def delete(self, name: str) -> None:
        if not _advapi32().CredDeleteW(self.target(name), _CRED_TYPE_GENERIC, 0):
            code = ctypes.get_last_error()
            if code != _ERROR_NOT_FOUND:
                raise _win_error(code)
