import os
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point


def test_infer_bbox_from_zonification_adds_padding(tmp_path: Path):
    # Minimal geo layer in EPSG:4326
    gdf = gpd.GeoDataFrame(
        {"ID": [1, 2]},
        geometry=[Point(-100.0, 20.0), Point(-99.0, 21.0)],
        crs="EPSG:4326",
    )
    zon_path = tmp_path / "zonification.geojson"
    gdf.to_file(zon_path, driver="GeoJSON")

    from kido_ruteo.routing.graph_loader import infer_bbox_from_zonification

    north, south, east, west = infer_bbox_from_zonification(str(zon_path), padding_ratio=0.1, min_padding_deg=0.01)

    # Original bounds: lon [-100, -99], lat [20, 21]
    assert north > 21.0
    assert south < 20.0
    assert east > -99.0
    assert west < -100.0


def test_infer_bbox_from_queries_and_zonification_unions_and_pads(tmp_path: Path):
    # Create a "zonification" layer with three zones spread out
    zones = gpd.GeoDataFrame(
        {"ID": [1, 2, 3]},
        geometry=[Point(-100.0, 20.0), Point(-99.5, 20.5), Point(-99.0, 21.0)],
        crs="EPSG:4326",
    )
    zon_path = tmp_path / "zonification.geojson"
    zones.to_file(zon_path, driver="GeoJSON")

    # Queries only reference a subset of zones (1 and 2)
    q1 = tmp_path / "checkpoint2001.csv"
    pd.DataFrame({"origin": [1], "destination": [2], "total_trips": [10]}).to_csv(q1, index=False)
    q2 = tmp_path / "checkpoint2002.csv"
    pd.DataFrame({"origin_id": [2], "destination_id": [1], "total_trips": [10]}).to_csv(q2, index=False)

    from kido_ruteo.routing.graph_loader import infer_bbox_from_queries_and_zonification

    north, south, east, west = infer_bbox_from_queries_and_zonification(
        [str(q1), str(q2)],
        str(zon_path),
        padding_ratio=0.1,
        min_padding_deg=0.01,
        ensure_covers_zonification=True,
    )

    # With ensure_covers_zonification=True, bbox must cover the full zonification extent
    # Zon bounds: lon [-100, -99], lat [20, 21]
    assert north > 21.0
    assert south < 20.0
    assert east > -99.0
    assert west < -100.0


def test_ensure_graph_downloads_when_missing(monkeypatch, tmp_path: Path):
    from kido_ruteo.routing import graph_loader

    network_path = tmp_path / "red.geojson"
    assert not network_path.exists()

    calls = {"download": 0, "save": 0, "load": 0}

    def fake_download_graph_from_bbox(*, north, south, east, west, network_type="drive"):
        calls["download"] += 1
        assert network_type == "drive"
        assert north == 1.0 and south == 0.0 and east == 2.0 and west == -1.0
        return object()

    def fake_save_graph_to_geojson(G, output_path: str):
        calls["save"] += 1
        # Create a placeholder file so 'exists' could be true if needed
        Path(output_path).write_text("{}", encoding="utf-8")

    def fake_load_graph_from_geojson(path: str):
        calls["load"] += 1
        assert os.path.exists(path)
        return {"graph": "ok"}

    monkeypatch.setattr(graph_loader, "download_graph_from_bbox", fake_download_graph_from_bbox)
    monkeypatch.setattr(graph_loader, "save_graph_to_geojson", fake_save_graph_to_geojson)
    monkeypatch.setattr(graph_loader, "load_graph_from_geojson", fake_load_graph_from_geojson)

    G = graph_loader.ensure_graph_from_geojson_or_osm(
        geojson_path=str(network_path),
        zonification_path=None,
        osm_bbox=[1.0, 0.0, 2.0, -1.0],
        network_type="drive",
    )

    assert G == {"graph": "ok"}
    assert calls["download"] == 1
    assert calls["save"] == 1
    assert calls["load"] == 1
