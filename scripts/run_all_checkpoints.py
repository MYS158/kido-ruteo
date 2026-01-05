r"""Ejecuta el pipeline para todas las queries tipo checkpoint.

- Recorre data/raw/queries/checkpoint/checkpoint*.csv
- Ejecuta kido_ruteo.pipeline.run_pipeline en modo NORMAL (STRICT contractual)
- Escribe processed_checkpointXXXX.csv en data/processed/

Uso (PowerShell):
  ./.venv/Scripts/python.exe scripts/run_all_checkpoints.py

Opcionales:
  - Procesar solo algunos (regex):
      ./.venv/Scripts/python.exe scripts/run_all_checkpoints.py --pattern "checkpoint2030\.csv$"
  - Dry-run (solo lista lo que correría):
      ./.venv/Scripts/python.exe scripts/run_all_checkpoints.py --dry-run
  - ROI manual (restringe red y cálculo a un bbox lon/lat):
      ./.venv/Scripts/python.exe scripts/run_all_checkpoints.py --roi bbox --roi-bbox "-99.5,19.0,-98.5,20.0"
  - ROI auto (elige la celda con más zonas/subzonas):
      ./.venv/Scripts/python.exe scripts/run_all_checkpoints.py --roi auto

  - Usar 8 workers (default):
      ./.venv/Scripts/python.exe scripts/run_all_checkpoints.py --workers 8

Nota importante:
  Este runner fuerza a desactivar el debug focalizado (DEBUG_CHECKPOINT_ID)
  para evitar que un entorno "contaminado" (p.ej. DEBUG_CHECKPOINT_ID=2030)
  filtre/altere el procesamiento batch.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Optional, Tuple


def _render_progress(current: int, total: int, *, width: int = 28) -> str:
    if total <= 0:
        total = 1
    current = max(0, min(current, total))
    frac = current / total
    filled = int(round(frac * width))
    bar = "#" * filled + "-" * (width - filled)
    return f"[{bar}] {current}/{total} ({frac*100:5.1f}%)"


def _parse_roi_bbox(value: str) -> Tuple[float, float, float, float]:
    parts = [p.strip() for p in value.split(",") if p.strip()]
    if len(parts) != 4:
        raise ValueError('ROI bbox debe ser "west,south,east,north" (4 números).')
    west, south, east, north = map(float, parts)
    if not (west < east and south < north):
        raise ValueError("ROI bbox inválido: se requiere west<east y south<north")
    return west, south, east, north


def _infer_roi_bbox_auto(
    zonification_path: Path,
    *,
    tile_deg: float,
    small_zone_quantile: float,
    padding_deg: float,
    only_core: bool = True,
) -> Tuple[float, float, float, float]:
    import geopandas as gpd
    import numpy as np

    zones = gpd.read_file(zonification_path)
    if zones.empty:
        raise ValueError(f"Zonification vacío: {zonification_path}")
    if zones.crs is None:
        raise ValueError(f"Zonification sin CRS: {zonification_path}")

    if (not zones.crs.is_geographic) or (str(zones.crs).upper() != "EPSG:4326"):
        zones = zones.to_crs("EPSG:4326")

    if only_core and "poly_type" in zones.columns:
        zones = zones[zones["poly_type"].astype(str).str.lower() == "core"].copy()
        if zones.empty:
            raise ValueError("No hay zonas Core para inferir ROI auto")

    # Para identificar el "foco con más subzonas", contamos cuántas zonas caen en
    # cada celda (por centroides). Opcionalmente, se puede restringir a zonas
    # "pequeñas" por un cuantil de área.
    zones_m = zones.to_crs("EPSG:3857")
    areas = zones_m.geometry.area
    q = float(np.clip(small_zone_quantile, 0.01, 1.0))
    if q < 1.0:
        thr = float(areas.quantile(q))
        zones_m = zones_m[areas <= thr].copy()
        if zones_m.empty:
            raise ValueError("ROI auto: no se detectaron zonas con el filtro de tamaño")

    zones_m["_centroid"] = zones_m.geometry.centroid
    cent = gpd.GeoDataFrame(zones_m[["_centroid"]], geometry="_centroid", crs=zones_m.crs).to_crs(
        "EPSG:4326"
    )
    lons = cent.geometry.x.to_numpy()
    lats = cent.geometry.y.to_numpy()

    min_lon = float(lons.min())
    min_lat = float(lats.min())
    gx = np.floor((lons - min_lon) / tile_deg).astype(int)
    gy = np.floor((lats - min_lat) / tile_deg).astype(int)
    # Contar celdas
    keys = gx.astype(str) + ":" + gy.astype(str)
    uniq, counts = np.unique(keys, return_counts=True)
    best_key = uniq[int(counts.argmax())]
    best_gx, best_gy = map(int, best_key.split(":"))

    west = min_lon + best_gx * tile_deg
    east = west + tile_deg
    south = min_lat + best_gy * tile_deg
    north = south + tile_deg

    west -= padding_deg
    south -= padding_deg
    east += padding_deg
    north += padding_deg
    return float(west), float(south), float(east), float(north)


def _unset_debug_env() -> None:
    # Evita activar el modo debug focalizado por accidente.
    for k in [
        "DEBUG_CHECKPOINT_ID",
        "DEBUG_OUTPUT_DIR",
        "DEBUG_OD_LIMIT",
        "DEBUG_MAX_ROUTE_PLOTS",
        "KIDO_DEBUG_N_WORKERS",
        "KIDO_DEBUG_CHUNK_SIZE",
    ]:
        os.environ.pop(k, None)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pattern",
        default=r"checkpoint\d+\.csv$",
        help="Regex (sobre el nombre de archivo) para filtrar checkpoints a correr.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo lista archivos a procesar, no ejecuta el pipeline.",
    )
    parser.add_argument(
        "--limit-pairs",
        type=int,
        default=100,
        help=(
            "Procesa solo los primeros N pares OD por checkpoint para una corrida rápida. "
            "Use 0 para desactivar el límite. Default: 100."
        ),
    )
    parser.add_argument(
        "--roi",
        choices=["none", "bbox", "auto"],
        default="none",
        help="Restringe red y cálculo a una región de interés (ROI).",
    )
    parser.add_argument(
        "--roi-bbox",
        default=None,
        help='BBox ROI en grados EPSG:4326 con formato "west,south,east,north" (solo con --roi bbox).',
    )
    parser.add_argument(
        "--roi-tile-deg",
        type=float,
        default=1.0,
        help="(ROI auto) Tamaño de celda en grados para buscar la zona más densa. Default: 1.0.",
    )
    parser.add_argument(
        "--roi-small-quantile",
        type=float,
        default=1.0,
        help=(
            "(ROI auto) Cuantil de áreas para filtrar 'zonas pequeñas'. "
            "Use 1.0 para considerar todas las zonas. Default: 1.0."
        ),
    )
    parser.add_argument(
        "--roi-padding-deg",
        type=float,
        default=0.25,
        help="(ROI auto/bbox) Padding extra en grados. Default: 0.25.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Número de workers para ruteo paralelo (MC/MC2). Default: 8.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=200,
        help="Tamaño de chunk para enviar tareas a cada worker. Default: 200.",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parents[1]

    od_dir = base_dir / "data" / "raw" / "queries" / "checkpoint"
    zonification_path = base_dir / "data" / "raw" / "zonification" / "zonification.geojson"
    network_path = base_dir / "data" / "raw" / "red.geojson"
    focus_network_path = base_dir / "data" / "raw" / "red_focus.geojson"
    capacity_path = base_dir / "data" / "raw" / "capacity" / "summary_capacity.csv"
    output_dir = base_dir / "data" / "processed"

    for p in [od_dir, zonification_path, network_path, capacity_path]:
        if not p.exists():
            raise FileNotFoundError(f"No existe insumo requerido: {p}")

    roi_bbox: Optional[Tuple[float, float, float, float]] = None  # west,south,east,north
    if args.roi == "bbox":
        if not args.roi_bbox:
            raise ValueError("--roi bbox requiere --roi-bbox")
        west, south, east, north = _parse_roi_bbox(args.roi_bbox)
        pad = float(args.roi_padding_deg)
        roi_bbox = (west - pad, south - pad, east + pad, north + pad)
    elif args.roi == "auto":
        roi_bbox = _infer_roi_bbox_auto(
            zonification_path,
            tile_deg=float(args.roi_tile_deg),
            small_zone_quantile=float(args.roi_small_quantile),
            padding_deg=float(args.roi_padding_deg),
            only_core=True,
        )

    rx = re.compile(args.pattern)
    od_files = sorted([p for p in od_dir.iterdir() if p.is_file() and rx.search(p.name)])

    if not od_files:
        print(f"No se encontraron archivos que matcheen --pattern={args.pattern!r} en {od_dir}")
        return 2

    print(f"Encontrados {len(od_files)} checkpoint CSVs")
    for p in od_files:
        print(f"- {p.name}")

    if args.dry_run:
        print("\nDRY-RUN: no se ejecutó nada.")
        return 0

    # Import tardío para que el script pueda listar sin depender de imports
    import sys

    sys.path.insert(0, str(base_dir / "src"))

    import pandas as pd

    from kido_ruteo.processing.preprocessing import normalize_column_names, prepare_data
    from kido_ruteo.processing.centroides import assign_nodes_to_zones, add_centroid_coordinates_to_od
    from kido_ruteo.processing.checkpoint_loader import get_checkpoint_node_mapping
    from kido_ruteo.routing.graph_loader import ensure_graph_from_geojson_or_osm, load_graph_from_geojson
    from kido_ruteo.routing.parallel_routing import ParallelRoutingSession
    from kido_ruteo.capacity.loader import load_capacity_data
    from kido_ruteo.capacity.matcher import match_capacity_to_od
    from kido_ruteo.congruence.classification import classify_congruence
    from kido_ruteo.trips.calculation import calculate_vehicle_trips

    _unset_debug_env()
    output_dir.mkdir(parents=True, exist_ok=True)

    limit_pairs = int(args.limit_pairs)
    if limit_pairs < 0:
        raise ValueError("--limit-pairs debe ser >= 0")
    if limit_pairs > 0:
        print(f"\n[Batch] Modo rápido: usando solo los primeros {limit_pairs} pares OD por checkpoint")

    # 1) Preparar grafo.
    #    IMPORTANTE: con ROI desactivado, NO intentamos re-descargar una red que cubra
    #    toda la zonificación (bbox enorme -> inviable con Overpass). En su lugar,
    #    se usa el red.geojson existente tal cual.
    if roi_bbox is None:
        print("\n[Batch] Cargando grafo desde red.geojson (sin re-descarga OSM)...")
        G = load_graph_from_geojson(str(network_path))
    else:
        west, south, east, north = roi_bbox
        print(
            "\n[Batch] ROI activo: bbox west={:.6f}, south={:.6f}, east={:.6f}, north={:.6f}".format(
                west, south, east, north
            )
        )
        # graph_loader espera [north, south, east, west]
        osm_bbox = [north, south, east, west]

        # Con ROI, generamos/validamos una red dedicada y "centralizada" al foco.
        # Esto evita tocar la red nacional (red.geojson) y permite que el foco sea detallado.
        G = ensure_graph_from_geojson_or_osm(
            geojson_path=str(focus_network_path),
            zonification_path=str(zonification_path),
            osm_bbox=osm_bbox,
            network_type="drive",
        )

        # A partir de aquí, todos los procesos del pool deben usar el MISMO archivo.
        network_path = focus_network_path

    # 2) Cargar zonificación (o subset ROI) y asignar nodos UNA sola vez.
    print("[Batch] Cargando zonificación y asignando nodos a zonas (una vez)...")
    import geopandas as gpd
    from shapely.geometry import box

    zones_gdf = gpd.read_file(zonification_path)
    if zones_gdf.crs is None:
        raise ValueError(f"Zonification sin CRS: {zonification_path}")
    if (not zones_gdf.crs.is_geographic) or (str(zones_gdf.crs).upper() != "EPSG:4326"):
        zones_gdf = zones_gdf.to_crs("EPSG:4326")

    zones_in_roi: Optional[set[int]] = None
    checkpoints_in_roi: Optional[set[int]] = None
    if roi_bbox is not None:
        west, south, east, north = roi_bbox
        roi_poly = box(west, south, east, north)

        # Zonas de interés: zonas cuyo polígono intersecta el ROI.
        zones_roi = zones_gdf[zones_gdf.geometry.intersects(roi_poly)].copy()
        if zones_roi.empty:
            raise ValueError("ROI no intersecta ninguna zona de la zonificación")
        if "ID" not in zones_roi.columns:
            raise ValueError("Zonification no tiene columna 'ID'")
        zones_in_roi = set(int(x) for x in zones_roi["ID"].dropna().astype(int).tolist())
        zones_gdf = zones_roi

        # Checkpoints dentro del ROI (para decidir si un checkpoint CSV se procesa o se llena con ceros)
        if "poly_type" in zones_gdf.columns and "NOMGEO" in zones_gdf.columns:
            pass
        all_zones_full = gpd.read_file(zonification_path)
        if all_zones_full.crs is None:
            raise ValueError(f"Zonification sin CRS: {zonification_path}")
        if (not all_zones_full.crs.is_geographic) or (str(all_zones_full.crs).upper() != "EPSG:4326"):
            all_zones_full = all_zones_full.to_crs("EPSG:4326")
        cp = all_zones_full[all_zones_full.get("poly_type") == "Checkpoint"].copy()
        if not cp.empty and "ID" in cp.columns:
            cp_m = cp.to_crs("EPSG:3857")
            cp_m["geometry"] = cp_m.geometry.centroid
            cp_pts = cp_m.to_crs("EPSG:4326")
            cp_in = cp_pts[cp_pts.geometry.within(roi_poly)]
            checkpoints_in_roi = set(int(x) for x in cp_in["ID"].dropna().astype(int).tolist())
        else:
            checkpoints_in_roi = set()

    zones_gdf = assign_nodes_to_zones(zones_gdf, G)

    # 3) Cargar mapping de checkpoints UNA sola vez.
    print("[Batch] Cargando checkpoints desde zonification.geojson (una vez)...")
    checkpoint_nodes = get_checkpoint_node_mapping(str(zonification_path), G)
    if checkpoints_in_roi is not None and len(checkpoints_in_roi) > 0:
        checkpoint_nodes = checkpoint_nodes[
            checkpoint_nodes["checkpoint_id"].astype(int).isin(list(checkpoints_in_roi))
        ].copy()
    checkpoint_node_dict = dict(
        zip(checkpoint_nodes["checkpoint_id"].astype(str), checkpoint_nodes["checkpoint_node_id"])
    )

    # 4) Cargar capacidad UNA sola vez.
    print("[Batch] Cargando summary_capacity.csv (una vez)...")
    df_cap = load_capacity_data(str(capacity_path))

    ok = 0
    failed: list[tuple[str, str]] = []

    # 5) Sesión paralela reutilizable: 8 workers (por defecto)
    #    En Windows cada worker tendrá su copia del grafo, pero esto ocurre UNA vez
    #    para todo el batch, no por cada checkpoint.
    print(f"[Batch] Iniciando ruteo paralelo: workers={args.workers} chunk={args.chunk_size}")
    with ParallelRoutingSession(
        network_path=str(network_path),
        sense_catalog_path=None,
        n_workers=int(args.workers),
        chunk_size=int(args.chunk_size),
    ) as session:
        for i, od_path in enumerate(od_files, start=1):
            print(_render_progress(i - 1, len(od_files)))
            print(f"\n[{i}/{len(od_files)}] Procesando: {od_path.name}")
            try:
                df_od = pd.read_csv(od_path)
                df_od = normalize_column_names(df_od)

                if limit_pairs > 0 and len(df_od) > limit_pairs:
                    df_od = df_od.head(limit_pairs).copy()

                # Inferir checkpoint_id del nombre de archivo si no existe
                if "checkpoint_id" not in df_od.columns:
                    m = re.search(r"checkpoint(\d+)", od_path.name, re.IGNORECASE)
                    if m:
                        df_od["checkpoint_id"] = m.group(1)
                    else:
                        raise ValueError(f"No se pudo inferir checkpoint_id desde: {od_path.name}")

                checkpoint_id_str = str(df_od["checkpoint_id"].iloc[0])

                # Si ROI está activo y este checkpoint está fuera, generar salida en ceros y saltar.
                if roi_bbox is not None:
                    if checkpoint_id_str not in checkpoint_node_dict:
                        prefix = "processed_preview" if limit_pairs > 0 else "processed"
                        out_path = output_dir / f"{prefix}_{od_path.name}"
                        df_out = pd.DataFrame(
                            {
                                "Origen": pd.to_numeric(df_od.get("origin_id"), errors="coerce"),
                                "Destino": pd.to_numeric(df_od.get("destination_id"), errors="coerce"),
                            }
                        )
                        for c in ["veh_M", "veh_A", "veh_B", "veh_CU", "veh_CAI", "veh_CAII", "veh_total"]:
                            df_out[c] = 0.0
                        df_out.to_csv(out_path, index=False)
                        ok += 1
                        print(f"ROI: checkpoint fuera -> ceros: {out_path}")
                        continue

                # ROI: calcular solo pares OD dentro del ROI; el resto se llena con ceros.
                # Sin ROI: se calcula todo.
                origin_ids = pd.to_numeric(df_od.get("origin_id"), errors="coerce")
                dest_ids = pd.to_numeric(df_od.get("destination_id"), errors="coerce")
                df_out = pd.DataFrame({"Origen": origin_ids, "Destino": dest_ids})
                for c in ["veh_M", "veh_A", "veh_B", "veh_CU", "veh_CAI", "veh_CAII", "veh_total"]:
                    df_out[c] = 0.0

                if zones_in_roi is not None:
                    mask = origin_ids.astype("Int64").isin(list(zones_in_roi)) & dest_ids.astype("Int64").isin(
                        list(zones_in_roi)
                    )
                else:
                    mask = pd.Series(True, index=df_od.index)

                if mask.any():
                    df_in = df_od.loc[mask].copy()

                    # STRICT: preparar trips_person e intrazonal_factor
                    df_in = prepare_data(df_in)

                    # Centroides: reutiliza zones_gdf ya con nodos asignados (subset ROI si aplica)
                    df_in = add_centroid_coordinates_to_od(df_in, zones_gdf)

                    # Mapear checkpoint_node_id
                    df_in["checkpoint_node_id"] = df_in["checkpoint_id"].astype(str).map(checkpoint_node_dict)

                    # Routing (MC + MC2 + sense_code) con pool reutilizado
                    df_in = session.compute(
                        df_in,
                        checkpoint_node_col="checkpoint_node_id",
                        origin_node_col="origin_node_id",
                        dest_node_col="destination_node_id",
                    )

                    # Validar rutas (igual que pipeline)
                    df_in["has_valid_path"] = (
                        (df_in["mc_distance_m"] > 0)
                        & (df_in["mc2_distance_m"] > 0)
                        & df_in["mc2_distance_m"].notna()
                    )

                    # Capacidad + congruencia + vehículos
                    df_in = match_capacity_to_od(df_in, df_cap)
                    df_in = classify_congruence(df_in)
                    df_in = calculate_vehicle_trips(df_in)

                    # Volcar vehículos calculados al output final, preservando el orden original
                    for c in ["veh_M", "veh_A", "veh_B", "veh_CU", "veh_CAI", "veh_CAII", "veh_total"]:
                        if c in df_in.columns:
                            df_out.loc[df_in.index, c] = df_in[c].astype(float).to_numpy()

                prefix = "processed_preview" if limit_pairs > 0 else "processed"
                out_path = output_dir / f"{prefix}_{od_path.name}"
                df_out.to_csv(out_path, index=False)
                ok += 1
                print(f"OK -> {out_path}")
            except Exception as e:
                failed.append((od_path.name, repr(e)))
                print(f"FAIL -> {od_path.name}: {e}")

            print(_render_progress(i, len(od_files)))

    print("\nResumen:")
    print(f"- OK: {ok}")
    print(f"- FAIL: {len(failed)}")
    if failed:
        print("\nFallos:")
        for name, err in failed:
            print(f"- {name}: {err}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
