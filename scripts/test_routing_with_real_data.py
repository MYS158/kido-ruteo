"""Script de prueba del pipeline de routing con datos realistas.

Este script simula el flujo completo:
1. Carga datos de zonas desde el archivo geográfico real
2. Crea una red sintética pero realista basada en las zonas
3. Ejecuta el pipeline de routing
4. Valida resultados y genera reporte
"""
from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import LineString, Point

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kido_ruteo.routing.routing_pipeline import run_routing_pipeline
from kido_ruteo.routing.graph_loader import load_graph_from_network_dir


def create_synthetic_network_from_zones(gdf_zones: gpd.GeoDataFrame, output_dir: Path):
    """Crea una red sintética basada en centroides de zonas reales.
    
    Args:
        gdf_zones: GeoDataFrame con zonas geográficas
        output_dir: Directorio donde guardar edges.gpkg y nodes.gpkg
    """
    print(f"\n📍 Creando red sintética desde {len(gdf_zones)} zonas...")
    
    # Calcular centroides de zonas
    gdf_zones = gdf_zones.to_crs("EPSG:32613")  # UTM Zone 13N para México
    gdf_zones["centroid"] = gdf_zones.geometry.centroid
    
    # Crear nodos desde centroides
    nodes_data = []
    for idx, row in gdf_zones.iterrows():
        nodes_data.append({
            "node_id": int(row["id"]),
            "zone_name": row["name"],
            "geometry": row["centroid"],
        })
    
    gdf_nodes = gpd.GeoDataFrame(nodes_data, crs="EPSG:32613")
    print(f"  ✓ Creados {len(gdf_nodes)} nodos")
    
    # Crear edges conectando zonas cercanas
    edges_data = []
    edge_types = ["motorway", "primary", "secondary", "tertiary"]
    speeds = {"motorway": 80, "primary": 60, "secondary": 40, "tertiary": 30}
    
    # Conectar cada nodo con sus vecinos más cercanos
    for idx, node in gdf_nodes.iterrows():
        node_id = node["node_id"]
        node_geom = node["geometry"]
        
        # Calcular distancias a otros nodos
        distances = gdf_nodes.geometry.distance(node_geom)
        # Ordenar y tomar los 5 más cercanos (excluyendo el mismo)
        nearest_indices = distances.nsmallest(6).index[1:]  # Skip el mismo nodo
        
        for target_idx in nearest_indices[:3]:  # Conectar con los 3 más cercanos
            target_node = gdf_nodes.loc[target_idx]
            target_id = target_node["node_id"]
            
            # Calcular distancia real
            length = node_geom.distance(target_node["geometry"])
            
            # Asignar tipo de vía basado en distancia
            if length < 3000:
                edge_type = "primary"
            elif length < 5000:
                edge_type = "secondary"
            else:
                edge_type = "tertiary"
            
            # Crear edge en ambas direcciones
            edges_data.append({
                "u": node_id,
                "v": target_id,
                "length": length,
                "speed": float(speeds[edge_type]),
                "primary_class": edge_type,
                "geometry": LineString([node_geom, target_node["geometry"]]),
            })
            
            edges_data.append({
                "u": target_id,
                "v": node_id,
                "length": length,
                "speed": float(speeds[edge_type]),
                "primary_class": edge_type,
                "geometry": LineString([target_node["geometry"], node_geom]),
            })
    
    gdf_edges = gpd.GeoDataFrame(edges_data, crs="EPSG:32613")
    print(f"  ✓ Creados {len(gdf_edges)} edges")
    
    # Guardar archivos
    output_dir.mkdir(parents=True, exist_ok=True)
    gdf_nodes.to_file(output_dir / "nodes.gpkg", driver="GPKG")
    gdf_edges.to_file(output_dir / "edges.gpkg", driver="GPKG")
    print(f"  ✓ Red guardada en {output_dir}")
    
    return gdf_nodes, gdf_edges


def create_od_sample_from_real_data(gdf_zones: gpd.GeoDataFrame, n_pairs: int = 20) -> pd.DataFrame:
    """Crea pares OD de muestra desde zonas reales.
    
    Args:
        gdf_zones: GeoDataFrame con zonas
        n_pairs: Número de pares a generar
        
    Returns:
        DataFrame con pares OD
    """
    print(f"\n🎯 Generando {n_pairs} pares OD de muestra...")
    
    zone_ids = gdf_zones["id"].astype(int).tolist()
    
    # Generar pares OD variados
    od_pairs = []
    np.random.seed(42)
    
    for i in range(n_pairs):
        origin = np.random.choice(zone_ids)
        # Asegurar que destino sea diferente
        destination = np.random.choice([z for z in zone_ids if z != origin])
        
        od_pairs.append({
            "origin_node_id": origin,
            "destination_node_id": destination,
            "pair_id": i + 1,
        })
    
    df_od = pd.DataFrame(od_pairs)
    print(f"  ✓ Generados {len(df_od)} pares OD")
    return df_od


