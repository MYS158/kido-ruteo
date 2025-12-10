#!/usr/bin/env python
"""
Script para calcular viajes finales (Pasos 9-12 KIDO).

Uso:
    python scripts/compute_viajes.py
"""

import sys
from pathlib import Path

# Añadir src/ al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kido_ruteo import io, viajes


def main():
    """Función principal."""
    print("=== KIDO-Ruteo: Pasos 9-12 - Viajes y Export ===\n")
    
    # Cargar datos
    print("Cargando matriz OD con congruencia...")
    od_df = io.load_processed("od_with_congruence.csv")
    
    # Calcular viajes
    print("\nCalculando Viajes = id_congruencia × id_potencial × (1-intrazonal) × total_trips_modif...")
    od_viajes = viajes.calculate_viajes(od_df)
    
    # Tablas diarias
    print("Añadiendo tablas diarias (tpdes, tpdfs, tpds)...")
    od_daily = viajes.add_daily_tables(od_viajes, fecha="2024-01-01")
    
    # Conversión a vehículo
    print("Convirtiendo a viajes en vehículo...")
    od_vehicle = viajes.convert_to_vehicle_trips(od_daily, factor_ocupacion=1.5)
    
    # Estadísticas
    print(f"\nEstadísticas:")
    print(f"  - Total Viajes: {od_vehicle['Viajes'].sum():.0f}")
    print(f"  - Total TPDA: {od_vehicle['TPDA'].sum():.0f}")
    
    # Guardar completo
    io.save_processed(od_vehicle, "od_final_viajes.csv")
    
    # Exportar por tipología
    print("\nExportando matrices por tipología...")
    viajes.export_matrices_by_tipologia(od_vehicle, "data/processed/")
    print("  ✓ matriz_tipologia_A.csv")
    print("  ✓ matriz_tipologia_B.csv")
    print("  ✓ matriz_tipologia_C.csv")
    
    print("\n✓ Pipeline KIDO completado")


if __name__ == "__main__":
    main()
