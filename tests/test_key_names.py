"""Private key file names come from vesper.paths, not retyped literals."""

from __future__ import annotations

import ast
from pathlib import Path

from vesper.paths import ECDSA_KEY_FILENAME, HMAC_KEY_FILENAME

SRC = Path(__file__).resolve().parents[1] / "src" / "vesper"
LITERALS = {ECDSA_KEY_FILENAME, HMAC_KEY_FILENAME}


def test_key_file_names_are_only_spelled_in_paths_py() -> None:
    offenders = []
    for path in sorted(SRC.glob("*.py")):
        if path.name == "paths.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value in LITERALS:
                offenders.append(f"{path.name}:{node.lineno}:{node.value}")
    assert offenders == []
