"""Tests para el módulo reader.py: Lectura de insumos KIDO y red vial."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from kido_ruteo.processing.reader import load_kido_raw, load_network_metadata


@pytest.fixture
def sample_kido_df() -> pd.DataFrame:
    """Crea un DataFrame de muestra con columnas mínimas KIDO."""
    return pd.DataFrame({
        "origin_id": ["1", "2", "1"],
        "destination_id": ["2", "3", "3"],
        "origin_name": ["Zone A", "Zone B", "Zone A"],
        "destination_name": ["Zone B", "Zone C", "Zone C"],
        "fecha": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "total_trips": [100, 50, 200],
    })


@pytest.fixture
def tmp_kido_csv(tmp_path: Path, sample_kido_df: pd.DataFrame) -> Path:
    """Crea un archivo CSV temporal con datos KIDO mínimos."""
    csv_file = tmp_path / "kido.csv"
    sample_kido_df.to_csv(csv_file, index=False)
    return csv_file.parent


class TestLoadKidoRaw:
    """Tests para load_kido_raw."""

    def test_load_kido_csv_success(self, sample_kido_df: pd.DataFrame, tmp_path: Path) -> None:
        """Carga exitosa de CSV con columnas mínimas."""
        csv_file = tmp_path / "kido.csv"
        sample_kido_df.to_csv(csv_file, index=False)
        
        paths_cfg = MagicMock()
        paths_cfg.data_raw = str(tmp_path)
        
        result = load_kido_raw(paths_cfg)
        assert len(result) == 3
        assert set(result.columns) >= {"origin_id", "destination_id", "fecha"}

    def test_load_kido_missing_directory(self, tmp_path: Path) -> None:
        """Lanza error si no existe data_raw."""
        paths_cfg = MagicMock()
        paths_cfg.data_raw = str(tmp_path / "nonexistent")
        
        with pytest.raises(FileNotFoundError):
            load_kido_raw(paths_cfg)

    def test_load_kido_no_file_in_dir(self, tmp_path: Path) -> None:
        """Lanza error si no hay archivos en data_raw."""
        paths_cfg = MagicMock()
        paths_cfg.data_raw = str(tmp_path)
        
        with pytest.raises(FileNotFoundError, match="No se encontraron archivos KIDO"):
            load_kido_raw(paths_cfg)

    def test_load_kido_missing_required_columns(self, tmp_path: Path) -> None:
        """Lanza error si faltan columnas obligatorias."""
        bad_df = pd.DataFrame({
            "origin_id": ["1", "2"],
            "destination_id": ["2", "3"],
            # Falta origin_name, destination_name, fecha, total_trips
        })
        csv_file = tmp_path / "bad_kido.csv"
        bad_df.to_csv(csv_file, index=False)
        
        paths_cfg = MagicMock()
        paths_cfg.data_raw = str(tmp_path)
        
        with pytest.raises(ValueError, match="Faltan columnas obligatorias"):
            load_kido_raw(paths_cfg)

    def test_load_kido_type_normalization(self, sample_kido_df: pd.DataFrame, tmp_path: Path) -> None:
        """Valida normalización de tipos (str, datetime, int)."""
        csv_file = tmp_path / "kido.csv"
        sample_kido_df.to_csv(csv_file, index=False)
        
        paths_cfg = MagicMock()
        paths_cfg.data_raw = str(tmp_path)
        
        result = load_kido_raw(paths_cfg)
        assert result["origin_id"].dtype == object  # str
        assert result["destination_id"].dtype == object  # str
        assert pd.api.types.is_datetime64_any_dtype(result["fecha"])
        assert result["total_trips"].dtype in [int, "int64"]

    def test_load_kido_with_invalid_dates(self, tmp_path: Path) -> None:
        """Maneja fechas inválidas sin fallar."""
        df = pd.DataFrame({
            "origin_id": ["1", "2"],
            "destination_id": ["2", "3"],
            "origin_name": ["A", "B"],
            "destination_name": ["B", "C"],
            "fecha": ["2024-01-01", "invalid-date"],
            "total_trips": [100, 50],
        })
        csv_file = tmp_path / "kido_bad_dates.csv"
        df.to_csv(csv_file, index=False)
        
        paths_cfg = MagicMock()
        paths_cfg.data_raw = str(tmp_path)
        
        result = load_kido_raw(paths_cfg)
        assert result["fecha"].isna().any()  # coerce=True convierte inválidas a NaT


class TestLoadNetworkMetadata:
    """Tests para load_network_metadata."""

    def test_load_network_empty_directory(self, tmp_path: Path) -> None:
        """Retorna dict vacío si no hay archivos de red."""
        network_dir = tmp_path / "network"
        network_dir.mkdir()
        
        paths_cfg = MagicMock()
        paths_cfg.network = str(network_dir)
        
        result = load_network_metadata(paths_cfg)
        assert isinstance(result, dict)
        # Puede estar vacío o tener llaves con None

    def test_load_network_missing_directory(self, tmp_path: Path) -> None:
        """Lanza error si no existe network."""
        paths_cfg = MagicMock()
        paths_cfg.network = str(tmp_path / "nonexistent_network")
        
        with pytest.raises(FileNotFoundError):
            load_network_metadata(paths_cfg)

    def test_load_network_with_csv_files(self, tmp_path: Path) -> None:
        """Carga archivos CSV de red si existen."""
        network_dir = tmp_path / "network"
        network_dir.mkdir()
        
        # Crear archivos de red
        nodes_df = pd.DataFrame({"node_id": [1, 2, 3]})
        edges_df = pd.DataFrame({"from": [1, 2], "to": [2, 3]})
        
        nodes_df.to_csv(network_dir / "nodes.csv", index=False)
        edges_df.to_csv(network_dir / "edges.csv", index=False)
        
        paths_cfg = MagicMock()
        paths_cfg.network = str(network_dir)
        
        result = load_network_metadata(paths_cfg)
        assert "nodes" in result or "edges" in result
