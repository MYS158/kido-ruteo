"""Generación automática de checkpoints para rutas."""
from __future__ import annotations

import logging
from typing import Any

import geopandas as gpd
import pandas as pd


logger = logging.getLogger(__name__)


def compute_auto_checkpoint(
    mc_nodes: list[Any],
    gdf_nodes: gpd.GeoDataFrame | None = None,
    gdf_edges: gpd.GeoDataFrame | None = None,
    percent_lower: float = 0.40,
    percent_upper: float = 0.60,
) -> dict[str, Any]:
    """Genera checkpoint automático basado en ruta MC.
    
    Regla:
    1. Seleccionar nodos en percentil 40-60% de la ruta
    2. Si hay datos de edges, preferir nodos en vías primarias
    3. Si la ruta es muy corta (<3 nodos), tomar el nodo medio
    
    Args:
        mc_nodes: Lista de nodos de la ruta MC (origen → destino)
        gdf_nodes: GeoDataFrame con información de nodos (opcional)
        gdf_edges: GeoDataFrame con información de edges (opcional)
        percent_lower: Percentil inferior (default: 0.40)
        percent_upper: Percentil superior (default: 0.60)
        
    Returns:
        Diccionario con:
        - checkpoint_node: ID del nodo seleccionado como checkpoint
        - checkpoint_source: "auto"
        - checkpoint_index: índice del nodo en mc_nodes
    """
    if not mc_nodes:
        raise ValueError("mc_nodes está vacío")
    
    # Caso 1: Ruta muy corta (menos de 3 nodos)
    if len(mc_nodes) < 3:
        checkpoint_idx = len(mc_nodes) // 2
        checkpoint_node = mc_nodes[checkpoint_idx]
        
        logger.info(
            "Ruta corta (%d nodos): checkpoint automático en índice %d (nodo %s)",
            len(mc_nodes),
            checkpoint_idx,
            checkpoint_node,
        )
        
        return {
            "checkpoint_node": checkpoint_node,
            "checkpoint_source": "auto",
            "checkpoint_index": checkpoint_idx,
        }
    
    # Caso 2: Ruta normal - seleccionar en percentil 40-60%
    candidates, idx_lower, idx_upper = get_candidate_nodes(mc_nodes, percent_lower, percent_upper)
    
    # Si tenemos información de edges, preferir vías primarias
    if gdf_edges is not None and "primary_class" in gdf_edges.columns:
        primary_candidates = _filter_primary_nodes(candidates, mc_nodes, gdf_edges)
        if primary_candidates:
            candidates = primary_candidates
            logger.info("Filtrados %d candidatos por vía primaria", len(candidates))
    
    # Seleccionar el nodo del medio del rango de candidatos
    checkpoint_idx = candidates[len(candidates) // 2]
    checkpoint_node = mc_nodes[checkpoint_idx]
    
    logger.info(
        "Checkpoint automático seleccionado: nodo %s (índice %d de %d)",
        checkpoint_node,
        checkpoint_idx,
        len(mc_nodes) - 1,
    )
    
    return {
        "checkpoint_node": checkpoint_node,
        "checkpoint_source": "auto",
        "checkpoint_index": checkpoint_idx,
    }


def get_candidate_nodes(
    mc_nodes: list[Any],
    percent_lower: float = 0.40,
    percent_upper: float = 0.60,
) -> tuple[list[int], int, int]:
    """Obtiene índices de nodos candidatos en percentil especificado.
    
    Args:
        mc_nodes: Lista de nodos de la ruta
        percent_lower: Percentil inferior (0.40 = 40%)
        percent_upper: Percentil superior (0.60 = 60%)
        
    Returns:
        Tupla (candidatos, idx_lower, idx_upper)
    """
    n = len(mc_nodes)
    
    if n < 3:
        # Ruta muy corta: solo el nodo medio
        mid = n // 2
        return [mid], mid, mid + 1
    
    # Calcular índices del rango percentil
    idx_lower = int(n * percent_lower)
    idx_upper = int(n * percent_upper)
    
    # Asegurar al menos un candidato
    if idx_lower == idx_upper:
        idx_upper = idx_lower + 1
    
    # Asegurar que no incluya origen ni destino
    idx_lower = max(1, idx_lower)
    idx_upper = min(n - 1, idx_upper)
    
    candidates = list(range(idx_lower, idx_upper))
    
    # Asegurar al menos un candidato
    if not candidates:
        mid = n // 2
        return [mid], mid, mid + 1
    
    return candidates, idx_lower, idx_upper


def _filter_primary_nodes(
    candidate_indices: list[int],
    mc_nodes: list[Any],
    gdf_edges: gpd.GeoDataFrame,
) -> list[int]:
    """Filtra candidatos que están en edges de vías primarias.
    
    Args:
        candidate_indices: Índices de nodos candidatos
        mc_nodes: Lista completa de nodos de la ruta
        gdf_edges: GeoDataFrame con edges que incluyen primary_class
        
    Returns:
        Lista de índices que están en vías primarias
    """
    primary_classes = {"motorway", "trunk", "primary", "secondary"}
    
    primary_candidates = []
    
    for idx in candidate_indices:
        node = mc_nodes[idx]
        
        # Verificar edges entrantes y salientes
        if idx > 0:
            prev_node = mc_nodes[idx - 1]
            # Buscar edge prev_node → node
            edge_mask = (gdf_edges["u"] == prev_node) & (gdf_edges["v"] == node)
            if edge_mask.any():
                edge_class = gdf_edges.loc[edge_mask, "primary_class"].iloc[0]
                if edge_class in primary_classes:
                    primary_candidates.append(idx)
                    continue
        
        if idx < len(mc_nodes) - 1:
            next_node = mc_nodes[idx + 1]
            # Buscar edge node → next_node
            edge_mask = (gdf_edges["u"] == node) & (gdf_edges["v"] == next_node)
            if edge_mask.any():
                edge_class = gdf_edges.loc[edge_mask, "primary_class"].iloc[0]
                if edge_class in primary_classes:
                    primary_candidates.append(idx)
    
    return primary_candidates
