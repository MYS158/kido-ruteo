"""Test de integración end-to-end para el pipeline completo de routing.

Este test valida:
1. Carga de grafo desde archivos GPKG
2. Procesamiento de pares OD
3. Generación de checkpoints automáticos
4. Cálculo de MC y MC2
5. Cálculo de ratio X
6. Exportación de resultados
7. Validación de formato y valores
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString, Point

from kido_ruteo.routing.routing_pipeline import run_routing_pipeline
from kido_ruteo.routing.graph_loader import load_graph_from_network_dir


@pytest.fixture
def realistic_network():
    """Crea una red realista para pruebas end-to-end.
    
    Red simulada de una ciudad pequeña:
    - 15 nodos (intersecciones)
    - 25 edges (calles)
    - Tipos de vías: motorway, primary, secondary, tertiary
    - Velocidades: 80, 60, 40, 30 km/h
    - Distancias realistas: 500-3000m
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Crear red en forma de cuadrícula con conexiones diagonales
        # Layout: 5x3 grid de nodos
        nodes_data = []
        node_id = 1
        for row in range(3):
            for col in range(5):
                x = col * 1000  # 1km entre columnas
                y = row * 1000  # 1km entre filas
                nodes_data.append({
                    "node_id": node_id,
                    "geometry": Point(x, y),
                    "name": f"Nodo_{node_id}",
                })
                node_id += 1
        
        gdf_nodes = gpd.GeoDataFrame(nodes_data, crs="EPSG:32633")
        
        # Crear edges horizontales, verticales y algunas diagonales
        edges_data = []
        edge_types = {
            "motorway": {"speed": 80, "color": "red"},
            "primary": {"speed": 60, "color": "orange"},
            "secondary": {"speed": 40, "color": "yellow"},
            "tertiary": {"speed": 30, "color": "gray"},
        }
        
        # Edges horizontales
        for row in range(3):
            for col in range(4):
                u = row * 5 + col + 1
                v = u + 1
                length = 1000.0
                
                # Variar tipo de vía según posición
                if row == 1:  # Fila central = motorway
                    edge_type = "motorway"
                elif col < 2:
                    edge_type = "primary"
                else:
                    edge_type = "secondary"
                
                node_u = gdf_nodes[gdf_nodes.node_id == u].iloc[0]
                node_v = gdf_nodes[gdf_nodes.node_id == v].iloc[0]
                
                edges_data.append({
                    "u": u,
                    "v": v,
                    "length": length,
                    "speed": edge_types[edge_type]["speed"],
                    "primary_class": edge_type,
                    "geometry": LineString([node_u.geometry, node_v.geometry]),
                })
                
                # Agregar edge en dirección opuesta
                edges_data.append({
                    "u": v,
                    "v": u,
                    "length": length,
                    "speed": edge_types[edge_type]["speed"],
                    "primary_class": edge_type,
                    "geometry": LineString([node_v.geometry, node_u.geometry]),
                })
        
        # Edges verticales
        for col in range(5):
            for row in range(2):
                u = row * 5 + col + 1
                v = u + 5
                length = 1000.0
                
                # Variar tipo de vía
                if col in [0, 4]:  # Bordes = primary
                    edge_type = "primary"
                elif col == 2:  # Centro = secondary
                    edge_type = "secondary"
                else:
                    edge_type = "tertiary"
                
                node_u = gdf_nodes[gdf_nodes.node_id == u].iloc[0]
                node_v = gdf_nodes[gdf_nodes.node_id == v].iloc[0]
                
                edges_data.append({
                    "u": u,
                    "v": v,
                    "length": length,
                    "speed": edge_types[edge_type]["speed"],
                    "primary_class": edge_type,
                    "geometry": LineString([node_u.geometry, node_v.geometry]),
                })
                
                # Agregar edge en dirección opuesta
                edges_data.append({
                    "u": v,
                    "v": u,
                    "length": length,
                    "speed": edge_types[edge_type]["speed"],
                    "primary_class": edge_type,
                    "geometry": LineString([node_v.geometry, node_u.geometry]),
                })
        
        # Algunas conexiones diagonales (atajos)
        diagonals = [
            (1, 7, "secondary", 1414.0),   # sqrt(1000^2 + 1000^2)
            (5, 11, "secondary", 1414.0),
            (6, 12, "primary", 1414.0),
        ]
        
        for u, v, edge_type, length in diagonals:
            node_u = gdf_nodes[gdf_nodes.node_id == u].iloc[0]
            node_v = gdf_nodes[gdf_nodes.node_id == v].iloc[0]
            
            edges_data.append({
                "u": u,
                "v": v,
                "length": length,
                "speed": edge_types[edge_type]["speed"],
                "primary_class": edge_type,
                "geometry": LineString([node_u.geometry, node_v.geometry]),
            })
            
            edges_data.append({
                "u": v,
                "v": u,
                "length": length,
                "speed": edge_types[edge_type]["speed"],
                "primary_class": edge_type,
                "geometry": LineString([node_v.geometry, node_u.geometry]),
            })
        
        gdf_edges = gpd.GeoDataFrame(edges_data, crs="EPSG:32633")
        
        # Guardar archivos
        gdf_nodes.to_file(tmp_path / "nodes.gpkg", driver="GPKG")
        gdf_edges.to_file(tmp_path / "edges.gpkg", driver="GPKG")
        
        yield tmp_path, gdf_nodes, gdf_edges


