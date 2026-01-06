import argparse
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kido_ruteo.pipeline import run_pipeline

def main():
    parser = argparse.ArgumentParser(description="Run KIDO pipeline for a single checkpoint query")
    parser.add_argument(
        "--checkpoint-id",
        default="2002",
        help="Checkpoint ID a procesar (ej: 2001). Default: 2002.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Activa debug focalizado (genera debug_checkpoint{ID}_trace.csv en debug_output/).",
    )
    parser.add_argument(
        "--debug-od-limit",
        type=int,
        default=None,
        help="Si --debug, limita a los primeros N pares OD (ej: 200).",
    )
    parser.add_argument(
        "--debug-output-dir",
        default=None,
        help="Si --debug, directorio para debug_output (default: debug_output).",
    )
    parser.add_argument(
        "--debug-max-route-plots",
        type=int,
        default=None,
        help="Si --debug, máximo de plots de rutas a generar (default: 20).",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"

    checkpoint_id = str(args.checkpoint_id).strip()
    od_path = data_dir / "raw" / "queries" / "checkpoint" / f"checkpoint{checkpoint_id}.csv"
    zonification_path = data_dir / "raw" / "zonification" / "zonification.geojson"
    network_path = data_dir / "raw" / "red.geojson"
    capacity_path = data_dir / "raw" / "capacity" / "summary_capacity.csv"
    output_dir = data_dir / "processed"
    osm_bbox = [20.8, 19.9, -99.7, -100.9]

    if args.debug:
        os.environ["DEBUG_CHECKPOINT_ID"] = checkpoint_id
        if args.debug_od_limit is not None:
            os.environ["DEBUG_OD_LIMIT"] = str(int(args.debug_od_limit))
        if args.debug_output_dir:
            os.environ["DEBUG_OUTPUT_DIR"] = str(args.debug_output_dir)
        if args.debug_max_route_plots is not None:
            os.environ["DEBUG_MAX_ROUTE_PLOTS"] = str(int(args.debug_max_route_plots))
    
    print(f"Processing {od_path}...")
    output_file = run_pipeline(
        od_path=str(od_path),
        zonification_path=str(zonification_path),
        network_path=str(network_path),
        capacity_path=str(capacity_path),
        output_dir=str(output_dir),
        osm_bbox=osm_bbox
    )
    print(f"Done: {output_file}")

if __name__ == "__main__":
    main()
