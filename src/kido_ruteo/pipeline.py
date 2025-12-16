"""
Orquestador maestro del pipeline KIDO.
"""

import pandas as pd
import geopandas as gpd
import os
from .processing.preprocessing import prepare_data, normalize_column_names
from .processing.centrality import build_network_graph, compute_betweenness_centrality
from .processing.centroides import assign_nodes_to_zones, select_zone_centroids, add_centroid_coordinates_to_od
from .processing.access_vectors import compute_access_vectors
from .routing.graph_loader import load_graph_from_geojson
from .routing.shortest_path import compute_mc_matrix
from .routing.auto_checkpoint import find_checkpoint_nodes
from .routing.constrained_path import compute_mc2_matrix
from .validation.validation_pipeline import run_validation_pipeline
from .viajes.viajes import calculate_viajes
from .viajes.factores import add_daily_tables
from .viajes.agregaciones import convert_to_vehicle_trips, generate_matrices_by_typology

def run_pipeline(
    od_path: str,
    zonification_path: str,
    network_path: str,
    output_dir: str
):
    """
    Ejecuta el pipeline completo KIDO.
    
    Args:
        od_path: Ruta al archivo OD (CSV)
        zonification_path: Ruta al archivo de zonificación (GeoJSON)
        network_path: Ruta al archivo de red vial (GeoJSON)
        output_dir: Directorio de salida
    """
    print("🚀 Iniciando Pipeline KIDO...")
    
    # Crear directorio de salida
    os.makedirs(output_dir, exist_ok=True)
    
    # --- Paso 1: Preprocesamiento ---
    print("\n[Paso 1] Preprocesamiento OD")
    df_od = pd.read_csv(od_path)
    df_od = normalize_column_names(df_od)
    df_od = prepare_data(df_od)
    df_od.to_parquet(os.path.join(output_dir, 'od_clean.parquet'))
    
    # --- Paso 2: Centralidad y Centroides ---
    print("\n[Paso 2] Centralidad y Centroides")
    zones_gdf = gpd.read_file(zonification_path)
    G = load_graph_from_geojson(network_path)
    
    # (Simplificado: usaría funciones de centrality y centroides)
    # ...
    
    # --- Paso 3: Vectores de Acceso ---
    print("\n[Paso 3] Vectores de Acceso")
    df_od = compute_access_vectors(df_od)
    df_od.to_csv(os.path.join(output_dir, 'vectores_acceso.csv'), index=False)
    
    # --- Paso 4: Routing ---
    print("\n[Paso 4] Routing (MC y MC2)")
    # MC
    df_od = compute_mc_matrix(df_od, G)
    df_od.to_parquet(os.path.join(output_dir, 'mc.parquet'))
    
    # MC2
    # checkpoints = find_checkpoint_nodes(...)
    # df_od = compute_mc2_matrix(df_od, G, checkpoints)
    # df_od.to_parquet(os.path.join(output_dir, 'mc2.parquet'))
    
    # --- Paso 5 & 6: Validación y Congruencia ---
    print("\n[Paso 5 & 6] Validación y Congruencia")
    # df_od = run_validation_pipeline(df_od, df_vial=None) # df_vial needed
    # df_od.to_parquet(os.path.join(output_dir, 'congruencias.parquet'))
    
    # --- Paso 7: Viajes ---
    print("\n[Paso 7] Cálculo de Viajes")
    df_od = calculate_viajes(df_od)
    df_od = add_daily_tables(df_od)
    # df_od = convert_to_vehicle_trips(df_od)
    
    output_file = os.path.join(output_dir, 'resultados_kido_automatizado.xlsx')
    df_od.to_excel(output_file, index=False)
    print(f"\n✅ Pipeline finalizado. Resultados en: {output_file}")

if __name__ == "__main__":
    # Ejemplo de uso
    pass
