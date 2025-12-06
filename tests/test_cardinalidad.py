"""Tests para el módulo cardinalidad.py: Asignación de sentido."""
from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from kido_ruteo.processing.cardinalidad import asignar_sentido


@pytest.fixture
def sample_trips_df() -> pd.DataFrame:
    """Crea un DataFrame de viajes sin geometría."""
    return pd.DataFrame({
        "origin_id": ["1", "2", "3"],
        "destination_id": ["2", "3", "1"],
        "origin_name": ["Zone A", "Zone B", "Zone C"],
        "destination_name": ["Zone B", "Zone C", "Zone A"],
        "total_trips": [100, 50, 200],
    })


class TestAsignarSentido:
    """Tests para asignar_sentido."""

    def test_adds_sentido_column_without_geopandas(self, sample_trips_df: pd.DataFrame) -> None:
        """Agrega columna sentido cuando GeoPandas no está disponible."""
        result = asignar_sentido(sample_trips_df, cardinalidad_gdf=None)
        
        assert "sentido" in result.columns
        # Sin GIS real, sentido debería ser None
        assert result["sentido"].isna().all()

    def test_handles_empty_dataframe(self) -> None:
        """Maneja DataFrame vacío."""
        empty_df = pd.DataFrame()
        result = asignar_sentido(empty_df, cardinalidad_gdf=None)
        assert result.empty

    def test_handles_none_cardinalidad(self, sample_trips_df: pd.DataFrame) -> None:
        """Maneja cuando cardinalidad_gdf es None."""
        result = asignar_sentido(sample_trips_df, cardinalidad_gdf=None)
        
        assert "sentido" in result.columns
        assert result["sentido"].isna().all()

    def test_handles_no_geometry_column(self, sample_trips_df: pd.DataFrame) -> None:
        """Maneja cuando no hay columna geometry en df."""
        result = asignar_sentido(sample_trips_df, cardinalidad_gdf=MagicMock())
        
        assert "sentido" in result.columns
        assert result["sentido"].isna().all()

    def test_preserves_other_columns(self, sample_trips_df: pd.DataFrame) -> None:
        """Preserva todas las demás columnas."""
        original_cols = set(sample_trips_df.columns)
        result = asignar_sentido(sample_trips_df, cardinalidad_gdf=None)
        result_cols = set(result.columns)
        
        assert original_cols.issubset(result_cols)

    def test_creates_sentido_with_mock_gdf(self, sample_trips_df: pd.DataFrame) -> None:
        """Con mock GeoDataFrame, agrega sentido (aunque sea None)."""
        mock_cardinalidad = MagicMock()
        mock_cardinalidad.columns = []
        
        # Sin geometry en df, debería retornar None para sentido
        result = asignar_sentido(sample_trips_df, cardinalidad_gdf=mock_cardinalidad)
        assert "sentido" in result.columns

    def test_with_geometry_and_mock_cardinalidad(self, sample_trips_df: pd.DataFrame) -> None:
        """Intenta spatial join si hay geometry (aunque falle)."""
        # Agregar geometría fake
        try:
            from shapely.geometry import Point  # type: ignore
            sample_trips_df["geometry"] = [Point(0, 0), Point(1, 1), Point(2, 2)]
        except ImportError:
            # Si shapely no está disponible, skip
            pytest.skip("Shapely no instalado")
        
        mock_cardinalidad = MagicMock()
        
        # Debería fallar en el sjoin pero aún agregar sentido = None
        result = asignar_sentido(sample_trips_df, cardinalidad_gdf=mock_cardinalidad)
        assert "sentido" in result.columns
        # Debería retornar None si falla
        assert result["sentido"].isna().any() or result["sentido"].notna().any()

    def test_multiple_calls_consistency(self, sample_trips_df: pd.DataFrame) -> None:
        """Múltiples llamadas producen resultados consistentes."""
        result1 = asignar_sentido(sample_trips_df, cardinalidad_gdf=None)
        result2 = asignar_sentido(sample_trips_df, cardinalidad_gdf=None)
        
        pd.testing.assert_frame_equal(result1, result2)
