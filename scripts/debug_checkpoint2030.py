"""Debug focalizado para checkpoint 2030.

Ejecuta el pipeline solo para checkpoint2030.csv y genera artefactos de auditoría:
- debug_output/debug_checkpoint2030_trace.csv (NO contractual)
- debug_output/plots/checkpoint2030_logic_flow.png
- debug_output/plots/checkpoint2030_route_{origin}_{destination}.png
- debug_output/plots/checkpoint2030_sense_{origin}_{destination}.png

Uso (PowerShell):
  $env:DEBUG_CHECKPOINT_ID="2030"; python scripts/debug_checkpoint2030.py

Opcionales:
  $env:DEBUG_OUTPUT_DIR="debug_output"   (default: debug_output)
  $env:DEBUG_MAX_ROUTE_PLOTS="20"        (default: 20)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure src/ is importable when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kido_ruteo.pipeline import run_pipeline


def main() -> int:
  # Forzar debug focalizado
    os.environ.setdefault("DEBUG_CHECKPOINT_ID", "2030")
  # Usar múltiples núcleos para ruteo en DEBUG 2030
    os.environ.setdefault("KIDO_DEBUG_N_WORKERS", "12")

    base_dir = Path(__file__).resolve().parents[1]
    data_dir = base_dir / "data"

    od_path = data_dir / "raw" / "queries" / "checkpoint" / "checkpoint2030.csv"
    zonification_path = data_dir / "raw" / "zonification" / "zonification.geojson"
    network_path = data_dir / "raw" / "red.geojson"
    capacity_path = data_dir / "raw" / "capacity" / "summary_capacity.csv"
    output_dir = data_dir / "processed"

    # Same bbox used elsewhere (only applies if OSM download is needed)
    osm_bbox = [20.8, 19.9, -99.7, -100.9]

    print(f"Procesando (DEBUG 2030): {od_path}")
    output_file = run_pipeline(
        od_path=str(od_path),
        zonification_path=str(zonification_path),
        network_path=str(network_path),
        capacity_path=str(capacity_path),
        output_dir=str(output_dir),
        osm_bbox=osm_bbox,
    )
    print(f"Listo (salida contractual): {output_file}")
    print(f"Artefactos de debug en: {Path(os.environ.get('DEBUG_OUTPUT_DIR', 'debug_output')).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
