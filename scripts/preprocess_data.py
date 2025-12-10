"""
Script de preprocesamiento de datos para KIDO-Ruteo.

Normaliza columnas, convierte tipos y valida matrices OD.
"""

import pandas as pd
import geopandas as gpd
from pathlib import Path
from typing import Dict, List, Optional
from tqdm import tqdm


def get_project_root() -> Path:
    """Obtiene el directorio raíz del proyecto."""
    return Path(__file__).parent.parent


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza nombres de columnas a snake_case.
    
    Args:
        df: DataFrame a normalizar
        
    Returns:
        DataFrame con columnas normalizadas
    """
    df = df.copy()
    df.columns = (
        df.columns
        .str.lower()
        .str.replace(' ', '_')
        .str.replace('-', '_')
        .str.replace('.', '_')
    )
    return df


def convert_od_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte tipos de datos en matrices OD.
    
    Args:
        df: DataFrame con datos OD
        
    Returns:
        DataFrame con tipos correctos
    """
    df = df.copy()
    
    # Identificar columnas de origen/destino
    id_cols = [col for col in df.columns if 'origen' in col or 'destino' in col or 'id' in col]
    for col in id_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
    
    # Identificar columnas numéricas (viajes, distancias, etc.)
    numeric_cols = [col for col in df.columns if any(
        kw in col for kw in ['viajes', 'trips', 'distancia', 'distance', 'tiempo', 'time']
    )]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df


def validate_od_matrix(df: pd.DataFrame) -> Dict[str, any]:
    """
    Valida consistencia de una matriz OD.
    
    Args:
        df: DataFrame con matriz OD
        
    Returns:
        Diccionario con resultados de validación
    """
    validation = {
        'total_rows': len(df),
        'null_origins': df.filter(regex='origen|origin').isnull().sum().sum(),
        'null_destinations': df.filter(regex='destino|destination').isnull().sum().sum(),
        'negative_trips': (df.filter(regex='viajes|trips') < 0).sum().sum(),
        'zero_trips': (df.filter(regex='viajes|trips') == 0).sum().sum(),
        'valid': True
    }
    
    # Marcar como inválida si hay problemas críticos
    if validation['null_origins'] > 0 or validation['null_destinations'] > 0:
        validation['valid'] = False
    
    return validation


def preprocess_consultas(input_dir: Path, output_dir: Path, subdir: str) -> None:
    """
    Preprocesa archivos CSV de consultas.
    
    Args:
        input_dir: Directorio con CSVs originales
        output_dir: Directorio de salida
        subdir: Subdirectorio ('general' o 'checkpoint')
    """
    input_subdir = input_dir / subdir
    output_subdir = output_dir / subdir
    output_subdir.mkdir(parents=True, exist_ok=True)
    
    csv_files = list(input_subdir.glob("*.csv"))
    
    print(f"\n📊 Preprocesando {len(csv_files)} archivos de {subdir}...")
    for csv_file in tqdm(csv_files):
        try:
            # Leer CSV
            df = pd.read_csv(csv_file)
            
            # Normalizar columnas
            df = normalize_column_names(df)
            
            # Convertir tipos
            df = convert_od_types(df)
            
            # Validar
            validation = validate_od_matrix(df)
            
            if validation['valid']:
                # Guardar procesado
                output_path = output_subdir / csv_file.name
                df.to_csv(output_path, index=False)
                print(f"  ✓ {csv_file.name}: {validation['total_rows']} registros válidos")
            else:
                print(f"  ⚠️  {csv_file.name}: Problemas de validación")
                print(f"      - Orígenes nulos: {validation['null_origins']}")
                print(f"      - Destinos nulos: {validation['null_destinations']}")
                
        except Exception as e:
            print(f"  ✗ Error en {csv_file.name}: {e}")


def preprocess_geojson(input_dir: Path, output_dir: Path) -> None:
    """
    Preprocesa archivos GeoJSON.
    
    Args:
        input_dir: Directorio con GeoJSON originales
        output_dir: Directorio de salida
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    geojson_files = list(input_dir.glob("*.geojson"))
    
    print(f"\n📍 Preprocesando {len(geojson_files)} archivos GeoJSON...")
    for geojson_file in tqdm(geojson_files):
        try:
            # Leer GeoJSON
            gdf = gpd.read_file(geojson_file)
            
            # Normalizar columnas
            gdf.columns = (
                gdf.columns
                .str.lower()
                .str.replace(' ', '_')
                .str.replace('-', '_')
            )
            
            # Verificar CRS
            if gdf.crs is None:
                print(f"  ⚠️  {geojson_file.name}: Sin CRS definido")
            
            # Guardar procesado
            output_path = output_dir / geojson_file.name
            gdf.to_file(output_path, driver='GeoJSON')
            print(f"  ✓ {geojson_file.name}: {len(gdf)} geometrías")
            
        except Exception as e:
            print(f"  ✗ Error en {geojson_file.name}: {e}")


def main():
    """Ejecuta el proceso completo de preprocesamiento."""
    print("=" * 60)
    print("KIDO-Ruteo - Preprocesamiento de Datos")
    print("=" * 60)
    
    root = get_project_root()
    
    input_base = root / "data" / "raw"
    output_base = root / "data" / "interim"
    
    # 1. Preprocesar consultas generales
    if (input_base / "consultas" / "general").exists():
        preprocess_consultas(input_base / "consultas", output_base / "consultas", "general")
    
    # 2. Preprocesar consultas checkpoint
    if (input_base / "consultas" / "checkpoint").exists():
        preprocess_consultas(input_base / "consultas", output_base / "consultas", "checkpoint")
    
    # 3. Preprocesar GeoJSON
    if (input_base / "geojson").exists():
        preprocess_geojson(input_base / "geojson", output_base / "geojson")
    
    print("\n" + "=" * 60)
    print("✅ Preprocesamiento completado")
    print("=" * 60)


if __name__ == "__main__":
    main()
