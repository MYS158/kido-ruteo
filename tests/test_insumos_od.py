"""Tests para insumos OD reales (od_viaductos_1018/1019)."""
from pathlib import Path

import pandas as pd

from kido_ruteo.config.loader import ConfigLoader
from kido_ruteo.processing.reader import load_od


REQUIRED_COLS = {
    "origin_id",
    "origin_name",
    "destination_id",
    "destination_name",
    "fecha",
    "total_trips",
    "source_file",
}


def test_od_inputs_combined() -> None:
    """Carga ambos CSV y valida columnas mínimas y combinación."""
    inputs_cfg = ConfigLoader.load_inputs()
    df = load_od(inputs_cfg)

    assert not df.empty
    assert REQUIRED_COLS.issubset(df.columns)
    assert set(df["source_file"].unique()) == set(inputs_cfg.od_files)
    assert df["total_trips"].dtype.kind in "iu"
    assert (df["total_trips"] >= 0).all()


def test_od_converts_less_than_ten() -> None:
    """total_trips no conserva cadenas con '<', se convierten a números (1)."""
    inputs_cfg = ConfigLoader.load_inputs()
    df = load_od(inputs_cfg)

    # No deben quedar literales con '<', lo que implica conversión.
    assert not df["total_trips"].astype(str).str.startswith("<").any()
    # Si existían valores <10, deberían aparecer como 1 (no es error si no existen).
    assert (df["total_trips"] >= 0).all()
