"""
Paso 3 del flujo KIDO: Congruencia Etapa 1 - Vectores de Acceso.

Genera:
- V1: vector con todos los orígenes
- V2: vector con todos los destinos
- Si zona NO está en V1 → Congruencia = 4, id_potencial = 1
"""

import pandas as pd
from typing import Tuple, Set


def generate_access_vectors(df_od: pd.DataFrame, origin_col: str = 'origin_id', dest_col: str = 'destination_id') -> Tuple[Set, Set]:
    """
    Genera vectores V1 (orígenes) y V2 (destinos).
    
    Args:
        df_od: DataFrame con datos OD
        origin_col: Nombre de columna de origen
        dest_col: Nombre de columna de destino
        
    Returns:
        Tupla (V1, V2) con conjuntos de IDs
    """
    V1 = set(df_od[origin_col].unique())
    V2 = set(df_od[dest_col].unique())
    
    return V1, V2


def assign_congruence_by_access(
    df_od: pd.DataFrame,
    V1: Set,
    origin_col: str = 'origin_id'
) -> pd.DataFrame:
    """
    Asigna congruencia = 4 e id_potencial = 1 si zona NO está en V1.
    
    Args:
        df_od: DataFrame con datos OD
        V1: Conjunto de orígenes válidos
        origin_col: Nombre de columna de origen
        
    Returns:
        DataFrame con columnas congruencia_acceso e id_potencial_acceso
    """
    df_od = df_od.copy()
    
    # Verificar si origen está en V1
    df_od['origin_in_v1'] = df_od[origin_col].isin(V1)
    
    # Asignar congruencia y potencial
    df_od['congruencia_acceso'] = df_od['origin_in_v1'].apply(
        lambda x: None if x else 4
    )
    
    df_od['id_potencial'] = df_od['origin_in_v1'].apply(
        lambda x: 2 if x else 1
    )
    
    return df_od


def compute_access_vectors(
    df_od: pd.DataFrame,
    origin_col: str = 'origin_id',
    dest_col: str = 'destination_id'
) -> pd.DataFrame:
    """
    Ejecuta proceso completo de vectores de acceso (Paso 3 KIDO).
    
    Args:
        df_od: DataFrame con datos OD
        origin_col: Nombre de columna de origen
        dest_col: Nombre de columna de destino
        
    Returns:
        DataFrame con congruencia_acceso e id_potencial asignados
    """
    print("=" * 60)
    print("PASO 3: Vectores de Acceso y Congruencia Etapa 1")
    print("=" * 60)
    
    # Generar vectores
    V1, V2 = generate_access_vectors(df_od, origin_col, dest_col)
    
    print(f"✓ Vector V1 (orígenes): {len(V1)} zonas únicas")
    print(f"✓ Vector V2 (destinos): {len(V2)} zonas únicas")
    
    # Asignar congruencia por acceso
    df_od = assign_congruence_by_access(df_od, V1, origin_col)
    
    no_access = (df_od['congruencia_acceso'] == 4).sum()
    print(f"\n✓ Viajes sin acceso (Congruencia=4): {no_access}")
    print(f"✓ id_potencial asignado:")
    print(f"  - id_potencial=1: {(df_od['id_potencial'] == 1).sum()}")
    print(f"  - id_potencial=2: {(df_od['id_potencial'] == 2).sum()}")
    
    return df_od
