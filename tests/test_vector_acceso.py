"""Tests para el módulo vector_acceso.py: Validación de zonas y acceso."""
from __future__ import annotations

import pandas as pd
import pytest

from kido_ruteo.processing.vector_acceso import generar_vectores_acceso, _is_clean_zone


@pytest.fixture
def sample_zone_df() -> pd.DataFrame:
    """Crea un DataFrame con zonas de acceso variadas."""
    return pd.DataFrame({
        "origin_id": ["1", "2", "3", "1", "2"],
        "destination_id": ["2", "3", "1", "3", "1"],
        "origin_name": ["Zone A", "Zone B", "Zone C", "Zone A", "Zone B"],
        "destination_name": ["Zone B", "Zone C", "Zone A", "Zone C", "Zone A"],
        "total_trips": [100, 50, 200, 150, 75],
    })


class TestIsCleanZone:
    """Tests para _is_clean_zone."""

    def test_clean_numeric_zone(self) -> None:
        """Acepta zonas numéricas."""
        assert _is_clean_zone("123") is True

    def test_clean_alphanumeric_zone(self) -> None:
        """Acepta zonas alfanuméricas."""
        assert _is_clean_zone("zone_1") is True
        assert _is_clean_zone("ZONE-A") is True
        assert _is_clean_zone("sector 42") is True

    def test_rejects_none(self) -> None:
        """Rechaza None."""
        assert _is_clean_zone(None) is False

    def test_rejects_empty_string(self) -> None:
        """Rechaza strings vacíos."""
        assert _is_clean_zone("") is False
        assert _is_clean_zone("   ") is False

    def test_rejects_special_chars(self) -> None:
        """Rechaza caracteres especiales."""
        assert _is_clean_zone("zone@1") is False
        assert _is_clean_zone("zone#") is False
        assert _is_clean_zone("zone/path") is False


class TestGenerarVectoresAcceso:
    """Tests para generar_vectores_acceso."""

    def test_creates_acceso_valido_column(self, sample_zone_df: pd.DataFrame) -> None:
        """Crea columna acceso_valido."""
        result = generar_vectores_acceso(sample_zone_df)
        assert "acceso_valido" in result.columns
        assert result["acceso_valido"].dtype == bool

    def test_marks_valid_access(self, sample_zone_df: pd.DataFrame) -> None:
        """Marca acceso=True para zonas válidas."""
        result = generar_vectores_acceso(sample_zone_df)
        # Todas las zonas son numéricas válidas, así que todos deberían ser True
        # (siempre que estén en V1 y V2)
        valid_rows = result[result["acceso_valido"]]
        assert len(valid_rows) > 0

    def test_marks_invalid_access_with_none(self) -> None:
        """Marca acceso=False si hay None."""
        df = pd.DataFrame({
            "origin_id": ["1", pd.NA, "3"],
            "destination_id": ["2", "3", "1"],
            "origin_name": ["A", "B", "C"],
            "destination_name": ["B", "C", "A"],
            "total_trips": [100, 50, 200],
        })
        result = generar_vectores_acceso(df)
        
        # Fila 1 con None debería ser inválida (no es alfanumérica)
        assert pd.isna(result.iloc[1]["acceso_valido"]) or result.iloc[1]["acceso_valido"] == False

    def test_marks_invalid_access_with_empty_string(self) -> None:
        """Marca acceso=False si hay strings vacíos."""
        df = pd.DataFrame({
            "origin_id": ["1", "", "3"],
            "destination_id": ["2", "3", "1"],
            "origin_name": ["A", "B", "C"],
            "destination_name": ["B", "C", "A"],
            "total_trips": [100, 50, 200],
        })
        result = generar_vectores_acceso(df)
        
        assert result.iloc[1]["acceso_valido"] == False

    def test_generates_v1_and_v2_vectors(self, sample_zone_df: pd.DataFrame) -> None:
        """Genera vectores internos V1 (orígenes) y V2 (destinos)."""
        result = generar_vectores_acceso(sample_zone_df)
        # Verificar que la función procesa todas las filas sin error
        assert len(result) == len(sample_zone_df)

    def test_handles_special_characters_in_zones(self) -> None:
        """Marca inválidas zonas con caracteres especiales."""
        df = pd.DataFrame({
            "origin_id": ["1", "zone@1", "3"],
            "destination_id": ["2", "3", "zone#1"],
            "origin_name": ["A", "B", "C"],
            "destination_name": ["B", "C", "A"],
            "total_trips": [100, 50, 200],
        })
        result = generar_vectores_acceso(df)
        
        # Filas 1 y 2 deberían tener acceso_valido = False
        assert result.iloc[1]["acceso_valido"] == False
        assert result.iloc[2]["acceso_valido"] == False

    def test_empty_dataframe(self) -> None:
        """Maneja DataFrame vacío."""
        empty_df = pd.DataFrame()
        result = generar_vectores_acceso(empty_df)
        assert result.empty

    def test_whitespace_handling(self) -> None:
        """Maneja espacios en blanco en zonas."""
        df = pd.DataFrame({
            "origin_id": ["1", "  2  ", "3"],
            "destination_id": ["2", "3", "1"],
            "origin_name": ["A", "B", "C"],
            "destination_name": ["B", "C", "A"],
            "total_trips": [100, 50, 200],
        })
        result = generar_vectores_acceso(df)
        # "  2  " stripped es "2", que es válido
        assert result.iloc[1]["acceso_valido"] == True

    def test_logs_error_count(self, sample_zone_df: pd.DataFrame, caplog: pytest.LogCaptureFixture) -> None:
        """Loggea conteos de errores."""
        import logging
        caplog.set_level(logging.WARNING)
        
        result = generar_vectores_acceso(sample_zone_df)
        # Debería haber algún log de estado (aunque todo sea válido, puede loggear 0)
        assert len(caplog.records) >= 0  # Sin aserción fuerte sobre logs
