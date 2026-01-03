"""Mapa resumen (muchas rutas) para checkpoint 2030.

Objetivo:
- Dibujar en UNA sola imagen muchas rutas MC vs MC2 (múltiples pares OD)
- Usar la red ya generada en data/raw/red.geojson (NO descargar OSM)
- Guardar:
  - debug_output/plots/checkpoint2030_routes_overview.png
  - debug_output/plots/checkpoint2030_routes_sample.csv (pares usados)

Uso (PowerShell):
    $env:DEBUG_OUTPUT_DIR="debug_output"; ./.venv/Scripts/python.exe scripts/debug_checkpoint2030_routes_overview.py

Parámetros opcionales:
  $env:ROUTE_SAMPLE_N="200"          (default: 200)
  $env:ROUTE_SAMPLE_SEED="2030"     (default: 2030)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import geopandas as gpd
import numpy as np
import pandas as pd

from kido_ruteo.processing.preprocessing import normalize_column_names, prepare_data
from kido_ruteo.processing.centroides import assign_nodes_to_zones, add_centroid_coordinates_to_od
from kido_ruteo.processing.checkpoint_loader import get_checkpoint_node_mapping
from kido_ruteo.routing.graph_loader import load_graph_from_geojson
from kido_ruteo.routing.shortest_path import compute_shortest_path_mc
from kido_ruteo.routing.constrained_path import compute_constrained_shortest_path, derive_sense_from_path
from kido_ruteo.utils.visual_debug import DebugVisualizer


def main() -> int:
    base_dir = Path(__file__).resolve().parents[1]
    data_dir = base_dir / "data"

    debug_output_dir = Path(os.environ.get("DEBUG_OUTPUT_DIR", "debug_output")).resolve()
    plots_dir = debug_output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    n = int(os.environ.get("ROUTE_SAMPLE_N", "200"))
    seed = int(os.environ.get("ROUTE_SAMPLE_SEED", "2030"))

    od_path = data_dir / "raw" / "queries" / "checkpoint" / "checkpoint2030.csv"
    zon_path = data_dir / "raw" / "zonification" / "zonification.geojson"
    net_path = data_dir / "raw" / "red.geojson"

    if not net_path.exists():
        raise FileNotFoundError(f"No existe red.geojson: {net_path}. Ya debería estar generado.")

    print(f"Cargando red desde: {net_path}")
    G = load_graph_from_geojson(str(net_path))

    print(f"Cargando zonificación: {zon_path}")
    zones = gpd.read_file(zon_path)
    zones = assign_nodes_to_zones(zones, G)

    print(f"Cargando OD: {od_path}")
    df = pd.read_csv(od_path)
    df = normalize_column_names(df)
    df = prepare_data(df)
    if "checkpoint_id" not in df.columns:
        df["checkpoint_id"] = "2030"

    # Filtrar 2030 y mapear nodos
    df = df[df["checkpoint_id"].astype(str).eq("2030")].copy()
    df = add_centroid_coordinates_to_od(df, zones)

    # Mapear checkpoint_node_id igual que pipeline
    cp_nodes = get_checkpoint_node_mapping(str(zon_path), G)
    cp_dict = dict(zip(cp_nodes["checkpoint_id"].astype(str), cp_nodes["checkpoint_node_id"]))
    cp_node = cp_dict.get("2030")
    if cp_node is None:
        raise ValueError("No se encontró checkpoint 2030 en zonification.geojson")
    df["checkpoint_node_id"] = cp_node

    # Validación intrazonal (actual): intrazonal_factor==1 si origin==destination (intrazonal)
    is_intraz = df["origin_id"].astype(str).eq(df["destination_id"].astype(str))
    mismatch = (is_intraz & (df["intrazonal_factor"] != 1)) | (~is_intraz & (df["intrazonal_factor"] != 0))
    if mismatch.any():
        print(f"ADVERTENCIA: intrazonal_factor no coincide en {int(mismatch.sum())} filas (revisar prepare_data)")

    # Elegir muestra de pares NO intrazonales con nodos válidos
    candidates = df[
        (~is_intraz)
        & df["origin_node_id"].notna()
        & df["destination_node_id"].notna()
        & df["checkpoint_node_id"].notna()
    ].copy()

    if candidates.empty:
        raise ValueError("No hay candidatos para graficar (revisar mapeo de nodos)")

    candidates = candidates.sample(n=min(n, len(candidates)), random_state=seed)

    routes_mc = []
    routes_mc2 = []
    origin_nodes = []
    dest_nodes = []

    rows_out = []

    print(f"Computing routes for sample N={len(candidates)} (this may take a few minutes)...")
    for _, r in candidates.iterrows():
        o_node = r["origin_node_id"]
        d_node = r["destination_node_id"]

        mc_path, mc_dist, _mc_time = compute_shortest_path_mc(G, o_node, d_node)
        mc2_path, mc2_dist = compute_constrained_shortest_path(G, o_node, d_node, cp_node)

        if mc_path:
            routes_mc.append(mc_path)
        if mc2_path:
            routes_mc2.append(mc2_path)

        origin_nodes.append(o_node)
        dest_nodes.append(d_node)

        sense_candidate = None
        if mc2_path:
            sense_candidate = derive_sense_from_path(G, mc2_path, str(cp_node))

        rows_out.append(
            {
                "origin_id": r.get("origin_id"),
                "destination_id": r.get("destination_id"),
                "trips_person": r.get("trips_person"),
                "intrazonal_factor": r.get("intrazonal_factor"),
                "mc_distance_m": mc_dist,
                "mc2_distance_m": mc2_dist,
                "sense_candidate": sense_candidate,
            }
        )

    df_out = pd.DataFrame(rows_out)
    csv_path = plots_dir / "checkpoint2030_routes_sample.csv"
    df_out.to_csv(csv_path, index=False)
    print(f"Saved sample list: {csv_path}")

    viz = DebugVisualizer(output_dir=str(plots_dir))
    # Baselayers for map-like output
    roads_gdf = gpd.read_file(net_path)

    # Filter zones to only those used by the OD (keeps the map readable)
    used_ids = set(pd.to_numeric(df['origin_id'], errors='coerce').dropna().astype(int).tolist())
    used_ids |= set(pd.to_numeric(df['destination_id'], errors='coerce').dropna().astype(int).tolist())
    used_ids |= {2030}
    zones_subset = zones
    if 'ID' in zones_subset.columns:
        zones_subset = zones_subset[zones_subset['ID'].isin(list(used_ids))].copy()

    out_png = plots_dir / "checkpoint2030_routes_overview_map.png"
    viz.plot_routes_overview_map(
        G=G,
        checkpoint_node=cp_node,
        routes_mc=routes_mc,
        routes_mc2=routes_mc2,
        roads_gdf=roads_gdf,
        zones_gdf=zones_subset,
        origin_nodes=origin_nodes,
        dest_nodes=dest_nodes,
        save_to=str(out_png),
        title=f"Checkpoint 2030 — Zonas + carreteras — MC (rojo) vs MC2 (azul) — {len(candidates)} pares",
    )

    print(f"OK: {out_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
