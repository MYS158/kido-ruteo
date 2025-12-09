"""Pipeline de procesamiento de datos KIDO (Fase B).

Flujo completo:
1. Cargar OD
2. Calcular o cargar centroides por subred
3. Asignar nodos origen/destino basados en centroides
4. Aplicar total_trips_modif
5. Detectar intrazonales
6. Aplicar cardinalidad (sentido)
7. Calcular vectores de acceso (V1, V2)
8. Validar contra vectores
9. Generar MC (matriz de caminos todos los pares)
10. Seleccionar top 80% viajes representativos
11. Generar MC2 con checkpoint (manual override si existe)
12. Calcular X = (A→C + C→B) / (A→B)
13. Asignar congruencia según umbrales
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from kido_ruteo.config.loader import Config, ConfigLoader, InputsConfig, PathsConfig
from .reader import (
    load_aforo,
    load_kido_raw,
    load_network_metadata,
    load_od,
    load_zonas,
)
from .cleaner import clean_kido
from .intrazonal import marcar_intrazonales
from .vector_acceso import generar_vectores_acceso
from .cardinalidad import asignar_sentido

# Imports opcionales para centroids y manual_selection
try:
    from .centroids import (
        compute_all_zone_centroids,
        load_centroids,
        save_centroids,
    )
    CENTROIDS_AVAILABLE = True
except (ImportError, AttributeError):
    CENTROIDS_AVAILABLE = False

try:
    from ..routing.manual_selection import load_manual_selection
    MANUAL_SELECTION_AVAILABLE = True
except ImportError:
    MANUAL_SELECTION_AVAILABLE = False


logger = logging.getLogger(__name__)


class KIDORawProcessor:
    """Orquesta la limpieza, enriquecimiento y routing de viajes KIDO."""

    def __init__(self, config: Optional[Config | ConfigLoader] = None) -> None:
        self.config: Optional[Config] = None
        self.paths_cfg: Optional[PathsConfig] = None
        self.inputs_cfg: Optional[InputsConfig] = None
        self.raw_df: Optional[pd.DataFrame] = None
        self.zonas: Any = None
        self.centroids_gdf: Any = None
        self.aforo: Optional[pd.DataFrame] = None
        self.network: dict[str, Any] = {}
        self.manual_checkpoints: Optional[pd.DataFrame] = None
        self.processed_df: Optional[pd.DataFrame] = None
        self.mc_df: Optional[pd.DataFrame] = None
        self.mc2_df: Optional[pd.DataFrame] = None

        if config is not None:
            self.load_data(config)

    def load_data(self, config: Config | ConfigLoader) -> None:
        """Carga viajes KIDO y metadatos de red desde la configuración."""
        cfg = config.load_all() if isinstance(config, ConfigLoader) else config
        self.config = cfg
        self.paths_cfg = cfg.paths
        self.inputs_cfg = cfg.inputs

        logger.info("=== Fase B: Cargando insumos ===")
        self.raw_df = self.load_od()
        self.zonas = self.load_zonas()
        self.aforo = self.load_aforo()
        self.network = load_network_metadata(cfg.paths)
        self.centroids_gdf = self.load_or_compute_centroids()
        self.manual_checkpoints = self.load_manual_checkpoints()

        logger.info(
            "Datos cargados: viajes=%d, zonas=%s, centroids=%s, aforo=%s, network=%s, manual_checkpoints=%s",
            len(self.raw_df),
            "ok" if self.zonas is not None else "None",
            len(self.centroids_gdf) if self.centroids_gdf is not None else "None",
            len(self.aforo) if self.aforo is not None else "None",
            list(self.network.keys()),
            len(self.manual_checkpoints) if self.manual_checkpoints is not None else "None",
        )

    def load_or_compute_centroids(self) -> Any:
        """Carga centroides existentes o los calcula si no existen o si recompute=True."""
        if not CENTROIDS_AVAILABLE:
            logger.warning("Módulo centroids no disponible (requiere geopandas + networkx)")
            return None

        if self.config is None:
            logger.warning("Config no disponible para centroids")
            return None

        centroids_cfg = self.config.routing.centroids
        if centroids_cfg is None:
            logger.warning("Configuración de centroides no disponible; usando valores por defecto")
            return None
        
        centroids_path = Path(centroids_cfg.output)

        # Verificar si forzar recálculo
        if centroids_cfg.recompute:
            logger.info("recompute=True: forzando recálculo de centroides")
        elif centroids_path.exists():
            try:
                logger.info("Cargando centroides existentes desde %s", centroids_path)
                centroids_gdf = load_centroids(centroids_path)
                self.centroids_gdf = centroids_gdf  # Asignar al atributo de instancia
                return centroids_gdf
            except Exception as exc:
                logger.warning("Error cargando centroides (%s), recalculando...", exc)

        # Calcular centroides
        if self.zonas is None:
            logger.warning("No hay zonas cargadas, no se pueden calcular centroides")
            return None

        nodes_gdf = self.network.get("nodes")
        edges_gdf = self.network.get("edges")

        if nodes_gdf is None or edges_gdf is None:
            logger.warning("Red vial incompleta (nodes/edges), no se calculan centroides")
            return None

        logger.info("Calculando centroides con método %s...", centroids_cfg.method)

        # Combinar zonas core y checkpoint si están separadas
        if isinstance(self.zonas, dict):
            zonas_gdf = pd.concat([self.zonas.get("core", pd.DataFrame()), self.zonas.get("checkpoint", pd.DataFrame())], ignore_index=True)
        else:
            zonas_gdf = self.zonas

        centroids_gdf = compute_all_zone_centroids(
            zonas_gdf=zonas_gdf,
            gdf_nodes=nodes_gdf,
            gdf_edges=edges_gdf,
            method=centroids_cfg.method,
        )

        # Guardar centroides
        save_centroids(centroids_gdf, centroids_path)
        
        self.centroids_gdf = centroids_gdf  # Asignar al atributo de instancia
        return centroids_gdf

    def load_manual_checkpoints(self) -> Optional[pd.DataFrame]:
        """Carga archivo CSV con selección manual de checkpoints."""
        if not MANUAL_SELECTION_AVAILABLE:
            logger.warning("Módulo manual_selection no disponible")
            return None

        if self.config is None:
            return None

        manual_cfg = self.config.routing.manual_selection
        
        if manual_cfg is None:
            logger.info("Configuración de manual_selection no disponible")
            return None

        if not manual_cfg.enabled:
            logger.info("Manual checkpoint selection disabled")
            return None

        manual_path = Path(manual_cfg.file)

        if not manual_path.exists():
            logger.warning("Archivo manual checkpoints no encontrado: %s", manual_path)
            return None

        try:
            df = load_manual_selection(manual_path)
            logger.info("Selecciones manuales cargadas: %d pares", len(df))
            self.manual_checkpoints = df  # Asignar al atributo de instancia
            return df
        except Exception as exc:
            logger.error("Error cargando manual checkpoints: %s", exc)
            return None

    def run_full_pipeline(self, config: Optional[Config | ConfigLoader] = None) -> pd.DataFrame:
        """Carga insumos (si aplica) y ejecuta el proceso completo de Fase B."""
        if config is not None:
            self.load_data(config)
        elif self.config is None:
            raise RuntimeError("Debe proporcionar config o ejecutar load_data antes de run_full_pipeline")

        return self.process()

    def process(self) -> pd.DataFrame:
        """Ejecuta la secuencia completa de Fase B.

        Pasos:
        1. Limpiar datos OD
        2. Asignar nodos origen/destino desde centroides
        3. Aplicar total_trips_modif
        4. Detectar intrazonales
        5. Aplicar cardinalidad (sentido)
        6. Calcular vectores de acceso
        7. [Fase C] Generar MC, MC2, congruencias
        """
        if self.paths_cfg is None or self.raw_df is None:
            raise RuntimeError("Debe ejecutar load_data primero")

        logger.info("=== Fase B: Procesando pipeline ===")

        # Paso 1: Limpieza
        logger.info("Paso 1: Limpieza de datos")
        df = clean_kido(self.raw_df)

        # Paso 2: Asignar nodos desde od_with_nodes.csv (preferido) o centroides (fallback)
        logger.info("Paso 2: Asignando nodos origen/destino")
        df = self._assign_nodes_from_od_with_nodes(df)

        # Paso 3: total_trips_modif ya se aplica en clean_kido

        # Paso 4: Detectar intrazonales
        logger.info("Paso 4: Detectando viajes intrazonales")
        df = marcar_intrazonales(df)

        # Paso 5: Cardinalidad
        logger.info("Paso 5: Asignando cardinalidad (sentido)")
        df = asignar_sentido(df, self.network.get("cardinalidad"))

        # Paso 6: Vectores de acceso
        logger.info("Paso 6: Calculando vectores de acceso V1/V2")
        df = generar_vectores_acceso(df)

        # Guardar resultados intermedios
        self.processed_df = df
        self._ensure_dirs(self.paths_cfg.data_interim, self.paths_cfg.logs)
        self.save_interim(df)

        logger.info("Pipeline Fase B completado: %d registros procesados", len(df))

        return df

    def _assign_nodes_from_od_with_nodes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Asigna origin_node_id y destination_node_id desde od_with_nodes.csv.
        
        Este método es preferible a _assign_nodes_from_centroids ya que usa
        asignaciones pre-calculadas y validadas en lugar de depender de un archivo
        de centroides que puede tener errores (ej: todas las zonas al mismo nodo).
        """
        od_nodes_path = Path(self.paths_cfg.data_interim) / "od_with_nodes.csv"
        
        if not od_nodes_path.exists():
            logger.warning(
                "Archivo od_with_nodes.csv no encontrado en %s. "
                "Fallando a asignación de centroides", 
                od_nodes_path
            )
            return self._assign_nodes_from_centroids(df)
        
        try:
            df_od_nodes = pd.read_csv(od_nodes_path)
            logger.info("Cargado od_with_nodes.csv con %d pares", len(df_od_nodes))
        except Exception as exc:
            logger.error("Error cargando od_with_nodes.csv: %s. Fallando a centroides", exc)
            return self._assign_nodes_from_centroids(df)
        
        df = df.copy()
        
        # Crear mapeos OD -> nodos desde od_with_nodes
        od_to_nodes = {}
        for idx, row in df_od_nodes.iterrows():
            origin_id = str(row.get("origin"))
            dest_id = str(row.get("destination"))
            origin_node = row.get("origin_node_id")
            dest_node = row.get("destination_node_id")
            
            if pd.notna(origin_node) and pd.notna(dest_node):
                od_to_nodes[(origin_id, dest_id)] = (origin_node, dest_node)
        
        # Aplicar mapeos
        origin_nodes = []
        dest_nodes = []
        not_found = 0
        
        for idx, row in df.iterrows():
            origin_id = str(row.get("origin_id"))
            dest_id = str(row.get("destination_id"))
            
            if (origin_id, dest_id) in od_to_nodes:
                on, dn = od_to_nodes[(origin_id, dest_id)]
                origin_nodes.append(on)
                dest_nodes.append(dn)
            else:
                origin_nodes.append(None)
                dest_nodes.append(None)
                not_found += 1
        
        df["origin_node_id"] = origin_nodes
        df["destination_node_id"] = dest_nodes
        
        if not_found > 0:
            logger.warning(
                "%d pares OD no encontrados en od_with_nodes.csv. "
                "Se asignarán como NaN", 
                not_found
            )
        
        assigned = (~df["origin_node_id"].isna()).sum()
        logger.info(
            "Nodos asignados desde od_with_nodes.csv: %d/%d pares (%.1f%%)",
            assigned,
            len(df),
            100.0 * assigned / len(df) if len(df) > 0 else 0
        )
        
        return df

    def _assign_nodes_from_centroids(self, df: pd.DataFrame) -> pd.DataFrame:
        """Asigna origin_node_id y destination_node_id desde centroides."""
        if self.centroids_gdf is None:
            logger.warning("No hay centroides, no se asignan nodos")
            df["origin_node_id"] = None
            df["destination_node_id"] = None
            return df

        df = df.copy()
        
        # Validar diversidad de centroides
        unique_nodes = self.centroids_gdf["centroid_node_id"].nunique()
        total_zones = len(self.centroids_gdf)
        
        if unique_nodes < total_zones * 0.5:  # Si menos del 50% de zonas tienen nodos únicos
            logger.warning(
                "ALERTA: Centroides con baja diversidad (%.1f%% zonas tienen nodos únicos). "
                "Posible error en el archivo de centroides. "
                "Considere regenerar con recompute=true o usar od_with_nodes.csv",
                100.0 * unique_nodes / total_zones
            )

        # Crear mapeo zone_id -> centroid_node_id
        zone_to_node = {}
        for idx, row in self.centroids_gdf.iterrows():
            zone_id = str(row.get("zone_id"))
            node_id = row.get("centroid_node_id")
            if node_id is not None:
                zone_to_node[zone_id] = str(node_id)

        # Asignar nodos
        df["origin_node_id"] = df["origin_id"].astype(str).map(zone_to_node)
        df["destination_node_id"] = df["destination_id"].astype(str).map(zone_to_node)

        missing_origin = df["origin_node_id"].isna().sum()
        missing_dest = df["destination_node_id"].isna().sum()

        if missing_origin > 0:
            logger.warning("%d viajes sin nodo origen asignado", missing_origin)
        if missing_dest > 0:
            logger.warning("%d viajes sin nodo destino asignado", missing_dest)

        return df

    def load_od(self) -> pd.DataFrame:
        if self.inputs_cfg is None:
            raise RuntimeError("inputs_cfg no está definido")
        return load_od(self.inputs_cfg)

    def load_zonas(self) -> Any:
        if self.inputs_cfg is None:
            raise RuntimeError("inputs_cfg no está definido")
        try:
            return load_zonas(self.inputs_cfg)
        except ImportError:
            logger.warning("GeoPandas no disponible; no se cargan zonas")
            return None

    def load_aforo(self) -> Optional[pd.DataFrame]:
        if self.inputs_cfg is None:
            raise RuntimeError("inputs_cfg no está definido")
        try:
            return load_aforo(self.inputs_cfg)
        except FileNotFoundError:
            logger.warning("Archivo de aforo no encontrado; se omite")
            return None
        except ImportError as exc:
            logger.warning("Dependencia opcional faltante para aforo (%s); se omite", exc)
            return None
        except ValueError as exc:
            logger.error("Error al cargar aforo: %s", exc)
            raise

    def save_interim(self, df: pd.DataFrame) -> None:
        """Guarda resultados intermedios en parquet y csv."""
        if self.paths_cfg is None:
            raise RuntimeError("paths_cfg no está definido")
        out_dir = Path(self.paths_cfg.data_interim)
        out_dir.mkdir(parents=True, exist_ok=True)
        parquet_path = out_dir / "kido_interim.parquet"
        csv_path = out_dir / "kido_interim.csv"
        try:
            df.to_parquet(parquet_path, index=False)
        except Exception as exc:  # pragma: no cover - dependerá de pyarrow/fastparquet
            logger.warning("No se pudo guardar parquet (%s); se continúa con CSV", exc)
        df.to_csv(csv_path, index=False)
        logger.info("Intermedios guardados en %s y %s", parquet_path, csv_path)

    @staticmethod
    def _ensure_dirs(*paths: Any) -> None:
        for p in paths:
            Path(p).mkdir(parents=True, exist_ok=True)
