#!/usr/bin/env python3
"""Validate the public Jetson RPS package without Jetson-only dependencies."""

from __future__ import annotations

import hashlib
import json
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "model-manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    model = ROOT / manifest["file"]

    assert model.is_file(), f"missing TensorRT engine: {model}"
    assert model.stat().st_size == manifest["size_bytes"], "TensorRT engine size mismatch"
    assert sha256(model) == manifest["sha256"], "TensorRT engine SHA-256 mismatch"

    python_files = [
        ROOT / "app" / "RPS_Web_4mode.py",
        ROOT / "app" / "trt_module.py",
    ]
    assets = [
        ROOT / "app" / "assets" / "paper.png",
        ROOT / "app" / "assets" / "rock.png",
        ROOT / "app" / "assets" / "scissors.png",
    ]

    for source in python_files:
        assert source.is_file(), f"missing source: {source}"
        py_compile.compile(str(source), doraise=True)

    for asset in assets:
        assert asset.is_file() and asset.stat().st_size > 0, f"missing asset: {asset}"

    print("PASS: Python syntax, TensorRT engine integrity, and UI asset inventory")


if __name__ == "__main__":
    main()
