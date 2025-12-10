"""
Script de evaluación de congruencia para KIDO-Ruteo.

Compara rutas vs centroides y calcula métricas E1 y E2.
"""

import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
from typing import Dict, Tuple
from tqdm import tqdm


def get_project_root() -> Path:
    """Obtiene el directorio raíz del proyecto."""
    return Path(__file__).parent.parent


def compute_e1_metric(
    routes: pd.DataFrame,
    zones: gpd.GeoDataFrame
) -> pd.DataFrame:
    """
    Calcula métrica E1: congruencia de rutas respecto a centroides.
    
    E1 mide la desviación de la ruta calculada respecto a la línea recta
    entre centroides de origen y destino.
    
    Args:
        routes: DataFrame con rutas calculadas
        zones: GeoDataFrame con zonas y centroides
        
    Returns:
        DataFrame con métricas E1
    """
    print("\n📏 Calculando métrica E1...")
    
    # Crear mapeo de zonas a centroides
    zone_centroids = {}
    for idx, row in zones.iterrows():
        zone_id = row.get('id', row.get('zone_id', idx))
        zone_centroids[zone_id] = row.centroid
    
    e1_results = []
    
    for idx, route in tqdm(routes.iterrows(), total=len(routes)):
        origin = route['origin']
        destination = route['destination']
        
        if route['path'] is None:
            e1_results.append({
                'origin': origin,
                'destination': destination,
                'e1_score': None,
                'straight_distance': None,
                'route_distance': None
            })
            continue
        
        # Distancia en línea recta (centroide a centroide)
        if origin in zone_centroids and destination in zone_centroids:
            straight_dist = zone_centroids[origin].distance(zone_centroids[destination])
            route_dist = route['path_length']
            
            # E1 = desviación relativa de la ruta
            if straight_dist > 0:
                e1_score = (route_dist - straight_dist) / straight_dist
            else:
                e1_score = 0.0
            
            e1_results.append({
                'origin': origin,
                'destination': destination,
                'e1_score': e1_score,
                'straight_distance': straight_dist,
                'route_distance': route_dist
            })
        else:
            e1_results.append({
                'origin': origin,
                'destination': destination,
                'e1_score': None,
                'straight_distance': None,
                'route_distance': None
            })
    
    df_e1 = pd.DataFrame(e1_results)
    
    valid_e1 = df_e1['e1_score'].notna().sum()
    mean_e1 = df_e1['e1_score'].mean()
    print(f"  ✓ E1 calculado para {valid_e1} rutas (E1 promedio: {mean_e1:.3f})")
    
    return df_e1


def compute_e2_metric(
    routes: pd.DataFrame,
    od_data: pd.DataFrame
) -> pd.DataFrame:
    """
    Calcula métrica E2: congruencia de distribución de flujos.
    
    E2 mide la consistencia entre los flujos de viajes observados
    y los esperados según la estructura de la red.
    
    Args:
        routes: DataFrame con rutas calculadas
        od_data: DataFrame con datos OD originales
        
    Returns:
        DataFrame con métricas E2
    """
    print("\n📊 Calculando métrica E2...")
    
    # Merge routes con datos OD
    merged = routes.merge(
        od_data,
        left_on=['origin', 'destination'],
        right_on=['origen', 'destino'],
        how='inner'
    )
    
    # Identificar columna de viajes
    trips_col = None
    for col in ['viajes', 'trips', 'flujo', 'flow']:
        if col in merged.columns:
            trips_col = col
            break
    
    if trips_col is None:
        print("  ⚠️  No se encontró columna de viajes en datos OD")
        return pd.DataFrame()
    
    e2_results = []
    
    # Calcular E2 por par OD
    for idx, row in tqdm(merged.iterrows(), total=len(merged)):
        if row['path'] is None or pd.isna(row[trips_col]):
            e2_results.append({
                'origin': row['origin'],
                'destination': row['destination'],
                'e2_score': None,
                'observed_trips': row[trips_col],
                'route_efficiency': None
            })
            continue
        
        # E2 = viajes / longitud_ruta (normalizado)
        trips = row[trips_col]
        route_length = row['path_length']
        
        if route_length > 0:
            route_efficiency = trips / route_length
        else:
            route_efficiency = 0.0
        
        e2_results.append({
            'origin': row['origin'],
            'destination': row['destination'],
            'e2_score': route_efficiency,
            'observed_trips': trips,
            'route_efficiency': route_efficiency
        })
    
    df_e2 = pd.DataFrame(e2_results)
    
    valid_e2 = df_e2['e2_score'].notna().sum()
    mean_e2 = df_e2['e2_score'].mean()
    print(f"  ✓ E2 calculado para {valid_e2} rutas (E2 promedio: {mean_e2:.3f})")
    
    return df_e2


