"""Tests para el módulo cleaner.py: Limpieza de viajes KIDO."""
from __future__ import annotations

import pandas as pd
import pytest

from kido_ruteo.processing.cleaner import clean_kido


@pytest.fixture
def sample_dirty_df() -> pd.DataFrame:
    """Crea un DataFrame sucio con problemas comunes."""
    return pd.DataFrame({
        "origin_id": ["1", "2", "1", "1", "3"],
        "destination_id": ["2", "3", "2", "2", "1"],
        "origin_name": ["Zone A", "Zone B", "Zone A", "Zone A", "Zone C"],
        "destination_name": ["Zone B", "Zone C", "Zone B", "Zone B", "Zone A"],
        "fecha": ["2024-01-01", "2024-01-02", "2024-01-01", "invalid", "2024-01-03"],
        "total_trips": [100, 50, 100, 5, 200],
    })


class TestCleanKido:
    """Tests para clean_kido."""

    def test_clean_removes_duplicates(self, sample_dirty_df: pd.DataFrame) -> None:
        """Elimina duplicados exactos."""
        before = len(sample_dirty_df)
        result = clean_kido(sample_dirty_df)
        # Hay un duplicado en las filas 2 y 3 (índices), así que debería haber menos
        assert len(result) < before

    def test_clean_preserves_unique(self, sample_dirty_df: pd.DataFrame) -> None:
        """Preserva filas únicas."""
        unique_df = sample_dirty_df.drop_duplicates()
        result = clean_kido(unique_df)
        assert len(result) == len(unique_df)

    def test_clean_normalizes_empty_strings(self) -> None:
        """Convierte strings vacíos a NaN."""
        df = pd.DataFrame({
            "origin_id": ["1", "  ", "3"],
            "destination_id": ["2", "3", "1"],
            "origin_name": ["A", "", "C"],
            "destination_name": ["B", "C", "A"],
            "fecha": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "total_trips": [100, 50, 200],
        })
        result = clean_kido(df)
        # Verificar que los strings vacíos fueron reemplazados
        assert pd.isna(result.iloc[1]["origin_name"])

    def test_clean_converts_dates(self, sample_dirty_df: pd.DataFrame) -> None:
        """Convierte fecha a datetime."""
        result = clean_kido(sample_dirty_df)
        assert pd.api.types.is_datetime64_any_dtype(result["fecha"])

    def test_clean_handles_invalid_dates(self, sample_dirty_df: pd.DataFrame) -> None:
        """Maneja fechas inválidas con coerce."""
        result = clean_kido(sample_dirty_df)
        # La fila con fecha 'invalid' debería ser NaT
        assert result["fecha"].isna().any()

    def test_clean_creates_trips_modif(self, sample_dirty_df: pd.DataFrame) -> None:
        """Crea columna total_trips_modif correctamente."""
        result = clean_kido(sample_dirty_df)
        assert "total_trips_modif" in result.columns
        
        # Verificar: trips < 10 → 1, else → trips
        assert (result.loc[result["total_trips"] < 10, "total_trips_modif"] == 1).all()
        assert (result.loc[result["total_trips"] >= 10, "total_trips_modif"] == result.loc[result["total_trips"] >= 10, "total_trips"]).all()

    def test_clean_creates_od_valido_flag(self, sample_dirty_df: pd.DataFrame) -> None:
        """Crea flag od_valido."""
        result = clean_kido(sample_dirty_df)
        assert "od_valido" in result.columns
        assert result["od_valido"].dtype == bool

    def test_clean_marks_invalid_od(self) -> None:
        """Marca como inválido cuando falta origin_id o destination_id."""
        df = pd.DataFrame({
            "origin_id": ["1", None, "3", "4"],
            "destination_id": ["2", "3", None, "1"],
            "origin_name": ["A", "B", "C", "D"],
            "destination_name": ["B", "C", "D", "A"],
            "fecha": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
            "total_trips": [100, 50, 200, 150],
        })
        result = clean_kido(df)
        
        # Las filas 1 y 2 deberían tener od_valido = False
        assert not result.iloc[1]["od_valido"]
        assert not result.iloc[2]["od_valido"]
        assert result.iloc[0]["od_valido"]
        assert result.iloc[3]["od_valido"]

    def test_clean_empty_dataframe(self) -> None:
        """Maneja DataFrame vacío."""
        empty_df = pd.DataFrame()
        result = clean_kido(empty_df)
        assert result.empty

    def test_clean_numeric_conversion(self) -> None:
        """Convierte total_trips a numérico y maneja coerce."""
        df = pd.DataFrame({
            "origin_id": ["1", "2"],
            "destination_id": ["2", "3"],
            "origin_name": ["A", "B"],
            "destination_name": ["B", "C"],
            "fecha": ["2024-01-01", "2024-01-02"],
            "total_trips": ["100", "invalid"],  # string values
        })
        result = clean_kido(df)
        # Verificar que es numérico (int o float)
        assert result["total_trips"].dtype in [int, float, "int64", "float64"]
        assert result.iloc[1]["total_trips"] == 0  # invalid → fillna(0)
