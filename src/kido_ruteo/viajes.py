"""
Pasos 9-12 del flujo KIDO: Cálculo de Viajes y Matrices Finales.

Paso 9: Viajes = id_congruencia × id_potencial × (1-intrazonal) × total_trips_modif
Paso 10: Tablas diarias (tpdes, tpdfs, tpds)
Paso 11: Conversión a viajes vehículo
Paso 12: Export matrices por tipología
"""

import pandas as pd
import numpy as np
from datetime import datetime


def calculate_viajes(
    df: pd.DataFrame,
    id_congruencia_col: str = 'id_congruencia',
    id_potencial_col: str = 'id_potencial',
    intrazonal_col: str = 'intrazonal',
    trips_modif_col: str = 'total_trips_modif'
) -> pd.DataFrame:
    """
    Calcula Viajes según fórmula KIDO (Paso 9).
    
    Viajes = id_congruencia × id_potencial × (1-intrazonal) × total_trips_modif
    
    Args:
        df: DataFrame con datos preparados
        id_congruencia_col: Columna de id_congruencia
        id_potencial_col: Columna de id_potencial
        intrazonal_col: Columna de intrazonal
        trips_modif_col: Columna de total_trips_modif
        
    Returns:
        DataFrame con columna Viajes
    """
    df = df.copy()
    
    df['Viajes'] = (
        df[id_congruencia_col] *
        df[id_potencial_col] *
        (1 - df[intrazonal_col]) *
        df[trips_modif_col]
    )
    
    return df


def add_daily_tables(
    df: pd.DataFrame,
    fecha: str = None
) -> pd.DataFrame:
    """
    Añade columnas para tablas diarias (Paso 10).
    
    - tpdes: Tráfico promedio día entre semana
    - tpdfs: Tráfico promedio día fin de semana
    - tpds: Tráfico promedio día sábado
    
    Args:
        df: DataFrame con Viajes
        fecha: Fecha en formato 'YYYY-MM-DD'
        
    Returns:
        DataFrame con columnas diarias
    """
    df = df.copy()
    
    # Agregar fecha
    if fecha is None:
        fecha = datetime.now().strftime('%Y-%m-%d')
    
    df['fecha'] = fecha
    
    # Por ahora, factores simplificados
    # (pueden ajustarse según datos reales)
    df['tpdes'] = df['Viajes'] * 0.70  # 70% en días entre semana
    df['tpdfs'] = df['Viajes'] * 0.25  # 25% en fin de semana
    df['tpds'] = df['Viajes'] * 0.30   # 30% en sábado
    
    return df


def convert_to_vehicle_trips(
    df: pd.DataFrame,
    datos_viales: pd.DataFrame = None,
    tipologia_col: str = 'tipologia'
) -> pd.DataFrame:
    """
    Convierte viajes a viajes vehículo (Paso 11).
    
    - Multiplicar dato vial × factor ocupación
    - Obtener TPDA (Tráfico Promedio Diario Anual)
    - Comparar KIDO vs Vial: E2/E1
    
    Args:
        df: DataFrame con Viajes
        datos_viales: DataFrame con datos viales por tipología
        tipologia_col: Columna de tipología
        
    Returns:
        DataFrame con viajes vehículo
    """
    df = df.copy()
    
    if datos_viales is not None:
        # Merge con datos viales
        df = df.merge(datos_viales, on=['origin_id', 'destination_id'], how='left')
    
    # Factores de ocupación por tipología
    factores_ocupacion = {
        'A': 1.5,  # Automóviles
        'B': 2.5,  # Buses
        'C': 1.2   # Otros
    }
    
    if tipologia_col in df.columns:
        df['factor_ocupacion'] = df[tipologia_col].map(factores_ocupacion)
        df['viajes_vehiculo'] = df['Viajes'] / df['factor_ocupacion']
    else:
        # Si no hay tipología, asumir factor promedio
        df['viajes_vehiculo'] = df['Viajes'] / 1.5
    
    # Calcular TPDA (simplificado)
    df['TPDA'] = df['viajes_vehiculo'] * 365
    
    return df


