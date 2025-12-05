"""Orchestrates the end-to-end KIDO routing and validation workflow."""
from pathlib import Path
from typing import Optional

import yaml


# Carga configuración YAML para paths y parámetros.
def load_config(paths_file: str | Path) -> dict:
    with Path(paths_file).open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}

# Ejecuta el pipeline completo de procesamiento, ruteo y validación.
# Este es un marcador de posición; complete las llamadas a los módulos de procesamiento/ruteo/validación
# a medida que se implementen.
def run_pipeline(paths_file: str | Path = "config/paths.yaml") -> None:
    cfg = load_config(paths_file)
    data_root = Path(cfg.get("data_processed", "data/processed"))
    data_root.mkdir(parents=True, exist_ok=True)
    print("[pipeline] Starting KIDO pipeline")
    print(f"[pipeline] Using processed data dir: {data_root}")
    # TODO: add cleaning, matrix generation, routing, validation, export steps.
    print("[pipeline] Pipeline finished (stub)")

# Genera solo el flujo de matrices (MC/MC2).
def generate_matrices(paths_file: str | Path = "config/paths.yaml") -> None:
    cfg = load_config(paths_file)
    processed_root = Path(cfg.get("data_processed", "data/processed"))
    processed_root.mkdir(parents=True, exist_ok=True)
    print("[matrices] Generating matrices (stub)")
    print(f"[matrices] Outputs → {processed_root}")

__all__ = ["run_pipeline", "generate_matrices", "load_config"]
