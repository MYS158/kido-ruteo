#!/usr/bin/env python
"""
Script para calcular matriz MC2 (Paso 6 KIDO) - con checkpoint.

Uso:
    python scripts/compute_impedance2.py
"""

import sys
from pathlib import Path

# Añadir src/ al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kido_ruteo import io, constrained_paths


def main():
    """Función principal."""
    print("=== KIDO-Ruteo: Paso 6 - Matriz MC2 (con checkpoint) ===\n")
    
    # Cargar datos
    print("Cargando red vial...")
    red_vial = io.load_red_vial()
    
    print("Cargando zonificación con checkpoints...")
    zonificacion = io.load_zonificacion()
    
    print("Cargando matriz OD con MC...")
    od_mc = io.load_processed("od_with_mc.csv")
    
    # Calcular MC2
    print("\nCalculando constrained shortest paths...")
    od_mc2 = constrained_paths.compute_impedance_matrix_mc2(
        od_mc, red_vial, zonificacion
    )
    io.save_processed(od_mc2, "od_with_mc2.csv")
    print(f"  ✓ {len(od_mc2)} pares OD con impedancia MC2")
    
    # Estadísticas
    with_mc2 = od_mc2['mc2_distance'].notna().sum()
    print(f"\nEstadísticas:")
    print(f"  - Pares con MC2 válido: {with_mc2}")
    print(f"  - Pares sin MC2: {len(od_mc2) - with_mc2}")
    
    print("\n✓ Matriz MC2 completada")


if __name__ == "__main__":
    main()
