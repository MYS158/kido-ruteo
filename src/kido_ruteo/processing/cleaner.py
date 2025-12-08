"""Rutinas de limpieza para viajes KIDO."""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd


logger = logging.getLogger(__name__)

def clean_kido(df: pd.DataFrame) -> pd.DataFrame:
    """Limpia el DataFrame de viajes KIDO.

    - Elimina duplicados exactos.
    - Normaliza strings vacíos/NaN.
    - Convierte fecha a datetime.
    - Calcula total_trips_modif (1 si total_trips < 10, else total_trips).
    - Marca banderas de validez mínima OD.
    """
    if df.empty:
        logger.warning("El DataFrame de KIDO está vacío")
        return df

    df = df.copy()

    # Quitar duplicados exactos.
    before = len(df)
    df = df.drop_duplicates()
    removed = before - len(df)
    if removed:
        logger.info("Eliminados %s duplicados", removed)

    # Normalizar strings vacíos.
    df.replace(to_replace=r"^\s*$", value=pd.NA, regex=True, inplace=True)

    # Fecha a datetime.
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    invalid_dates = df["fecha"].isna().sum()
    if invalid_dates:
        logger.warning("%s registros con fecha inválida", invalid_dates)

    # total_trips_modif: convierte texto a numérico, "<10" → 1, resto → valor.
    df["total_trips_modif"] = pd.to_numeric(df["total_trips"], errors="coerce").fillna(0)
    df["total_trips_modif"] = df["total_trips_modif"].apply(lambda x: 1 if x < 10 else x)

    # Flags básicos de validez OD.
    df["od_valido"] = (~df["origin_id"].isna()) & (~df["destination_id"].isna())
    df["od_valido"] &= df["origin_id"].astype(str).str.len() > 0
    df["od_valido"] &= df["destination_id"].astype(str).str.len() > 0

    invalid_od = (~df["od_valido"]).sum()
    if invalid_od:
        logger.warning("%s registros con OD inválido", invalid_od)

    return df
