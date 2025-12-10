"""
Pasos 7-8 del flujo KIDO: Cálculo de Congruencia.

Fórmula: X = [(A-Checkpnt) + (Checkpnt-B)] / (A-B)
         Numerador: distancia de MC2
         Denominador: distancia de MC

Reglas:
- Si viaje pasa por enlace del checkpoint → Congruencia = 4
- Si -10% < X < 10% → Congruencia = 3
- Si no cumple → Congruencia = 4

id_congruencia:
- Si congruencia == 4 → id_congruencia = 0
- Si no → id_congruencia = 1
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
        mc2_path_col: Columna con path de MC2
        
    Returns:
        DataFrame con columna pasa_checkpoint
    """
    df = df.copy()
    
    def passes_checkpoint(path):
        if path is None:
            return False
        return any(node in checkpoint_nodes for node in path)
    
    df['pasa_checkpoint'] = df[mc2_path_col].apply(passes_checkpoint)
    
    # Ajustar congruencia: si pasa por checkpoint, asignar 4
    # (esto ya está implícito en MC2, pero lo hacemos explícito)
    df.loc[df['pasa_checkpoint'], 'congruencia_nivel'] = 4
    
    return df


def calculate_id_congruencia(
    df: pd.DataFrame,
    congruencia_col: str = 'congruencia_nivel'
) -> pd.DataFrame:
    """
    Calcula id_congruencia según regla KIDO.
    
    - Si congruencia == 4 → id_congruencia = 0
    - Si no → id_congruencia = 1
    
    Args:
        df: DataFrame con congruencia_nivel
        congruencia_col: Columna con nivel de congruencia
        
    Returns:
        DataFrame con columna id_congruencia
    """
    df = df.copy()
    
    df['id_congruencia'] = (df[congruencia_col] != 4).astype(int)
    
    return df


def merge_with_access_congruence(
    df: pd.DataFrame,
    congruencia_acceso_col: str = 'congruencia_acceso'
) -> pd.DataFrame:
    """
    Combina congruencia calculada con congruencia por acceso (Paso 3).
    
    Prioridad: Si congruencia_acceso == 4, mantener 4.
    
    Args:
        df: DataFrame con ambas congruencias
        congruencia_acceso_col: Columna de congruencia por acceso
        
    Returns:
        DataFrame con congruencia_final
    """
    df = df.copy()
    
    # Si tiene congruencia_acceso = 4, mantener esa
    df['congruencia_final'] = df['congruencia_nivel']
    
    if congruencia_acceso_col in df.columns:
        mask = df[congruencia_acceso_col] == 4
        df.loc[mask, 'congruencia_final'] = 4
        df.loc[mask, 'id_congruencia'] = 0
    
    return df


def compute_congruence(
    df_od_with_mc_mc2: pd.DataFrame,
    checkpoint_nodes: list = None
) -> pd.DataFrame:
    """
    Ejecuta proceso completo de cálculo de congruencia (Pasos 7-8 KIDO).
    
    Args:
        df_od_with_mc_mc2: DataFrame con MC y MC2 calculadas
        checkpoint_nodes: Lista de nodos checkpoint (opcional)
        
    Returns:
        DataFrame con congruencia_final e id_congruencia
    """
    print("=" * 60)
    print("PASOS 7-8: Cálculo de Congruencia")
    print("=" * 60)
    
    # Calcular X
    df = calculate_congruence_x(df_od_with_mc_mc2)
    print(f"✓ Calculado congruence_x para {df['congruence_x'].notna().sum()} viajes")
    
    # Asignar nivel de congruencia
    df = assign_congruence_nivel(df)
    
    # Verificar paso por checkpoint (si se proporciona lista)
    if checkpoint_nodes:
        df = check_checkpoint_passage(df, checkpoint_nodes)
    
    # Calcular id_congruencia
    df = calculate_id_congruencia(df)
    
    # Combinar con congruencia por acceso
    df = merge_with_access_congruence(df)
    
    # Estadísticas
    cong_3 = (df['congruencia_final'] == 3).sum()
    cong_4 = (df['congruencia_final'] == 4).sum()
    id_cong_0 = (df['id_congruencia'] == 0).sum()
    id_cong_1 = (df['id_congruencia'] == 1).sum()
    
    print(f"\n✓ Resultados de congruencia:")
    print(f"  - Congruencia nivel 3 (-10% < X < 10%): {cong_3}")
    print(f"  - Congruencia nivel 4 (fuera de rango): {cong_4}")
    print(f"  - id_congruencia = 0: {id_cong_0}")
    print(f"  - id_congruencia = 1: {id_cong_1}")
    
    if 'congruence_x' in df.columns and df['congruence_x'].notna().any():
        mean_x = df['congruence_x'].mean()
        print(f"  - X promedio: {mean_x:.3f}")
    
    return df