def validate_routing_results(df_results: pd.DataFrame) -> dict:
    """Valida resultados del routing y genera reporte.
    
    Args:
        df_results: DataFrame con resultados del routing
        
    Returns:
        Diccionario con estadísticas de validación
    """
    print("\n📊 Validando resultados...")
    
    # Filtrar pares exitosos
    if "error" in df_results.columns:
        df_success = df_results[df_results["error"].isna()].copy()
        df_errors = df_results[df_results["error"].notna()].copy()
    else:
        df_success = df_results.copy()
        df_errors = pd.DataFrame()
    
    n_total = len(df_results)
    n_success = len(df_success)
    n_errors = len(df_errors)
    
    stats = {
        "total_pairs": n_total,
        "successful_pairs": n_success,
        "failed_pairs": n_errors,
        "success_rate": n_success / n_total if n_total > 0 else 0,
    }
    
    print(f"\n✅ Tasa de éxito: {stats['success_rate']*100:.1f}% ({n_success}/{n_total})")
    
    if n_errors > 0:
        print(f"\n⚠️  Errores encontrados en {n_errors} pares:")
        for idx, row in df_errors.head(5).iterrows():
            print(f"  - Par {row['origin_node_id']}→{row['destination_node_id']}: {row['error']}")
    
    if n_success > 0:
        print("\n📈 Estadísticas de pares exitosos:")
        
        # Ratio X
        ratio_x_stats = df_success["ratio_x"].describe()
        print(f"\n  Ratio X (MC2/MC):")
        print(f"    - Mínimo: {ratio_x_stats['min']:.3f}")
        print(f"    - Media: {ratio_x_stats['mean']:.3f}")
        print(f"    - Mediana: {ratio_x_stats['50%']:.3f}")
        print(f"    - Máximo: {ratio_x_stats['max']:.3f}")
        
        stats["ratio_x_mean"] = ratio_x_stats["mean"]
        stats["ratio_x_max"] = ratio_x_stats["max"]
        
        # Distancias
        print(f"\n  Distancias MC:")
        mc_km = df_success["mc_length_m"] / 1000
        print(f"    - Mínimo: {mc_km.min():.2f} km")
        print(f"    - Media: {mc_km.mean():.2f} km")
        print(f"    - Máximo: {mc_km.max():.2f} km")
        
        # Tiempos
        print(f"\n  Tiempos MC:")
        print(f"    - Mínimo: {df_success['mc_time_min'].min():.1f} min")
        print(f"    - Media: {df_success['mc_time_min'].mean():.1f} min")
        print(f"    - Máximo: {df_success['mc_time_min'].max():.1f} min")
        
        # Checkpoints
        checkpoint_sources = df_success["checkpoint_source"].value_counts()
        print(f"\n  Checkpoints:")
        for source, count in checkpoint_sources.items():
            print(f"    - {source}: {count} ({count/n_success*100:.1f}%)")
        
        # Validar coherencia
        print("\n🔍 Validaciones de coherencia:")
        
        # Definir epsilon para errores de precisión numérica
        epsilon_m = 1e-6  # 1 micrómetro
        epsilon_ratio = 1e-9  # Precisión de punto flotante
        
        # MC2 debe ser >= MC (considerando epsilon)
        invalid_mc2 = df_success[df_success["mc2_length_m"] < (df_success["mc_length_m"] - epsilon_m)]
        if len(invalid_mc2) > 0:
            print(f"  ❌ {len(invalid_mc2)} pares con MC2 < MC (INCONSISTENCIA REAL)")
            stats["inconsistency_mc2_shorter"] = len(invalid_mc2)
        else:
            print(f"  ✓ Todos los pares tienen MC2 >= MC (epsilon: {epsilon_m}m)")
        
        # Ratio X debe ser >= 1.0 (considerando epsilon)
        invalid_ratio = df_success[df_success["ratio_x"] < (1.0 - epsilon_ratio)]
        if len(invalid_ratio) > 0:
            print(f"  ❌ {len(invalid_ratio)} pares con ratio X < 1.0 (INCONSISTENCIA REAL)")
            stats["inconsistency_ratio_x"] = len(invalid_ratio)
        else:
            print(f"  ✓ Todos los pares tienen ratio X >= 1.0 (epsilon: {epsilon_ratio})")
        
        # Ratio X muy alto (> 2.0) puede indicar problema
        high_ratio = df_success[df_success["ratio_x"] > 2.0]
        if len(high_ratio) > 0:
            print(f"  ⚠️  {len(high_ratio)} pares con ratio X > 2.0 (revisar)")
            print(f"      Esto puede indicar checkpoints muy desviados")
            stats["warning_high_ratio_x"] = len(high_ratio)
        
        # Velocidades promedio
        df_success["avg_speed_kmh"] = (df_success["mc_length_m"] / 1000) / (df_success["mc_time_min"] / 60)
        speed_stats = df_success["avg_speed_kmh"].describe()
        print(f"\n  Velocidades promedio:")
        print(f"    - Mínimo: {speed_stats['min']:.1f} km/h")
        print(f"    - Media: {speed_stats['mean']:.1f} km/h")
        print(f"    - Máximo: {speed_stats['max']:.1f} km/h")
        
        invalid_speeds = df_success[
            (df_success["avg_speed_kmh"] < 10) | (df_success["avg_speed_kmh"] > 120)
        ]
        if len(invalid_speeds) > 0:
            print(f"  ⚠️  {len(invalid_speeds)} pares con velocidades fuera de rango 10-120 km/h")
            stats["warning_invalid_speeds"] = len(invalid_speeds)
        else:
            print(f"  ✓ Todas las velocidades en rango razonable")
    
    return stats