def calculate_e1_e2(
    df: pd.DataFrame,
    vol_kido_col: str = 'Viajes',
    vol_vial_col: str = 'vol_vial'
) -> pd.DataFrame:
    """
    Calcula métricas E1 y E2 para comparación KIDO vs Vial.
    
    Args:
        df: DataFrame con viajes KIDO y viales
        vol_kido_col: Columna con volumen KIDO
        vol_vial_col: Columna con volumen vial
        
    Returns:
        DataFrame con E1 y E2
    """
    df = df.copy()
    
    if vol_vial_col in df.columns:
        # E1: Diferencia absoluta
        df['E1'] = (df[vol_kido_col] - df[vol_vial_col]).abs()
        
        # E2: Ratio
        df['E2'] = df[vol_kido_col] / df[vol_vial_col]
        df['E2'] = df['E2'].replace([np.inf, -np.inf], np.nan)
        
        # E2/E1
        df['E2_E1_ratio'] = df['E2'] / df['E1']
        df['E2_E1_ratio'] = df['E2_E1_ratio'].replace([np.inf, -np.inf], np.nan)
    
    return df


def export_matrices_by_tipologia(
    df: pd.DataFrame,
    tipologia_col: str = 'tipologia',
    output_dir: str = 'data/processed'
) -> None:
    """
    Exporta matrices finales por tipología A, B, C (Paso 12).
    
    Args:
        df: DataFrame con viajes finales
        tipologia_col: Columna de tipología
        output_dir: Directorio de salida
    """
    from pathlib import Path
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    if tipologia_col not in df.columns:
        print("⚠️  No se encontró columna de tipología. Exportando matriz única.")
        df.to_csv(output_path / 'matriz_final.csv', index=False)
        return
    
    tipologias = df[tipologia_col].unique()
    
    for tip in tipologias:
        df_tip = df[df[tipologia_col] == tip]
        output_file = output_path / f'matriz_tipologia_{tip}.csv'
        df_tip.to_csv(output_file, index=False)
        print(f"  ✓ Exportada: {output_file.name} ({len(df_tip)} registros)")


def compute_viajes_completo(
    df: pd.DataFrame,
    datos_viales: pd.DataFrame = None,
    fecha: str = None
) -> pd.DataFrame:
    """
    Ejecuta proceso completo de cálculo de viajes (Pasos 9-12 KIDO).
    
    Args:
        df: DataFrame con congruencia e id_potencial
        datos_viales: DataFrame opcional con datos viales
        fecha: Fecha para tablas diarias
        
    Returns:
        DataFrame con viajes finales y métricas
    """
    print("=" * 60)
    print("PASOS 9-12: Cálculo de Viajes y Matrices Finales")
    print("=" * 60)
    
    # Paso 9: Calcular Viajes
    print("\nPaso 9: Calculando Viajes...")
    df = calculate_viajes(df)
    total_viajes = df['Viajes'].sum()
    viajes_no_cero = (df['Viajes'] > 0).sum()
    print(f"  ✓ Total de viajes: {total_viajes:,.0f}")
    print(f"  ✓ Pares con viajes > 0: {viajes_no_cero}/{len(df)}")
    
    # Paso 10: Tablas diarias
    print("\nPaso 10: Añadiendo tablas diarias...")
    df = add_daily_tables(df, fecha)
    print(f"  ✓ Columnas diarias añadidas (tpdes, tpdfs, tpds)")
    
    # Paso 11: Conversión a viajes vehículo
    print("\nPaso 11: Convirtiendo a viajes vehículo...")
    df = convert_to_vehicle_trips(df, datos_viales)
    total_vehiculos = df['viajes_vehiculo'].sum()
    print(f"  ✓ Total viajes vehículo: {total_vehiculos:,.0f}")
    
    # Calcular E1/E2 si hay datos viales
    if datos_viales is not None:
        df = calculate_e1_e2(df)
        print(f"  ✓ Métricas E1/E2 calculadas")
    
    # Paso 12: Exportar matrices por tipología
    print("\nPaso 12: Exportando matrices por tipología...")
    export_matrices_by_tipologia(df)
    
    print(f"\n✓ Proceso de viajes completado")
    
    return df
