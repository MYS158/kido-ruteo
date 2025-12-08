"""Genera red vial sintética desde zonas geográficas.

Este script crea una topología de red (edges.gpkg, nodes.gpkg) basada en
centroides de zonas y conectividad por proximidad. Es un placeholder hasta
que se obtengan datos reales de red vial (OSM, shapefiles de calles, etc.).

Para usar datos reales de red vial, reemplazar este script con uno que:
1. Lea shapefiles de calles/vías del municipio
2. Extraiga nodos de intersecciones
3. Genere edges con atributos reales (velocidad, tipo de vía, etc.)
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import LineString

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def generate_network_from_zones(
    zones_file: Path,
    output_dir: Path,
    max_connections: int = 5,
    max_distance_km: float = 20.0,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Genera red sintética desde zonas geográficas.
    
    Args:
        zones_file: Archivo GeoJSON con polígonos de zonas
        output_dir: Directorio donde guardar edges.gpkg y nodes.gpkg
        max_connections: Máximo número de conexiones por nodo
        max_distance_km: Distancia máxima para conectar nodos (km)
        
    Returns:
        Tupla (gdf_nodes, gdf_edges)
    """
    logger.info("=== Generando red sintética ===")
    
    # 1. Cargar zonas
    logger.info("Cargando zonas desde %s", zones_file)
    gdf_zones = gpd.read_file(zones_file)
    logger.info("  ✓ Cargadas %d zonas", len(gdf_zones))
    
    # 2. Proyectar a CRS métrico (UTM Zone 13N para México central)
    if gdf_zones.crs.is_geographic:
        logger.info("Proyectando a CRS métrico (EPSG:32613)...")
        gdf_zones = gdf_zones.to_crs("EPSG:32613")
    
    # 3. Calcular centroides
    logger.info("Calculando centroides de zonas...")
    gdf_zones["centroid"] = gdf_zones.geometry.centroid
    
    # 4. Crear nodos desde centroides
    logger.info("Creando nodos...")
    nodes_data = []
    for idx, row in gdf_zones.iterrows():
        nodes_data.append({
            "node_id": int(row["id"]),
            "zone_name": str(row["name"]),
            "zone_id": int(row["id"]),
            "geometry": row["centroid"],
        })
    
    gdf_nodes = gpd.GeoDataFrame(nodes_data, crs=gdf_zones.crs)
    logger.info("  ✓ Creados %d nodos", len(gdf_nodes))
    
    # 5. Crear edges conectando zonas cercanas
    logger.info("Generando edges (conectividad por proximidad)...")
    logger.info("  Parámetros:")
    logger.info("    - Max conexiones por nodo: %d", max_connections)
    logger.info("    - Distancia máxima: %.1f km", max_distance_km)
    
    edges_data = []
    edge_types = ["motorway", "trunk", "primary", "secondary", "tertiary"]
    speeds = {
        "motorway": 80,
        "trunk": 70,
        "primary": 60,
        "secondary": 50,
        "tertiary": 40,
    }
    
    max_distance_m = max_distance_km * 1000
    
    for idx, node in gdf_nodes.iterrows():
        node_id = node["node_id"]
        node_geom = node["geometry"]
        
        # Calcular distancias a otros nodos
        distances = gdf_nodes.geometry.distance(node_geom)
        
        # Filtrar nodos dentro de distancia máxima (excluyendo el mismo)
        mask = (distances > 0) & (distances <= max_distance_m)
        nearby_nodes = gdf_nodes[mask].copy()
        nearby_distances = distances[mask]
        
        # Ordenar por distancia y tomar los N más cercanos
        if len(nearby_nodes) > 0:
            sorted_indices = nearby_distances.sort_values().index[:max_connections]
            
            for target_idx in sorted_indices:
                target_node = gdf_nodes.loc[target_idx]
                target_id = target_node["node_id"]
                
                # Calcular distancia real
                length = node_geom.distance(target_node["geometry"])
                
                # Asignar tipo de vía basado en distancia
                if length < 3000:
                    edge_type = "primary"
                elif length < 6000:
                    edge_type = "secondary"
                elif length < 10000:
                    edge_type = "tertiary"
                else:
                    edge_type = "tertiary"
                
                speed = float(speeds[edge_type])
                
                # Crear edge (bidireccional)
                edges_data.append({
                    "u": node_id,
                    "v": target_id,
                    "length": length,
                    "speed": speed,
                    "primary_class": edge_type,
                    "geometry": LineString([node_geom, target_node["geometry"]]),
                })
                
                edges_data.append({
                    "u": target_id,
                    "v": node_id,
                    "length": length,
                    "speed": speed,
                    "primary_class": edge_type,
                    "geometry": LineString([target_node["geometry"], node_geom]),
                })
    
    gdf_edges = gpd.GeoDataFrame(edges_data, crs=gdf_zones.crs)
    
    # Eliminar duplicados (puede haber edges repetidos por bidireccionalidad)
    logger.info("  Eliminando edges duplicados...")
    gdf_edges = gdf_edges.drop_duplicates(subset=["u", "v"], keep="first")
    
    logger.info("  ✓ Creados %d edges", len(gdf_edges))
    
    # 6. Estadísticas de la red
    logger.info("\n=== Estadísticas de la red ===")
    logger.info("  Nodos: %d", len(gdf_nodes))
    logger.info("  Edges: %d", len(gdf_edges))
    
    # Conexiones por nodo
    connections_per_node = gdf_edges.groupby("u").size()
    logger.info("  Conexiones por nodo:")
    logger.info("    - Media: %.1f", connections_per_node.mean())
    logger.info("    - Mín: %d", connections_per_node.min())
    logger.info("    - Máx: %d", connections_per_node.max())
    
    # Distancias
    distances_km = gdf_edges["length"] / 1000
    logger.info("  Distancias de edges:")
    logger.info("    - Media: %.2f km", distances_km.mean())
    logger.info("    - Mín: %.2f km", distances_km.min())
    logger.info("    - Máx: %.2f km", distances_km.max())
    
    # Tipos de vía
    logger.info("  Distribución de tipos de vía:")
    for edge_type, count in gdf_edges["primary_class"].value_counts().items():
        pct = count / len(gdf_edges) * 100
        logger.info("    - %s: %d (%.1f%%)", edge_type, count, pct)
    
    # 7. Guardar archivos
    output_dir.mkdir(parents=True, exist_ok=True)
    
    nodes_file = output_dir / "nodes.gpkg"
    edges_file = output_dir / "edges.gpkg"
    
    logger.info("\n=== Guardando archivos ===")
    gdf_nodes.to_file(nodes_file, driver="GPKG")
    logger.info("  ✓ Nodos guardados en %s", nodes_file)
    
    gdf_edges.to_file(edges_file, driver="GPKG")
    logger.info("  ✓ Edges guardados en %s", edges_file)
    
    return gdf_nodes, gdf_edges


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Genera red vial sintética desde zonas geográficas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Generar red con parámetros por defecto
  python scripts/generate_network.py
  
  # Generar red con más conexiones y mayor alcance
  python scripts/generate_network.py --max-connections 8 --max-distance 30
  
  # Especificar archivo de zonas y directorio de salida
  python scripts/generate_network.py \\
    --zones data/raw/geografia/mi_archivo.geojson \\
    --output data/network/custom

