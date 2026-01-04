"""Analiza el output contractual del checkpoint 2030 y explica por qué hay ceros.

Este script NO recalcula ruteo. Solo cruza:
- data/processed/processed_checkpoint2030.csv
- debug_output/debug_checkpoint2030_trace.csv

Uso (PowerShell):
  ./.venv/Scripts/python.exe scripts/analyze_processed_checkpoint2030.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def main() -> int:
    base = Path(__file__).resolve().parents[1]
    proc = base / "data" / "processed" / "processed_checkpoint2030.csv"
    trace = base / "debug_output" / "debug_checkpoint2030_trace.csv"

    if not proc.exists():
        raise FileNotFoundError(f"No existe: {proc}")
    if not trace.exists():
        raise FileNotFoundError(f"No existe: {trace}")

    df = pd.read_csv(proc)
    veh_cols = ["veh_M", "veh_A", "veh_B", "veh_CU", "veh_CAI", "veh_CAII"]

    df["sum_cats"] = df[veh_cols].sum(axis=1)
    df["diff"] = df["veh_total"] - df["sum_cats"]

    zeros = df[df["veh_total"] == 0][["Origen", "Destino"]].copy()

    print(f"Rows: {len(df)}")
    print(f"veh_total==0: {len(zeros)}")
    print(f"veh_total>0 : {(df['veh_total'] > 0).sum()}")
    print(f"max |veh_total-sum(veh_*)|: {df['diff'].abs().max():.3e}")

    # Ejemplo que el usuario marcó
    ex = df[(df["Origen"] == 104) & (df["Destino"] == 1025)][["Origen", "Destino", "veh_total"] + veh_cols]
    print("\nEjemplo 104->1025 (no debería ser cero):")
    print(ex.to_string(index=False) if len(ex) else "(no encontrado)")

    dt = pd.read_csv(trace)
    dt["origin_id"] = pd.to_numeric(dt.get("origin_id"), errors="coerce")
    dt["destination_id"] = pd.to_numeric(dt.get("destination_id"), errors="coerce")

    cols = [
        "origin_id",
        "destination_id",
        "trips_person",
        "intrazonal_factor",
        "mc2_distance_m",
        "cap_total",
        "checkpoint_is_directional",
        "sense_code",
        "congruence_id",
        "veh_total",
    ]
    cols = [c for c in cols if c in dt.columns]

    print("\nPrimeros 10 pares en cero y su causa probable (desde traza):")
    for o, d in zeros.head(10).itertuples(index=False, name=None):
        r = dt[(dt["origin_id"] == int(o)) & (dt["destination_id"] == int(d))]
        if r.empty:
            print(f"- {int(o)}->{int(d)}: no aparece en traza (inesperado)")
            continue

        r0 = r.iloc[0]
        intraz = r0.get("intrazonal_factor")
        cong = r0.get("congruence_id")
        mc2 = r0.get("mc2_distance_m")
        cap = r0.get("cap_total")
        directional = r0.get("checkpoint_is_directional")
        sense = r0.get("sense_code")

        reasons: list[str] = []

        if pd.notna(intraz) and float(intraz) >= 0.999:
            reasons.append("intrazonal_factor=1 (intrazonal => 0 viajes)")

        if pd.notna(cong) and int(cong) == 4:
            sub: list[str] = []
            if pd.isna(mc2) or float(mc2) <= 0:
                sub.append("mc2_distance_m inválida")
            if pd.isna(cap) or float(cap) == 0:
                sub.append("cap_total faltante/0")
            if (directional is True) and (pd.isna(sense) or str(sense) == "0"):
                sub.append("sentido inválido (direccional)")
            reasons.append("congruence_id=4" + (" (" + ", ".join(sub) + ")" if sub else ""))

        if not reasons:
            reasons.append("revisar focup/fa/share (menos común)")

        print(f"- {int(o)}->{int(d)}: {'; '.join(reasons)}")
        print(r[cols].head(1).to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
