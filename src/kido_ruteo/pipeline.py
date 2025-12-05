"""Orchestrates the end-to-end KIDO routing and validation workflow."""
from pathlib import Path
from typing import Optional

import yaml


def load_config(paths_file: str | Path) -> dict:
    """Load YAML configuration for file paths and parameters."""
    with Path(paths_file).open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def run_pipeline(paths_file: str | Path = "config/paths.yaml") -> None:
    """Run the full processing, routing, and validation pipeline.

    This is a placeholder; fill in calls to the processing/routing/validation
    modules as they are implemented.
    """
    cfg = load_config(paths_file)
    data_root = Path(cfg.get("data_processed", "data/processed"))
    data_root.mkdir(parents=True, exist_ok=True)
    print("[pipeline] Starting KIDO pipeline")
    print(f"[pipeline] Using processed data dir: {data_root}")
    # TODO: add cleaning, matrix generation, routing, validation, export steps.
    print("[pipeline] Pipeline finished (stub)")


def generate_matrices(paths_file: str | Path = "config/paths.yaml") -> None:
    """Generate matrices-only flow (MC/MC2)."""
    cfg = load_config(paths_file)
    processed_root = Path(cfg.get("data_processed", "data/processed"))
    processed_root.mkdir(parents=True, exist_ok=True)
    print("[matrices] Generating matrices (stub)")
    print(f"[matrices] Outputs → {processed_root}")


__all__ = ["run_pipeline", "generate_matrices", "load_config"]
