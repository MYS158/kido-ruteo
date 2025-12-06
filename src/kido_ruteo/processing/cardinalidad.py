"""Asignación de sentido mediante cardinalidad y spatial join."""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

try:
    import geopandas as gpd  # type: ignore
    from geopandas.tools import sjoin  # type: ignore
except Exception:  # pragma: no cover
    gpd = None
    sjoin = None


logger = logging.getLogger(__name__)

def asignar_sentido(df: pd.DataFrame, cardinalidad_gdf: Any) -> pd.DataFrame:
    """Asigna columna ``sentido`` a cada viaje usando un spatial join punto-línea.

    Requiere GeoPandas; si no está disponible, se deja sentido en None y se loggea
    advertencia. Si no hay geometría en df, se deja sentido en None.
    """
    if df.empty:
        return df

    if gpd is None or sjoin is None:
        logger.warning("GeoPandas no disponible; sentido se deja en None")
        df = df.copy()
        df["sentido"] = None
        return df

    if "geometry" not in df.columns:
        logger.warning("No hay columna geometry en df; sentido se deja en None")
        df = df.copy()
        df["sentido"] = None
        return df

    if cardinalidad_gdf is None:
        logger.warning("No se proporcionó cardinalidad; sentido se deja en None")
        df = df.copy()
        df["sentido"] = None
        return df

    try:
        trips = gpd.GeoDataFrame(df, geometry="geometry", crs=getattr(df, "crs", None))
        joined = sjoin(trips, cardinalidad_gdf, how="left", predicate="intersects")
        df_out = pd.DataFrame(joined)
        if "sentido" not in df_out.columns:
            logger.warning("cardinalidad no tiene columna 'sentido'; se deja None")
            df_out["sentido"] = None
        return df_out
    except Exception as exc:  # pragma: no cover
        logger.warning("Fallo al asignar sentido: %s", exc)
        df = df.copy()
        df["sentido"] = None
        return df
