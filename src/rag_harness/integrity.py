from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluator_files() -> list[Path]:
    root = Path(__file__).resolve().parent
    return sorted(p for p in root.glob("*.py") if p.is_file())


def evaluator_hash() -> str:
    digest = hashlib.sha256()
    for path in evaluator_files():
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def snapshot(gold: Path, run: Path, config: Path, corpus_manifest: Path | None = None) -> dict:
    files = {
        "gold": {"path": str(gold.resolve()), "sha256": sha256_file(gold)},
        "run": {"path": str(run.resolve()), "sha256": sha256_file(run)},
        "config": {"path": str(config.resolve()), "sha256": sha256_file(config)},
    }
    if corpus_manifest is not None:
        files["corpus_manifest"] = {
            "path": str(corpus_manifest.resolve()),
            "sha256": sha256_file(corpus_manifest),
        }
    return {
        "algorithm": "sha256",
        "files": files,
        "evaluator": {
            "path": str(Path(__file__).resolve().parent),
            "sha256": evaluator_hash(),
            "files": [p.name for p in evaluator_files()],
        },
    }
