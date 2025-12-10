#!/usr/bin/env python
"""
Script para calcular congruencia (Pasos 7-8 KIDO).

Uso:
    python scripts/compute_congruence.py
"""

import sys
from pathlib import Path

# Añadir src/ al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kido_ruteo import io, access_vectors, congruence


def main():
    """Función principal."""
    print("=== KIDO-Ruteo: Pasos 7-8 - Congruencia ===\n")
    
    # Cargar datos
    print("Cargando matriz OD con MC y MC2...")
    od_df = io.load_processed("od_with_mc2.csv")
    
    # Vectores de acceso (Paso 3)
    print("\nGenerando vectores de acceso...")
    od_access = access_vectors.compute_access_vectors(od_df)
    io.save_processed(od_access, "od_with_access.csv")
    print(f"  ✓ id_potencial y congruencia_acceso asignados")
    
    # Congruencia
    print("\nCalculando congruencia X y niveles...")
    od_congruence = congruence.compute_congruence(od_access)
    io.save_processed(od_congruence, "od_with_congruence.csv")
    
    # Estadísticas
    print(f"\nEstadísticas:")
    print(f"  - Congruencia nivel 3: {(od_congruence['congruencia'] == 3).sum()}")
    print(f"  - Congruencia nivel 4: {(od_congruence['congruencia'] == 4).sum()}")
    print(f"  - id_congruencia = 1: {(od_congruence['id_congruencia'] == 1).sum()}")
    print(f"  - id_congruencia = 0: {(od_congruence['id_congruencia'] == 0).sum()}")
    
    print("\n✓ Congruencia completada")


if __name__ == "__main__":
    main()
