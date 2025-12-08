"""Tests para scoring y clasificación de validación."""
from __future__ import annotations

from kido_ruteo.validation.scoring import classify_score, motivo_principal, normalize_weights, weighted_score


def test_normalize_weights():
    pesos = {"a": 2, "b": 2, "c": 1}
    normalized = normalize_weights(pesos)
    assert round(sum(normalized.values()), 6) == 1.0
    assert normalized["a"] == 0.4
    assert normalized["c"] == 0.2


def test_weighted_score_basic():
    component_scores = {"a": 1.0, "b": 0.5, "c": 0.0}
    pesos = {"a": 2, "b": 1, "c": 1}
    score = weighted_score(component_scores, pesos)
    # Weighted: (1*2 + 0.5*1 + 0*1) / 4 = 0.625
    assert score == 0.625


def test_classify_score_thresholds():
    umbrales = {"seguro": 0.85, "probable": 0.60, "poco_probable": 0.35}
    assert classify_score(0.90, umbrales) == 1
    assert classify_score(0.70, umbrales) == 2
    assert classify_score(0.40, umbrales) == 3
    assert classify_score(0.10, umbrales) == 4


def test_motivo_principal_returns_min_key():
    comp = {"map_matching": 0.9, "checkpoint": 0.3, "tiempo": 0.5}
    assert motivo_principal(comp) == "checkpoint"

    empty_reason = motivo_principal({})
    assert empty_reason == "desconocido"
