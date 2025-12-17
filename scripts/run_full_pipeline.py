#!/usr/bin/env python
"""
Script para ejecutar el pipeline completo KIDO-Ruteo v2.0.

Este script orquesta todo el proceso desde la carga de datos hasta la generación
de resultados finales, utilizando la arquitectura modular en src/kido_ruteo.

Uso:
    python scripts/run_full_pipeline.py
"""

import pandas as pd
import sys
import os
from pathlib import Path

# Añadir src/ al path para poder importar el paquete kido_ruteo
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kido_ruteo.pipeline import run_pipeline

def main():
    # Definición de rutas
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    
    # Rutas de entrada
    checkpoint_dir = data_dir / "raw" / "queries" / "checkpoint"
    general_dir = data_dir / "raw" / "queries" / "general"
    
    # Recolectar todos los archivos a procesar
    files_to_process = []
    if checkpoint_dir.exists():
        files_to_process.extend(list(checkpoint_dir.glob("checkpoint*.csv")))
    if general_dir.exists():
        files_to_process.extend(list(general_dir.glob("*.csv")))
        
    if not files_to_process:
        print(f"No se encontraron archivos en {checkpoint_dir} ni en {general_dir}")
        return

    zonification_path = data_dir / "raw" / "zonification" / "zonification.geojson"
    
    # Asumimos que la red vial está en data/raw/network/red.geojson o similar
    network_path = data_dir / "raw" / "network" / "red.geojson"
    if not network_path.exists():
        network_path = data_dir / "raw" / "red.geojson"
        
    capacity_path = data_dir / "raw" / "capacity" / "summary_capacity.csv"
    
    # Bounding Box para Querétaro (aprox)
    osm_bbox = [20.8, 19.9, -99.7, -100.9]
    
    # Directorio de salida
    output_dir = data_dir / "processed"
    
    print(f"=== KIDO-Ruteo: Ejecución de Pipeline Completo ===")
    print(f"Archivos a procesar: {len(files_to_process)}")
    print(f"  - Zonificación: {zonification_path}")
    print(f"  - Red Vial: {network_path}")
    print(f"  - Capacidad: {capacity_path}")
    print(f"Salida: {output_dir}")
    print("==================================================")
    
    if not zonification_path.exists():
        print(f"❌ Error: No se encuentra el archivo de zonificación en {zonification_path}")
        return

    success_count = 0
    fail_count = 0
    
    for od_path in files_to_process:
        print(f"\nProcesando: {od_path.name}...")
        try:
            output_file = run_pipeline(
                od_path=str(od_path),
                zonification_path=str(zonification_path),
                network_path=str(network_path),
                capacity_path=str(capacity_path),
                output_dir=str(output_dir),
                osm_bbox=osm_bbox
            )
            print(f"  ✅ Completado: {output_file}")
            success_count += 1
        except Exception as e:
            print(f"  ❌ Error procesando {od_path.name}: {e}")
            import traceback
            traceback.print_exc()
            fail_count += 1
            
    print(f"\n=== Resumen ===")
    print(f"Procesados exitosamente: {success_count}")
    print(f"Fallidos: {fail_count}")


if __name__ == "__main__":
    main()
