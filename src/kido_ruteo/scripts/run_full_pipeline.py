"""CLI para ejecutar el pipeline maestro KIDO (fases B, C, D)."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from time import perf_counter

from kido_ruteo.config.loader import ConfigLoader
from kido_ruteo.pipeline import run_kido_pipeline

logger = logging.getLogger(__name__)


def _setup_console_logging() -> None:
    """Configura logging en consola."""
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logging.getLogger().addHandler(console_handler)


def main() -> None:
    """Punto de entrada principal."""
    parser = argparse.ArgumentParser(
        description="Ejecuta el pipeline completo KIDO (fases A–D)"
    )
    parser.add_argument(
        "--config-paths",
        default="config/paths.yaml",
        help="Ruta al archivo paths.yaml (default: config/paths.yaml)",
    )
    parser.add_argument(
        "--config-routing",
        default="config/routing.yaml",
        help="Ruta al archivo routing.yaml (default: config/routing.yaml)",
    )
    parser.add_argument(
        "--config-validation",
        default="config/validation.yaml",
        help="Ruta al archivo validation.yaml (default: config/validation.yaml)",
    )
    parser.add_argument(
        "--no-fix-disconnected-nodes",
        action="store_true",
        help="No remapear nodos desconectados al nodo más cercano",
    )
    parser.add_argument(
        "--export-geojson",
        action="store_true",
        help="Habilitar exportación a GeoJSON de resultados de validación",
    )

    args = parser.parse_args()

    _setup_console_logging()
    logger.info("=== KIDO Pipeline CLI ===")

    try:
        # Cargar configuración
        logger.info("Cargando configuración...")
        cfg = ConfigLoader.load_all(
            paths_file=args.config_paths,
            routing_file=args.config_routing,
            validation_file=args.config_validation,
        )

        # Actualizar flag de validación si se solicita
        if args.export_geojson:
            cfg.validation.campos_salida["incluir_geojson"] = True

        # Ejecutar pipeline
        t0 = perf_counter()
        logger.info("Iniciando pipeline...")
        result = run_kido_pipeline(
            cfg,
            fix_disconnected_nodes=not args.no_fix_disconnected_nodes,
        )
        elapsed = perf_counter() - t0

        # Imprimir resumen
        df_processed = result.get("processed", None)
        df_routing = result.get("routing", None)
        df_validation = result.get("validation", None)

        print("\n" + "=" * 60)
        print("RESUMEN DEL PIPELINE")
        print("=" * 60)

        if df_processed is not None:
            print(f"✓ Viajes procesados (Fase B):     {len(df_processed):,}")
        if df_routing is not None:
            errors = df_routing["error"].notna().sum() if "error" in df_routing else 0
            print(f"✓ Rutas calculadas (Fase C):     {len(df_routing):,} ({errors} errores)")
        if df_validation is not None:
            print(f"✓ Viajes validados (Fase D):     {len(df_validation):,}")

            # Distribución de congruencia
            if "congruencia_nivel" in df_validation.columns:
                dist = df_validation["congruencia_nivel"].value_counts().to_dict()
                print("\n  Distribución de congruencia:")
                for level in ["seguro", "probable", "poco_probable", "imposible"]:
                    count = dist.get(level, 0)
                    pct = (count / len(df_validation) * 100) if len(df_validation) > 0 else 0
                    print(f"    {level:20s}: {count:,} ({pct:6.2f}%)")

            # Score promedio
            if "score_final" in df_validation.columns:
                avg_score = df_validation["score_final"].mean()
                print(f"\n  Score promedio:                 {avg_score:.3f}")

        print(f"\nTiempo total:                   {elapsed:.2f}s")
        print("=" * 60 + "\n")

        final_dir = Path(cfg.paths.data_processed) / "final"
        print(f"Resultados guardados en:        {final_dir}\n")

    except Exception as exc:
        logger.exception("Error en pipeline: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
