#!/usr/bin/env python
"""
Script para ingestar datos desde kido-data2/.

Uso:
    python scripts/ingest.py
"""

import sys
from pathlib import Path

# Añadir src/ al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kido_ruteo import io


def main():
    """Función principal."""
    print("=== KIDO-Ruteo: Ingesta de Datos ===\n")
    
    # Cargar datos
    print("Cargando OD General...")
    od_general = io.load_od_general()
    print(f"  ✓ {len(od_general)} registros\n")
    
    print("Cargando OD Checkpoint...")
    od_checkpoint = io.load_od_checkpoint()
    print(f"  ✓ {len(od_checkpoint)} registros\n")
    
    print("Cargando red vial...")
    red_vial = io.load_red_vial()
    print(f"  ✓ {len(red_vial)} aristas\n")
    
    print("Cargando zonificación...")
    zonificacion = io.load_zonificacion()
    print(f"  ✓ {len(zonificacion)} zonas\n")
    
    print("Cargando cardinalidad...")
    cardinalidad = io.load_cardinalidad()
    print(f"  ✓ {len(cardinalidad)} registros\n")
    
    # Guardar en interim
    print("Guardando en data/interim/...")
    io.save_interim(od_general, "od_general.csv")
    io.save_interim(od_checkpoint, "od_checkpoint.csv")
    io.save_geojson(red_vial, "red_vial.geojson")
    io.save_geojson(zonificacion, "zonificacion.geojson")
    io.save_interim(cardinalidad, "cardinalidad.csv")
    
    print("\n✓ Ingesta completada")


if __name__ == "__main__":
    main()
