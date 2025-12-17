"""
Orquestador maestro del pipeline KIDO.
"""

import pandas as pd
import geopandas as gpd
import os
import logging
from .processing.preprocessing import prepare_data, normalize_column_names
from .processing.centrality import build_network_graph
from .processing.centroides import assign_nodes_to_zones, add_centroid_coordinates_to_od
from .processing.checkpoint_loader import get_checkpoint_node_mapping
from .routing.graph_loader import load_graph_from_geojson, download_graph_from_bbox, save_graph_to_geojson
from .routing.shortest_path import compute_mc_matrix
from .routing.constrained_path import compute_mc2_matrix
from .capacity.loader import load_capacity_data
from .capacity.matcher import match_capacity_to_od
from .congruence.potential import calculate_potential
from .congruence.scoring import calculate_scores
from .congruence.classification import classify_congruence
from .trips.calculation import calculate_vehicle_trips

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
    
    # --- Paso 2: Grafo y Centroides ---
    logger.info("[Paso 2] Construcción de Grafo y Asignación de Centroides")
    
    # Verificar si existe el archivo de red, si no, descargar de OSM
    if not os.path.exists(network_path):
        logger.warning(f"No se encontró archivo de red en {network_path}.")
        if osm_bbox:
            logger.info("Intentando descargar de OpenStreetMap...")
            try:
                G_osm = download_graph_from_bbox(*osm_bbox)
                save_graph_to_geojson(G_osm, network_path)
                logger.info(f"Red descargada y guardada en {network_path}")
            except Exception as e:
                logger.error(f"Error descargando de OSM: {e}")
                raise
        else:
            raise FileNotFoundError(f"No se encontró red y no se proveyó BBox para descarga.")

    # Cargar grafo
    G = load_graph_from_geojson(network_path)
    
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

    
    # --- Paso 3: Routing (MC - Shortest Path) ---
    logger.info("[Paso 3] Cálculo de Ruta Más Corta (MC)")
    df_od = compute_mc_matrix(df_od, G)
    
    if is_general_query:
        logger.info("Query GENERAL detectada. Saltando cálculo de MC2, Capacidad y Congruencia.")
        # Inicializar columnas requeridas con NaN (Strict Rule 5)
        cols_veh = ['veh_auto', 'veh_bus', 'veh_cu', 'veh_cai', 'veh_caii', 'veh_total']
        for col in cols_veh:
            df_od[col] = float('nan')
            
        # Congruencia Impossible para General
        df_od['congruence_id'] = 4
        df_od['congruence_label'] = 'Impossible'
        df_od['id_potential'] = 0
        
    else:
        # --- Paso 4: Ruteo Restringido (MC2) ---
        logger.info("[Paso 4] Cálculo de Ruta Restringida (MC2) por Checkpoint y Derivación de Sentido")
        
        # compute_mc2_matrix now derives sense_code
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
        df_od = match_capacity_to_od(df_od, df_cap)
        
        # --- Paso 6: Congruencia y Potencial ---
        logger.info("[Paso 6] Cálculo de Congruencia y Potencial")
        df_od = calculate_potential(df_od)
        df_od = calculate_scores(df_od)
        df_od = classify_congruence(df_od)
        
        # --- Paso 7: Cálculo de Viajes ---
        logger.info("[Paso 7] Cálculo de Viajes Vehiculares")
        df_od = calculate_vehicle_trips(df_od)
    
    # --- Paso 8: Guardar Resultados ---
    logger.info("[Paso 8] Guardando Resultados")
    
    # STRICT RULE 6: Salida FINAL limpia
    # SOLO estas columnas. Sin auditoría, sin geometría, sin flags.
    # Columnas de vehículos renombradas según especificación:
    # veh_auto → veh_AU, veh_cu → veh_CU, veh_cai → veh_CAI, veh_caii → veh_CAII
    
    # Renombrar columnas de vehículos antes de extraer
    rename_veh = {
        'origin_id': 'Origen',
        'destination_id': 'Destino',
        'veh_auto': 'veh_AU',
        'veh_cu': 'veh_CU',
        'veh_cai': 'veh_CAI',
        'veh_caii': 'veh_CAII'
    }
    
    df_od = df_od.rename(columns=rename_veh)
    
    output_cols = [
        'Origen', 'Destino', 
        'veh_AU', 'veh_CU', 'veh_CAI', 'veh_CAII', 'veh_total'
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
