"""Tests para selección manual de checkpoints."""
from pathlib import Path

import pandas as pd
import pytest

from kido_ruteo.routing.manual_selection import (
    load_manual_selection,
    get_checkpoint_override,
    get_node_overrides,
)


@pytest.fixture
def manual_csv_path(tmp_path: Path) -> Path:
    """Crea CSV con selecciones manuales."""
    csv_path = tmp_path / "manual_checkpoints.csv"
    data = pd.DataFrame(
        {
            "origin_zone_id": ["Z1", "Z2", "Z3"],
            "destination_zone_id": ["Z2", "Z3", "Z4"],
            "origin_node_id": ["N1", "N2", "N3"],
            "destination_node_id": ["N2", "N3", "N4"],
            "checkpoint_node_id": ["C1", "C2", "C3"],
            "author": ["John", "Jane", "Bob"],
            "timestamp": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "notes": ["Manual route", "Optimized", "Test"],
        }
    )
    data.to_csv(csv_path, index=False)
    return csv_path


def test_load_manual_selection_success(manual_csv_path):
    """Cargar CSV válido con todas las columnas."""
    df = load_manual_selection(manual_csv_path)

    assert len(df) == 3
    assert "origin_zone_id" in df.columns
    assert "destination_zone_id" in df.columns
    assert "checkpoint_node_id" in df.columns
    assert df["origin_zone_id"].dtype == object  # str
    assert df["checkpoint_node_id"].iloc[0] == "C1"


def test_load_manual_selection_missing_file(tmp_path):
    """Archivo inexistente debe lanzar FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_manual_selection(tmp_path / "nonexistent.csv")


def test_load_manual_selection_missing_columns(tmp_path):
    """CSV sin columnas obligatorias debe lanzar ValueError."""
    bad_csv = tmp_path / "bad.csv"
    pd.DataFrame({"origin": [1], "destination": [2]}).to_csv(bad_csv, index=False)

    with pytest.raises(ValueError, match="Faltan columnas obligatorias"):
        load_manual_selection(bad_csv)


def test_get_checkpoint_override_found(manual_csv_path):
    """Override presente debe retornar checkpoint_node_id."""
    df = load_manual_selection(manual_csv_path)

    checkpoint = get_checkpoint_override(df, "Z1", "Z2")
    assert checkpoint == "C1"

    checkpoint = get_checkpoint_override(df, "Z2", "Z3")
    assert checkpoint == "C2"


def test_get_checkpoint_override_not_found(manual_csv_path):
    """Override ausente debe retornar None."""
    df = load_manual_selection(manual_csv_path)

    checkpoint = get_checkpoint_override(df, "Z1", "Z999")
    assert checkpoint is None

    checkpoint = get_checkpoint_override(df, "Z999", "Z1")
    assert checkpoint is None


def test_get_node_overrides_complete(manual_csv_path):
    """get_node_overrides debe retornar todos los nodos disponibles."""
    df = load_manual_selection(manual_csv_path)

    overrides = get_node_overrides(df, "Z1", "Z2")

    assert overrides["origin_node_id"] == "N1"
    assert overrides["destination_node_id"] == "N2"
    assert overrides["checkpoint_node_id"] == "C1"


def test_get_node_overrides_not_found(manual_csv_path):
    """get_node_overrides sin match debe retornar None en todos."""
    df = load_manual_selection(manual_csv_path)

    overrides = get_node_overrides(df, "Z999", "Z888")

    assert overrides["origin_node_id"] is None
    assert overrides["destination_node_id"] is None
    assert overrides["checkpoint_node_id"] is None


def test_multiple_overrides_uses_first(tmp_path):
    """Múltiples overrides para mismo par deben usar el primero."""
    csv_path = tmp_path / "duplicates.csv"
    data = pd.DataFrame(
        {
            "origin_zone_id": ["Z1", "Z1"],
            "destination_zone_id": ["Z2", "Z2"],
            "checkpoint_node_id": ["C1", "C2"],
        }
    )
    data.to_csv(csv_path, index=False)

    df = load_manual_selection(csv_path)
    checkpoint = get_checkpoint_override(df, "Z1", "Z2")

    assert checkpoint == "C1"  # Primer match


def test_checkpoint_source_metadata():
    """Verificar que checkpoint_source refleja manual vs auto."""
    # Este test verifica lógica de negocio que se implementará en constrained_path
    manual_df = pd.DataFrame(
        {
            "origin_zone_id": ["Z1"],
            "destination_zone_id": ["Z2"],
            "checkpoint_node_id": ["C_manual"],
        }
    )

    # Con override manual
    checkpoint = get_checkpoint_override(manual_df, "Z1", "Z2")
    assert checkpoint == "C_manual"
    checkpoint_source = "manual" if checkpoint else "auto"
    assert checkpoint_source == "manual"

    # Sin override manual
    checkpoint = get_checkpoint_override(manual_df, "Z3", "Z4")
    assert checkpoint is None
    checkpoint_source = "manual" if checkpoint else "auto"
    assert checkpoint_source == "auto"
