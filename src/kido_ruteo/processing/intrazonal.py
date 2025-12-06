"""Marcado de viajes intrazonales."""
from __future__ import annotations

import logging
from typing import Callable

import pandas as pd


logger = logging.getLogger(__name__)

def _normalize_name(name: str | None) -> str:
    if name is None:
        return ""
    return str(name).strip().casefold()

def marcar_intrazonales(df: pd.DataFrame, normalizador: Callable[[str | None], str] | None = None) -> pd.DataFrame:
    """Añade columna ``intrazonal`` (1 si origen == destino normalizado)."""
    if df.empty:
        return df

    norm = normalizador or _normalize_name
    df = df.copy()
    df["intrazonal"] = (
        df["origin_name"].apply(norm) == df["destination_name"].apply(norm)
    ).astype(int)
    return df
