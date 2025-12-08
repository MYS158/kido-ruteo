"""Tests de pipeline completo con insumos reales."""
from pathlib import Path

import pandas as pd
import pytest

from kido_ruteo.config.loader import ConfigLoader
from kido_ruteo.processing.processing_pipeline import KIDORawProcessor


def test_pipeline_real_inputs_creates_outputs() -> None:
    """Ejecuta KIDORawProcessor con insumos reales y valida salidas."""
    cfg = ConfigLoader.load_all()
    processor = KIDORawProcessor()

    processor.load_data(cfg)
    df = processor.process()

    assert not df.empty
    required_cols = {
        "intrazonal",
        "acceso_valido",
        "total_trips_modif",
        "origin_name",
        "destination_name",
    }
    assert required_cols.issubset(df.columns)

    interim_dir = Path(cfg.paths.data_interim)
    assert (interim_dir / "kido_interim.csv").exists()
    # Parquet puede fallar sin pyarrow, pero si existe mejor.
    if (interim_dir / "kido_interim.parquet").exists():
        loaded_parquet = pd.read_parquet(interim_dir / "kido_interim.parquet")
        assert not loaded_parquet.empty

    loaded_csv = pd.read_csv(interim_dir / "kido_interim.csv")
    assert not loaded_csv.empty
