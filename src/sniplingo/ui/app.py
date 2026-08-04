"""Composition root: build adapters, wire signals, run the Qt event loop.

This is the ONLY place dependencies are constructed and connected (see
`.claude/rules/architecture.md`). Everything else receives its collaborators.

Flow: pick a region (hotkey or tray) -> it is translated automatically -> the result
is shown in a draggable overlay. There is no separate translate hotkey.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QLockFile, QObject, QRect, Qt
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from sniplingo.adapters.argos_backend import ArgosTranslator
from sniplingo.adapters.deep_translator_backend import GoogleFreeTranslator
from sniplingo.adapters.deepl_backend import DeepLTranslator
from sniplingo.adapters.gemini_backend import GeminiTranslator
from sniplingo.adapters.mss_capturer import MssCapturer
from sniplingo.adapters.winrt_ocr import WinRtOcrEngine
from sniplingo.core.config import AppConfig, default_config_path, load_config, save_config
from sniplingo.core.pipeline import TranslationPipeline
from sniplingo.core.settings_update import apply_settings
from sniplingo.core.translator_chain import TranslatorChain
from sniplingo.domain.models import BackendName, Region
from sniplingo.ports.image_translate import ImageTranslator
from sniplingo.ui.hotkey import GlobalHotkey
from sniplingo.ui.hotkey_dialog import HotkeyCaptureDialog
from sniplingo.ui.overlay_window import OverlayWindow
from sniplingo.ui.region_selector import RegionSelector
from sniplingo.ui.settings_dialog import SettingsDialog
from sniplingo.ui.tray import Tray
from sniplingo.ui.worker import PipelineRunner

_OCR_INSTALL_CMD = 'Add-WindowsCapability -Online -Name "Language.OCR~~~en-US~0.0.1.0"'


def _pretty_hotkey(combo: str) -> str:
    """Render a pynput combo for display: ``<ctrl>+<alt>+r`` -> ``Ctrl+Alt+R``."""
    parts = []
    for raw in combo.split("+"):
        token = raw.strip().strip("<>")
        parts.append(token.upper() if len(token) == 1 else token.capitalize())
    return "+".join(parts)


def build_translator_chain(config: AppConfig):
    """Primary backend per config, with Argos offline fallback when enabled.

    Keyed backends (DeepL, Gemini) require their key in config; without the key
    the request silently falls through to the default Google free endpoint.

    When Gemini is the chosen primary AND Vision is wired up (see
    :func:`_build_image_translator`), this text chain is the **fallback** path,
    so we deliberately skip Gemini here — it would just hit the same rate limit
    that the Vision call hit. Google free becomes the text primary instead.
    """

    def make(name: str):
        if name == BackendName.DEEPL.value and config.has_deepl:
            return DeepLTranslator(config.deepl_api_key or "")
        if name == BackendName.GEMINI.value and config.has_gemini:
            return GeminiTranslator(config.gemini_api_key or "", model=config.gemini_model)
        if name == BackendName.ARGOS.value:
            return ArgosTranslator()
        return GoogleFreeTranslator()

    text_primary_name = config.default_backend
    if text_primary_name == BackendName.GEMINI.value and config.has_gemini:
        # Gemini handles the primary attempt via Vision; don't re-try it as text.
        text_primary_name = BackendName.GOOGLE_FREE.value

    primary = make(text_primary_name)
    fallbacks = []
    if config.enable_offline_fallback and text_primary_name != BackendName.ARGOS.value:
        fallbacks.append(ArgosTranslator())
    return TranslatorChain(primary, fallbacks, retries=1, backoff_seconds=0.5)


def _build_image_translator(config: AppConfig) -> ImageTranslator | None:
    """Enable the Vision (image-direct) path only when Gemini is the chosen primary.

    LLMs can do OCR + translation in one round-trip, which is faster and more
    accurate than Windows OCR + text translate. The text-based :class:`TranslatorChain`
    above still runs as a fallback if the Vision call fails.
    """
    if config.default_backend == BackendName.GEMINI.value and config.has_gemini:
        return GeminiTranslator(config.gemini_api_key or "", model=config.gemini_model)
    return None


class Application(QObject):
    def __init__(self, config: AppConfig, config_path) -> None:
        super().__init__()
        self._config = config
        self._config_path = config_path
        self._region: Region | None = config.region

        self._ocr = WinRtOcrEngine(scale=config.ocr_scale)
        self._capturer = MssCapturer()
        self._runner = PipelineRunner(self._build_pipeline(config))
        self._overlay = OverlayWindow(config.overlay_opacity)
        self._selector = RegionSelector()
        self._tray = Tray()
        self._hotkey = GlobalHotkey(config.select_region_hotkey)

        self._wire()

    def _wire(self) -> None:
        queued = Qt.ConnectionType.QueuedConnection
        self._hotkey.bridge.triggered.connect(self._selector.start, queued)
        self._tray.select_region_requested.connect(self._selector.start)
        self._tray.translate_now_requested.connect(self._on_translate_now)
        self._tray.set_hotkey_requested.connect(self._on_set_hotkey)
        self._tray.settings_requested.connect(self._on_open_settings)
        self._tray.quit_requested.connect(self._quit)
        self._selector.selected.connect(self._on_region_selected)
        self._overlay.moved.connect(self._on_overlay_moved)
        self._runner.finished.connect(self._on_result)
        self._runner.failed.connect(self._on_failed)

    def _build_pipeline(self, config: AppConfig) -> TranslationPipeline:
        return TranslationPipeline(
            self._capturer,
            self._ocr,
            build_translator_chain(config),
            source=config.source_lang,
            target=config.target_lang,
            image_translator=_build_image_translator(config),
            capture_padding=config.capture_padding,
        )

    def start(self) -> None:
        # No startup notification on purpose. Only surface actionable problems below.
        try:
            self._hotkey.start()
        except Exception:  # noqa: BLE001 - hotkey is optional; tray still works
            self._tray.notify("ホットキー登録失敗", "トレイメニューから操作してください。")
        if not self._ocr.is_language_available(self._config.source_lang):
            self._tray.notify(
                "OCR言語パック未導入",
                f"管理者PowerShellで次を実行してください: {_OCR_INSTALL_CMD}",
            )

    # --- slots -------------------------------------------------------------------

    def _on_region_selected(self, region: Region) -> None:
        self._region = region
        self._config.region = region
        self._save_config()
        self._runner.submit(region)  # selecting a region translates it automatically

    def _on_translate_now(self) -> None:
        if self._region is None:
            self._tray.notify("範囲が未選択", "先に「範囲を選択して翻訳」してください。")
            self._selector.start()
            return
        self._runner.submit(self._region)

    def _on_result(self, result) -> None:
        if result.error == "no_text":
            self._tray.set_status("テキストなし")
            return
        if not result.ok:
            self._tray.set_status("失敗")
            # Adapter-level errors carry no secrets (see `.claude/rules/secrets.md`),
            # so it's safe to surface them — they're the fastest path to a diagnosis.
            detail = result.error or "ネットワーク/バックエンドを確認してください。"
            self._tray.notify("翻訳に失敗", detail)
            return
        self._tray.set_status(result.backend)
        if self._region is not None:
            anchor = QRect(
                self._region.left, self._region.top, self._region.width, self._region.height
            )
            self._overlay.show_translation(
                result.translated_text, anchor, self._config.overlay_position
            )

    def _on_overlay_moved(self, x: int, y: int) -> None:
        self._config.overlay_position = (x, y)
        self._save_config()

    def _on_failed(self, message: str) -> None:
        self._tray.set_status("エラー")
        self._tray.notify("エラー", message)

    def _on_open_settings(self) -> None:
        dialog = SettingsDialog(self._config)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        new_config = apply_settings(self._config, dialog.form_values())
        self._config = new_config
        self._save_config()
        # Rebuild the chain + pipeline so the change takes effect for the next run.
        self._runner.set_pipeline(self._build_pipeline(new_config))
        self._tray.notify("翻訳設定", "保存しました。次の翻訳から有効になります。")

    def _on_set_hotkey(self) -> None:
        self._hotkey.stop()  # don't trigger selection while capturing keys
        dialog = HotkeyCaptureDialog(self._config.select_region_hotkey)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        combo = dialog.hotkey()
        if accepted and combo:
            try:
                self._hotkey.set_combo(combo)
            except ValueError:
                self._tray.notify("ショートカット設定", "無効な組み合わせです。")
            else:
                self._config.select_region_hotkey = combo
                self._save_config()
                self._tray.notify(
                    "ショートカット設定", f"範囲選択を {_pretty_hotkey(combo)} に変更しました。"
                )
        try:
            self._hotkey.start()
        except Exception:  # noqa: BLE001 - hotkey is optional; tray still works
            self._tray.notify("ホットキー登録失敗", "トレイメニューから操作してください。")

    def _save_config(self) -> None:
        try:
            save_config(self._config, self._config_path)
        except OSError:
            pass  # not fatal; settings stay active for this session

    def _quit(self) -> None:
        self._hotkey.stop()
        self._runner.shutdown()
        QApplication.quit()


def run() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # live in the tray, not tied to a window

    config_path = default_config_path()

    # Single-instance guard. Two instances both hook the global hotkey (pynput uses a
    # low-level keyboard hook, not RegisterHotKey), so both would show a full-screen
    # selection overlay — only the front one gets the mouse, leaving the other's dim
    # layer stuck on screen until it is clicked.
    config_path.parent.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(config_path.parent / "sniplingo.lock"))
    if not lock.tryLock(0):
        QMessageBox.information(
            None,
            "SnipLingo",
            "SnipLingo は既に起動しています。タスクトレイのアイコンから操作してください。",
        )
        return 0

    config = load_config(config_path)

    application = Application(config, config_path)
    application.start()
    return app.exec()
