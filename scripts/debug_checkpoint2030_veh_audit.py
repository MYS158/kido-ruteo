r"""Audita anomalías de veh_* para el checkpoint 2030.

Lee el CSV de trazas de debug existente (producido por el pipeline de debug del
checkpoint 2030) y resume casos donde los viajes son NO intrazonales pero
veh_total es 0 o NaN.

Este script NO recalcula ruteo.

Uso (PowerShell):
        .venv\Scripts\python.exe scripts\debug_checkpoint2030_veh_audit.py

Salidas:
    - debug_output/veh_audit_checkpoint2030_flagged.csv
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


def _first_existing(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def main() -> None:
    trace_path = Path("debug_output") / "debug_checkpoint2030_trace.csv"
    if not trace_path.exists():
        raise SystemExit(f"Traza no encontrada: {trace_path}")

    df = pd.read_csv(trace_path)

    veh_total_col = _first_existing(df, ["veh_total", "veh_tot", "veh"]) or next(
        (c for c in df.columns if c.lower().startswith("veh")),
        None,
    )
    if veh_total_col is None:
        raise SystemExit("No veh_* column found in trace")

    intrazonal_factor_col = _first_existing(df, ["intrazonal_factor", "intrazonal", "intra_zonal", "intrazonal"])

    veh = pd.to_numeric(df[veh_total_col], errors="coerce")
    veh_zero_or_nan = veh.isna() | (veh == 0)

    if intrazonal_factor_col == "intrazonal_factor":
        # In this codebase: 1 => intrazonal (0 trips), 0 => non-intrazonal
        non_intraz = pd.to_numeric(df[intrazonal_factor_col], errors="coerce").fillna(0) == 0
    elif intrazonal_factor_col is not None:
        # Generic interpretation: intrazonal==1 means intrazonal
        non_intraz = pd.to_numeric(df[intrazonal_factor_col], errors="coerce").fillna(0) == 0
    else:
        non_intraz = None

    if non_intraz is None:
        flagged = df[veh_zero_or_nan].copy()
        print(f"veh_total 0/NaN (no intrazonal indicator found): {len(flagged)}")
    else:
        flagged = df[non_intraz & veh_zero_or_nan].copy()
        print(f"non-intrazonal & veh_total 0/NaN: {len(flagged)}")

    # Add common guard flags if columns exist
    def _flag_leq0(col: str, out: str) -> None:
        if col in flagged.columns:
            s = pd.to_numeric(flagged[col], errors="coerce")
            flagged[out] = s.isna() | (s <= 0)

    _flag_leq0("cap_total", "_cap_missing_or_zero")
    _flag_leq0("fa", "_fa_missing_or_zero")
    _flag_leq0("focup", "_focup_missing_or_zero")

    if "congruence_id" in flagged.columns:
        cong = pd.to_numeric(flagged["congruence_id"], errors="coerce")
        flagged["_cong_is_4"] = cong == 4

    if "share" in flagged.columns:
        sh = pd.to_numeric(flagged["share"], errors="coerce").fillna(0)
        flagged["_share_zero"] = sh == 0

    out_csv = Path("debug_output") / "veh_audit_checkpoint2030_flagged.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    flagged.to_csv(out_csv, index=False)
    print(f"Saved: {out_csv}")

    # Console summary
    flag_cols = [c for c in flagged.columns if c.startswith("_")]
    if flag_cols:
        print("\nTop flag combinations:")
        print(flagged[flag_cols].value_counts().head(10).to_string())

    show_cols = [c for c in ["origin_id", "destination_id", "origin_zone", "destination_zone", intrazonal_factor_col, veh_total_col] if c and c in flagged.columns]
    for c in ["mc_distance_m", "mc2_distance_m", "sense_code", "cap_total", "congruence_id", "fa", "focup", "share"]:
        if c in flagged.columns and c not in show_cols:
            show_cols.append(c)

    if len(flagged):
        print("\nExamples (first 15):")
        print(flagged[show_cols].head(15).to_string(index=False))


if __name__ == "__main__":
    main()