@pytest.fixture
def od_pairs_sample():
    """Pares OD de ejemplo para testing."""
    return pd.DataFrame({
        "origin_node_id": [1, 1, 3, 6, 11],
        "destination_node_id": [15, 10, 13, 15, 1],
        "description": [
            "Diagonal completa (1→15)",
            "Media distancia (1→10)",
            "Corta distancia (3→13)",
            "Ruta larga (6→15)",
            "Ruta inversa (11→1)",
        ],
    })


@pytest.fixture
def manual_checkpoints_sample():
    """Checkpoints manuales para algunos pares."""
    return pd.DataFrame({
        "origin_zone_id": [1, 6],
        "destination_zone_id": [15, 15],
        "checkpoint_node_id": [8, 10],  # Checkpoints en el medio
    })


def test_load_realistic_network(realistic_network):
    """Test: Cargar red realista."""
    network_path, gdf_nodes, gdf_edges = realistic_network
    
    graph = load_graph_from_network_dir(network_path)
    
    # Verificar tamaño
    assert graph.number_of_nodes() == 15
    assert graph.number_of_edges() >= 50  # Al menos 50 edges
    
    # Verificar que es dirigido
    assert graph.is_directed()
    
    # Verificar que tiene atributos de peso
    for u, v in graph.edges():
        edge_data = graph[u][v]
        assert "weight" in edge_data
        assert "length" in edge_data
        assert "speed" in edge_data
        assert edge_data["weight"] > 0


def test_routing_pipeline_basic(realistic_network, od_pairs_sample):
    """Test: Pipeline básico con pares OD."""
    network_path, gdf_nodes, gdf_edges = realistic_network
    
    df_results = run_routing_pipeline(
        network_path=network_path,
        df_od=od_pairs_sample,
        gdf_nodes=gdf_nodes,
        gdf_edges=gdf_edges,
        checkpoint_mode="auto",
    )
    
    # Verificar que se procesaron todos los pares
    assert len(df_results) == len(od_pairs_sample)
    
    # Verificar columnas requeridas
    expected_cols = {
        "origin_node_id",
        "destination_node_id",
        "auto_checkpoint",
        "checkpoint_source",
        "mc_length_m",
        "mc_time_min",
        "mc2_length_m",
        "mc2_time_min",
        "ratio_x",
    }
    assert expected_cols.issubset(set(df_results.columns))
    
    # Verificar que no hay errores (o al menos la mayoría funcionó)
    if "error" in df_results.columns:
        errors = df_results["error"]
        success_rate = errors.isna().sum() / len(df_results)
    else:
        success_rate = 1.0
    assert success_rate >= 0.8, f"Solo {success_rate*100:.0f}% de pares exitosos"


