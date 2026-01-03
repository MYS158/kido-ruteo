"""Ayuda de depuración: explica por qué veh_* queda en NaN para una consulta de checkpoint.

Uso:
    python scripts/debug_blank_vehicles.py 2030

Imprime un desglose de razones para filas donde todos los veh_* son NaN.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Asegurar que src/ sea importable al ejecutar como script
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import geopandas as gpd
import numpy as np
import pandas as pd

from kido_ruteo.capacity.loader import load_capacity_data
from kido_ruteo.capacity.matcher import match_capacity_to_od
from kido_ruteo.congruence.classification import classify_congruence
from kido_ruteo.processing.checkpoint_loader import get_checkpoint_node_mapping
from kido_ruteo.processing.centroides import add_centroid_coordinates_to_od, assign_nodes_to_zones
from kido_ruteo.processing.preprocessing import normalize_column_names, prepare_data
from kido_ruteo.routing.constrained_path import compute_mc2_matrix
from kido_ruteo.routing.graph_loader import load_graph_from_geojson
from kido_ruteo.routing.shortest_path import compute_mc_matrix
from kido_ruteo.trips.calculation import calculate_vehicle_trips


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python scripts/debug_blank_vehicles.py <checkpoint_id>")
        return 2

    checkpoint_id = str(sys.argv[1]).strip()

    base = Path(__file__).resolve().parents[1]
    raw_od = base / "data" / "raw" / "queries" / "checkpoint" / f"checkpoint{checkpoint_id}.csv"
    zon = base / "data" / "raw" / "zonification" / "zonification.geojson"
    net = base / "data" / "raw" / "red.geojson"
    cap = base / "data" / "raw" / "capacity" / "summary_capacity.csv"

    print(f"Cargando OD: {raw_od}")
    df = pd.read_csv(raw_od)
    df = normalize_column_names(df)
    df = prepare_data(df)

    if "checkpoint_id" not in df.columns:
        df["checkpoint_id"] = checkpoint_id

    # Graph + zones + checkpoints
    G = load_graph_from_geojson(str(net))

    zones = gpd.read_file(zon)
    zones = assign_nodes_to_zones(zones, G)
    df = add_centroid_coordinates_to_od(df, zones)

    cp_nodes = get_checkpoint_node_mapping(str(zon), G)
    cp_dict = dict(zip(cp_nodes["checkpoint_id"].astype(str), cp_nodes["checkpoint_node_id"]))
    df["checkpoint_node_id"] = df["checkpoint_id"].astype(str).map(cp_dict)

    # Ruteo
    print("Ruteando MC/MC2...")
    df = compute_mc_matrix(df, G)
    df = compute_mc2_matrix(
        df,
        G,
        checkpoint_col="checkpoint_node_id",
        origin_node_col="origin_node_id",
        dest_node_col="destination_node_id",
    )
    df["has_valid_path"] = (
        (df["mc_distance_m"] > 0)
        & (df["mc2_distance_m"] > 0)
        & df["mc2_distance_m"].notna()
    )

    # Capacity + congruence + vehicles
    cap_df = load_capacity_data(str(cap))
    df = match_capacity_to_od(df, cap_df)
    df = classify_congruence(df)
    df = calculate_vehicle_trips(df)

    veh_cols = ["veh_M", "veh_A", "veh_B", "veh_CU", "veh_CAI", "veh_CAII", "veh_total"]
    blank = df[veh_cols].isna().all(axis=1)

    print(f"\nRows: {len(df)}")
    print(f"Rows with ALL veh_* blank: {int(blank.sum())}")

    invalid_route = ~df["has_valid_path"].fillna(False)

    directional = (
        df.get("checkpoint_is_directional", pd.Series([True] * len(df), index=df.index))
        .astype("boolean")
        .fillna(True)
    )
    invalid_sense = directional & (
        df["sense_code"].isna() | df["sense_code"].astype("string").eq("0")
    )

    invalid_cap = df["cap_total"].isna()
    zero_cap = df["cap_total"].eq(0)

    eligible = df["cap_total"].notna() & (df["cap_total"] > 0) & (df["congruence_id"] != 4)

    cats = ["M", "A", "B", "CU", "CAI", "CAII"]
    fa_missing = df["fa"].isna()
    needs_den = pd.Series(False, index=df.index)
    for c in cats:
        capc = df[f"cap_{c}"]
        foc = df[f"focup_{c}"]
        needs_den = needs_den | (capc.notna() & (capc > 0) & (foc.isna() | (foc <= 0)))

    reasons = {
        "invalid_route": int((blank & invalid_route).sum()),
        "invalid_sense": int((blank & ~invalid_route & invalid_sense).sum()),
        "missing_capacity": int((blank & ~invalid_route & ~invalid_sense & invalid_cap).sum()),
        "zero_capacity": int((blank & ~invalid_route & ~invalid_sense & ~invalid_cap & zero_cap).sum()),
        "eligible_but_missing_fa_or_focup": int((blank & eligible & (fa_missing | needs_den)).sum()),
    }

    print("\nReason breakdown (among rows with ALL veh_* blank):")
    for k, v in sorted(reasons.items(), key=lambda kv: kv[1], reverse=True):
        print(f"  {k}: {v}")

    # Print a small sample for the top reasons
    def show_sample(title: str, mask: pd.Series) -> None:
        if not mask.any():
            return
        cols = [
            "origin_id",
            "destination_id",
            "intrazonal_factor",
            "mc_distance_m",
            "mc2_distance_m",
            "sense_code",
            "checkpoint_is_directional",
            "cap_total",
            "fa",
            "congruence_id",
        ]
        cols = [c for c in cols if c in df.columns]
        print(f"\nSample rows for {title}:")
        print(df.loc[mask, cols].head(8).to_string(index=False))

    show_sample("invalid_route", blank & invalid_route)
    show_sample("invalid_sense", blank & ~invalid_route & invalid_sense)
    show_sample("missing_capacity", blank & ~invalid_route & ~invalid_sense & invalid_cap)

    intraz = df.get("intrazonal_factor", pd.Series([1] * len(df), index=df.index)).eq(0)
    print(f"\nIntrazonal rows: {int(intraz.sum())} ; intrazonal & blank veh: {int((intraz & blank).sum())}")

    if "origin_node_id" in df.columns and "destination_node_id" in df.columns:
        same_node = df["origin_node_id"].notna() & df["destination_node_id"].notna() & df["origin_node_id"].eq(df["destination_node_id"])
        print(
            "Origin/Destination mapped to SAME graph node:",
            int(same_node.sum()),
            "; among blank veh rows:",
            int((same_node & blank).sum()),
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
