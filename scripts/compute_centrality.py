#!/usr/bin/env python
"""
Script para calcular centralidad y centroides (Pasos 2a-2b KIDO).

Uso:
    python scripts/compute_centrality.py
"""

import sys
from pathlib import Path

# Añadir src/ al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kido_ruteo import io, centrality, centroides


def main():
    """Función principal."""
    print("=== KIDO-Ruteo: Pasos 2a-2b - Centralidad y Centroides ===\n")
    
    # Cargar red vial y zonificación
    print("Cargando red vial...")
    red_vial = io.load_red_vial()
    
    print("Cargando zonificación...")
    zonificacion = io.load_zonificacion()
    
    # Calcular centralidad
    print("\nCalculando centralidad de nodos...")
    G, node_centrality = centrality.compute_all_centralities(red_vial)
    io.save_interim(node_centrality, "node_centrality.csv")
    print(f"  ✓ {len(node_centrality)} nodos con centralidad")
    
    # Seleccionar centroides
    print("\nSeleccionando centroides por zona...")
    centroids_df = centroides.compute_centroids(
        red_vial, zonificacion, node_centrality
    )
    io.save_processed(centroids_df, "zone_centroids.csv")
    print(f"  ✓ {len(centroids_df)} centroides seleccionados")
    
    # Añadir coordenadas a OD
    print("\nAñadiendo coordenadas a matriz OD...")
    od_df = io.load_interim("od_preprocessed.csv")
    od_with_coords = centroides.add_centroid_coordinates_to_od(od_df, centroids_df)
    io.save_processed(od_with_coords, "od_with_coordinates.csv")
    
    print("\n✓ Centralidad y centroides completados")


if __name__ == "__main__":
    main()
