"""Pipeline completo de routing: MC, MC2 y cálculo de ratio X."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import networkx as nx
import pandas as pd

from .auto_checkpoint import compute_auto_checkpoint
from .constrained_path import compute_constrained_path
from .graph_loader import load_graph_from_network_dir
from .shortest_path import compute_shortest_path, NoPathFoundError


logger = logging.getLogger(__name__)


def run_routing_pipeline(
    df_od: pd.DataFrame,
    gdf_nodes: gpd.GeoDataFrame | None = None,
    gdf_edges: gpd.GeoDataFrame | None = None,
    df_manual_checkpoints: pd.DataFrame | None = None,
    network_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    weight: str = "weight",
    checkpoint_mode: str = "auto",
    percent_lower: float = 0.40,
    percent_upper: float = 0.60,
    fix_disconnected_nodes: bool = True,
    max_snap_distance_m: float = 400.0,
) -> pd.DataFrame:
    """Ejecuta pipeline completo de routing para pares OD.
    
    Args:
        df_od: DataFrame con columnas origin_node_id, destination_node_id
        gdf_nodes: GeoDataFrame con nodos (para auto_checkpoint e identificar conexiones)
        gdf_edges: GeoDataFrame con edges (para detectar nodos desconectados)
        df_manual_checkpoints: DataFrame con checkpoints manuales (opcional)
        network_path: Ruta al directorio con edges.gpkg, nodes.gpkg (opcional si gdf_*=provided)
        output_dir: Directorio para guardar resultados (opcional)
        weight: Atributo de peso para routing (default: "weight")
        checkpoint_mode: "auto" o "manual" (default: "auto")
        percent_lower: Percentil inferior para auto checkpoint
        percent_upper: Percentil superior para auto checkpoint
        fix_disconnected_nodes: Si True, remapea nodos desconectados al más cercano
        max_snap_distance_m: Distancia máxima para remapeo de nodos
        
    Returns:
        DataFrame con resultados de routing con atributo .attrs["remapped_nodes"] si aplica
    """
    logger.info("=== Iniciando pipeline de routing ===")
    
    # Cargar o usar geodataframes proporcionados
    if gdf_nodes is None or gdf_edges is None:
        if network_path is None:
            raise ValueError("Se requiere network_path si gdf_nodes/gdf_edges no se proporcionan")
        logger.info("Cargando grafo desde %s", network_path)
        graph = load_graph_from_network_dir(network_path)
        gdf_nodes = gpd.read_file(Path(network_path) / "nodes.gpkg")
        gdf_edges = gpd.read_file(Path(network_path) / "edges.gpkg")
    else:
        graph = None
    
    # Si no tenemos el grafo aún, construirlo desde edges
    if graph is None:
        logger.info("Construyendo grafo dirigido desde edges")
        graph = nx.DiGraph()
        for _, row in gdf_edges.iterrows():
            u, v = row["u"], row["v"]
            length = float(row.get("length", 1.0))
            speed = float(row.get("speed", 50.0))
            weight_val = (length / 1000.0) / speed * 60.0 if speed > 0 else 1.0
            graph.add_edge(u, v, length=length, speed=speed, weight=weight_val)

    # Detectar nodos desconectados
    graph_nodes = set(graph.nodes())
    remapped_nodes: dict[int | str, int | str] = {}

    if fix_disconnected_nodes and gdf_nodes is not None:
        gdf_connected = gdf_nodes[gdf_nodes["node_id"].isin(graph_nodes)].copy()
        gdf_disconnected = gdf_nodes[~gdf_nodes["node_id"].isin(graph_nodes)].copy()
        if not gdf_disconnected.empty:
            logger.info("Detectados %d nodos desconectados", len(gdf_disconnected))
            for _, row in gdf_disconnected.iterrows():
                node_id = row["node_id"]
                geom = row.geometry
                dist = gdf_connected.geometry.distance(geom)
                nearest_idx = dist.idxmin()
                nearest_node = int(gdf_connected.loc[nearest_idx, "node_id"])
                nearest_dist = dist.iloc[nearest_idx]
                if nearest_dist <= max_snap_distance_m:
                    remapped_nodes[node_id] = nearest_node
                    logger.debug("Nodo %s remapeado a %s (%.1f m)", node_id, nearest_node, nearest_dist)
    
    # Validar columnas requeridas en df_od
    required_cols = {"origin_node_id", "destination_node_id"}
    missing_cols = required_cols - set(df_od.columns)
    if missing_cols:
        raise ValueError(f"Faltan columnas en df_od: {missing_cols}")
    
    # Aplicar remapeo a df_od
    df_od_remapped = df_od.copy()
    if remapped_nodes:
        df_od_remapped["origin_node_id"] = df_od_remapped["origin_node_id"].replace(remapped_nodes)
        df_od_remapped["destination_node_id"] = df_od_remapped["destination_node_id"].replace(remapped_nodes)
    
    # Preparar lista de resultados
    results = []
    
    total_pairs = len(df_od_remapped)
    logger.info("Procesando %d pares OD (con remapeo aplicado)", total_pairs)
    
    for idx, row in df_od_remapped.iterrows():
        origin = row["origin_node_id"]
        destination = row["destination_node_id"]
        
        if idx % 100 == 0 and idx > 0:
            logger.info("Procesando par %d/%d", idx + 1, total_pairs)
        
        try:
            result = _process_od_pair(
                graph=graph,
                origin=origin,
                destination=destination,
                df_manual_checkpoints=df_manual_checkpoints,
                gdf_nodes=gdf_nodes,
                gdf_edges=gdf_edges,
                weight=weight,
                checkpoint_mode=checkpoint_mode,
                percent_lower=percent_lower,
                percent_upper=percent_upper,
            )
            results.append(result)
            
        except Exception as exc:
            logger.error(
                "Error procesando par %s → %s: %s",
                origin,
                destination,
                exc,
            )
            # Agregar resultado con error
            results.append({
                "origin_node_id": origin,
                "destination_node_id": destination,
                "error": str(exc),
            })
    
    # Crear DataFrame de resultados
    df_results = pd.DataFrame(results)
    
    success_count = (~df_results.get("error", pd.Series(dtype=object)).notna()).sum()
    logger.info(
        "Pipeline completado: %d/%d pares procesados exitosamente",
        success_count,
        total_pairs,
    )
    
    # Guardar resultados si se especificó output_dir
    if output_dir is not None:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        output_file = output_path / "routing_results.csv"
        df_results.to_csv(output_file, index=False)
        logger.info("Resultados guardados en %s", output_file)
        
        if remapped_nodes:
            mapping_file = output_path / "mapping_disconnected_nodes.csv"
            pd.DataFrame([
                {"original_node_id": k, "mapped_to_node_id": v}
                for k, v in remapped_nodes.items()
            ]).to_csv(mapping_file, index=False)
            logger.info("Mapeo de nodos desconectados guardado en %s", mapping_file)
    
    # Almacenar remapped_nodes en atributos del DataFrame para auditoría
    df_results.attrs["remapped_nodes"] = remapped_nodes
    
    return df_results


def _process_od_pair(
    graph: nx.DiGraph,
    origin: Any,
    destination: Any,
    df_manual_checkpoints: pd.DataFrame | None,
    gdf_nodes: gpd.GeoDataFrame | None,
    gdf_edges: gpd.GeoDataFrame | None,
    weight: str,
    checkpoint_mode: str,
    percent_lower: float,
    percent_upper: float,
) -> dict[str, Any]:
    """Procesa un par OD individual: calcula MC, checkpoint y MC2.
    
    Returns:
        Diccionario con resultados del par
    """
    result: dict[str, Any] = {
        "origin_node_id": origin,
        "destination_node_id": destination,
    }
    
    # Paso 1: Calcular MC (A → B)
    try:
        mc_result = compute_shortest_path(graph, origin, destination, weight=weight)
    except NoPathFoundError:
        result["error"] = "No hay ruta MC"
        return result
    except ValueError as exc:
        result["error"] = f"Nodo no válido: {exc}"
        return result
    
    result["mc_length_m"] = mc_result["length_m"]
    result["mc_time_min"] = mc_result["time_min"]
    result["path_nodes_mc"] = mc_result["path_nodes"]
    
    # Paso 2: Determinar checkpoint
    manual_checkpoint = None
    
    # Verificar si existe checkpoint manual
    if df_manual_checkpoints is not None and not df_manual_checkpoints.empty:
        mask = (
            (df_manual_checkpoints["origin_zone_id"] == origin)
            & (df_manual_checkpoints["destination_zone_id"] == destination)
        )
        if mask.any():
            manual_checkpoint = df_manual_checkpoints.loc[mask, "checkpoint_node_id"].iloc[0]
            logger.debug("Checkpoint manual encontrado para %s → %s: %s", origin, destination, manual_checkpoint)
    
    # Determinar checkpoint final
    if checkpoint_mode == "manual" and manual_checkpoint is not None:
        checkpoint = manual_checkpoint
        checkpoint_source = "manual"
        result["manual_checkpoint"] = manual_checkpoint
    else:
        # Generar checkpoint automático
        try:
            auto_result = compute_auto_checkpoint(
                mc_nodes=mc_result["path_nodes"],
                gdf_nodes=gdf_nodes,
                gdf_edges=gdf_edges,
                percent_lower=percent_lower,
                percent_upper=percent_upper,
            )
            checkpoint = auto_result["checkpoint_node"]
            checkpoint_source = "auto"
            result["auto_checkpoint"] = checkpoint
        except Exception as exc:
            logger.warning("Error generando checkpoint automático: %s", exc)
            result["error"] = f"Error auto checkpoint: {exc}"
            return result
    
    result["checkpoint_node"] = checkpoint
    result["checkpoint_source"] = checkpoint_source
    
    # Paso 3: Calcular MC2 (A → C → B)
    try:
        mc2_result = compute_constrained_path(
            graph,
            origin,
            checkpoint,
            destination,
            weight=weight,
        )
    except NoPathFoundError as exc:
        result["error"] = f"No hay ruta MC2: {exc}"
        return result
    except ValueError as exc:
        result["error"] = f"Error MC2: {exc}"
        return result
    
    result["mc2_length_m"] = mc2_result["length_m"]
    result["mc2_time_min"] = mc2_result["time_min"]
    result["path_nodes_mc2"] = mc2_result["path_nodes"]
    
    # Paso 4: Calcular ratio X
    if mc_result["length_m"] > 0:
        ratio_x = mc2_result["length_m"] / mc_result["length_m"]
    else:
        ratio_x = 1.0
    
    result["ratio_x"] = ratio_x
    
    return result
