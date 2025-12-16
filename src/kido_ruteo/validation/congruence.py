"""
Módulo de cálculo de congruencia.
"""

import pandas as pd
import numpy as np

def calculate_congruence_x(
    df: pd.DataFrame,
    mc_dist_col: str = 'mc_distance',
    mc2_dist_col: str = 'mc2_distance'
) -> pd.DataFrame:
    """
    Calcula X = (distancia_MC2) / (distancia_MC).
    
    Numerador: MC2 (paso por checkpoint)
    Denominador: MC (shortest path directo)
    
    Args:
        df: DataFrame con MC y MC2
        mc_dist_col: Columna con distancia MC
        mc2_dist_col: Columna con distancia MC2
        
    Returns:
        DataFrame con columna congruence_x
    """
    df = df.copy()
    
    df['congruence_x'] = df[mc2_dist_col] / df[mc_dist_col]
    
    # Manejar valores inválidos
    df['congruence_x'] = df['congruence_x'].replace([np.inf, -np.inf], np.nan)
    
    return df

def assign_congruence_nivel(
    df: pd.DataFrame,
    x_col: str = 'congruence_x',
    lower_threshold: float = 0.90,  # -10%
    upper_threshold: float = 1.10   # +10%
) -> pd.DataFrame:
    """
    Asigna nivel de congruencia según reglas KIDO.
    
    Reglas:
    - Si -10% < X < 10% → Congruencia = 3
    - Si no cumple → Congruencia = 4
    - Si X es None (no hay ruta) → Congruencia = 4
    
    Args:
        df: DataFrame con congruence_x
        x_col: Columna con X
        lower_threshold: Umbral inferior (0.90 = -10%)
        upper_threshold: Umbral superior (1.10 = +10%)
        
    Returns:
        DataFrame con columna congruencia_nivel
    """
    df = df.copy()
    
    def determine_congruence(x):
        if pd.isna(x):
            return 4
        elif lower_threshold <= x <= upper_threshold:
            return 3
        else:
            return 4
    
    df['congruencia_nivel'] = df[x_col].apply(determine_congruence)
    
    return df

def check_checkpoint_passage(
    df: pd.DataFrame,
    checkpoint_nodes: list,
    mc2_path_col: str = 'mc2_path'
) -> pd.DataFrame:
    """
    Verifica si la ruta pasa por enlace del checkpoint.
    
    Si pasa por checkpoint → Congruencia = 4
    
    Args:
        df: DataFrame con rutas MC2
        checkpoint_nodes: Lista de nodos checkpoint
        mc2_path_col: Columna con ruta MC2
        
    Returns:
        DataFrame con flag de paso por checkpoint
    """
    # Implementación pendiente o simplificada
    # Aquí se debería chequear si la ruta contiene los nodos del checkpoint
    # Por ahora retornamos el DF original
    return df
