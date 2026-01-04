r"""Ejecuta el pipeline para todas las queries tipo checkpoint.

- Recorre data/raw/queries/checkpoint/checkpoint*.csv
- Ejecuta kido_ruteo.pipeline.run_pipeline en modo NORMAL (STRICT contractual)
- Escribe processed_checkpointXXXX.csv en data/processed/

Uso (PowerShell):
  ./.venv/Scripts/python.exe scripts/run_all_checkpoints.py

Opcionales:
  - Procesar solo algunos (regex):
      ./.venv/Scripts/python.exe scripts/run_all_checkpoints.py --pattern "checkpoint2030\.csv$"
  - Dry-run (solo lista lo que correría):
      ./.venv/Scripts/python.exe scripts/run_all_checkpoints.py --dry-run

Nota importante:
  Este runner fuerza a desactivar el debug focalizado (DEBUG_CHECKPOINT_ID)
  para evitar que un entorno "contaminado" (p.ej. DEBUG_CHECKPOINT_ID=2030)
  filtre/altere el procesamiento batch.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


def _unset_debug_env() -> None:
    # Evita activar el modo debug focalizado por accidente.
    for k in [
        "DEBUG_CHECKPOINT_ID",
        "DEBUG_OUTPUT_DIR",
        "DEBUG_OD_LIMIT",
        "DEBUG_MAX_ROUTE_PLOTS",
        "KIDO_DEBUG_N_WORKERS",
        "KIDO_DEBUG_CHUNK_SIZE",
    ]:
        os.environ.pop(k, None)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pattern",
        default=r"checkpoint\d+\.csv$",
        help="Regex (sobre el nombre de archivo) para filtrar checkpoints a correr.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo lista archivos a procesar, no ejecuta el pipeline.",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parents[1]

    od_dir = base_dir / "data" / "raw" / "queries" / "checkpoint"
    zonification_path = base_dir / "data" / "raw" / "zonification" / "zonification.geojson"
    network_path = base_dir / "data" / "raw" / "red.geojson"
    capacity_path = base_dir / "data" / "raw" / "capacity" / "summary_capacity.csv"
    output_dir = base_dir / "data" / "processed"

    for p in [od_dir, zonification_path, network_path, capacity_path]:
        if not p.exists():
            raise FileNotFoundError(f"No existe insumo requerido: {p}")

    rx = re.compile(args.pattern)
    od_files = sorted([p for p in od_dir.iterdir() if p.is_file() and rx.search(p.name)])

    if not od_files:
        print(f"No se encontraron archivos que matcheen --pattern={args.pattern!r} en {od_dir}")
        return 2

    print(f"Encontrados {len(od_files)} checkpoint CSVs")
    for p in od_files:
        print(f"- {p.name}")

    if args.dry_run:
        print("\nDRY-RUN: no se ejecutó nada.")
        return 0

    # Import tardío para que el script pueda listar sin depender de imports
    import sys

    sys.path.insert(0, str(base_dir / "src"))
    from kido_ruteo.pipeline import run_pipeline

    _unset_debug_env()

    output_dir.mkdir(parents=True, exist_ok=True)

    ok = 0
    failed: list[tuple[str, str]] = []

    for i, od_path in enumerate(od_files, start=1):
        print(f"\n[{i}/{len(od_files)}] Ejecutando: {od_path.name}")
        try:
            out = run_pipeline(
                od_path=str(od_path),
                zonification_path=str(zonification_path),
                network_path=str(network_path),
                capacity_path=str(capacity_path),
                output_dir=str(output_dir),
                osm_bbox=None,
            )
            ok += 1
            print(f"OK -> {out}")
        except Exception as e:
            failed.append((od_path.name, repr(e)))
            print(f"FAIL -> {od_path.name}: {e}")

    print("\nResumen:")
    print(f"- OK: {ok}")
    print(f"- FAIL: {len(failed)}")
    if failed:
        print("\nFallos:")
        for name, err in failed:
            print(f"- {name}: {err}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
