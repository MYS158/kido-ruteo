"""
Script de construcción de rutas para KIDO-Ruteo.

Carga zonas, construye grafo y genera rutas shortest-path entre pares OD.
"""

import pandas as pd
import geopandas as gpd
import networkx as nx
from pathlib import Path
from typing import Tuple, Optional
from tqdm import tqdm


def get_project_root() -> Path:
    """Obtiene el directorio raíz del proyecto."""
    return Path(__file__).parent.parent


def load_zones(geojson_path: Path) -> gpd.GeoDataFrame:
    """
    Carga geometrías de zonas desde GeoJSON.
    
    Args:
        geojson_path: Ruta al archivo GeoJSON
        
    Returns:
        GeoDataFrame con zonas
    """
    print(f"📍 Cargando zonas desde {geojson_path.name}...")
    gdf = gpd.read_file(geojson_path)
    
    # Calcular centroides si no existen
    if 'centroid' not in gdf.columns:
        gdf['centroid'] = gdf.geometry.centroid
    
    print(f"  ✓ {len(gdf)} zonas cargadas")
    return gdf


def build_graph(zones: gpd.GeoDataFrame) -> nx.Graph:
    """
    Construye grafo de conectividad entre zonas.
    
    Args:
        zones: GeoDataFrame con zonas
        
    Returns:
        Grafo de NetworkX
    """
    print("\n🔗 Construyendo grafo de conectividad...")
    
    G = nx.Graph()
    
    # Agregar nodos (zonas)
    for idx, row in zones.iterrows():
        zone_id = row.get('id', row.get('zone_id', idx))
        G.add_node(
            zone_id,
            pos=(row.centroid.x, row.centroid.y),
            geometry=row.geometry
        )
    
    # Agregar aristas entre zonas adyacentes
    for i, zone_i in zones.iterrows():
        id_i = zone_i.get('id', zone_i.get('zone_id', i))
        
        for j, zone_j in zones.iterrows():
            if i >= j:
                continue
            
            id_j = zone_j.get('id', zone_j.get('zone_id', j))
            
            # Verificar adyacencia (zonas que se tocan)
            if zone_i.geometry.touches(zone_j.geometry):
                distance = zone_i.centroid.distance(zone_j.centroid)
                G.add_edge(id_i, id_j, weight=distance)
    
    print(f"  ✓ Grafo construido: {G.number_of_nodes()} nodos, {G.number_of_edges()} aristas")
    return G


def compute_shortest_paths(
    G: nx.Graph,
    od_pairs: pd.DataFrame,
    origin_col: str = 'origen',
    dest_col: str = 'destino'
) -> pd.DataFrame:
    """
    Calcula rutas shortest-path para pares OD.
    
    Args:
        G: Grafo de NetworkX
        od_pairs: DataFrame con pares OD
        origin_col: Nombre de columna de origen
        dest_col: Nombre de columna de destino
        
    Returns:
        DataFrame con rutas calculadas
    """
    print("\n🚗 Calculando rutas shortest-path...")
    
    routes = []
    
    for idx, row in tqdm(od_pairs.iterrows(), total=len(od_pairs)):
        origin = row[origin_col]
        destination = row[dest_col]
        
        try:
            # Calcular ruta más corta
            path = nx.shortest_path(G, source=origin, target=destination, weight='weight')
            path_length = nx.shortest_path_length(G, source=origin, target=destination, weight='weight')
            
            routes.append({
                'origin': origin,
                'destination': destination,
                'path': path,
                'path_length': path_length,
                'num_segments': len(path) - 1
            })
        except (nx.NetworkXNoPath, nx.NodeNotFound) as e:
            # No existe ruta o nodo no encontrado
            routes.append({
                'origin': origin,
                'destination': destination,
                'path': None,
                'path_length': None,
                'num_segments': None,
                'error': str(e)
            })
    
    df_routes = pd.DataFrame(routes)
    
    valid_routes = df_routes['path'].notna().sum()
    print(f"  ✓ {valid_routes}/{len(df_routes)} rutas calculadas exitosamente")
    
    return df_routes


def main():
    """Ejecuta el proceso completo de construcción de rutas."""
    print("=" * 60)
    print("KIDO-Ruteo - Construcción de Rutas")
    print("=" * 60)
    
    root = get_project_root()
    
    # Rutas de entrada
    interim_dir = root / "data" / "interim"
    geojson_dir = interim_dir / "geojson"
    consultas_dir = interim_dir / "consultas"
    
    # Directorio de salida
    output_dir = root / "data" / "processed" / "routes"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Cargar zonas
    geojson_files = list(geojson_dir.glob("*.geojson"))
    if not geojson_files:
        print("❌ No se encontraron archivos GeoJSON en data/interim/geojson/")
        return
    
    zones = load_zones(geojson_files[0])
    
    # 2. Construir grafo
    G = build_graph(zones)
    
    # 3. Cargar pares OD
    od_files = list((consultas_dir / "general").glob("*.csv"))
    if not od_files:
        print("❌ No se encontraron archivos OD en data/interim/consultas/general/")
        return
    
    print(f"\n📊 Cargando pares OD desde {od_files[0].name}...")
    od_data = pd.read_csv(od_files[0])
    print(f"  ✓ {len(od_data)} pares OD cargados")
    
    # 4. Calcular rutas
    routes = compute_shortest_paths(G, od_data)
    
    # 5. Guardar resultados
    output_path = output_dir / "routes_shortest_path.csv"
    routes.to_csv(output_path, index=False)
    print(f"\n💾 Rutas guardadas en: {output_path}")
    
    print("\n" + "=" * 60)
    print("✅ Construcción de rutas completada")
    print("=" * 60)


if __name__ == "__main__":
    main()
