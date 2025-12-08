"""Ejecuta Fase D de validación sobre routing real.

Usa routing_results.csv generado previamente y un DataFrame procesado
mínimo construido desde kido_interim_with_nodes.csv para entregar
campos requeridos (cardinalidad_ok, validation_flags).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from kido_ruteo.validation.validation_pipeline import run_validation_pipeline

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
ROUTING_FILE = DATA_DIR / "processed" / "routing" / "routing_results.csv"
OD_FILE = DATA_DIR / "interim" / "kido_interim_with_nodes.csv"
OUTPUT_DIR = DATA_DIR / "processed" / "routing"


def build_processed_stub() -> pd.DataFrame:
    od = pd.read_csv(OD_FILE)
    # Campos mínimos para validación
    processed = od[["origin_node_id", "destination_node_id"]].copy()
    processed = processed.drop_duplicates().reset_index(drop=True)
    processed["cardinalidad_ok"] = True
    processed["validation_flags"] = ""
    return processed


def main() -> None:
    processed_stub = build_processed_stub()
    res = run_validation_pipeline(
        df_routing=ROUTING_FILE,
        df_processed=processed_stub,
        df_aforo=None,
        output_dir=OUTPUT_DIR,
    )
    print(res.head())
    print("rows", len(res))


if __name__ == "__main__":
    main()
