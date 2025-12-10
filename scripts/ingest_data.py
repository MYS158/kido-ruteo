"""
Script de ingesta de datos para KIDO-Ruteo.

Lee datos desde las fuentes oficiales y los copia en data/raw/
"""

import os
import shutil
from pathlib import Path
from typing import List
import geopandas as gpd
import pandas as pd
from tqdm import tqdm


def get_project_root() -> Path:
    """Obtiene el directorio raíz del proyecto."""
    return Path(__file__).parent.parent


def ingest_geojson(source_dir: Path, target_dir: Path) -> None:
    """
    Ingesta archivos GeoJSON desde la fuente.
    
    Args:
        source_dir: Directorio fuente con archivos .geojson
        target_dir: Directorio destino en data/raw/
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    geojson_files = list(source_dir.glob("*.geojson"))
    
    print(f"\n📍 Ingiriendo {len(geojson_files)} archivos GeoJSON...")
    for geojson_file in tqdm(geojson_files):
        # Validar que sea un GeoJSON válido
        try:
            gdf = gpd.read_file(geojson_file)
            print(f"  ✓ {geojson_file.name}: {len(gdf)} geometrías")
            
            # Copiar a destino
            target_path = target_dir / geojson_file.name
            shutil.copy2(geojson_file, target_path)
        except Exception as e:
            print(f"  ✗ Error en {geojson_file.name}: {e}")


def ingest_csv_consultas(source_dir: Path, target_dir: Path, subdir: str) -> None:
    """
    Ingesta archivos CSV de consultas (General o Checkpoint).
    
    Args:
        source_dir: Directorio fuente con archivos .csv
        target_dir: Directorio destino en data/raw/
        subdir: Subdirectorio ('general' o 'checkpoint')
    """
    target_subdir = target_dir / subdir
    target_subdir.mkdir(parents=True, exist_ok=True)
    
    csv_files = list(source_dir.glob("*.csv"))
    
    print(f"\n📊 Ingiriendo {len(csv_files)} archivos CSV de {subdir}...")
    for csv_file in tqdm(csv_files):
        try:
            df = pd.read_csv(csv_file)
            print(f"  ✓ {csv_file.name}: {len(df)} registros")
            
            # Copiar a destino
            target_path = target_subdir / csv_file.name
            shutil.copy2(csv_file, target_path)
        except Exception as e:
            print(f"  ✗ Error en {csv_file.name}: {e}")


def ingest_zoning(source_dir: Path, target_dir: Path) -> None:
    """
    Ingesta archivos de zonificación (.qmd).
    
    Args:
        source_dir: Directorio fuente con archivos .qmd
        target_dir: Directorio destino en data/raw/
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    qmd_files = list(source_dir.glob("*.qmd"))
    
    print(f"\n🗺️  Ingiriendo {len(qmd_files)} archivos de zonificación...")
    for qmd_file in tqdm(qmd_files):
        target_path = target_dir / qmd_file.name
        shutil.copy2(qmd_file, target_path)
        print(f"  ✓ {qmd_file.name}")


def main():
    """Ejecuta el proceso completo de ingesta de datos."""
    print("=" * 60)
    print("KIDO-Ruteo - Ingesta de Datos")
    print("=" * 60)
    
    root = get_project_root()
    
    # Definir rutas de origen (ajustar según tu estructura real)
    source_base = root / "data" / "raw" / "kido-data2"
    
    # Rutas de destino
    target_base = root / "data" / "raw"
    
    # 1. Ingestar GeoJSON
    geojson_source = source_base / "Geojson"
    if geojson_source.exists():
        ingest_geojson(geojson_source, target_base / "geojson")
    else:
        print(f"⚠️  No se encontró: {geojson_source}")
    
    # 2. Ingestar consultas generales
    general_source = source_base / "Consultas" / "General"
    if general_source.exists():
        ingest_csv_consultas(general_source, target_base / "consultas", "general")
    else:
        print(f"⚠️  No se encontró: {general_source}")
    
    # 3. Ingestar consultas checkpoint
    checkpoint_source = source_base / "Consultas" / "Checkpoint"
    if checkpoint_source.exists():
        ingest_csv_consultas(checkpoint_source, target_base / "consultas", "checkpoint")
    else:
        print(f"⚠️  No se encontró: {checkpoint_source}")
    
    # 4. Ingestar zonificación
    zoning_source = source_base / "Zoning"
    if zoning_source.exists():
        ingest_zoning(zoning_source, target_base / "zoning")
    else:
        print(f"⚠️  No se encontró: {zoning_source}")
    
    print("\n" + "=" * 60)
    print("✅ Ingesta completada")
    print("=" * 60)


if __name__ == "__main__":
    main()
