"""Pipeline maestro de KIDO: fases A–D en un solo flujo."""
from __future__ import annotations

import logging
from pathlib import Path
from shutil import copyfile
from time import perf_counter
from typing import Dict

import pandas as pd

from kido_ruteo.config.loader import Config
from kido_ruteo.processing.processing_pipeline import KIDORawProcessor
from kido_ruteo.routing.routing_pipeline import run_routing_pipeline
from kido_ruteo.validation.validation_pipeline import run_validation_pipeline

LOGGER_NAME = "kido.pipeline"


def _setup_logging(log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "pipeline.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Evitar duplicar handlers hacia el mismo archivo
    if not any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None) == str(log_path) for h in root_logger.handlers):
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(name)s - %(message)s"))
        root_logger.addHandler(handler)

    return log_path


def _export_dataframe(df: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)


def run_kido_pipeline(cfg: Config, *, fix_disconnected_nodes: bool = True) -> Dict[str, pd.DataFrame]:
    """Ejecuta Fases B, C y D con logging unificado.

    Args:
        cfg: Configuración completa (Fase A) cargada con ``Config.load_all``.
        fix_disconnected_nodes: Si True, remapea nodos fuera del grafo al más cercano.

    Returns:
        Dict con DataFrames de processed, routing y validation.
    """

    log_path = _setup_logging(Path(cfg.paths.logs))
    logger = logging.getLogger(LOGGER_NAME)
    logger.info("=== Inicio pipeline KIDO ===")

    t0 = perf_counter()

    final_root = Path(cfg.paths.data_processed) / "final"
    cleaned_dir = final_root / "cleaned"
    routing_dir = final_root / "routing"
    validation_dir = final_root / "validation"
    final_logs_dir = final_root / "logs"
    for path in (cleaned_dir, routing_dir, validation_dir, final_logs_dir):
        path.mkdir(parents=True, exist_ok=True)

    # Fase B
    phase_start = perf_counter()
    try:
        processor = KIDORawProcessor(cfg)
        df_processed = processor.run_full_pipeline()
    except Exception as exc:  # pragma: no cover - runtime safety
        logger.exception("Error en Fase B (processing): %s", exc)
        raise RuntimeError(f"Fase B falló: {exc}") from exc
    logger.info("Fase B completada en %.2fs (%d viajes)", perf_counter() - phase_start, len(df_processed))

    # Preparar insumos de red
    gdf_nodes = processor.network.get("nodes") if processor.network else None
    gdf_edges = processor.network.get("edges") if processor.network else None
    if gdf_nodes is None or gdf_edges is None:
        raise RuntimeError("Red vial incompleta: se requieren nodes y edges para ruteo")

    df_od = df_processed[["origin_node_id", "destination_node_id"]].dropna()

    checkpoint_cfg = getattr(cfg.routing, "checkpoint", {})

    # Fase C
    phase_start = perf_counter()
    try:
        df_routing = run_routing_pipeline(
            df_od=df_od,
            df_manual_checkpoints=getattr(processor, "manual_checkpoints", None),
            gdf_nodes=gdf_nodes,
            gdf_edges=gdf_edges,
            output_dir=routing_dir,
            weight=getattr(cfg.routing, "weight", "weight"),
            checkpoint_mode=checkpoint_cfg.get("mode", "auto"),
            percent_lower=float(checkpoint_cfg.get("percent_lower", 0.40)),
            percent_upper=float(checkpoint_cfg.get("percent_upper", 0.60)),
            fix_disconnected_nodes=fix_disconnected_nodes,
            max_snap_distance_m=float(getattr(cfg.routing, "max_snap_distance_m", 400.0)),
        )
    except Exception as exc:  # pragma: no cover - runtime safety
        logger.exception("Error en Fase C (routing): %s", exc)
        raise RuntimeError(f"Fase C falló: {exc}") from exc
    remap_info = getattr(df_routing, "attrs", {}).get("remapped_nodes", {})
    if remap_info:
        logger.info("Nodos remapeados por desconexión: %d", len(remap_info))
    logger.info("Fase C completada en %.2fs (%d rutas)", perf_counter() - phase_start, len(df_routing))

    # Fase D
    phase_start = perf_counter()
    try:
        df_validation = run_validation_pipeline(
            df_routing=df_routing,
            df_processed=df_processed,
            df_aforo=getattr(processor, "aforo", None),
            validation_config=cfg.validation,
            output_dir=validation_dir,
        )
    except Exception as exc:  # pragma: no cover - runtime safety
        logger.exception("Error en Fase D (validación): %s", exc)
        raise RuntimeError(f"Fase D falló: {exc}") from exc
    logger.info("Fase D completada en %.2fs", perf_counter() - phase_start)

    # Exportar CSV mínimos
    _export_dataframe(df_processed, cleaned_dir / "processed.csv")
    _export_dataframe(df_routing, routing_dir / "routing_results.csv")
    if not (validation_dir / "validation_results.csv").exists():
        _export_dataframe(df_validation, validation_dir / "validation_results.csv")

    # Copiar log al folder final
    try:
        copyfile(log_path, final_logs_dir / "pipeline.log")
    except Exception:
        logger.warning("No se pudo copiar pipeline.log a carpeta final")

    logger.info("Pipeline completado en %.2fs", perf_counter() - t0)

    return {
        "processed": df_processed,
        "routing": df_routing,
        "validation": df_validation,
    }


__all__ = ["run_kido_pipeline"]
