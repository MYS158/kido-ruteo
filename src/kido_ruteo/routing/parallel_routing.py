"""kido_ruteo.routing.parallel_routing

Cómputo paralelo de MC/MC2 usado SOLO para el modo debug del checkpoint 2030.

Motivación:
- Las rutas más cortas en NetworkX son cargas CPU-bound en Python (limitadas por el GIL en hilos).
- En Windows se requiere multiprocessing para usar múltiples núcleos.
- Esto se mantiene fuera del flujo normal/contractual salvo que se habilite explícitamente.

Notas:
- Cada worker carga el grafo desde GeoJSON una vez (en Windows, "spawn" no comparte memoria).
    Esto puede consumir mucha RAM con grafos grandes.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Iterable, Optional

import ast
import math
import os

import numpy as np
import pandas as pd

from .graph_loader import load_graph_from_geojson
from .shortest_path import compute_shortest_path_mc
from .constrained_path import compute_constrained_shortest_path, derive_sense_from_path, _load_valid_sense_codes


# Globales del worker (uno por proceso)
_G = None
_valid_sense_codes: set[str] | None = None


def _init_worker(network_path: str, sense_catalog_path: Optional[str]) -> None:
    global _G, _valid_sense_codes
    _G = load_graph_from_geojson(network_path)
    _valid_sense_codes = _load_valid_sense_codes(sense_catalog_path)


@dataclass(frozen=True)
class _Task:
    idx: int
    origin_node: object
    dest_node: object
    checkpoint_node: object


def _process_chunk(tasks: list[_Task]) -> list[dict]:
    global _G, _valid_sense_codes
    if _G is None or _valid_sense_codes is None:
        raise RuntimeError("Worker no inicializado (falta grafo/catálogo)")

    out: list[dict] = []

    for t in tasks:
        origin = t.origin_node
        dest = t.dest_node
        checkpoint = t.checkpoint_node

        if pd.isna(origin) or pd.isna(dest):
            out.append(
                {
                    "idx": t.idx,
                    "mc_path": None,
                    "mc_distance_m": 0.0,
                    "mc_time_h": 0.0,
                    "mc2_distance_m": 0.0,
                    "sense_code": np.nan,
                }
            )
            continue

        # MC
        mc_path, mc_dist, mc_time = compute_shortest_path_mc(_G, origin, dest)

        # MC2
        sense = np.nan
        mc2_dist = 0.0
        if not pd.isna(checkpoint):
            cp = str(checkpoint)
            mc2_path, mc2_dist_val = compute_constrained_shortest_path(_G, origin, dest, cp)
            if mc2_dist_val is not None:
                mc2_dist = float(mc2_dist_val)
            if mc2_path:
                candidate = derive_sense_from_path(_G, mc2_path, cp)
                if candidate == "0":
                    sense = "0"
                elif candidate and (candidate in _valid_sense_codes) and (candidate != "0"):
                    sense = candidate

        out.append(
            {
                "idx": t.idx,
                "mc_path": str(mc_path) if mc_path else None,
                "mc_distance_m": float(mc_dist) if mc_dist is not None else 0.0,
                "mc_time_h": float(mc_time) if mc_time is not None else 0.0,
                "mc2_distance_m": mc2_dist,
                "sense_code": sense,
            }
        )

    return out


def _chunked(it: Iterable[_Task], chunk_size: int) -> Iterable[list[_Task]]:
    chunk: list[_Task] = []
    for x in it:
        chunk.append(x)
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def compute_mc_and_mc2_parallel_debug2030(
    df_od: pd.DataFrame,
    network_path: str,
    checkpoint_node_col: str = "checkpoint_node_id",
    origin_node_col: str = "origin_node_id",
    dest_node_col: str = "destination_node_id",
    sense_catalog_path: Optional[str] = None,
    n_workers: int = 8,
    chunk_size: int = 200,
) -> pd.DataFrame:
    # Calcula MC + MC2 (+ sense_code) en paralelo.
    # Uso previsto: SOLO modo debug del checkpoint 2030.
    # Devuelve una copia de df_od con:
    #   - mc_path, mc_distance_m, mc_time_h
    #   - mc2_distance_m, sense_code

    if n_workers <= 1:
        # Fallback: secuencial usando funciones existentes (mantiene el comportamiento)
        from .shortest_path import compute_mc_matrix
        from .constrained_path import compute_mc2_matrix

        out = compute_mc_matrix(df_od, _G if _G is not None else load_graph_from_geojson(network_path))
        out = compute_mc2_matrix(out, _G if _G is not None else load_graph_from_geojson(network_path), checkpoint_col=checkpoint_node_col, origin_node_col=origin_node_col, dest_node_col=dest_node_col, sense_catalog_path=sense_catalog_path)
        return out

    df = df_od.copy()

    # Pre-crea salidas para preservar el orden de filas
    # NOTA: pandas infiere dtype float para `np.nan`, lo que luego rompe cuando
    # asignamos strings (FutureWarning hoy, error en futuras versiones).
    if "mc_path" not in df.columns:
        df["mc_path"] = pd.Series(index=df.index, dtype="object")
    if "sense_code" not in df.columns:
        df["sense_code"] = pd.Series(index=df.index, dtype="object")
    for col in ["mc_distance_m", "mc_time_h", "mc2_distance_m"]:
        if col not in df.columns:
            df[col] = np.nan

    tasks = (
        _Task(
            idx=int(i),
            origin_node=df.at[i, origin_node_col],
            dest_node=df.at[i, dest_node_col],
            checkpoint_node=df.at[i, checkpoint_node_col] if checkpoint_node_col in df.columns else np.nan,
        )
        for i in df.index
    )

    results: list[dict] = []

    # Process pool compatible con Windows
    with ProcessPoolExecutor(
        max_workers=n_workers,
        initializer=_init_worker,
        initargs=(str(network_path), sense_catalog_path),
    ) as ex:
        for chunk_out in ex.map(_process_chunk, _chunked(tasks, chunk_size)):
            results.extend(chunk_out)

    # Assign back
    for r in results:
        i = r["idx"]
        df.at[i, "mc_path"] = r["mc_path"]
        df.at[i, "mc_distance_m"] = r["mc_distance_m"]
        df.at[i, "mc_time_h"] = r["mc_time_h"]
        df.at[i, "mc2_distance_m"] = r["mc2_distance_m"]
        df.at[i, "sense_code"] = r["sense_code"]

    return df
