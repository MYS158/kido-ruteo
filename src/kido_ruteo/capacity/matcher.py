import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def match_capacity_to_od(df_od: pd.DataFrame, df_capacity: pd.DataFrame) -> pd.DataFrame:
    """
    Cruza datos de OD/Ruteo con datos de Capacidad basados en Checkpoint y Sentido.
    
        STRICT MODE (FLOW.md):
        - Se clasifica cada checkpoint como:
                - Direccional: existe al menos un registro con Sentido != '0'
                - Agregado: TODOS los registros tienen Sentido == '0'
        - Direccional: Match EXACTO (checkpoint_id, sense_code) con (Checkpoint, Sentido)
        - Agregado: NO se usa sentido geométrico; se fija conceptualmente sense_code='0' y
            se hace match SOLO por checkpoint_id usando la fila Sentido=='0'
        - NO hay "fallback" de direccional → '0'.
        - NO agregación en este paso (la agregación, si existe, ocurre en loader)
        - Si no hay match según reglas → todas las capacidades/factores quedan NaN
    
    Args:
        df_od: DataFrame con 'checkpoint_id' y 'sense_code' (derivado geométricamente)
        df_capacity: DataFrame con 'Checkpoint', 'Sentido', y capacidades por categoría
        
    Returns:
        DataFrame con columnas:
        - cap_M, cap_A, cap_B, cap_CU, cap_CAI, cap_CAII, cap_total
        - fa
        - focup_M, focup_A, focup_B, focup_CU, focup_CAI, focup_CAII
        Si no hay match: todo queda NaN
    """
    # Si no hay checkpoint_id, no podemos cruzar capacidad
    if 'checkpoint_id' not in df_od.columns:
        df_od = df_od.copy()
        for col in [
            'cap_M', 'cap_A', 'cap_B', 'cap_CU', 'cap_CAI', 'cap_CAII', 'cap_total',
            'fa',
            'focup_M', 'focup_A', 'focup_B', 'focup_CU', 'focup_CAI', 'focup_CAII',
        ]:
            df_od[col] = np.nan
        return df_od

    df_od = df_od.copy()
    df_capacity = df_capacity.copy()

    # Llaves y tipos
    # STRICT MODE: NO convertir NaN a strings; NaN debe permanecer NaN
    df_od['checkpoint_id'] = df_od['checkpoint_id'].astype('string')
    if 'sense_code' not in df_od.columns:
        df_od['sense_code'] = pd.Series([pd.NA] * len(df_od), dtype='string')
    else:
        df_od['sense_code'] = df_od['sense_code'].astype('string')

    df_capacity['Checkpoint'] = df_capacity['Checkpoint'].astype('string')
    df_capacity['Sentido'] = df_capacity['Sentido'].astype('string')
    
    # Seleccionar solo columnas necesarias de capacity (ya agregada)
    capacity_cols = [
        'Checkpoint', 'Sentido',
        'FA',
        'M', 'A', 'B', 'CU', 'CAI', 'CAII',
        'Focup_M', 'Focup_A', 'Focup_B', 'Focup_CU', 'Focup_CAI', 'Focup_CAII',
    ]
    df_capacity_slim = df_capacity[capacity_cols].copy()

    # Clasificación checkpoint (direccional vs agregado)
    # Direccional si existe al menos un Sentido != '0'
    dir_flags = (
        df_capacity_slim
        .assign(_is_dir=df_capacity_slim['Sentido'].notna() & ~df_capacity_slim['Sentido'].eq('0'))
        .groupby('Checkpoint', dropna=False)['_is_dir']
        .any()
    )

    # STRICT: checkpoints mixtos (tienen Sentido='0' y también sentidos explícitos)
    # Se tratan como direccionales (por dir_flags), pero se documenta con warning.
    mixed_flags = (
        df_capacity_slim
        .assign(
            _has_zero=df_capacity_slim['Sentido'].eq('0'),
            _has_nonzero=df_capacity_slim['Sentido'].notna() & ~df_capacity_slim['Sentido'].eq('0'),
        )
        .groupby('Checkpoint', dropna=False)[['_has_zero', '_has_nonzero']]
        .any()
    )
    mixed_checkpoints = mixed_flags.index[mixed_flags['_has_zero'] & mixed_flags['_has_nonzero']].tolist()
    if mixed_checkpoints:
        logger.warning(
            "STRICT MODE: Detectados checkpoints mixtos en capacity (Sentido '0' y != '0'). "
            "Se tratarán como DIRECCIONALES (sin fallback a '0'). Checkpoints: %s",
            mixed_checkpoints,
        )
    df_od['checkpoint_is_directional'] = df_od['checkpoint_id'].map(dir_flags).astype('boolean')

    # Desconocidos (checkpoint no presente en capacity) => mantener strict:
    # tratarlos como direccionales para evitar cualquier "rescate" a Sentido 0.
    checkpoint_is_directional = df_od['checkpoint_is_directional'].fillna(True)

    # Pre-crear columnas destino con NaN (para filas sin match)
    out_cols = [
        'cap_M', 'cap_A', 'cap_B', 'cap_CU', 'cap_CAI', 'cap_CAII', 'cap_total',
        'fa',
        'focup_M', 'focup_A', 'focup_B', 'focup_CU', 'focup_CAI', 'focup_CAII',
    ]
    for col in out_cols:
        if col not in df_od.columns:
            df_od[col] = np.nan

    # --- 1) Direccional: merge exacto por (checkpoint_id, sense_code) ---
    dir_mask = checkpoint_is_directional
    if dir_mask.any():
        # STRICT: en direccional (incluyendo mixtos), Sentido='0' NO participa en el match.
        # Esto evita que sense_code='0' haga match accidentalmente.
        df_capacity_dir = df_capacity_slim[~df_capacity_slim['Sentido'].eq('0')].copy()

        merged_dir = pd.merge(
            df_od.loc[dir_mask].drop(columns=out_cols, errors='ignore'),
            df_capacity_dir,
            left_on=['checkpoint_id', 'sense_code'],
            right_on=['Checkpoint', 'Sentido'],
            how='left',
            suffixes=('', '_cap'),
            validate='many_to_one'
        )

        rename_map = {
            'FA': 'fa',
            'M': 'cap_M',
            'A': 'cap_A',
            'B': 'cap_B',
            'CU': 'cap_CU',
            'CAI': 'cap_CAI',
            'CAII': 'cap_CAII',
            'Focup_M': 'focup_M',
            'Focup_A': 'focup_A',
            'Focup_B': 'focup_B',
            'Focup_CU': 'focup_CU',
            'Focup_CAI': 'focup_CAI',
            'Focup_CAII': 'focup_CAII',
        }
        merged_dir = merged_dir.rename(columns=rename_map)
        cap_cols = ['cap_M', 'cap_A', 'cap_B', 'cap_CU', 'cap_CAI', 'cap_CAII']
        merged_dir['cap_total'] = merged_dir[cap_cols].sum(axis=1, min_count=len(cap_cols))

        # Limpiar columnas auxiliares
        merged_dir = merged_dir.drop(columns=[c for c in ['Checkpoint', 'Sentido'] if c in merged_dir.columns])

        # Escribir de vuelta (alineado por índice)
        df_od.loc[dir_mask, out_cols] = merged_dir[out_cols].to_numpy()

    # --- 2) Agregado: merge SOLO por checkpoint, usando Sentido == '0' ---
    agg_mask = ~checkpoint_is_directional
    if agg_mask.any():
        # STRICT MODE: En checkpoints agregados, el sentido geométrico NO se usa.
        # Se fija explícitamente a '0' para dejarlo claro en trazas/análisis.
        df_od.loc[agg_mask, 'sense_code'] = '0'

        df_capacity_zero = df_capacity_slim[df_capacity_slim['Sentido'].eq('0')].copy()
        merged_agg = pd.merge(
            df_od.loc[agg_mask].drop(columns=out_cols, errors='ignore'),
            df_capacity_zero,
            left_on='checkpoint_id',
            right_on='Checkpoint',
            how='left',
            suffixes=('', '_cap'),
            validate='many_to_one'
        )

        rename_map = {
            'FA': 'fa',
            'M': 'cap_M',
            'A': 'cap_A',
            'B': 'cap_B',
            'CU': 'cap_CU',
            'CAI': 'cap_CAI',
            'CAII': 'cap_CAII',
            'Focup_M': 'focup_M',
            'Focup_A': 'focup_A',
            'Focup_B': 'focup_B',
            'Focup_CU': 'focup_CU',
            'Focup_CAI': 'focup_CAI',
            'Focup_CAII': 'focup_CAII',
        }
        merged_agg = merged_agg.rename(columns=rename_map)
        cap_cols = ['cap_M', 'cap_A', 'cap_B', 'cap_CU', 'cap_CAI', 'cap_CAII']
        merged_agg['cap_total'] = merged_agg[cap_cols].sum(axis=1, min_count=len(cap_cols))

        merged_agg = merged_agg.drop(columns=[c for c in ['Checkpoint', 'Sentido'] if c in merged_agg.columns])
        df_od.loc[agg_mask, out_cols] = merged_agg[out_cols].to_numpy()

    return df_od
