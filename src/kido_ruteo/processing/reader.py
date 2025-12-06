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

REQUIRED_RAW_OD_COLS = {
    "origin",
    "origin_name",
    "destination",
    "destination_name",
    "date",
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


def _coerce_total_trips(series: pd.Series) -> pd.Series:
    """Convierte total_trips, manejando valores como "<10" → 1."""
    def _convert(value: Any) -> float:
        if isinstance(value, str) and value.strip().startswith("<"):
            return 1.0
        return pd.to_numeric(value, errors="coerce")

    return series.apply(_convert).fillna(0).astype(float)


def load_od(inputs_cfg: Any) -> pd.DataFrame:
    """Carga y combina los archivos OD declarados en inputs_cfg.od_files.

    - Valida columnas mínimas: origin, origin_name, destination, destination_name, date, total_trips.
    - Agrega columna source_file con el nombre del archivo.
    - Renombra columnas a convención interna (origin_id, destination_id, fecha, total_trips) y normaliza tipos.
    - Convierte valores "<10" a 1 en total_trips.
    """
    od_dir = Path(inputs_cfg.od_dir)
    if not od_dir.exists():
        raise FileNotFoundError(f"No existe el directorio OD: {od_dir}")

    frames: list[pd.DataFrame] = []
    for file_name in inputs_cfg.od_files:
        file_path = od_dir / file_name
        if not file_path.exists():
            raise FileNotFoundError(f"No se encontró archivo OD: {file_path}")

        df = pd.read_csv(file_path)
        missing = REQUIRED_RAW_OD_COLS.difference(df.columns)
        if missing:
            raise ValueError(f"Faltan columnas obligatorias en {file_name}: {missing}")

        df = df.copy()
        df["source_file"] = file_path.name
        df.rename(
            columns={
                "origin": "origin_id",
                "destination": "destination_id",
                "date": "fecha",
            },
            inplace=True,
        )

        # Tipos y normalización
        df["origin_id"] = df["origin_id"].astype(str)
        df["destination_id"] = df["destination_id"].astype(str)
        df["origin_name"] = df["origin_name"].astype(str).str.strip()
        df["destination_name"] = df["destination_name"].astype(str).str.strip()
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        df["total_trips"] = _coerce_total_trips(df["total_trips"])

        frames.append(df)

    if not frames:
        raise ValueError("No se cargaron archivos OD")

    combined = pd.concat(frames, ignore_index=True)
    if combined.empty:
        raise ValueError("Los archivos OD están vacíos")

    # Asegurar columnas finales y tipo numérico int para trips.
    combined["total_trips"] = combined["total_trips"].astype(int)
    expected = [
        "origin_id",
        "origin_name",
        "destination_id",
        "destination_name",
        "fecha",
        "total_trips",
        "source_file",
    ]
    return combined[expected]


def load_zonas(inputs_cfg: Any) -> Dict[str, Any]:
    """Carga zonas desde GeoJSON, separando core y checkpoint por tipo geométrico."""
    if gpd is None:
        raise ImportError("GeoPandas es requerido para cargar zonas")

    zonas_path = Path(inputs_cfg.geografia_zonas)
    if not zonas_path.exists():
        candidate_dir = zonas_path.parent if zonas_path.parent.name else Path(inputs_cfg.geografia_zonas).parent
        if candidate_dir.exists():
            fallback = next(candidate_dir.glob("*.geojson"), None)
            if fallback:
                zonas_path = fallback
        if not zonas_path.exists():
            raise FileNotFoundError(f"No existe el geojson de zonas: {zonas_path}")

    gdf = gpd.read_file(zonas_path)
    if gdf.empty:
        raise ValueError("El geojson de zonas está vacío")
    if "name" not in gdf.columns:
        raise ValueError("El geojson de zonas debe contener la columna 'name'")

    geom_type = gdf.geometry.geom_type.str.lower()
    core_mask = geom_type.str.contains("polygon")
    checkpoint_mask = geom_type.str.contains("point") | (~core_mask)

    return {
        "core": gdf[core_mask].copy(),
        "checkpoint": gdf[checkpoint_mask].copy(),
    }


def load_aforo(inputs_cfg: Any) -> pd.DataFrame:
    """Carga factores de aforo TPDS desde Excel y renombra columnas."""
    aforo_path = Path(inputs_cfg.aforo_factors)
    if not aforo_path.exists():
        candidate_dir = aforo_path.parent if aforo_path.parent.name else Path(inputs_cfg.aforo_factors).parent
        if candidate_dir.exists():
            fallback = next(candidate_dir.glob("*.xlsx"), None)
            if fallback:
                aforo_path = fallback
        if not aforo_path.exists():
            raise FileNotFoundError(f"No existe el archivo de aforo: {aforo_path}")

    df = pd.read_excel(aforo_path, sheet_name="TPDS")
    required = ["M", "A", "B", "CU", "CAI", "CAII"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en aforo TPDS: {missing}")

    rename_map = {
        "M": "motos",
        "A": "autos",
        "B": "bus",
        "CU": "camion_unitario",
        "CAI": "camion_articulado1",
        "CAII": "camion_articulado2",
    }
    df = df.rename(columns=rename_map)

    for col in rename_map.values():
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if df[col].isna().any():
            raise ValueError(f"Valores no numéricos en columna {col} de aforo TPDS")

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
