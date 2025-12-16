"""
Módulo de chequeos de validación (E1, E2).
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
    Calcula factor de validación (E1/E2).
    
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
        (df[factor_col] > lower_threshold) & 
        (df[factor_col] < upper_threshold)
    )
    
    return df
