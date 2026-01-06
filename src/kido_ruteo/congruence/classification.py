import pandas as pd
import numpy as np

def classify_congruence(df: pd.DataFrame) -> pd.DataFrame:
    """
    STRICT MODE (flow.md):
        - congruence_id = 4 (Impossible) si ocurre cualquiera:
      - MC2 inexistente / ruta no viable
      - sense_code inválido (NaN)
      - Capacidad inexistente (cap_total NaN)
      - cap_total == 0

        Regla adicional (validación de distancias):
        - Si mc2_distance_m está dentro de ±10% de mc_distance_m => congruence_id = 3
        - Si está fuera de esa banda => congruence_id = 4
    """

    df = df.copy()

    # Ruta no viable: preferir has_valid_path si existe; si no, usar mc2_distance_m
    if 'has_valid_path' in df.columns:
        invalid_route = ~df['has_valid_path'].fillna(False)
    elif 'mc2_distance_m' in df.columns:
        invalid_route = df['mc2_distance_m'].isna() | (df['mc2_distance_m'] <= 0)
    else:
        invalid_route = pd.Series([True] * len(df), index=df.index)

    # Sentido: requerido SOLO si el checkpoint es direccional.
    # Para checkpoints agregados, sense_code='0' es válido (FLOW.md).
    if 'checkpoint_is_directional' in df.columns:
        directional = df['checkpoint_is_directional'].astype('boolean').fillna(True)
    else:
        directional = pd.Series([True] * len(df), index=df.index)

    if 'sense_code' in df.columns:
        sense_is_missing = df['sense_code'].isna()
        sense_is_zero = df['sense_code'].astype('string').eq('0')
        invalid_sense = directional & (sense_is_missing | sense_is_zero)
    else:
        invalid_sense = directional

    invalid_capacity = df['cap_total'].isna() if 'cap_total' in df.columns else pd.Series([True] * len(df), index=df.index)
    zero_capacity = (df['cap_total'] == 0) if 'cap_total' in df.columns else pd.Series([False] * len(df), index=df.index)

    impossible = invalid_route | invalid_sense | invalid_capacity | zero_capacity

    # Regla: si la ruta MC2 pasa por el enlace del checkpoint => congruencia 1
    if 'mc2_passes_checkpoint_link' in df.columns:
        passes_cp = df['mc2_passes_checkpoint_link'].astype('boolean').fillna(False)
    else:
        passes_cp = pd.Series([False] * len(df), index=df.index)

    # Validación de distancias (±10%): solo aplica si NO pasa por el checkpoint
    if 'mc_distance_m' in df.columns and 'mc2_distance_m' in df.columns:
        mc = pd.to_numeric(df['mc_distance_m'], errors='coerce')
        mc2 = pd.to_numeric(df['mc2_distance_m'], errors='coerce')
        valid_mc = mc.notna() & (mc > 0)
        valid_mc2 = mc2.notna() & (mc2 > 0)
        ratio_ok = (mc2 >= (0.9 * mc)) & (mc2 <= (1.1 * mc))
        dist_congruent = valid_mc & valid_mc2 & ratio_ok
        missing_distances = mc.isna() | mc2.isna() | (mc <= 0) | (mc2 <= 0)
    else:
        dist_congruent = pd.Series([False] * len(df), index=df.index)
        missing_distances = pd.Series([True] * len(df), index=df.index)

    is_valid_base = ~impossible
    id1 = is_valid_base & passes_cp
    id3 = is_valid_base & (~passes_cp) & dist_congruent

    df['congruence_id'] = np.select(
        [id1, id3],
        [1, 3],
        default=4,
    )

    # Motivo / etiqueta explicativa para debug
    reasons = np.select(
        [
            df['congruence_id'].eq(1),
            df['congruence_id'].eq(3),
            invalid_route,
            invalid_sense,
            invalid_capacity,
            zero_capacity,
            missing_distances,
        ],
        [
            'passes_checkpoint_link',
            'mc2_within_10pct_of_mc',
            'invalid_route',
            'invalid_sense',
            'missing_capacity',
            'zero_capacity',
            'missing_distances',
        ],
        default='mc2_outside_10pct_of_mc',
    )

    df['congruence_reason'] = pd.Series(reasons, index=df.index, dtype='string')
    df['congruence_label'] = np.select(
        [df['congruence_id'].eq(1), df['congruence_id'].eq(3)],
        ['PassesCheckpoint', 'Within10pct'],
        default='Impossible',
    )
    return df
