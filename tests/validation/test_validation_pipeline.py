"""Tests para validation_pipeline (Fase D)."""
from __future__ import annotations

import pandas as pd

from kido_ruteo.validation import run_validation_pipeline


def _build_data():
    routing = pd.DataFrame(
        [
            # Perfecto → nivel 1
            {
                "origin_node_id": 1,
                "destination_node_id": 2,
                "mc_length_m": 1000.0,
                "mc2_length_m": 1000.0,
                "mc_time_min": 10.0,
                "mc2_time_min": 10.0,
                "checkpoint_passed": True,
            },
            # Media → nivel 2
            {
                "origin_node_id": 2,
                "destination_node_id": 3,
                "mc_length_m": 1000.0,
                "mc2_length_m": 1500.0,  # ratio 1.5 (map matching bajo)
                "mc_time_min": 10.0,
                "mc2_time_min": 12.0,  # 20% más
                "checkpoint_passed": True,
            },
            # Baja → nivel 3
            {
                "origin_node_id": 3,
                "destination_node_id": 4,
                "mc_length_m": 1000.0,
                "mc2_length_m": 1350.0,  # ratio 1.35
                "mc_time_min": 10.0,
                "mc2_time_min": 13.5,  # 35% más
                "checkpoint_passed": False,
            },
            # Imposible → nivel 4
            {
                "origin_node_id": 4,
                "destination_node_id": 5,
                "mc_length_m": 800.0,
                "mc2_length_m": 2000.0,
                "mc_time_min": 8.0,
                "mc2_time_min": 20.0,
                "checkpoint_passed": False,
            },
        ]
    )

    processed = pd.DataFrame(
        [
            {"origin_node_id": 1, "destination_node_id": 2, "cardinalidad_ok": True, "flags": None},
            {"origin_node_id": 2, "destination_node_id": 3, "cardinalidad_ok": True, "flags": None},
            {"origin_node_id": 3, "destination_node_id": 4, "cardinalidad_ok": True, "flags": "warning"},
            {"origin_node_id": 4, "destination_node_id": 5, "cardinalidad_ok": False, "flags": "critical"},
        ]
    )

    aforo = pd.DataFrame(
        [
            {"origin_node_id": 1, "destination_node_id": 2, "aforo_diff_pct": 0.02},
            {"origin_node_id": 2, "destination_node_id": 3, "aforo_diff_pct": 0.20},
            {"origin_node_id": 3, "destination_node_id": 4, "aforo_diff_pct": 0.25},
            {"origin_node_id": 4, "destination_node_id": 5, "aforo_diff_pct": 0.50},
        ]
    )

    return routing, processed, aforo


def test_validation_pipeline_levels(tmp_path):
    routing, processed, aforo = _build_data()

    output_dir = tmp_path / "validation_outputs"
    result = run_validation_pipeline(routing, processed, aforo, output_dir=output_dir)

    # Verificar niveles esperados
    levels = result.set_index(["origin_node_id", "destination_node_id"])["congruencia_nivel"]
    assert levels.loc[(1, 2)] == 1
    assert levels.loc[(2, 3)] == 2
    assert levels.loc[(3, 4)] == 3
    assert levels.loc[(4, 5)] == 4

    # Verificar que se guardó CSV
    assert (output_dir / "validation_results.csv").exists()


def test_validation_pipeline_handles_zero_and_missing():
    routing = pd.DataFrame(
        [
            {
                "origin_node_id": 10,
                "destination_node_id": 10,
                "mc_length_m": 0.0,
                "mc2_length_m": 0.0,
                "mc_time_min": 0.0,
                "mc2_time_min": 0.0,
                "checkpoint_passed": None,
            },
            {
                "origin_node_id": 11,
                "destination_node_id": 12,
                "mc_length_m": 500.0,
                "mc2_length_m": 500.0,
                "mc_time_min": 8.0,
                "mc2_time_min": 8.0,
                # checkpoint_passed no presente → None
            },
        ]
    )

    processed = pd.DataFrame(
        [
            {"origin_node_id": 10, "destination_node_id": 10, "cardinalidad_ok": True, "flags": None},
            {"origin_node_id": 11, "destination_node_id": 12, "cardinalidad_ok": True, "flags": None},
        ]
    )

    aforo = pd.DataFrame(
        [
            {"origin_node_id": 10, "destination_node_id": 10, "aforo_diff_pct": 0.0},
            {"origin_node_id": 11, "destination_node_id": 12, "aforo_diff_pct": 0.0},
        ]
    )

    result = run_validation_pipeline(routing, processed, aforo)

    # No debe fallar por divisiones entre cero; score_final dentro de [0,1]
    assert ((result["score_final"] >= 0.0) & (result["score_final"] <= 1.0)).all()
