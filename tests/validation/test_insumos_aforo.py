"""Tests para insumos de aforo TPDS reales."""
import pandas as pd
import pytest

from kido_ruteo.config.loader import ConfigLoader
from kido_ruteo.processing.reader import load_aforo


EXPECTED_COLS = {
    "motos",
    "autos",
    "bus",
    "camion_unitario",
    "camion_articulado1",
    "camion_articulado2",
}


def test_aforo_tpds_columns_and_numeric() -> None:
    """Carga Excel TPDS y valida renombrado + valores numéricos."""
    pytest.importorskip("openpyxl")
    inputs_cfg = ConfigLoader.load_inputs()
    df = load_aforo(inputs_cfg)

    assert EXPECTED_COLS.issubset(df.columns)
    for col in EXPECTED_COLS:
        assert pd.api.types.is_numeric_dtype(df[col])
        assert df[col].notna().all()