NOTA: Este script genera una red SINTÉTICA basada en proximidad de centroides.
Para usar red vial real, reemplazar con script que lea:
  - Shapefiles de calles/vías del municipio
  - Datos de OpenStreetMap (OSM)
  - Base de datos de red vial oficial
        """,
    )
    
    parser.add_argument(
        "--zones",
        type=Path,
        default=Path("data/raw/geografia/470-458_kido_geografico.geojson"),
        help="Archivo GeoJSON con zonas (default: data/raw/geografia/470-458_kido_geografico.geojson)",
    )
    
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/network/synthetic"),
        help="Directorio de salida para nodes.gpkg y edges.gpkg (default: data/network/synthetic)",
    )
    
    parser.add_argument(
        "--max-connections",
        type=int,
        default=5,
        help="Máximo número de conexiones por nodo (default: 5)",
    )
    
    parser.add_argument(
        "--max-distance",
        type=float,
        default=20.0,
        help="Distancia máxima para conectar nodos en km (default: 20.0)",
    )
    
    args = parser.parse_args()
    
    # Validar archivo de entrada
    if not args.zones.exists():
        logger.error("Error: Archivo de zonas no existe: %s", args.zones)
        return 1
    
    # Generar red
    try:
        generate_network_from_zones(
            zones_file=args.zones,
            output_dir=args.output,
            max_connections=args.max_connections,
            max_distance_km=args.max_distance,
        )
        
        logger.info("\n✅ Red sintética generada exitosamente")
        logger.info("\nPróximos pasos:")
        logger.info("  1. Asignar nodos a datos OD: python scripts/assign_nodes_to_od.py")
        logger.info("  2. Ejecutar routing: python scripts/run_pipeline.py")
        
        return 0
        
    except Exception as exc:
        logger.error("Error generando red: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
