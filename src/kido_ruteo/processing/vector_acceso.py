"""Generación de vectores de acceso y validación de zonas."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Set

import pandas as pd


logger = logging.getLogger(__name__)

def _is_clean_zone(value: Any) -> bool:
    if value is None:
        return False
    s = str(value).strip()
    if not s:
        return False
    # Acepta alfanumérico; marcamos raro si tiene caracteres de control.
    return all(ch.isalnum() or ch in {"_", "-", " "} for ch in s)

def generar_vectores_acceso(df: pd.DataFrame) -> pd.DataFrame:
    """Crea vectores de zonas origen/destino y marca ``acceso_valido``.

    - V1: zonas origen únicas
    - V2: zonas destino únicas
    - acceso_valido = True si ambas zonas son limpias y existen en V1/V2
    """
    if df.empty:
        logger.warning("DataFrame vacío en generar_vectores_acceso")
        return df

    df = df.copy()

    V1: Set[str] = set(df["origin_id"].astype(str).str.strip())
    V2: Set[str] = set(df["destination_id"].astype(str).str.strip())

    def _valid_row(row: pd.Series) -> bool:
        o = str(row["origin_id"]).strip()
        d = str(row["destination_id"]).strip()
        ok = _is_clean_zone(o) and _is_clean_zone(d)
        ok &= o in V1 and d in V2
        return ok

    df["acceso_valido"] = df.apply(_valid_row, axis=1)

    # Registro de errores comunes.
    errores: Dict[str, int] = {
        "zona_origen_invalida": (~df["origin_id"].astype(str).str.strip().apply(_is_clean_zone)).sum(),
        "zona_destino_invalida": (~df["destination_id"].astype(str).str.strip().apply(_is_clean_zone)).sum(),
        "acceso_invalido": (~df["acceso_valido"]).sum(),
    }
    for k, v in errores.items():
        if v:
            logger.warning("%s: %s", k, v)

    return df