def main():
    """Función principal."""
    print("=" * 70)
    print("🚀 TEST DE PIPELINE DE ROUTING CON DATOS REALES")
    print("=" * 70)
    
    # Rutas
    project_root = Path(__file__).parent.parent
    geo_file = project_root / "data" / "raw" / "geografia" / "470-458_kido_geografico.geojson"
    network_dir = project_root / "data" / "network" / "synthetic"
    output_dir = project_root / "data" / "processed" / "routing"
    
    # 1. Cargar zonas geográficas reales
    print(f"\n📂 Cargando zonas desde {geo_file.name}...")
    gdf_zones = gpd.read_file(geo_file)
    print(f"  ✓ Cargadas {len(gdf_zones)} zonas")
    
    # 2. Crear red sintética desde zonas reales
    gdf_nodes, gdf_edges = create_synthetic_network_from_zones(gdf_zones, network_dir)
    
    # 3. Crear pares OD de muestra
    df_od = create_od_sample_from_real_data(gdf_zones, n_pairs=20)
    
    # 4. Ejecutar pipeline de routing
    print("\n🔄 Ejecutando pipeline de routing...")
    try:
        df_results = run_routing_pipeline(
            network_path=network_dir,
            df_od=df_od,
            gdf_nodes=gdf_nodes,
            gdf_edges=gdf_edges,
            output_dir=output_dir,
            checkpoint_mode="auto",
            percent_lower=0.40,
            percent_upper=0.60,
        )
        
        print(f"  ✓ Pipeline completado")
        
        # 5. Validar resultados
        stats = validate_routing_results(df_results)
        
        # 6. Guardar resultados
        output_file = output_dir / "routing_test_results.csv"
        df_results.to_csv(output_file, index=False)
        print(f"\n💾 Resultados guardados en: {output_file}")
        
        # 7. Resumen final
        print("\n" + "=" * 70)
        print("📋 RESUMEN FINAL")
        print("=" * 70)
        print(f"  Total de pares: {stats['total_pairs']}")
        print(f"  Exitosos: {stats['successful_pairs']}")
        print(f"  Fallidos: {stats['failed_pairs']}")
        print(f"  Tasa de éxito: {stats['success_rate']*100:.1f}%")
        
        if stats['successful_pairs'] > 0:
            print(f"\n  Ratio X promedio: {stats['ratio_x_mean']:.3f}")
            print(f"  Ratio X máximo: {stats['ratio_x_max']:.3f}")
        
        # Detectar inconsistencias
        inconsistencies = []
        if "inconsistency_mc2_shorter" in stats:
            inconsistencies.append(f"MC2 < MC en {stats['inconsistency_mc2_shorter']} pares")
        if "inconsistency_ratio_x" in stats:
            inconsistencies.append(f"Ratio X < 1.0 en {stats['inconsistency_ratio_x']} pares")
        
        if inconsistencies:
            print("\n  ❌ INCONSISTENCIAS DETECTADAS:")
            for inc in inconsistencies:
                print(f"     - {inc}")
        else:
            print("\n  ✅ No se detectaron inconsistencias críticas")
        
        # Warnings
        warnings = []
        if "warning_high_ratio_x" in stats:
            warnings.append(f"Ratio X > 2.0 en {stats['warning_high_ratio_x']} pares")
        if "warning_invalid_speeds" in stats:
            warnings.append(f"Velocidades fuera de rango en {stats['warning_invalid_speeds']} pares")
        
        if warnings:
            print("\n  ⚠️  ADVERTENCIAS:")
            for warn in warnings:
                print(f"     - {warn}")
        
        print("\n" + "=" * 70)
        
        return 0 if stats['success_rate'] >= 0.8 else 1
        
    except Exception as exc:
        print(f"\n❌ ERROR durante ejecución del pipeline:")
        print(f"   {exc}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
