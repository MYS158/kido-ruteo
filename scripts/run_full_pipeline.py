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
    
    # Paso 0: Combinar todos los archivos de checkpoint
    print("Combinando archivos de checkpoint...")
    all_files = list(checkpoint_dir.glob("checkpoint*.csv"))
    
    if not all_files:
        print(f"No se encontraron archivos en {checkpoint_dir}")
        return

    dfs = []
    for f in all_files:
        try:
            # Extraer ID del nombre
            import re
            match = re.search(r'checkpoint(\d+)', f.name, re.IGNORECASE)
            if match:
                chk_id = match.group(1)
                df_temp = pd.read_csv(f)
                df_temp['checkpoint_id'] = chk_id
                dfs.append(df_temp)
                print(f"  - Cargado: {f.name} (ID: {chk_id})")
        except Exception as e:
            print(f"  - Error cargando {f.name}: {e}")
    
    if not dfs:
        print("No se pudo cargar ningún archivo válido.")
        return
        
    # Concatenar y guardar temporalmente
    df_combined = pd.concat(dfs, ignore_index=True)
    combined_od_path = data_dir / "interim" / "combined_checkpoints.csv"
    os.makedirs(combined_od_path.parent, exist_ok=True)
    df_combined.to_csv(combined_od_path, index=False)
    print(f"Archivo combinado guardado en: {combined_od_path} ({len(df_combined)} filas)")

    # Usar el archivo combinado como entrada
    od_path = combined_od_path
    
    zonification_path = data_dir / "raw" / "zonification" / "zonification.geojson"
    
    # Asumimos que la red vial está en data/raw/network/red.geojson o similar
    # Si no existe, el usuario debe proveer la ruta correcta
    network_path = data_dir / "raw" / "network" / "red.geojson"
    if not network_path.exists():
        # Intentar buscar en otra ubicación común o usar un placeholder
        network_path = data_dir / "raw" / "red.geojson"
        
    capacity_path = data_dir / "raw" / "capacity" / "summary_capacity.csv"
    
    # Bounding Box para Querétaro (aprox)
    # North, South, East, West
    osm_bbox = [20.8, 19.9, -99.7, -100.9]
    
    # Directorio de salida
    output_dir = data_dir / "processed"
    
    print(f"=== KIDO-Ruteo: Ejecución de Pipeline Completo ===")
    print(f"Entradas:")
    print(f"  - OD: {od_path}")
    print(f"  - Zonificación: {zonification_path}")
    print(f"  - Red Vial: {network_path} (Se descargará si no existe)")
    print(f"  - Capacidad: {capacity_path}")
    print(f"Salida: {output_dir}")
    print("==================================================")
    
    # Verificar existencia de archivos críticos
    if not od_path.exists():
        print(f"❌ Error: No se encuentra el archivo OD en {od_path}")
        return
    if not zonification_path.exists():
        print(f"❌ Error: No se encuentra el archivo de zonificación en {zonification_path}")
        return
    # network_path y capacity_path son críticos, pero dejamos que el pipeline falle si no están
    # para mostrar el error específico del loader.
    
    try:
        output_file = run_pipeline(
            od_path=str(od_path),
            zonification_path=str(zonification_path),
            network_path=str(network_path),
            capacity_path=str(capacity_path),
            output_dir=str(output_dir),
            osm_bbox=osm_bbox
        )
        print(f"\n✅ Proceso finalizado exitosamente.")
        print(f"Resultados disponibles en: {output_file}")
        
    except Exception as e:
        print(f"\n❌ Error durante la ejecución del pipeline:")
        print(str(e))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
