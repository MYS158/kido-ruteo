"""Post-proceso de debug para checkpoint 2030.

Este script NO recalcula ruteo (MC/MC2). Usa la traza ya generada por el pipeline:
  debug_output/debug_checkpoint2030_trace.csv

Genera:
- Plot lógico: debug_output/plots/checkpoint2030_logic_flow.png
- Output contractual (7 cols veh_*): data/processed/processed_checkpoint2030.csv

Uso (PowerShell):
  ./.venv/Scripts/python.exe scripts/debug_checkpoint2030_postprocess.py

Opcionales:
  $env:DEBUG_OUTPUT_DIR="debug_output"   (default: debug_output)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from kido_ruteo.utils.visual_debug import DebugVisualizer


def main() -> int:
    base_dir = Path(__file__).resolve().parents[1]
    debug_output_dir = Path(os.environ.get("DEBUG_OUTPUT_DIR", "debug_output")).resolve()
    plots_dir = debug_output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    trace_path = debug_output_dir / "debug_checkpoint2030_trace.csv"
    if not trace_path.exists():
        raise FileNotFoundError(f"No existe la traza esperada: {trace_path}")

    df_trace = pd.read_csv(trace_path)

    # 1) Plot lógico (no requiere Tk)
    viz = DebugVisualizer(output_dir=str(plots_dir))
    viz.plot_logic_flow(df_trace, save_to=str(plots_dir / "checkpoint2030_logic_flow.png"))

    # 2) Output contractual desde traza (mismas columnas contractuales)
    required = [
        "origin_id",
        "destination_id",
        "veh_M",
        "veh_A",
        "veh_B",
        "veh_CU",
        "veh_CAI",
        "veh_CAII",
        "veh_total",
    ]
    missing = [c for c in required if c not in df_trace.columns]
    if missing:
        raise ValueError(f"Traza no contiene columnas necesarias para output contractual: {missing}")

    df_final = df_trace[required].rename(columns={"origin_id": "Origen", "destination_id": "Destino"})

    out_dir = base_dir / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "processed_checkpoint2030.csv"
    df_final.to_csv(out_path, index=False)

    print(f"OK: plot lógico -> {plots_dir / 'checkpoint2030_logic_flow.png'}")
    print(f"OK: output contractual -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
