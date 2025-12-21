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
    - No existe scoring informativo ni rescates.
    """

    df = df.copy()

    # Ruta no viable: preferir has_valid_path si existe; si no, usar mc2_distance_m
    if 'has_valid_path' in df.columns:
        invalid_route = ~df['has_valid_path'].fillna(False)
    elif 'mc2_distance_m' in df.columns:
        invalid_route = df['mc2_distance_m'].isna() | (df['mc2_distance_m'] <= 0)
    else:
        invalid_route = pd.Series([True] * len(df), index=df.index)

    if 'sense_code' in df.columns:
        invalid_sense = df['sense_code'].isna() | df['sense_code'].astype('string').eq('0')
    else:
        invalid_sense = pd.Series([True] * len(df), index=df.index)

    invalid_capacity = df['cap_total'].isna() if 'cap_total' in df.columns else pd.Series([True] * len(df), index=df.index)
    zero_capacity = (df['cap_total'] == 0) if 'cap_total' in df.columns else pd.Series([False] * len(df), index=df.index)

    impossible = invalid_route | invalid_sense | invalid_capacity | zero_capacity

    df['congruence_id'] = np.where(impossible, 4, 1)
    df['congruence_label'] = np.where(impossible, 'Impossible', 'Valid')
    return df
