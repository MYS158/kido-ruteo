"""Tests para funciones de checks (Fase D)."""
from __future__ import annotations

from kido_ruteo.validation.checks import (
    aggregate_score,
    check_aforo,
    check_cardinalidad,
    check_checkpoint,
    check_distancia_pct,
    check_flags_validacion,
    check_ratio_x,
    check_tiempo_pct,
)


def test_check_ratio_x_within_tolerance():
    score = check_ratio_x(1.05, tolerancia_distancia_pct=0.15, smoothing_factor=0.1)
    assert score == 1.0

    score_far = check_ratio_x(1.35, tolerancia_distancia_pct=0.15, smoothing_factor=0.1)
    # diff = 0.35, extra 0.20 over tolerance => score should decay
    assert 0.15 < score_far < 0.25


def test_check_tiempo_pct_decay():
    score_ok = check_tiempo_pct(0.18, tolerancia_tiempo_pct=0.20, smoothing_factor=0.1)
    assert score_ok == 1.0

    score_high = check_tiempo_pct(0.40, tolerancia_tiempo_pct=0.20, smoothing_factor=0.1)
    assert 0.3 < score_high < 0.5


def test_check_distancia_pct_handles_none():
    assert check_distancia_pct(None, 0.15, 0.1) == 0.0


def test_check_checkpoint_required():
    assert check_checkpoint(True, requiere_checkpoint=True) == 1.0
    assert check_checkpoint(False, requiere_checkpoint=True) == 0.0
    # No info but not requerido
    assert check_checkpoint(None, requiere_checkpoint=False) == 1.0


def test_check_cardinalidad():
    assert check_cardinalidad(True) == 1.0
    assert check_cardinalidad(False) == 0.0
    assert check_cardinalidad(None) == 0.5


def test_check_aforo():
    score_ok = check_aforo(0.05, None, 0.15, 0.1)
    assert score_ok == 1.0

    score_decay = check_aforo(0.30, None, 0.15, 0.1)
    assert 0.3 < score_decay < 0.6

    score_flag = check_aforo(None, True, 0.15, 0.1)
    assert score_flag == 1.0

    score_flag_bad = check_aforo(None, False, 0.15, 0.1)
    assert score_flag_bad == 0.0


def test_check_flags_validacion():
    assert check_flags_validacion(None) == 1.0
    assert check_flags_validacion("warning") == 0.5
    assert check_flags_validacion("critical") == 0.0
    assert check_flags_validacion(["ok"]) == 1.0


def test_aggregate_score():
    comp = {"a": 1.0, "b": 0.0}
    pesos = {"a": 1, "b": 1}
    assert aggregate_score(comp, pesos) == 0.5

    pesos_zero = {"a": 0, "b": 0}
    assert aggregate_score(comp, pesos_zero) == 0.0
