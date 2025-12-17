import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kido_ruteo.pipeline import run_pipeline

def main():
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    
    od_path = data_dir / "raw" / "queries" / "checkpoint" / "checkpoint2002.csv"
    zonification_path = data_dir / "raw" / "zonification" / "zonification.geojson"
    network_path = data_dir / "raw" / "red.geojson"
    capacity_path = data_dir / "raw" / "capacity" / "summary_capacity.csv"
    output_dir = data_dir / "processed"
    osm_bbox = [20.8, 19.9, -99.7, -100.9]
    
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
