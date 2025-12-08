"""Pipeline de validación (Fase D).

Combina resultados de ruteo (MC/MC2) con datos procesados de Fase B y
consistencia de aforo para generar un score final y nivel de congruencia.
"""
from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any, Mapping, Sequence

import geopandas as gpd
import pandas as pd

from kido_ruteo.config.loader import ConfigLoader, ValidationConfig
from .checks import (
    aggregate_score,
    check_aforo,
    check_cardinalidad,
    check_checkpoint,
    check_distancia_pct,
    check_flags_validacion,
    check_ratio_x,
    check_tiempo_pct,
)
from .scoring import classify_score, motivo_principal

logger = logging.getLogger(__name__)


def _load_df(data: pd.DataFrame | str | Path) -> pd.DataFrame:
    """Carga un DataFrame desde CSV si se pasa una ruta."""
    if isinstance(data, pd.DataFrame):
        return data.copy()
    return pd.read_csv(Path(data))


def _to_list(value: Any) -> list[Any]:
    """Convierte strings tipo lista a lista real; retorna vacío si falla."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
            if isinstance(parsed, Sequence):
                return list(parsed)
        except (ValueError, SyntaxError):
            return []
    return []


def _compute_checkpoint_passed(row: Mapping[str, Any], requiere_checkpoint: bool) -> bool | None:
    """Determina si el checkpoint fue recorrido en la ruta MC2."""
    if "checkpoint_passed" in row and pd.notna(row.get("checkpoint_passed")):
        value = row.get("checkpoint_passed")
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes", "y"}
        return bool(value)

    checkpoint_node = row.get("checkpoint_node")
    path_nodes_mc2 = row.get("path_nodes_mc2")
    if checkpoint_node is None or path_nodes_mc2 is None:
        return None if requiere_checkpoint else True

    nodes = _to_list(path_nodes_mc2)
    try:
        return int(checkpoint_node) in {int(n) for n in nodes}
    except Exception:
        return None if requiere_checkpoint else True


def _coerce_validation_config(cfg: ValidationConfig | Mapping[str, Any] | None) -> ValidationConfig:
    if cfg is None:
        return ConfigLoader.load_validation()
    if isinstance(cfg, ValidationConfig):
        return cfg
    if isinstance(cfg, Mapping):
        return ValidationConfig.from_dict(cfg)
    raise TypeError("validation_config debe ser ValidationConfig, Mapping o None")


def _compute_component_scores(row: pd.Series, cfg: ValidationConfig) -> dict[str, float]:
    tolerancia_tiempo = float(cfg.calibracion.get("tolerancia_tiempo_pct", 0.2))
    tolerancia_distancia = float(cfg.calibracion.get("tolerancia_distancia_pct", 0.15))
    tolerancia_volumen = float(cfg.calibracion.get("tolerancia_volumen_pct", 0.15))
    smoothing = float(cfg.calibracion.get("smoothing_factor", 0.1))
    requiere_checkpoint = bool(cfg.checks_logicos.get("requiere_checkpoint", True))

    ratio_score = check_ratio_x(row.get("ratio_x"), tolerancia_distancia, smoothing)
    dist_score = check_distancia_pct(row.get("dist_diff_pct"), tolerancia_distancia, smoothing)
    map_matching_score = (ratio_score + dist_score) / 2 if dist_score is not None else ratio_score

    tiempo_score = check_tiempo_pct(row.get("time_diff_pct"), tolerancia_tiempo, smoothing)
    checkpoint_score = check_checkpoint(_compute_checkpoint_passed(row, requiere_checkpoint), requiere_checkpoint)
    aforo_score = check_aforo(row.get("aforo_diff_pct"), row.get("aforo_ok"), tolerancia_volumen, smoothing)
    trips_score = check_cardinalidad(row.get("cardinalidad_ok"))
    validez_score = check_flags_validacion(row.get("flags") or row.get("validation_flags"))

    return {
        "map_matching": map_matching_score,
        "checkpoint": checkpoint_score,
        "tiempo": tiempo_score,
        "volumen": aforo_score,
        "trips": trips_score,
        "validez": validez_score,
    }


def _prepare_dataframe(
    df_routing: pd.DataFrame,
    df_processed: pd.DataFrame,
    df_aforo: pd.DataFrame | None,
) -> pd.DataFrame:
    """Combina DataFrames de ruteo, procesados y aforo."""
    # Si el routing está vacío, retornar vacío
    if df_routing.empty:
        logger.warning("Datos de routing vacíos; retornando DataFrame vacío")
        return df_routing.copy()
    
    # Verificar que las columnas de merge existan
    merge_cols = [col for col in ["origin_node_id", "destination_node_id"] if col in df_routing.columns]
    if not merge_cols:
        logger.warning("Columnas de merge no encontradas en routing; retornando sin merge")
        return df_routing.copy()
    
    merged = df_routing.merge(df_processed, on=merge_cols, how="left", suffixes=("", "_proc"))
    if df_aforo is not None and not df_aforo.empty:
        merged = merged.merge(df_aforo, on=merge_cols, how="left", suffixes=("", "_aforo"))
    return merged


def _add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    
    df = df.copy()
    # Ratio X
    if "ratio_x" not in df.columns or df["ratio_x"].isna().all():
        df["ratio_x"] = df.apply(
            lambda r: (r["mc2_length_m"] / r["mc_length_m"]) if r["mc_length_m"] not in (0, None) else None,
            axis=1,
        )

    # Dif. porcentual distancia y tiempo
    df["dist_diff_pct"] = df.apply(
        lambda r: ((r["mc2_length_m"] - r["mc_length_m"]) / r["mc_length_m"]) if r["mc_length_m"] not in (0, None) else None,
        axis=1,
    )
    df["time_diff_pct"] = df.apply(
        lambda r: ((r["mc2_time_min"] - r["mc_time_min"]) / r["mc_time_min"]) if r["mc_time_min"] not in (0, None) else None,
        axis=1,
    )
    return df


def run_validation_pipeline(
    df_routing: pd.DataFrame | str | Path,
    df_processed: pd.DataFrame | str | Path,
    df_aforo: pd.DataFrame | str | Path | None = None,
    validation_config: ValidationConfig | Mapping[str, Any] | None = None,
    output_dir: str | Path | None = None,
) -> pd.DataFrame:
    """Ejecuta la Fase D de validación.

    Args:
        df_routing: Resultados de ruteo (DataFrame o CSV) con mc/mc2.
        df_processed: Datos procesados de Fase B con cardinalidad, flags, etc.
        df_aforo: Datos de aforo (opcional).
        validation_config: Objeto o dict con configuración de validación.
        output_dir: Si se indica, guarda CSV/GeoJSON según config.

    Returns:
        DataFrame con score_final, congruencia_nivel y motivo_principal.
    """
    cfg = _coerce_validation_config(validation_config)

    routing_df = _load_df(df_routing)
    processed_df = _load_df(df_processed)
    aforo_df = _load_df(df_aforo) if df_aforo is not None else None

    merged = _prepare_dataframe(routing_df, processed_df, aforo_df)
    merged = _add_derived_metrics(merged)

    def _score_row(row: pd.Series) -> pd.Series:
        component_scores = _compute_component_scores(row, cfg)
        score_final = aggregate_score(component_scores, cfg.pesos_componentes)
        nivel = classify_score(score_final, cfg.umbrales_congruencia)
        return pd.Series({
            "score_final": score_final,
            "congruencia_nivel": nivel,
            "motivo_principal": motivo_principal(component_scores),
            **{f"score_{k}": v for k, v in component_scores.items()},
        })

    scores_df = merged.apply(_score_row, axis=1)
    result = pd.concat([merged, scores_df], axis=1)

    # Exportar si se solicita
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if cfg.campos_salida.get("incluir_csv", True):
            csv_path = output_path / "validation_results.csv"
            result.to_csv(csv_path, index=False)
            logger.info("Resultados de validación guardados en %s", csv_path)

        if cfg.campos_salida.get("incluir_geojson", False) and "geometry" in result.columns:
            try:
                gdf = gpd.GeoDataFrame(result, geometry="geometry", crs="EPSG:4326")
                geojson_path = output_path / "validation_results.geojson"
                gdf.to_file(geojson_path, driver="GeoJSON")
                logger.info("GeoJSON de validación guardado en %s", geojson_path)
            except Exception as exc:
                logger.warning("No se pudo exportar GeoJSON: %s", exc)

        if cfg.campos_salida.get("incluir_resumen", True):
            summary_path = output_path / "validation_summary.csv"
            try:
                summary = result.groupby("congruencia_nivel").size().reset_index(name="count")
                summary.to_csv(summary_path, index=False)
                logger.info("Resumen de validación guardado en %s", summary_path)
            except Exception as exc:
                logger.warning("No se pudo generar resumen: %s", exc)

    logger.info("Validación completada: %d registros", len(result))
    return result


__all__ = ["run_validation_pipeline"]
