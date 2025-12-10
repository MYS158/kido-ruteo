#!/usr/bin/env python
"""
Script para calcular matriz MC (Paso 5 KIDO) - sin checkpoint.

Uso:
    python scripts/compute_impedance.py
"""

import sys
from pathlib import Path

# Añadir src/ al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kido_ruteo import io, impedance


def main():
    """Función principal."""
    print("=== KIDO-Ruteo: Paso 5 - Matriz MC (sin checkpoint) ===\n")
    
    # Cargar datos
    print("Cargando red vial...")
    red_vial = io.load_red_vial()
    
    print("Cargando matriz OD con coordenadas...")
    od_df = io.load_processed("od_with_coordinates.csv")
    
    # Calcular MC
    print("\nCalculando shortest paths...")
    od_mc = impedance.compute_mc_matrix(od_df, red_vial)
    io.save_processed(od_mc, "od_with_mc.csv")
    print(f"  ✓ {len(od_mc)} pares OD con impedancia MC")
    
    # Identificar top 80%
    print("\nIdentificando top 80% de viajes...")
    top_80_df = impedance.identify_top_80_percent_trips(od_mc)
    io.save_processed(top_80_df, "od_top_80_percent.csv")
    print(f"  ✓ {len(top_80_df)} pares en top 80%")
    
    # Exportar rutas
    print("\nExportando rutas como GeoJSON...")
    impedance.export_routes_geojson(
        top_80_df, red_vial, "data/processed/routes_mc.geojson"
    )
    
    print("\n✓ Matriz MC completada")


if __name__ == "__main__":
    main()
