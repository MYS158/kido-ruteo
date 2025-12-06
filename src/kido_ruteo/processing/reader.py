"""Lectura de insumos KIDO y red vial."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

try:  # GeoPandas es opcional; se usa si está instalado.
    import geopandas as gpd  # type: ignore
except Exception:  # pragma: no cover - fallback
    gpd = None


logger = logging.getLogger(__name__)

REQUIRED_OD_COLS = {
    "origin_id",
    "destination_id",
    "origin_name",
    "destination_name",
    "fecha",
    "total_trips",
}

def _first_existing_file(root: Path, patterns: tuple[str, ...]) -> Optional[Path]:
    for pattern in patterns:
        for file in root.glob(pattern):
            if file.is_file():
                return file
    return None

def load_kido_raw(paths_cfg: Any) -> pd.DataFrame:
    """Carga viajes KIDO desde ``paths_cfg.data_raw`` con auto-detención de formato.

    Acepta .parquet, .csv o .gpkg. Valida columnas mínimas y normaliza tipos.
    """
    data_root = Path(paths_cfg.data_raw)
    if not data_root.exists():
        raise FileNotFoundError(f"No existe el directorio data_raw: {data_root}")

    file_path = _first_existing_file(data_root, ("*.parquet", "*.csv", "*.gpkg"))
    if not file_path:
        raise FileNotFoundError("No se encontraron archivos KIDO (.parquet, .csv, .gpkg)")

    logger.info("Cargando viajes KIDO: %s", file_path)
    if file_path.suffix.lower() == ".parquet":
        df = pd.read_parquet(file_path)
    elif file_path.suffix.lower() == ".csv":
        df = pd.read_csv(file_path)
    elif file_path.suffix.lower() == ".gpkg":
        if gpd is None:
            raise ImportError("GeoPandas requerido para leer .gpkg")
        df = gpd.read_file(file_path)  # type: ignore[assignment]
    else:  # pragma: no cover - no debería llegar
        raise ValueError(f"Extensión no soportada: {file_path.suffix}")

    missing = REQUIRED_OD_COLS.difference(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas obligatorias en KIDO: {missing}")

    # Normalización básica de tipos.
    df = df.copy()
    for col in ["origin_id", "destination_id"]:
        df[col] = df[col].astype(str)
    for col in ["origin_name", "destination_name"]:
        df[col] = df[col].astype(str).str.strip()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["total_trips"] = pd.to_numeric(df["total_trips"], errors="coerce").fillna(0).astype(int)

    return df


def _read_any(path: Path) -> pd.DataFrame:
    """Lee CSV/Parquet/GeoPackage devolviendo DataFrame/GeoDataFrame si aplica."""
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {path}")

    ext = path.suffix.lower()
    if ext == ".parquet":
        return pd.read_parquet(path)
    if ext == ".csv":
        return pd.read_csv(path)
    if ext == ".gpkg":
        if gpd is None:
            raise ImportError("GeoPandas requerido para leer .gpkg")
        return gpd.read_file(path)  # type: ignore[return-value]
    raise ValueError(f"Extensión no soportada: {ext}")

def load_network_metadata(paths_cfg: Any) -> Dict[str, Any]:
    """Carga nodos, arcos, centroides y cardinalidad desde ``paths_cfg.network``.

    Retorna un dict con llaves: nodes, edges, centroids, cardinalidad (opcional).
    """
    net_root = Path(paths_cfg.network)
    if not net_root.exists():
        raise FileNotFoundError(f"No existe el directorio network: {net_root}")

    files = {
        "nodes": _first_existing_file(net_root, ("nodes.*", "nodos.*")),
        "edges": _first_existing_file(net_root, ("edges.*", "arcos.*")),
        "centroids": _first_existing_file(net_root, ("centroids.*", "centroides.*")),
        "cardinalidad": _first_existing_file(net_root, ("cardinalidad.*", "cardinality.*")),
    }

    out: Dict[str, Any] = {}
    for key, path in files.items():
        if path:
            try:
                out[key] = _read_any(path)
                logger.info("Cargado %s desde %s", key, path)
            except Exception as exc:  # pragma: no cover - runtime safety
                logger.warning("No se pudo cargar %s (%s): %s", key, path, exc)
        else:
            logger.warning("No se encontró archivo para %s en %s", key, net_root)

    return out
