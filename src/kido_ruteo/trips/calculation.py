import pandas as pd
import numpy as np

def calculate_vehicle_trips(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula viajes vehiculares (STRICT MODE) según flow.md.

    Fórmula:
        Veh_cat = (Trips_person × (1 - intrazonal_factor) × FA × Share_cat) / Focup_cat

    Donde:
      - Share_cat = cap_cat / cap_total
      - Categorías: M, A, B, CU, CAI, CAII

        Guard estricto (bloqueante):
            - Solo se calcula si:
                    cap_total notna AND cap_total > 0 AND congruence_id != 4
            - Si congruence_id == 4 (Impossible): veh_* = 0 (explícito), no NaN.
            - Si no pasa el guard por otras razones: no se toca esa fila (veh_* permanecen NaN).

    Notas STRICT:
      - Para share==0 (cap_cat==0), veh_cat = 0 (no depende de Focup).
      - veh_total solo se calcula si todas las categorías quedaron definidas (no NaN).
    """

    df = df.copy()

    # Defaults
    if 'trips_person' not in df.columns:
        df['trips_person'] = 1.0
    if 'intrazonal_factor' not in df.columns:
        # Interpret intrazonal_factor as: 1 => intrazonal (0 trips), 0 => non-intrazonal
        # Default to non-intrazonal to avoid wiping trips when the column is absent.
        df['intrazonal_factor'] = 0.0
    if 'cap_total' not in df.columns:
        df['cap_total'] = np.nan
    if 'congruence_id' not in df.columns:
        df['congruence_id'] = 4
    if 'fa' not in df.columns:
        df['fa'] = np.nan

    categories = ['M', 'A', 'B', 'CU', 'CAI', 'CAII']
    cap_cols = {cat: f'cap_{cat}' for cat in categories}
    focup_cols = {cat: f'focup_{cat}' for cat in categories}
    veh_cols = {cat: f'veh_{cat}' for cat in categories}

    # Ensure expected columns exist
    for cat in categories:
        if cap_cols[cat] not in df.columns:
            df[cap_cols[cat]] = np.nan
        if focup_cols[cat] not in df.columns:
            df[focup_cols[cat]] = np.nan

    # Guard estricto ANTES de calcular
    eligible = df['cap_total'].notna() & (df['cap_total'] > 0) & (df['congruence_id'] != 4)

    # Inicializar TODO como NaN
    for cat in categories:
        df[veh_cols[cat]] = np.nan
    df['veh_total'] = np.nan

    # STRICT: Congruencia imposible => veh_* debe ser 0 (no NaN)
    impossible = df['congruence_id'].eq(4)
    if impossible.any():
        for cat in categories:
            df.loc[impossible, veh_cols[cat]] = 0.0
        df.loc[impossible, 'veh_total'] = 0.0

    if not eligible.any():
        return df

    # Trips efectivos: intrazonal_factor==1 anula (0), ==0 deja pasar (1)
    intrazonal_flag = pd.to_numeric(df['intrazonal_factor'], errors='coerce').fillna(0.0)
    intrazonal_gate = (1.0 - intrazonal_flag).clip(lower=0.0, upper=1.0)
    trips_eff = (pd.to_numeric(df['trips_person'], errors='coerce').fillna(1.0) * intrazonal_gate).astype(float)

    # Computar por categoría solo donde aplica
    for cat in categories:
        cap = df[cap_cols[cat]]
        share = cap / df['cap_total']

        # Si share==0 => veh=0 incluso si focup es NaN
        share_zero = eligible & cap.notna() & cap.eq(0)
        df.loc[share_zero, veh_cols[cat]] = 0.0

        # Si share>0 => requiere FA y Focup válidos
        share_pos = eligible & cap.notna() & cap.gt(0)
        valid_den = df[focup_cols[cat]].notna() & (df[focup_cols[cat]] > 0)
        valid_fa = df['fa'].notna()

        can_compute = share_pos & valid_den & valid_fa
        if can_compute.any():
            df.loc[can_compute, veh_cols[cat]] = (
                trips_eff.loc[can_compute] * df.loc[can_compute, 'fa'] * share.loc[can_compute]
            ) / df.loc[can_compute, focup_cols[cat]]

    # veh_total solo si todas las categorías quedaron definidas
    veh_cols_list = [veh_cols[cat] for cat in categories]
    all_defined = eligible & df[veh_cols_list].notna().all(axis=1)
    df.loc[all_defined, 'veh_total'] = df.loc[all_defined, veh_cols_list].sum(axis=1)
    return df
