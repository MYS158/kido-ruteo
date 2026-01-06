"""
Orquestador maestro del pipeline KIDO.
"""

import pandas as pd
import numpy as np
import geopandas as gpd
import os
import logging
import ast
from pathlib import Path
from .processing.preprocessing import prepare_data, normalize_column_names
from .processing.centrality import build_network_graph
from .processing.centroides import assign_nodes_to_zones, add_centroid_coordinates_to_od
from .processing.checkpoint_loader import get_checkpoint_node_mapping
from .routing.graph_loader import ensure_graph_from_geojson_or_osm
from .routing.shortest_path import compute_mc_matrix
from .routing.constrained_path import compute_mc2_matrix
from .routing.parallel_routing import compute_mc_and_mc2_parallel_debug2030
from .capacity.loader import load_capacity_data
from .capacity.matcher import match_capacity_to_od
from .congruence.classification import classify_congruence
from .trips.calculation import calculate_vehicle_trips
from .routing.constrained_path import compute_constrained_shortest_path, calculate_bearing, get_cardinality
from .utils.visual_debug import DebugVisualizer

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_pipeline(
    od_path: str,
    zonification_path: str,
    network_path: str,
    capacity_path: str,
    output_dir: str,
    osm_bbox: list = None
):
    """
    Ejecuta el pipeline completo KIDO con la nueva arquitectura modular.
    
    Args:
        od_path: Ruta al archivo OD (CSV)
        zonification_path: Ruta al archivo de zonificación (GeoJSON)
        network_path: Ruta al archivo de red vial (GeoJSON)
        capacity_path: Ruta al archivo de capacidad (CSV)
        output_dir: Directorio de salida
        osm_bbox: Lista [north, south, east, west] para descargar de OSM si no existe red.
    """
    logger.info("🚀 Iniciando Pipeline KIDO...")

    # --- Debug focalizado (solo checkpoint 2030) ---
    debug_checkpoint_id = os.environ.get('DEBUG_CHECKPOINT_ID')
    debug_enabled = bool(debug_checkpoint_id)
    if debug_enabled:
        debug_checkpoint_id = str(debug_checkpoint_id).strip()
        debug_output_dir = Path(os.environ.get('DEBUG_OUTPUT_DIR', 'debug_output')).resolve()
        debug_plots_dir = debug_output_dir / 'plots'
        debug_output_dir.mkdir(parents=True, exist_ok=True)
        debug_plots_dir.mkdir(parents=True, exist_ok=True)
        debug_max_route_plots = int(os.environ.get('DEBUG_MAX_ROUTE_PLOTS', '20'))
        logger.info(
            "🧪 DEBUG focalizado activado: checkpoint_id=%s | output=%s",
            debug_checkpoint_id,
            str(debug_output_dir),
        )
    
    # Crear directorio de salida
    os.makedirs(output_dir, exist_ok=True)
    
    # --- Paso 1: Carga y Preprocesamiento OD ---
    logger.info("[Paso 1] Carga y Preprocesamiento OD")
    df_od = pd.read_csv(od_path)
    df_od = normalize_column_names(df_od)
    
    # Inferir checkpoint_id del nombre de archivo si no existe
    if 'checkpoint_id' not in df_od.columns:
        filename = os.path.basename(od_path)
        # Intentar extraer número del nombre (ej: checkpoint2001.csv -> 2001)
        import re
        match = re.search(r'checkpoint(\d+)', filename, re.IGNORECASE)
        if match:
            checkpoint_id = match.group(1)
            df_od['checkpoint_id'] = checkpoint_id
            logger.info(f"Checkpoint ID inferido del archivo: {checkpoint_id}")
        else:
            logger.warning("No se pudo inferir checkpoint_id del nombre de archivo. Se asume Query GENERAL.")
            
    is_general_query = 'checkpoint_id' not in df_od.columns

    # STRICT MODE: Sense is handled in normalize_column_names
    # No need for duplicate check here
    df_od = prepare_data(df_od)

    # DEBUG focalizado: filtrar SOLO checkpoint solicitado (sin afectar runs normales)
    if debug_enabled:
        if 'checkpoint_id' not in df_od.columns:
            df_od['checkpoint_id'] = debug_checkpoint_id
        before = len(df_od)
        df_od = df_od[df_od['checkpoint_id'].astype(str).eq(debug_checkpoint_id)].copy()
        after = len(df_od)
        logger.info("🧪 DEBUG: filtrado OD por checkpoint_id==%s (%s → %s filas)", debug_checkpoint_id, before, after)

        debug_limit = os.environ.get('DEBUG_OD_LIMIT')
        if debug_limit:
            n_lim = int(str(debug_limit).strip())
            if n_lim > 0 and len(df_od) > n_lim:
                df_od = df_od.head(n_lim).copy()
                logger.info("🧪 DEBUG: aplicando DEBUG_OD_LIMIT=%s (filas=%s)", n_lim, len(df_od))

    # STRICT MODE: Queries generales => salida determinista con ceros (NaN ≠ 0)
    if is_general_query:
        logger.info("Query GENERAL detectada. Generando salida con ceros y terminando.")

        output_cols = [
            'Origen', 'Destino',
            'veh_M', 'veh_A', 'veh_B', 'veh_CU', 'veh_CAI', 'veh_CAII',
            'veh_total',
        ]

        df_final = pd.DataFrame({
            'Origen': df_od['origin_id'],
            'Destino': df_od['destination_id'],
            'veh_M': 0,
            'veh_A': 0,
            'veh_B': 0,
            'veh_CU': 0,
            'veh_CAI': 0,
            'veh_CAII': 0,
            'veh_total': 0,
        })

        input_filename = os.path.basename(od_path)
        output_filename = f"processed_{input_filename}"
        output_file = os.path.join(output_dir, output_filename)
        df_final[output_cols].to_csv(output_file, index=False)

        logger.info(f"Pipeline completado (GENERAL) para {input_filename}. Resultados en: {output_file}")
        return output_file
    
    # --- Paso 2: Grafo y Centroides ---
    logger.info("[Paso 2] Construcción de Grafo y Asignación de Centroides")

    # Si la red no existe, descargar desde OSM y guardarla como GeoJSON.
    # BBox: preferir osm_bbox (si lo pasaron), si no inferirlo de la zonificación.
    G = ensure_graph_from_geojson_or_osm(
        geojson_path=network_path,
        zonification_path=zonification_path,
        osm_bbox=osm_bbox,
        network_type='drive',
    )
    
    # Cargar zonificación y asignar nodos
    zones_gdf = gpd.read_file(zonification_path)
    zones_gdf = assign_nodes_to_zones(zones_gdf, G)
    
    # Mapear centroides a OD
    df_od = add_centroid_coordinates_to_od(df_od, zones_gdf)
    
    # --- Paso 2.5: Cargar Checkpoints y Asignar Nodos ---
    logger.info("[Paso 2.5] Carga de Checkpoints desde Zonification.geojson")
    checkpoint_nodes = get_checkpoint_node_mapping(zonification_path, G)
    
    # Crear diccionario para mapeo rápido
    checkpoint_node_dict = dict(zip(
        checkpoint_nodes['checkpoint_id'].astype(str), 
        checkpoint_nodes['checkpoint_node_id']
    ))
    
    # Asignar checkpoint_node_id a cada fila de OD
    if 'checkpoint_id' in df_od.columns:
        df_od['checkpoint_node_id'] = df_od['checkpoint_id'].astype(str).map(checkpoint_node_dict)
        
        # Validar que todos los checkpoints fueron encontrados
        missing_checkpoints = df_od[df_od['checkpoint_node_id'].isna()]['checkpoint_id'].unique()
        if len(missing_checkpoints) > 0:
            logger.warning(f"⚠️ Checkpoints sin ubicación en zonification.geojson: {missing_checkpoints}")
    else:
        df_od['checkpoint_node_id'] = None

    
    # --- Paso 3/4: Routing (MC y MC2) ---
    if debug_enabled:
        n_workers = int(os.environ.get('KIDO_DEBUG_N_WORKERS', '8'))
        chunk_size = int(os.environ.get('KIDO_DEBUG_CHUNK_SIZE', '200'))
        logger.info(
            "[Paso 3/4][DEBUG] MC+MC2 en paralelo: workers=%s chunk=%s (Windows spawn: cada worker carga el grafo)",
            n_workers,
            chunk_size,
        )
        df_od = compute_mc_and_mc2_parallel_debug2030(
            df_od=df_od,
            network_path=network_path,
            checkpoint_node_col='checkpoint_node_id',
            origin_node_col='origin_node_id',
            dest_node_col='destination_node_id',
            sense_catalog_path=None,
            n_workers=n_workers,
            chunk_size=chunk_size,
        )
    else:
        logger.info("[Paso 3] Cálculo de Ruta Más Corta (MC)")
        df_od = compute_mc_matrix(df_od, G)

        logger.info("[Paso 4] Cálculo de Ruta Restringida (MC2) por Checkpoint y Derivación de Sentido")
        # compute_mc2_matrix deriva sense_code
        df_od = compute_mc2_matrix(
            df_od,
            G,
            checkpoint_col='checkpoint_node_id',
            origin_node_col='origin_node_id',
            dest_node_col='destination_node_id'
        )

    # Validar rutas
    df_od['has_valid_path'] = (
        (df_od['mc_distance_m'] > 0) &
        (df_od['mc2_distance_m'] > 0) &
        df_od['mc2_distance_m'].notna()
    )

    # --- Paso 5: Capacidad ---
    logger.info("[Paso 5] Integración de Capacidad")
    df_cap = load_capacity_data(capacity_path)

    # DEBUG: validación específica (solo checkpoint 2030 debe ser agregado, Sentido=0)
    if debug_enabled and str(debug_checkpoint_id) == '2030':
        cap2030 = df_cap[df_cap['Checkpoint'].astype(str).eq(debug_checkpoint_id)].copy()
        if cap2030.empty:
            raise AssertionError(f"DEBUG 2030: summary_capacity no contiene Checkpoint={debug_checkpoint_id}")
        sentidos = sorted(cap2030['Sentido'].astype(str).dropna().unique().tolist())
        if sentidos != ['0']:
            raise AssertionError(
                f"DEBUG 2030: Se esperaba Sentido único ['0'] en summary_capacity, encontrado: {sentidos}"
            )
        # Log explícito de la fila aplicada (es única por checkpoint agregado)
        row0 = cap2030.iloc[0].to_dict()
        logger.info(
            "🧪 DEBUG 2030: capacity aplicada (Checkpoint=%s, Sentido=0): FA=%s | TOTAL=%s | M=%s A=%s B=%s CU=%s CAI=%s CAII=%s",
            debug_checkpoint_id,
            row0.get('FA'),
            row0.get('TOTAL'),
            row0.get('M'), row0.get('A'), row0.get('B'), row0.get('CU'), row0.get('CAI'), row0.get('CAII'),
        )

    df_od = match_capacity_to_od(df_od, df_cap)

    if debug_enabled and str(debug_checkpoint_id) == '2030':
        # checkpoint 2030 debe ser NO direccional
        if 'checkpoint_is_directional' not in df_od.columns:
            raise AssertionError("DEBUG 2030: columna checkpoint_is_directional no fue calculada")
        bad = df_od['checkpoint_is_directional'].fillna(True).astype(bool)
        if bad.any():
            raise AssertionError(
                "DEBUG 2030: checkpoint_is_directional debía ser False para todas las filas. "
                f"Filas con True: {int(bad.sum())}"
            )

    # --- Paso 6: Congruencia (bloqueante) ---
    logger.info("[Paso 6] Cálculo de Congruencia (STRICT)")
    df_od = classify_congruence(df_od)

    # --- Paso 7: Cálculo de Viajes (STRICT guard) ---
    logger.info("[Paso 7] Cálculo de Viajes Vehiculares")
    df_od = calculate_vehicle_trips(df_od)

    # --- DEBUG: trazabilidad numérica + visualizaciones (NO contractual) ---
    if debug_enabled:
        # Trace dataframe con columnas explícitas
        trace_cols = [
            'origin_id', 'destination_id',
            'trips_person',
            'intrazonal_factor',
            'mc_distance_m',
            'mc2_distance_m',
            'mc2_passes_checkpoint_link',
            'sense_code',
            'checkpoint_is_directional',
            'cap_M', 'cap_A', 'cap_B', 'cap_CU', 'cap_CAI', 'cap_CAII', 'cap_total',
            'fa',
            'focup_M', 'focup_A', 'focup_B', 'focup_CU', 'focup_CAI', 'focup_CAII',
            'veh_M', 'veh_A', 'veh_B', 'veh_CU', 'veh_CAI', 'veh_CAII',
            'veh_total',
            'congruence_id',
            'congruence_reason',
        ]
        for c in trace_cols:
            if c not in df_od.columns:
                df_od[c] = np.nan

        df_trace = df_od[trace_cols].copy()

        # Shares
        for cat in ['M', 'A', 'B', 'CU', 'CAI', 'CAII']:
            capc = df_trace[f'cap_{cat}']
            df_trace[f'share_{cat}'] = capc / df_trace['cap_total']

        # Orden solicitado (shares y focup intercalados ya están)
        ordered = [
            'origin_id', 'destination_id',
            'trips_person', 'intrazonal_factor',
            'mc_distance_m', 'mc2_distance_m',
            'mc2_passes_checkpoint_link',
            'sense_code', 'checkpoint_is_directional',
            'cap_M', 'cap_A', 'cap_B', 'cap_CU', 'cap_CAI', 'cap_CAII', 'cap_total',
            'fa',
            'focup_M', 'focup_A', 'focup_B', 'focup_CU', 'focup_CAI', 'focup_CAII',
            'share_M', 'share_A', 'share_B', 'share_CU', 'share_CAI', 'share_CAII',
            'veh_M', 'veh_A', 'veh_B', 'veh_CU', 'veh_CAI', 'veh_CAII',
            'veh_total',
            'congruence_id',
            'congruence_reason',
        ]
        df_trace = df_trace[ordered]

        trace_path = debug_output_dir / f'debug_checkpoint{debug_checkpoint_id}_trace.csv'
        df_trace.to_csv(trace_path, index=False)
        logger.info("🧪 DEBUG %s: traza guardada: %s", debug_checkpoint_id, str(trace_path))

        # Visualizaciones
        viz = DebugVisualizer(output_dir=str(debug_plots_dir))

        # 1) Flujo lógico (tabular)
        viz.plot_logic_flow(
            df_trace,
            save_to=str(debug_plots_dir / f'checkpoint{debug_checkpoint_id}_logic_flow.png'),
        )

        # 2) Rutas MC vs MC2 + sentido (limitado por DEBUG_MAX_ROUTE_PLOTS)
        plotted = 0
        for _, r in df_od.iterrows():
            if plotted >= debug_max_route_plots:
                break
            o_node = r.get('origin_node_id')
            d_node = r.get('destination_node_id')
            cp_node = r.get('checkpoint_node_id')
            if pd.isna(o_node) or pd.isna(d_node) or pd.isna(cp_node):
                continue

            # Parse MC path (guardado como string repr)
            mc_path_raw = r.get('mc_path')
            mc_path = None
            if isinstance(mc_path_raw, str) and mc_path_raw.strip():
                try:
                    mc_path = ast.literal_eval(mc_path_raw)
                except Exception:
                    mc_path = None

            # Recomputar MC2 path SOLO para plotting (no cambia lógica contractual)
            mc2_path, _mc2_dist = compute_constrained_shortest_path(G, o_node, d_node, cp_node)

            origin_id = str(r.get('origin_id'))
            dest_id = str(r.get('destination_id'))
            sense_code = r.get('sense_code')
            if pd.isna(sense_code):
                sense_code = None
            else:
                sense_code = str(sense_code)

            viz.plot_route_comparison(
                G=G,
                origin_node=o_node,
                dest_node=d_node,
                checkpoint_node=cp_node,
                mc_path=mc_path,
                mc2_path=mc2_path,
                origin_id=origin_id,
                dest_id=dest_id,
                sense_code=sense_code,
                save_to=str(debug_plots_dir / f'checkpoint{debug_checkpoint_id}_route_{origin_id}_{dest_id}.png'),
            )

            # Detalle de sentido (entrante/saliente)
            bearing_in = bearing_out = None
            card_in = card_out = None
            if mc2_path and cp_node in mc2_path and len(mc2_path) >= 3:
                idx_cp = mc2_path.index(cp_node)
                if 0 < idx_cp < len(mc2_path) - 1:
                    u = mc2_path[idx_cp - 1]
                    v = cp_node
                    w = mc2_path[idx_cp + 1]
                    bearing_in = calculate_bearing(G, u, v)
                    bearing_out = calculate_bearing(G, v, w)
                    card_in = get_cardinality(bearing_in, is_origin=True) if bearing_in is not None else None
                    card_out = get_cardinality(bearing_out, is_origin=False) if bearing_out is not None else None

            viz.plot_sense_detail(
                bearing_in=bearing_in,
                bearing_out=bearing_out,
                cardinality_in=card_in,
                cardinality_out=card_out,
                sense_code=sense_code,
                origin_id=origin_id,
                dest_id=dest_id,
                save_to=str(debug_plots_dir / f'checkpoint{debug_checkpoint_id}_sense_{origin_id}_{dest_id}.png'),
            )

            plotted += 1
        logger.info(
            "🧪 DEBUG %s: plots generados para %s ODs (max=%s)",
            debug_checkpoint_id,
            plotted,
            debug_max_route_plots,
        )
    
    # --- Paso 8: Guardar Resultados ---
    logger.info("[Paso 8] Guardando Resultados")
    
    # STRICT MODE: Salida FINAL limpia (solo columnas contractuales)
    df_od = df_od.rename(columns={
        'origin_id': 'Origen',
        'destination_id': 'Destino',
    })

    output_cols = [
        'Origen', 'Destino',
        'veh_M', 'veh_A', 'veh_B', 'veh_CU', 'veh_CAI', 'veh_CAII',
        'veh_total',
    ]
    
    # Asegurar que existan las columnas (rellenar con NaN si faltan, NUNCA 0)
    for col in output_cols:
        if col not in df_od.columns:
            df_od[col] = float('nan')
            
    df_final = df_od[output_cols]
    
    # Generar nombre de archivo de salida basado en entrada
    input_filename = os.path.basename(od_path)
    output_filename = f"processed_{input_filename}"
    output_file = os.path.join(output_dir, output_filename)
    
    df_final.to_csv(output_file, index=False)
    
    logger.info(f"Pipeline completado exitosamente para {input_filename}. Resultados en: {output_file}")
    return output_file