def test_routing_metrics_validation(realistic_network, od_pairs_sample):
    """Test: Validar métricas de routing."""
    network_path, gdf_nodes, gdf_edges = realistic_network
    
    df_results = run_routing_pipeline(
        network_path=network_path,
        df_od=od_pairs_sample,
        gdf_nodes=gdf_nodes,
        gdf_edges=gdf_edges,
    )
    
    # Filtrar solo pares exitosos
    if "error" not in df_results.columns:
        df_success = df_results.copy()
    else:
        df_success = df_results[df_results["error"].isna()].copy()
    
    assert len(df_success) > 0, "No se procesó ningún par exitosamente"
    
    for idx, row in df_success.iterrows():
        # MC2 debe ser mayor o igual que MC (nunca puede ser más corto)
        assert row["mc2_length_m"] >= row["mc_length_m"], \
            f"MC2 ({row['mc2_length_m']}) < MC ({row['mc_length_m']})"
        
        # Ratio X debe ser >= 1.0
        assert row["ratio_x"] >= 1.0, \
            f"Ratio X ({row['ratio_x']}) < 1.0"
        
        # Métricas deben ser positivas
        assert row["mc_length_m"] > 0
        assert row["mc_time_min"] > 0
        assert row["mc2_length_m"] > 0
        assert row["mc2_time_min"] > 0
        
        # Verificar coherencia tiempo/distancia
        # Velocidad promedio MC: length/time (debe estar en rango razonable)
        avg_speed_mc = (row["mc_length_m"] / 1000) / (row["mc_time_min"] / 60)
        assert 20 <= avg_speed_mc <= 100, \
            f"Velocidad promedio MC ({avg_speed_mc:.1f} km/h) fuera de rango"


def test_auto_checkpoint_percentile(realistic_network, od_pairs_sample):
    """Test: Checkpoints automáticos están en rango percentil."""
    network_path, gdf_nodes, gdf_edges = realistic_network
    
    df_results = run_routing_pipeline(
        network_path=network_path,
        df_od=od_pairs_sample,
        gdf_nodes=gdf_nodes,
        gdf_edges=gdf_edges,
        percent_lower=0.40,
        percent_upper=0.60,
    )
    
    # Verificar que los checkpoints están en el rango esperado
    if "error" not in df_results.columns:
        df_success = df_results.copy()
    else:
        df_success = df_results[df_results["error"].isna()].copy()
    
    for idx, row in df_success.iterrows():
        if "path_nodes_mc" in row and isinstance(row["path_nodes_mc"], list):
            mc_nodes = row["path_nodes_mc"]
            checkpoint = row.get("auto_checkpoint")
            
            if checkpoint and checkpoint in mc_nodes:
                checkpoint_idx = mc_nodes.index(checkpoint)
                n = len(mc_nodes)
                
                # Verificar que está en el rango 40-60% (aproximadamente)
                position_pct = checkpoint_idx / (n - 1) if n > 1 else 0.5
                
                # Permitir margen de error
                assert 0.30 <= position_pct <= 0.70, \
                    f"Checkpoint en posición {position_pct*100:.0f}% (fuera de rango 30-70%)"


def test_routing_with_manual_checkpoints(
    realistic_network,
    od_pairs_sample,
    manual_checkpoints_sample,
):
    """Test: Pipeline con checkpoints manuales."""
    network_path, gdf_nodes, gdf_edges = realistic_network
    
    df_results = run_routing_pipeline(
        network_path=network_path,
        df_od=od_pairs_sample,
        df_manual_checkpoints=manual_checkpoints_sample,
        gdf_nodes=gdf_nodes,
        gdf_edges=gdf_edges,
        checkpoint_mode="manual",
    )
    
    # Verificar que los pares con checkpoints manuales los usan
    manual_origins = set(manual_checkpoints_sample["origin_zone_id"])
    manual_dests = set(manual_checkpoints_sample["destination_zone_id"])
    
    for idx, row in df_results.iterrows():
        origin = row["origin_node_id"]
        dest = row["destination_node_id"]
        
        if origin in manual_origins and dest in manual_dests:
            # Este par debería tener checkpoint manual
            manual_row = manual_checkpoints_sample[
                (manual_checkpoints_sample["origin_zone_id"] == origin) &
                (manual_checkpoints_sample["destination_zone_id"] == dest)
            ]
            
            if not manual_row.empty:
                assert row["checkpoint_source"] == "manual"
                assert row.get("manual_checkpoint") == manual_row.iloc[0]["checkpoint_node_id"]


