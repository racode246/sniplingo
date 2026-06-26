"""Modal dialog for translation settings (default backend, API keys, Gemini model).

Thin shell: it collects user input into a :class:`SettingsForm` and the caller
applies it via :func:`core.settings_update.apply_settings`. Secret inputs use
``QLineEdit.EchoMode.Password`` and are never pre-filled — a "(設定済み)" label
shows that a key is saved, and a "クリア" button explicitly removes it.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from sniplingo.core.config import AppConfig
from sniplingo.core.settings_update import SettingsForm
from sniplingo.domain.models import BackendName

_BACKEND_LABELS: list[tuple[str, str]] = [
    (BackendName.GOOGLE_FREE.value, "Google 無料 (既定・キー不要)"),
    (BackendName.ARGOS.value, "Argos オフライン"),
    (BackendName.DEEPL.value, "DeepL (キー必要)"),
    (BackendName.GEMINI.value, "Gemini (キー必要)"),
]


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("翻訳設定")
        self.setModal(True)
        self._deepl_clear = False
        self._gemini_clear = False
        self._deepl_has_existing = config.has_deepl
        self._gemini_has_existing = config.has_gemini

        outer = QVBoxLayout(self)
        form = QFormLayout()
        outer.addLayout(form)

        # --- backend selection -------------------------------------------------------
        self._backend = QComboBox()
        for value, label in _BACKEND_LABELS:
            self._backend.addItem(label, userData=value)
        self._select_backend(config.default_backend)
        form.addRow("既定バックエンド", self._backend)

        self._offline_fallback = QCheckBox("失敗時は Argos オフラインへフォールバック")
        self._offline_fallback.setChecked(config.enable_offline_fallback)
        form.addRow("", self._offline_fallback)

        # --- DeepL -------------------------------------------------------------------
        self._deepl_key = QLineEdit()
        self._deepl_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._deepl_key.setPlaceholderText("(未入力なら現在の値を保持)")
        self._deepl_status, deepl_row = self._key_row(
            line_edit=self._deepl_key,
            has_existing=config.has_deepl,
            on_clear=self._on_deepl_clear,
        )
        form.addRow("DeepL APIキー", deepl_row)
        form.addRow("", self._deepl_status)

        # --- Gemini ------------------------------------------------------------------
        self._gemini_key = QLineEdit()
        self._gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._gemini_key.setPlaceholderText("(未入力なら現在の値を保持)")
        self._gemini_status, gemini_row = self._key_row(
            line_edit=self._gemini_key,
            has_existing=config.has_gemini,
            on_clear=self._on_gemini_clear,
        )
        form.addRow("Gemini APIキー", gemini_row)
        form.addRow("", self._gemini_status)

        self._gemini_model = QLineEdit(config.gemini_model)
        self._gemini_model.setPlaceholderText("gemini-2.5-flash")
        form.addRow("Gemini モデル", self._gemini_model)

        # --- OK / Cancel -------------------------------------------------------------
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def _key_row(
        self, line_edit: QLineEdit, has_existing: bool, on_clear
    ) -> tuple[QLabel, QWidget]:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(line_edit, stretch=1)
        clear_btn = QPushButton("クリア")
        clear_btn.setEnabled(has_existing)

        status = QLabel(self._status_text(has_existing, cleared=False))

        def handle_clear() -> None:
            line_edit.clear()
            clear_btn.setEnabled(False)
            on_clear(status)

        clear_btn.clicked.connect(handle_clear)
        row.addWidget(clear_btn)
        return status, container

    @staticmethod
    def _status_text(has_existing: bool, cleared: bool) -> str:
        if cleared:
            return "クリア予定 (保存時に削除)"
        return "(設定済み)" if has_existing else "(未設定)"

    def _on_deepl_clear(self, status: QLabel) -> None:
        self._deepl_clear = True
        status.setText(self._status_text(self._deepl_has_existing, cleared=True))

    def _on_gemini_clear(self, status: QLabel) -> None:
        self._gemini_clear = True
        status.setText(self._status_text(self._gemini_has_existing, cleared=True))

    def _select_backend(self, value: str) -> None:
        index = self._backend.findData(value)
        if index >= 0:
            self._backend.setCurrentIndex(index)

    def form_values(self) -> SettingsForm:
        """Snapshot the current widget state into a SettingsForm."""
        return SettingsForm(
            default_backend=self._backend.currentData(),
            enable_offline_fallback=self._offline_fallback.isChecked(),
            deepl_key_input=self._deepl_key.text(),
            deepl_clear=self._deepl_clear,
            gemini_key_input=self._gemini_key.text(),
            gemini_clear=self._gemini_clear,
            gemini_model=self._gemini_model.text(),
        )
