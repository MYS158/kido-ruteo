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
            logger.warning("No se pudo inferir checkpoint_id del nombre de archivo.")
            
    # --- Inferencia de Sentido desde Capacidad ---
    # ELIMINADO: No se debe inferir ni expandir sentidos desde capacidad.
    # La capacidad solo valida. Si no hay sense_code, se asume inválido.
    if 'sense_code' not in df_od.columns:
        logger.warning("Columna 'sense_code' no encontrada en OD. No se realizará expansión. Se asignará '0' (Inválido).")
        df_od['sense_code'] = '0'

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
    
    # --- Paso 3: Routing (MC y MC2) ---
    logger.info("[Paso 3] Cálculo de Rutas (MC y MC2)")
    # MC: Ruta libre
    df_od = compute_mc_matrix(df_od, G)
    
    # MC2: Ruta obligada por checkpoint
    # Usamos la función actualizada que toma el checkpoint de la fila
    df_od = compute_mc2_matrix(
        df_od, 
        G, 
        checkpoint_col='checkpoint_node_id',
        origin_node_col='origin_node_id',
        dest_node_col='destination_node_id'
    )
    
    # Validar rutas
    # has_valid_path es True solo si ambas distancias son válidas (>0)
    # Nota: compute_mc2_matrix puede devolver None o inf si no hay ruta
    df_od['has_valid_path'] = (
        (df_od['mc_distance_m'] > 0) & 
        (df_od['mc2_distance_m'] > 0) & 
        df_od['mc2_distance_m'].notna()
    )
    
    # --- Paso 4: Capacidad ---
    logger.info("[Paso 4] Integración de Capacidad")
    df_cap = load_capacity_data(capacity_path)
    df_od = match_capacity_to_od(df_od, df_cap)
    
    # --- Paso 5: Congruencia y Potencial ---
    logger.info("[Paso 5] Cálculo de Congruencia y Potencial")
    df_od = calculate_potential(df_od)
    df_od = calculate_scores(df_od)
    df_od = classify_congruence(df_od)
    
    # --- Paso 6: Cálculo de Viajes ---
    logger.info("[Paso 6] Cálculo de Viajes Vehiculares")
    df_od = calculate_vehicle_trips(df_od)
    
    # --- Paso 7: Guardar Resultados ---
    logger.info("[Paso 7] Guardando Resultados")
    
    # Seleccionar columnas finales requeridas
    final_columns = [
        'origin_id', 'destination_id', 'checkpoint_id', 'sense_code',
        'trips_person', 'intrazonal', 'intrazonal_factor',
        'mc_distance_m', 'mc2_distance_m', 'ratio_dist',
        'e1_route_score', 'e2_capacity_score', 'id_potential',
        'congruence_id', 'congruence_label',
        'veh_auto', 'veh_moto', 'veh_bus', 'veh_cu', 'veh_cai', 'veh_caii',
        'tpdm', 'tpda'
    ]
    
    # Asegurar que existan todas las columnas
    for col in final_columns:
        if col not in df_od.columns:
            # logger.warning(f"Columna {col} no encontrada, llenando con 0.")
            df_od[col] = 0 # O valor por defecto apropiado
            
    df_final = df_od[final_columns]
    
    output_file = os.path.join(output_dir, 'results_kido_automated.csv')
    df_final.to_csv(output_file, index=False)
    
    logger.info(f"Pipeline completado exitosamente. Resultados en: {output_file}")
    return output_file
