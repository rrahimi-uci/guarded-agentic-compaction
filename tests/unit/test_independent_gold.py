"""Architecture checks for independently constructed benchmark gold."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_gold_module_does_not_import_macro_or_tool_facade_implementations() -> None:
    path = ROOT / "benchmarks/gold.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported_modules = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    imported_modules.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    assert not any(module.startswith("benchmarks.adapters") for module in imported_modules)
    identifiers = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not {"vulnerability_macro", "hmda_macro", "sec_macro"} & identifiers


def test_pool_builders_use_independent_gold_not_macro_candidates() -> None:
    for name, forbidden in (
        ("vulnerability_pool.py", "vulnerability_macro"),
        ("hmda_pool.py", "hmda_macro"),
        ("sec_pool.py", "sec_macro"),
    ):
        source = (ROOT / "benchmarks/build" / name).read_text(encoding="utf-8")
        assert forbidden not in source
        assert "_gold_from_records" in source
