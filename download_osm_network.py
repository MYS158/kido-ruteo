"""
Script para descargar una red vial de OSM que cubra todos los checkpoints.
"""

import geopandas as gpd
import osmnx as ox
from src.kido_ruteo.processing.checkpoint_loader import load_checkpoints_from_zonification
from src.kido_ruteo.routing.graph_loader import save_graph_to_geojson

# 1. Cargar todos los checkpoints
print("Cargando checkpoints desde zonification.geojson...")
checkpoints = load_checkpoints_from_zonification('data/raw/zonification/zonification.geojson')

# 2. Calcular bounding box que cubra todos los checkpoints
print("\nCalculando bounding box...")
# Agregar un margen del 10% para incluir carreteras circundantes
margin = 0.1

minx, miny, maxx, maxy = checkpoints.total_bounds
dx = (maxx - minx) * margin
dy = (maxy - miny) * margin

bbox_north = maxy + dy
bbox_south = miny - dy
bbox_east = maxx + dx
bbox_west = minx - dx

print(f"  Norte: {bbox_north:.4f}")
print(f"  Sur:   {bbox_south:.4f}")
print(f"  Este:  {bbox_east:.4f}")
print(f"  Oeste: {bbox_west:.4f}")

# 3. Descargar red de OSM
print("\n⏳ Descargando red vial de OpenStreetMap...")
print("   (Esto puede tomar varios minutos dependiendo del área)")

try:
    # bbox format: (north, south, east, west) - orden correcto para OSMnx
    G = ox.graph_from_bbox(
        bbox=(bbox_north, bbox_south, bbox_east, bbox_west),
        network_type='drive',
        simplify=True
    )
    
    print(f"\n✓ Red descargada exitosamente")
    print(f"  Nodos: {G.number_of_nodes()}")
    print(f"  Aristas: {G.number_of_edges()}")
    
    # 4. Guardar como GeoJSON
    output_path = 'data/raw/red_extended.geojson'
    print(f"\n💾 Guardando red en {output_path}...")
    save_graph_to_geojson(G, output_path)
    
    print(f"\n✅ Red extendida guardada exitosamente")
    print(f"   Para usarla, actualiza el script de ejecución:")
    print(f"   network_path = 'data/raw/red_extended.geojson'")
    
except Exception as e:
    print(f"\n❌ Error al descargar red: {e}")
    print("\nPosibles causas:")
    print("  - Área demasiado grande")
    print("  - Problemas de conectividad")
    print("  - Límites de la API de OSM")
