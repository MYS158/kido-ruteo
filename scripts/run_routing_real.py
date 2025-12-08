"""Ejecuta routing real con remapeo de nodos fuera del grafo.

Pasos:
1) Carga OD asignados con nodos.
2) Remapea nodos que no están en edges.gpkg al nodo conectado más cercano.
3) Corre pipeline de routing y guarda resultados en data/processed/routing/routing_results.csv.
4) Guarda tabla mapping_missing_nodes.csv con remapeos aplicados.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.ops import nearest_points

from kido_ruteo.routing.routing_pipeline import run_routing_pipeline

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
INTERIM_OD = DATA_DIR / "interim" / "kido_interim_with_nodes.csv"
NETWORK_DIR = DATA_DIR / "network" / "synthetic"
OUTPUT_DIR = DATA_DIR / "processed" / "routing"


def load_inputs() -> tuple[pd.DataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    df_od = pd.read_csv(INTERIM_OD)
    gdf_nodes = gpd.read_file(NETWORK_DIR / "nodes.gpkg")
    gdf_edges = gpd.read_file(NETWORK_DIR / "edges.gpkg")
    return df_od, gdf_nodes, gdf_edges


def build_remap(gdf_nodes: gpd.GeoDataFrame, graph_nodes: set[int]) -> dict[int, int]:
    """Mapea nodos fuera del grafo al nodo conectado más cercano."""
    gdf_connected = gdf_nodes[gdf_nodes["node_id"].isin(graph_nodes)].copy()
    gdf_missing = gdf_nodes[~gdf_nodes["node_id"].isin(graph_nodes)].copy()

    if gdf_missing.empty:
        return {}

    # Índice espacial simple; dataset pequeño, distancia lineal basta
    remap: dict[int, int] = {}
    for _, row in gdf_missing.iterrows():
        geom = row.geometry
        # Encontrar candidato más cercano
        nearest_idx = gdf_connected.distance(geom).idxmin()
        remap[row["node_id"]] = int(gdf_connected.loc[nearest_idx, "node_id"])
    return remap


def apply_remap(df_od: pd.DataFrame, remap: dict[int, int]) -> pd.DataFrame:
    if not remap:
        return df_od
    df = df_od.copy()
    df["origin_node_id"] = df["origin_node_id"].replace(remap)
    df["destination_node_id"] = df["destination_node_id"].replace(remap)
    return df


def main() -> None:
    df_od, gdf_nodes, gdf_edges = load_inputs()
    graph_nodes = set(gdf_edges["u"]).union(set(gdf_edges["v"]))

    remap = build_remap(gdf_nodes, graph_nodes)
    if remap:
        print(f"Remapeando {len(remap)} nodos fuera del grafo")
    df_remapped = apply_remap(df_od[["origin_node_id", "destination_node_id"]], remap)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if remap:
        pd.DataFrame([
            {"missing_node_id": k, "mapped_to_node_id": v}
            for k, v in remap.items()
        ]).to_csv(OUTPUT_DIR / "mapping_missing_nodes.csv", index=False)

    res = run_routing_pipeline(
        network_path=NETWORK_DIR,
        df_od=df_remapped,
        gdf_nodes=gdf_nodes,
        gdf_edges=gdf_edges,
        output_dir=OUTPUT_DIR,
    )
    print(res.head())
    print(f"rows {len(res)} errors {(res['error'].notna().sum() if 'error' in res else 0)}")


if __name__ == "__main__":
    main()
