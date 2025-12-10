#!/usr/bin/env python
"""
Script para ejecutar preprocesamiento (Paso 1 KIDO).

Uso:
    python scripts/run_preprocessing.py
"""

import sys
from pathlib import Path

# Añadir src/ al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kido_ruteo import io, preprocessing


def main():
    """Función principal."""
    print("=== KIDO-Ruteo: Paso 1 - Preprocesamiento ===\n")
    
    # Cargar datos
    print("Cargando OD General...")
    od_df = io.load_od_general()
    
    # Preprocesar
    print("Creando total_trips_modif e intrazonal...")
    od_processed = preprocessing.prepare_data(od_df)
    
    print(f"\nEstadísticas:")
    print(f"  - Registros: {len(od_processed)}")
    print(f"  - Intrazonales: {od_processed['intrazonal'].sum()}")
    print(f"  - Viajes modificados: {od_processed['total_trips_modif'].sum():.0f}")
    
    # Guardar
    print("\nGuardando en data/processed/...")
    io.save_processed(od_processed, "od_preprocessed.csv")
    
    print("\n✓ Preprocesamiento completado")


if __name__ == "__main__":
    main()
