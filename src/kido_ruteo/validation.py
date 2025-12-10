"""
Paso 4 del flujo KIDO: Validación KIDO vs Dato Vial.

Calcula:
- VolDV_personas = dato_vial × factor_ocupación (por tipología A, B, C)
- Factor = VolDV_personas / VolKIDO
- Validación: 0.95 < Factor < 1.05 → válido
"""

import pandas as pd
from typing import Dict


# Factores de ocupación por tipología (valores por defecto)
FACTORES_OCUPACION = {
    'A': 1.5,  # Automóviles
    'B': 2.5,  # Buses
    'C': 1.2   # Otros vehículos
}


def calculate_vol_dv_personas(
    df: pd.DataFrame,
    dato_vial_col: str = 'dato_vial',
    tipologia_col: str = 'tipologia',
    factores: Dict[str, float] = FACTORES_OCUPACION
) -> pd.DataFrame:
    """
    Calcula volumen de dato vial en personas.
    
    VolDV_personas = dato_vial × factor_ocupación
    
    Args:
        df: DataFrame con datos viales
        dato_vial_col: Columna con dato vial
        tipologia_col: Columna con tipología (A, B, C)
        factores: Diccionario de factores de ocupación
        
    Returns:
        DataFrame con columna vol_dv_personas
    """
    df = df.copy()
    
    df['factor_ocupacion'] = df[tipologia_col].map(factores)
    df['vol_dv_personas'] = df[dato_vial_col] * df['factor_ocupacion']
    
    return df


def calculate_validation_factor(
    df: pd.DataFrame,
    vol_dv_col: str = 'vol_dv_personas',
    vol_kido_col: str = 'vol_kido'
) -> pd.DataFrame:
    """
    Calcula factor de validación.
    
    Factor = VolDV_personas / VolKIDO
    
    Args:
        df: DataFrame con volúmenes
        vol_dv_col: Columna con volumen dato vial
        vol_kido_col: Columna con volumen KIDO
        
    Returns:
        DataFrame con columna factor_validacion
    """
    df = df.copy()
    
    df['factor_validacion'] = df[vol_dv_col] / df[vol_kido_col]
    
    # Manejar divisiones por cero
    df['factor_validacion'] = df['factor_validacion'].replace([float('inf'), -float('inf')], None)
    
    return df


def validate_consistency(
    df: pd.DataFrame,
    factor_col: str = 'factor_validacion',
    lower_threshold: float = 0.95,
    upper_threshold: float = 1.05
) -> pd.DataFrame:
    """
    Valida consistencia según umbrales.
    
    Validación: 0.95 < Factor < 1.05 → válido
    
    Args:
        df: DataFrame con factor de validación
        factor_col: Columna con factor
        lower_threshold: Umbral inferior
        upper_threshold: Umbral superior
        
    Returns:
        DataFrame con columna es_valido
    """
    df = df.copy()
    
    df['es_valido'] = (
        (df[factor_col] >= lower_threshold) &
        (df[factor_col] <= upper_threshold)
    )
    
    df['observacion'] = df['es_valido'].apply(
        lambda x: 'Válido' if x else 'Consulta no confiable - preferir dato de campo'
    )
    
    return df


def validate_kido_vs_vial(
    df_kido: pd.DataFrame,
    df_vial: pd.DataFrame,
    factores: Dict[str, float] = FACTORES_OCUPACION
) -> pd.DataFrame:
    """
    Ejecuta validación completa KIDO vs Dato Vial (Paso 4 KIDO).
    
    Args:
        df_kido: DataFrame con volúmenes KIDO
        df_vial: DataFrame con datos viales
        factores: Factores de ocupación por tipología
        
    Returns:
        DataFrame con validación completa
    """
    print("=" * 60)
    print("PASO 4: Validación KIDO vs Dato Vial")
    print("=" * 60)
    
    # Calcular volumen dato vial en personas
    df_vial = calculate_vol_dv_personas(df_vial, factores=factores)
    print(f"✓ Calculado vol_dv_personas para {len(df_vial)} registros")
    
    # Merge KIDO con vial
    df_merged = df_kido.merge(df_vial, on=['origin_id', 'destination_id'], how='left')
    
    # Calcular factor de validación
    df_merged = calculate_validation_factor(df_merged)
    print(f"✓ Calculado factor_validacion")
    
    # Validar consistencia
    df_merged = validate_consistency(df_merged)
    
    validos = df_merged['es_valido'].sum()
    no_validos = (~df_merged['es_valido']).sum()
    
    print(f"\n✓ Resultados de validación:")
    print(f"  - Válidos (0.95 < Factor < 1.05): {validos}")
    print(f"  - No válidos: {no_validos}")
    
    if len(df_merged) > 0:
        mean_factor = df_merged['factor_validacion'].mean()
        print(f"  - Factor promedio: {mean_factor:.3f}")
    
    return df_merged
