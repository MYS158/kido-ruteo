"""Tests para insumos de zonas geográficas reales."""
import pytest

from kido_ruteo.config.loader import ConfigLoader
from kido_ruteo.processing.reader import load_zonas


def test_zonas_geojson_core_checkpoint() -> None:
    """Carga geojson real y valida core/checkpoint con columna name."""
    pytest.importorskip("geopandas")
    inputs_cfg = ConfigLoader.load_inputs()
    zonas = load_zonas(inputs_cfg)

    core = zonas.get("core")
    checkpoint = zonas.get("checkpoint")

    assert core is not None and checkpoint is not None
    assert not core.empty or not checkpoint.empty
    if not core.empty:
        assert "name" in core.columns
        assert core.geometry.notna().all()
    if not checkpoint.empty:
        assert "name" in checkpoint.columns
        assert checkpoint.geometry.notna().all()