def test_routing_output_export(realistic_network, od_pairs_sample):
    """Test: Exportación de resultados a CSV."""
    network_path, gdf_nodes, gdf_edges = realistic_network
    
    with tempfile.TemporaryDirectory() as output_dir:
        df_results = run_routing_pipeline(
            network_path=network_path,
            df_od=od_pairs_sample,
            gdf_nodes=gdf_nodes,
            gdf_edges=gdf_edges,
            output_dir=output_dir,
        )
        
        # Verificar que se creó el archivo
        output_file = Path(output_dir) / "routing_results.csv"
        assert output_file.exists()
        
        # Cargar y verificar contenido
        df_loaded = pd.read_csv(output_file)
        assert len(df_loaded) == len(df_results)
        
        # Verificar columnas clave
        assert "origin_node_id" in df_loaded.columns
        assert "destination_node_id" in df_loaded.columns
        assert "mc_length_m" in df_loaded.columns
        assert "ratio_x" in df_loaded.columns


def test_routing_ratio_x_realistic_values(realistic_network):
    """Test: Ratio X tiene valores realistas."""
    network_path, gdf_nodes, gdf_edges = realistic_network
    
    # Crear pares OD variados
    od_pairs = pd.DataFrame({
        "origin_node_id": [1, 1, 6, 11],
        "destination_node_id": [15, 8, 15, 5],
    })
    
    df_results = run_routing_pipeline(
        network_path=network_path,
        df_od=od_pairs,
        gdf_nodes=gdf_nodes,
        gdf_edges=gdf_edges,
    )
    
    if "error" not in df_results.columns:
        df_success = df_results.copy()
    else:
        df_success = df_results[df_results["error"].isna()].copy()
    
    # Ratio X típicamente está entre 1.0 y 1.5 para rutas urbanas
    # (el desvío por checkpoint no debería ser enorme)
    for idx, row in df_success.iterrows():
        assert 1.0 <= row["ratio_x"] <= 2.0, \
            f"Ratio X ({row['ratio_x']:.2f}) fuera de rango esperado [1.0, 2.0]"


def test_routing_handles_short_routes(realistic_network):
    """Test: Manejo correcto de rutas cortas."""
    network_path, gdf_nodes, gdf_edges = realistic_network
    
    # Pares OD adyacentes
    od_pairs = pd.DataFrame({
        "origin_node_id": [1, 6, 7],
        "destination_node_id": [2, 7, 8],
    })
    
    df_results = run_routing_pipeline(
        network_path=network_path,
        df_od=od_pairs,
        gdf_nodes=gdf_nodes,
        gdf_edges=gdf_edges,
    )
    
    # Todas las rutas cortas deberían procesarse exitosamente
    if "error" in df_results.columns:
        errors = df_results["error"]
        assert errors.isna().all(), "Algunas rutas cortas fallaron"
    # Si no hay columna error, todo salió bien
    
    # Para rutas cortas, ratio X debería estar cerca de 1.0
    for idx, row in df_results.iterrows():
        # Rutas adyacentes deberían tener ratio X bajo
        assert 1.0 <= row["ratio_x"] <= 1.5, \
            f"Ratio X para ruta corta ({row['ratio_x']:.2f}) inesperadamente alto"


def test_routing_data_types(realistic_network, od_pairs_sample):
    """Test: Tipos de datos correctos en resultados."""
    network_path, gdf_nodes, gdf_edges = realistic_network
    
    df_results = run_routing_pipeline(
        network_path=network_path,
        df_od=od_pairs_sample,
        gdf_nodes=gdf_nodes,
        gdf_edges=gdf_edges,
    )
    
    if "error" not in df_results.columns:
        df_success = df_results.copy()
    else:
        df_success = df_results[df_results["error"].isna()].copy()
    
    # Verificar tipos de datos
    assert pd.api.types.is_integer_dtype(df_success["origin_node_id"]) or \
           pd.api.types.is_object_dtype(df_success["origin_node_id"])
    assert pd.api.types.is_numeric_dtype(df_success["mc_length_m"])
    assert pd.api.types.is_numeric_dtype(df_success["mc_time_min"])
    assert pd.api.types.is_numeric_dtype(df_success["ratio_x"])
    
    # Checkpoint source debe ser string
    assert df_success["checkpoint_source"].dtype == object
    assert set(df_success["checkpoint_source"]).issubset({"auto", "manual"})