def generate_congruence_report(
    e1_data: pd.DataFrame,
    e2_data: pd.DataFrame,
    output_path: Path
) -> None:
    """
    Genera reporte consolidado de congruencia.
    
    Args:
        e1_data: DataFrame con métricas E1
        e2_data: DataFrame con métricas E2
        output_path: Ruta de salida para el reporte
    """
    print("\n📋 Generando reporte de congruencia...")
    
    # Merge E1 y E2
    congruence = e1_data.merge(
        e2_data[['origin', 'destination', 'e2_score', 'observed_trips']],
        on=['origin', 'destination'],
        how='outer'
    )
    
    # Guardar reporte
    congruence.to_csv(output_path, index=False)
    print(f"  ✓ Reporte guardado en: {output_path}")
    
    # Estadísticas resumen
    print("\n📈 Estadísticas de Congruencia:")
    print(f"  - E1 (desviación de ruta):")
    print(f"      Media: {congruence['e1_score'].mean():.3f}")
    print(f"      Mediana: {congruence['e1_score'].median():.3f}")
    print(f"      Desv. Est.: {congruence['e1_score'].std():.3f}")
    
    print(f"  - E2 (eficiencia de flujo):")
    print(f"      Media: {congruence['e2_score'].mean():.3f}")
    print(f"      Mediana: {congruence['e2_score'].median():.3f}")
    print(f"      Desv. Est.: {congruence['e2_score'].std():.3f}")


def main():
    """Ejecuta el proceso completo de evaluación de congruencia."""
    print("=" * 60)
    print("KIDO-Ruteo - Evaluación de Congruencia")
    print("=" * 60)
    
    root = get_project_root()
    
    # Rutas de entrada
    processed_dir = root / "data" / "processed"
    routes_path = processed_dir / "routes" / "routes_shortest_path.csv"
    
    interim_dir = root / "data" / "interim"
    geojson_dir = interim_dir / "geojson"
    consultas_dir = interim_dir / "consultas" / "general"
    
    # Directorio de salida
    output_dir = processed_dir / "congruence"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Cargar rutas
    if not routes_path.exists():
        print(f"❌ No se encontró archivo de rutas: {routes_path}")
        print("   Ejecuta primero: python scripts/build_routes.py")
        return
    
    print(f"📊 Cargando rutas desde {routes_path.name}...")
    routes = pd.read_csv(routes_path)
    print(f"  ✓ {len(routes)} rutas cargadas")
    
    # 2. Cargar zonas
    geojson_files = list(geojson_dir.glob("*.geojson"))
    if not geojson_files:
        print(f"❌ No se encontraron archivos GeoJSON en {geojson_dir}")
        return
    
    print(f"📍 Cargando zonas desde {geojson_files[0].name}...")
    zones = gpd.read_file(geojson_files[0])
    print(f"  ✓ {len(zones)} zonas cargadas")
    
    # 3. Cargar datos OD
    od_files = list(consultas_dir.glob("*.csv"))
    if not od_files:
        print(f"❌ No se encontraron archivos OD en {consultas_dir}")
        return
    
    print(f"📊 Cargando datos OD desde {od_files[0].name}...")
    od_data = pd.read_csv(od_files[0])
    print(f"  ✓ {len(od_data)} pares OD cargados")
    
    # 4. Calcular E1
    e1_data = compute_e1_metric(routes, zones)
    
    # 5. Calcular E2
    e2_data = compute_e2_metric(routes, od_data)
    
    # 6. Generar reporte consolidado
    report_path = output_dir / "congruence_report.csv"
    generate_congruence_report(e1_data, e2_data, report_path)
    
    print("\n" + "=" * 60)
    print("✅ Evaluación de congruencia completada")
    print("=" * 60)


if __name__ == "__main__":
    main()
