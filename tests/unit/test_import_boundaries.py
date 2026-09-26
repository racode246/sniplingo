"""Architecture guard: enforce the layer rules of `.claude/rules/architecture.md`.

Parses every module under ``src/sniplingo`` (no importing) and checks:

1. **Pure layers** (``domain``, ``ports``, ``core``) import only the standard library and
   ``sniplingo`` at runtime. Imports under ``if TYPE_CHECKING:`` are exempt (that's how
   ``ports`` names ``PIL.Image`` without depending on it).
2. **Dependency direction** between sniplingo layers (runtime *and* type-only imports):
   ``domain <- ports <- core <- adapters / ui``; adapters never import core or ui.
3. **Composition root**: within ``ui`` only ``ui/app.py`` may import ``adapters``.
4. No relative imports (they would slip past the checks above).
"""

from __future__ import annotations

import ast
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src" / "sniplingo"

PURE_LAYERS = ("domain", "ports", "core")
ALLOWED_LAYER_DEPS = {
    "domain": {"domain"},
    "ports": {"domain", "ports"},
    "core": {"domain", "ports", "core"},
    "adapters": {"domain", "ports", "adapters"},
    "ui": {"domain", "ports", "core", "ui", "adapters"},
}
COMPOSITION_ROOT = Path("ui") / "app.py"


@dataclass(frozen=True)
class ImportRef:
    module: str  # absolute dotted name ("" for a relative import)
    type_only: bool
    lineno: int
    relative: bool = False


def _is_type_checking(test: ast.expr) -> bool:
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )


def collect_imports(source: str) -> list[ImportRef]:
    refs: list[ImportRef] = []

    def visit(node: ast.AST, type_only: bool) -> None:
        if isinstance(node, ast.If) and _is_type_checking(node.test):
            for child in node.body:
                visit(child, True)
            for child in node.orelse:
                visit(child, type_only)
            return
        if isinstance(node, ast.Import):
            refs.extend(ImportRef(a.name, type_only, node.lineno) for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            refs.append(
                ImportRef(node.module or "", type_only, node.lineno, relative=node.level > 0)
            )
        for child in ast.iter_child_nodes(node):
            visit(child, type_only)

    visit(ast.parse(source), False)
    return refs


def _modules() -> list[tuple[Path, list[ImportRef]]]:
    return [
        (py.relative_to(_SRC), collect_imports(py.read_text(encoding="utf-8")))
        for py in sorted(_SRC.rglob("*.py"))
    ]


def _layer(module: str) -> str | None:
    parts = module.split(".")
    return parts[1] if len(parts) > 1 and parts[0] == "sniplingo" else None


# --- the checker itself ----------------------------------------------------------------


def test_collector_separates_runtime_and_type_only_imports():
    source = textwrap.dedent(
        """
        import os
        from typing import TYPE_CHECKING
        if TYPE_CHECKING:
            from PIL.Image import Image
        else:
            import json
        def f():
            import mss
        """
    )
    refs = {r.module: r.type_only for r in collect_imports(source)}
    assert refs == {"os": False, "typing": False, "PIL.Image": True, "json": False, "mss": False}


def test_collector_flags_relative_imports():
    (ref,) = collect_imports("from .models import Region")
    assert ref.relative


# --- the rules -----------------------------------------------------------------------


@pytest.mark.parametrize("layer", PURE_LAYERS)
def test_pure_layers_use_only_stdlib_at_runtime(layer):
    offenders = {
        f"{path}:{ref.lineno}": ref.module
        for path, refs in _modules()
        if path.parts[0] == layer
        for ref in refs
        if not ref.type_only
        and ref.module.split(".")[0] not in sys.stdlib_module_names
        and ref.module.split(".")[0] != "sniplingo"
    }
    assert not offenders, f"third-party imports in pure layer {layer}: {offenders}"


def test_layer_dependencies_point_inward():
    offenders = {}
    for path, refs in _modules():
        layer = path.parts[0]
        if layer not in ALLOWED_LAYER_DEPS:
            continue
        for ref in refs:
            target = _layer(ref.module)
            if target and target not in ALLOWED_LAYER_DEPS[layer]:
                offenders[f"{path}:{ref.lineno}"] = ref.module
    assert not offenders, f"imports against the dependency direction: {offenders}"


def test_only_the_composition_root_imports_adapters():
    offenders = {
        f"{path}:{ref.lineno}": ref.module
        for path, refs in _modules()
        if path.parts[0] == "ui" and path != COMPOSITION_ROOT
        for ref in refs
        if _layer(ref.module) == "adapters"
    }
    assert not offenders, f"adapters wired outside {COMPOSITION_ROOT}: {offenders}"


def test_no_relative_imports():
    offenders = [
        f"{path}:{ref.lineno}" for path, refs in _modules() for ref in refs if ref.relative
    ]
    assert not offenders, f"use absolute imports: {offenders}"
