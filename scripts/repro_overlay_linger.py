"""Reproduce: does the RegionSelector's dim overlay leave the screen after a REAL drag?

Unlike QTest-synthesized events, this drives the actual OS input path with pynput
(real mouse move/press/release), which exercises implicit grabs and the Windows
message pump. Screen pixels are then measured with mss to see whether the dim
layer is still composited after dismissal.
"""

from __future__ import annotations

import statistics
import sys
import threading
import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from sniplingo.ui.region_selector import RegionSelector


def screen_brightness(points: list[tuple[int, int]]) -> float:
    import mss

    with mss.mss() as sct:
        vals = []
        for x, y in points:
            img = sct.grab({"left": x, "top": y, "width": 4, "height": 4})
            px = img.pixel(0, 0)
            vals.append(sum(px) / 3)
    return statistics.mean(vals)


def real_drag(x1: int, y1: int, x2: int, y2: int) -> None:
    from pynput.mouse import Button, Controller

    mouse = Controller()
    mouse.position = (x1, y1)
    time.sleep(0.15)
    mouse.press(Button.left)
    time.sleep(0.15)
    for i in range(1, 11):  # move in steps so Qt sees a drag, not a jump
        mouse.position = (x1 + (x2 - x1) * i // 10, y1 + (y2 - y1) * i // 10)
        time.sleep(0.02)
    time.sleep(0.1)
    mouse.release(Button.left)


def main() -> int:
    app = QApplication(sys.argv)
    sel = RegionSelector()
    outcome: dict[str, object] = {}

    sel.selected.connect(lambda r: outcome.setdefault("signal", ("selected", r)))
    sel.cancelled.connect(lambda: outcome.setdefault("signal", ("cancelled",)))

    points = [(200, 200), (900, 500), (1400, 300)]
    outcome["baseline"] = screen_brightness(points)

    sel.start()

    def after_shown() -> None:
        outcome["shown"] = screen_brightness(points)
        threading.Thread(target=lambda: real_drag(400, 400, 700, 550), daemon=True).start()

        def poll() -> None:
            if "signal" in outcome or outcome.get("polls", 0) > 40:
                QTimer.singleShot(400, finish)
                return
            outcome["polls"] = outcome.get("polls", 0) + 1
            QTimer.singleShot(100, poll)

        poll()

    def finish() -> None:
        outcome["after"] = screen_brightness(points)
        outcome["visible_after"] = sel.isVisible()
        app.quit()

    QTimer.singleShot(600, after_shown)
    app.exec()

    base, shown, after = outcome["baseline"], outcome["shown"], outcome["after"]
    print(f"baseline brightness      : {base:.1f}")
    print(f"overlay shown brightness : {shown:.1f}  (should be darker)")
    print(f"after dismiss brightness : {after:.1f}  (should match baseline)")
    print(f"isVisible after          : {outcome['visible_after']}")
    print(f"signal                   : {outcome.get('signal')}")
    dimmed = shown < base - 8
    restored = abs(after - base) < 8
    print(f"verdict: dim_applied={dimmed} dim_removed={restored}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
