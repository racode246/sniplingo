"""Entry point: `python -m sniplingo.ui.main` (also the `sniplingo` gui-script)."""

from __future__ import annotations

import sys


def main() -> int:
    from sniplingo.ui.app import run

    return run()


if __name__ == "__main__":
    sys.exit(main())
