"""Architecture guard: the pure layers must not import framework / I/O libraries.

Walks every module under `domain` and `core` and asserts none import the forbidden
top-level packages. See `.claude/rules/architecture.md`.
"""

import ast
from pathlib import Path

import pytest

FORBIDDEN = {
    "PySide6",
    "winrt",
    "mss",
    "pynput",
    "deep_translator",
    "argostranslate",
    "requests",
}

_SRC = Path(__file__).resolve().parents[2] / "src" / "sniplingo"


def _imported_top_level_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module.split(".")[0])
    return modules


@pytest.mark.parametrize("layer", ["domain", "core"])
def test_pure_layers_have_no_forbidden_imports(layer):
    offenders: dict[str, set[str]] = {}
    for py in (_SRC / layer).rglob("*.py"):
        bad = _imported_top_level_modules(py) & FORBIDDEN
        if bad:
            offenders[str(py.relative_to(_SRC))] = bad
    assert not offenders, f"forbidden imports in {layer}: {offenders}"
