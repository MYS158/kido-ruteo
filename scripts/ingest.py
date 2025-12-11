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
    
    # Definir rutas base
    base_path = Path("data/raw")
    queries_path = base_path / "queries"
    zonif_path = base_path / "zonification"
    
    # Cargar datos
    print("Cargando OD General...")
    # Usamos load_all_od_files para cargar todos los CSVs del directorio
    try:
        od_general = io.load_all_od_files(queries_path / "general", tipo="general")
        print(f"  ✓ {len(od_general)} registros\n")
    except FileNotFoundError as e:
        print(f"  x Error: {e}\n")
        od_general = None

    print("Cargando OD Checkpoint...")
    try:
        od_checkpoint = io.load_all_od_files(queries_path / "checkpoint", tipo="checkpoint")
        print(f"  ✓ {len(od_checkpoint)} registros\n")
    except FileNotFoundError as e:
        print(f"  x Error: {e}\n")
        od_checkpoint = None
    
    print("Cargando red vial...")
    # Asumimos que red.geojson debería estar en zonification o en raw root
    # Ajustar ruta según donde se decida poner el archivo faltante
    red_path = zonif_path / "red.geojson" 
    if red_path.exists():
        red_vial = io.load_red_vial(red_path)
        print(f"  ✓ {len(red_vial)} aristas\n")
    else:
        print(f"  x Archivo no encontrado: {red_path}\n")
        red_vial = None
    
    print("Cargando zonificación...")
    zonif_file = zonif_path / "zonification.geojson"
    if zonif_file.exists():
        zonificacion = io.load_zonificacion(zonif_file)
        print(f"  ✓ {len(zonificacion)} zonas\n")
    else:
        print(f"  x Archivo no encontrado: {zonif_file}\n")
        zonificacion = None
    
    print("Cargando cardinalidad...")
    # Asumimos ubicación en raw/cardinalidad.csv o similar
    card_path = base_path / "cardinalidad.csv"
    if card_path.exists():
        cardinalidad = io.load_cardinalidad(card_path)
        print(f"  ✓ {len(cardinalidad)} registros\n")
    else:
        print(f"  x Archivo no encontrado: {card_path}\n")
        cardinalidad = None
    
    # Guardar en interim solo si se cargaron correctamente
    print("Guardando en data/interim/...")
    
    if od_general is not None:
        io.save_interim(od_general, "od_general")
    
    if od_checkpoint is not None:
        io.save_interim(od_checkpoint, "od_checkpoint")
        
    if red_vial is not None:
        io.save_geojson(red_vial, "red_vial.geojson")
        
    if zonificacion is not None:
        io.save_geojson(zonificacion, "zonificacion.geojson")
        
    if cardinalidad is not None:
        io.save_interim(cardinalidad, "cardinalidad")
    
    print("\n✓ Ingesta completada (con advertencias si faltan archivos)")


if __name__ == "__main__":
    main()
