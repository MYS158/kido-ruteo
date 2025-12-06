"""Pipeline de procesamiento de datos KIDO (Fase B)."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from kido_ruteo.config.loader import Config, ConfigLoader, PathsConfig
from .reader import load_kido_raw, load_network_metadata
from .cleaner import clean_kido
from .intrazonal import marcar_intrazonales
from .vector_acceso import generar_vectores_acceso
from .cardinalidad import asignar_sentido


logger = logging.getLogger(__name__)

class KIDORawProcessor:
    """Orquesta la limpieza y enriquecimiento de viajes KIDO."""

    def __init__(self) -> None:
        self.paths_cfg: Optional[PathsConfig] = None
        self.raw_df: Optional[pd.DataFrame] = None
        self.network: dict[str, Any] = {}
        self.processed_df: Optional[pd.DataFrame] = None

    def load_data(self, config: Config | ConfigLoader) -> None:
        """Carga viajes KIDO y metadatos de red desde la configuración."""
        cfg = config.load_all() if isinstance(config, ConfigLoader) else config
        self.paths_cfg = cfg.paths
        self.raw_df = load_kido_raw(cfg.paths)
        self.network = load_network_metadata(cfg.paths)
        logger.info("Datos cargados: viajes=%s, network=%s", len(self.raw_df), list(self.network))

    def process(self) -> pd.DataFrame:
        """Ejecuta la secuencia de limpieza y enriquecimiento."""
        if self.paths_cfg is None or self.raw_df is None:
            raise RuntimeError("Debe ejecutar load_data primero")

        df = clean_kido(self.raw_df)
        df = marcar_intrazonales(df)
        df = generar_vectores_acceso(df)
        df = asignar_sentido(df, self.network.get("cardinalidad"))

        self.processed_df = df
        self._ensure_dirs(self.paths_cfg.data_interim, self.paths_cfg.logs)
        self.save_interim(df)
        return df

    def save_interim(self, df: pd.DataFrame) -> None:
        """Guarda resultados intermedios en parquet y csv."""
        if self.paths_cfg is None:
            raise RuntimeError("paths_cfg no está definido")
        out_dir = Path(self.paths_cfg.data_interim)
        out_dir.mkdir(parents=True, exist_ok=True)
        parquet_path = out_dir / "kido_interim.parquet"
        csv_path = out_dir / "kido_interim.csv"
        df.to_parquet(parquet_path, index=False)
        df.to_csv(csv_path, index=False)
        logger.info("Intermedios guardados en %s y %s", parquet_path, csv_path)

    @staticmethod
    def _ensure_dirs(*paths: Any) -> None:
        for p in paths:
            Path(p).mkdir(parents=True, exist_ok=True)
