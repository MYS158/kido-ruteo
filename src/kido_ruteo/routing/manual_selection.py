"""Selección manual de checkpoints para pares origen-destino específicos.

Permite overrides manuales del checkpoint automático usando un archivo CSV
con especificaciones explícitas de nodo intermedio para rutas A→C→B.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import pandas as pd


logger = logging.getLogger(__name__)


def load_manual_selection(path: Path) -> pd.DataFrame:
    """Carga archivo CSV con selección manual de checkpoints.

    Formato esperado del CSV:
        origin_zone_id,destination_zone_id,origin_node_id,destination_node_id,checkpoint_node_id,author,timestamp,notes

    Args:
        path: Ruta al archivo manual_pair_checkpoints.csv

    Returns:
        DataFrame con columnas validadas.

    Raises:
        FileNotFoundError: Si el archivo no existe.
        ValueError: Si faltan columnas obligatorias.
    """
    if not path.exists():
        raise FileNotFoundError(f"Archivo de selección manual no encontrado: {path}")

    df = pd.read_csv(path)

    required_cols = {
        "origin_zone_id",
        "destination_zone_id",
        "checkpoint_node_id",
    }

    missing = required_cols.difference(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas obligatorias en {path}: {missing}")

    # Normalizar tipos
    df["origin_zone_id"] = df["origin_zone_id"].astype(str)
    df["destination_zone_id"] = df["destination_zone_id"].astype(str)
    df["checkpoint_node_id"] = df["checkpoint_node_id"].astype(str)

    # Columnas opcionales
    if "origin_node_id" in df.columns:
        df["origin_node_id"] = df["origin_node_id"].astype(str)
    if "destination_node_id" in df.columns:
        df["destination_node_id"] = df["destination_node_id"].astype(str)

    logger.info("Cargadas %d selecciones manuales desde %s", len(df), path)

    return df


def get_checkpoint_override(
    df_manual: pd.DataFrame,
    origin_zone_id: str,
    destination_zone_id: str,
) -> Optional[str]:
    """Devuelve checkpoint_node_id si existe override manual; si no, None.

    Args:
        df_manual: DataFrame con selecciones manuales (de load_manual_selection).
        origin_zone_id: ID de zona origen.
        destination_zone_id: ID de zona destino.

    Returns:
        checkpoint_node_id si existe override, None en caso contrario.
    """
    origin_zone_id = str(origin_zone_id)
    destination_zone_id = str(destination_zone_id)

    # Buscar coincidencia exacta
    matches = df_manual[
        (df_manual["origin_zone_id"] == origin_zone_id)
        & (df_manual["destination_zone_id"] == destination_zone_id)
    ]

    if matches.empty:
        return None

    if len(matches) > 1:
        logger.warning(
            "Múltiples overrides para %s→%s, usando el primero",
            origin_zone_id,
            destination_zone_id,
        )

    checkpoint_id = matches.iloc[0]["checkpoint_node_id"]
    return str(checkpoint_id) if pd.notna(checkpoint_id) else None


def get_node_overrides(
    df_manual: pd.DataFrame,
    origin_zone_id: str,
    destination_zone_id: str,
) -> dict[str, Optional[str]]:
    """Devuelve todos los overrides disponibles (origen, destino, checkpoint).

    Args:
        df_manual: DataFrame con selecciones manuales.
        origin_zone_id: ID de zona origen.
        destination_zone_id: ID de zona destino.

    Returns:
        Dict con llaves: origin_node_id, destination_node_id, checkpoint_node_id
        (None si no hay override).
    """
    origin_zone_id = str(origin_zone_id)
    destination_zone_id = str(destination_zone_id)

    matches = df_manual[
        (df_manual["origin_zone_id"] == origin_zone_id)
        & (df_manual["destination_zone_id"] == destination_zone_id)
    ]

    if matches.empty:
        return {
            "origin_node_id": None,
            "destination_node_id": None,
            "checkpoint_node_id": None,
        }

    row = matches.iloc[0]

    return {
        "origin_node_id": str(row.get("origin_node_id")) if pd.notna(row.get("origin_node_id")) else None,
        "destination_node_id": str(row.get("destination_node_id"))
        if pd.notna(row.get("destination_node_id"))
        else None,
        "checkpoint_node_id": str(row.get("checkpoint_node_id"))
        if pd.notna(row.get("checkpoint_node_id"))
        else None,
    }
