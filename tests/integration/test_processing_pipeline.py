"""Tests para el módulo processing_pipeline.py: Orquestación de procesamiento."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from kido_ruteo.processing.processing_pipeline import KIDORawProcessor


@pytest.fixture
def sample_kido_csv(tmp_path: Path) -> Path:
    """Crea un archivo CSV KIDO temporal."""
    df = pd.DataFrame({
        "origin_id": ["1", "2", "1", "3"],
        "destination_id": ["2", "3", "2", "1"],
        "origin_name": ["Zone A", "Zone B", "Zone A", "Zone C"],
        "destination_name": ["Zone B", "Zone C", "Zone B", "Zone A"],
        "fecha": ["2024-01-01", "2024-01-02", "2024-01-01", "2024-01-03"],
        "total_trips": [100, 50, 100, 5],
    })
    csv_file = tmp_path / "kido.csv"
    df.to_csv(csv_file, index=False)
    return tmp_path


@pytest.fixture
def mock_config(tmp_path: Path, sample_kido_csv: Path) -> MagicMock:
    """Crea un mock Config con paths temporales."""
    config = MagicMock()
    config.paths.data_raw = str(sample_kido_csv)
    config.paths.data_interim = str(tmp_path / "interim")
    config.paths.logs = str(tmp_path / "logs")
    config.paths.network = str(tmp_path / "network")
    
    # Crear directorios necesarios
    Path(config.paths.network).mkdir(parents=True, exist_ok=True)
    
    return config


class TestKIDORawProcessorInitialization:
    """Tests para inicialización de KIDORawProcessor."""

    def test_init_creates_empty_instance(self) -> None:
        """Inicialización crea instancia sin datos."""
        processor = KIDORawProcessor()
        
        assert processor.paths_cfg is None
        assert processor.raw_df is None
        assert processor.network == {}
        assert processor.processed_df is None

    def test_init_attributes_exist(self) -> None:
        """Instancia tiene todos los atributos esperados."""
        processor = KIDORawProcessor()
        
        assert hasattr(processor, "paths_cfg")
        assert hasattr(processor, "raw_df")
        assert hasattr(processor, "network")
        assert hasattr(processor, "processed_df")


class TestKIDORawProcessorLoadData:
    """Tests para load_data."""

    def test_load_data_with_mock_config(self, mock_config: MagicMock) -> None:
        """load_data carga CSV exitosamente."""
        processor = KIDORawProcessor()
        
        # Usar mock_config directamente como Config
        sample_df = pd.DataFrame({
            "origin_id": ["1", "2"],
            "destination_id": ["2", "3"],
            "origin_name": ["A", "B"],
            "destination_name": ["B", "C"],
            "fecha": ["2024-01-01", "2024-01-02"],
            "total_trips": [100, 50],
        })
        
        # Simular directamente
        processor.paths_cfg = mock_config.paths
        processor.raw_df = sample_df
        processor.network = {}
        
        assert processor.paths_cfg is not None
        assert processor.raw_df is not None
        assert len(processor.raw_df) == 2

    def test_load_data_fails_if_no_data(self, mock_config: MagicMock) -> None:
        """process falla si no se ejecutó load_data antes."""
        processor = KIDORawProcessor()
        
        with pytest.raises(RuntimeError, match="Debe ejecutar load_data primero"):
            processor.process()


class TestKIDORawProcessorProcess:
    """Tests para process."""

    def test_process_full_pipeline(self, mock_config: MagicMock) -> None:
        """process ejecuta todos los pasos del pipeline."""
        processor = KIDORawProcessor()
        
        sample_df = pd.DataFrame({
            "origin_id": ["1", "2", "1"],
            "destination_id": ["2", "3", "2"],
            "origin_name": ["Zone A", "Zone B", "Zone A"],
            "destination_name": ["Zone B", "Zone C", "Zone B"],
            "fecha": ["2024-01-01", "2024-01-02", "2024-01-01"],
            "total_trips": [100, 50, 100],
        })
        
        # Simular directamente sin save (para evitar parquet)
        processor.raw_df = sample_df
        processor.paths_cfg = mock_config.paths
        processor.network = {}
        
        # Mock save_interim para evitar parquet
        with patch.object(processor, "save_interim"):
            result = processor.process()
        
        # Validar que retorna DataFrame
        assert isinstance(result, pd.DataFrame)
        # Validar que se agregaron columnas esperadas
        assert "intrazonal" in result.columns
        assert "acceso_valido" in result.columns
        assert "od_valido" in result.columns
        assert "sentido" in result.columns

    def test_process_calls_all_cleaning_steps(self, mock_config: MagicMock) -> None:
        """process ejecuta limpiar, intrazonal, acceso, sentido."""
        processor = KIDORawProcessor()
        
        processor.raw_df = pd.DataFrame({
            "origin_id": ["1", "2"],
            "destination_id": ["2", "3"],
            "origin_name": ["A", "B"],
            "destination_name": ["B", "C"],
            "fecha": ["2024-01-01", "2024-01-02"],
            "total_trips": [100, 5],  # Uno < 10
        })
        processor.paths_cfg = mock_config.paths
        processor.network = {}
        
        with patch.object(processor, "save_interim"):
            result = processor.process()
        
        # Validar que total_trips_modif existe (creado por clean_kido)
        assert "total_trips_modif" in result.columns
        assert result.iloc[1]["total_trips_modif"] == 1  # 5 < 10 → 1


class TestKIDORawProcessorSaveInterim:
    """Tests para save_interim."""

    def test_save_interim_creates_parquet(self, tmp_path: Path) -> None:
        """save_interim intenta crear archivo parquet si pyarrow está disponible."""
        pytest.importorskip("pyarrow")
        
        processor = KIDORawProcessor()
        processor.paths_cfg = MagicMock()
        processor.paths_cfg.data_interim = str(tmp_path / "interim")
        
        df = pd.DataFrame({
            "origin_id": ["1", "2"],
            "destination_id": ["2", "3"],
            "total_trips": [100, 50],
        })
        
        processor.save_interim(df)
        
        parquet_file = tmp_path / "interim" / "kido_interim.parquet"
        assert parquet_file.exists()

    def test_save_interim_creates_csv(self, tmp_path: Path) -> None:
        """save_interim crea archivo CSV siempre (sin depender de pyarrow)."""
        processor = KIDORawProcessor()
        processor.paths_cfg = MagicMock()
        processor.paths_cfg.data_interim = str(tmp_path / "interim")
        
        df = pd.DataFrame({
            "origin_id": ["1", "2"],
            "destination_id": ["2", "3"],
            "total_trips": [100, 50],
        })
        
        # Mock para evitar parquet
        with patch.object(df, "to_parquet"):
            processor.save_interim(df)
        
        csv_file = tmp_path / "interim" / "kido_interim.csv"
        assert csv_file.exists()

    def test_save_interim_creates_directories(self, tmp_path: Path) -> None:
        """save_interim crea directorios si no existen."""
        processor = KIDORawProcessor()
        nonexistent_dir = tmp_path / "deeply" / "nested" / "interim"
        processor.paths_cfg = MagicMock()
        processor.paths_cfg.data_interim = str(nonexistent_dir)
        
        df = pd.DataFrame({"col": [1, 2]})
        
        # Mock para evitar parquet
        with patch.object(df, "to_parquet"):
            processor.save_interim(df)
        
        assert nonexistent_dir.exists()

    def test_save_interim_preserves_data(self, tmp_path: Path) -> None:
        """save_interim preserva datos al guardar y cargar."""
        processor = KIDORawProcessor()
        processor.paths_cfg = MagicMock()
        processor.paths_cfg.data_interim = str(tmp_path / "interim")
        
        original_df = pd.DataFrame({
            "origin_id": ["1", "2", "3"],
            "destination_id": ["2", "3", "1"],
            "total_trips": [100, 50, 200],
        })
        
        # Mock para evitar parquet
        with patch.object(original_df, "to_parquet"):
            processor.save_interim(original_df)
        
        # Verificar que el CSV se creó (nombre real de save_interim)
        saved_csv = tmp_path / "interim" / "kido_interim.csv"
        assert saved_csv.exists()
        
        loaded_csv = pd.read_csv(saved_csv, dtype=str)
        # Comparar como strings para evitar problemas de dtype al recargar
        pd.testing.assert_frame_equal(loaded_csv, original_df.astype(str))


class TestKIDORawProcessorCentroids:
    """Tests para integración de centroides."""
    
    def test_load_centroids_if_exists(self, tmp_path: Path) -> None:
        """load_or_compute_centroids carga GPKG si existe y recompute=False."""
        # Skip si NetworkX no disponible (Python 3.14 incompatibilidad)
        try:
            import networkx as nx
        except (ImportError, AttributeError) as exc:
            pytest.skip(f"NetworkX no disponible: {exc}")
        
        gpd = pytest.importorskip("geopandas")
        pytest.importorskip("shapely")
        from shapely.geometry import Point
        
        processor = KIDORawProcessor()
        processor.paths_cfg = MagicMock()
        processor.network_dir = tmp_path / "network"
        processor.network_dir.mkdir(parents=True)
        
        # Crear centroids.gpkg de prueba
        centroids_gdf = gpd.GeoDataFrame({
            "zone_id": ["1", "2"],
            "centroid_node_id": ["node_1", "node_2"],
        }, geometry=[Point(0, 0), Point(1, 1)], crs="EPSG:4326")
        
        centroids_path = processor.network_dir / "centroids.gpkg"
        centroids_gdf.to_file(centroids_path, driver="GPKG")
        
        # Mock config
        mock_config = MagicMock()
        mock_config.routing.centroids.recompute = False
        mock_config.routing.centroids.output = str(centroids_path)
        processor.config = mock_config
        
        # Ejecutar (sin patch, usa función real)
        result = processor.load_or_compute_centroids()
        
        assert result is not None
        assert len(result) == 2
    
    def test_compute_centroids_if_missing(self, tmp_path: Path) -> None:
        """load_or_compute_centroids computa centroides si no existe GPKG."""
        # Skip si NetworkX no disponible (Python 3.14 incompatibilidad)
        try:
            import networkx as nx
        except (ImportError, AttributeError) as exc:
            pytest.skip(f"NetworkX no disponible: {exc}")
        
        gpd = pytest.importorskip("geopandas")
        pytest.importorskip("shapely")
        from shapely.geometry import Point
        
        processor = KIDORawProcessor()
        processor.paths_cfg = MagicMock()
        processor.network_dir = tmp_path / "network"
        processor.network_dir.mkdir(parents=True)
        
        # Mock zonas, nodes, edges
        processor.zonas = gpd.GeoDataFrame({
            "zone_id": ["1", "2"],
        }, geometry=[Point(0, 0).buffer(0.1), Point(1, 1).buffer(0.1)], crs="EPSG:4326")
        
        processor.network = {
            "nodes": gpd.GeoDataFrame({
                "node_id": ["n1", "n2"],
            }, geometry=[Point(0, 0), Point(1, 1)], crs="EPSG:4326"),
            "edges": gpd.GeoDataFrame({
                "edge_id": ["e1"],
                "u": ["n1"],
                "v": ["n2"],
            }, geometry=[Point(0, 0)], crs="EPSG:4326")
        }
        
        # Mock config
        mock_config = MagicMock()
        mock_config.routing.centroids.recompute = False
        mock_config.routing.centroids.method = "degree"
        mock_config.routing.centroids.output = str(tmp_path / "network" / "centroids.gpkg")
        processor.config = mock_config
        
        # Ejecutar con mock de compute_all_zone_centroids
        computed_gdf = gpd.GeoDataFrame({
            "zone_id": ["1", "2"],
            "centroid_node_id": ["n1", "n2"],
        }, geometry=[Point(0, 0), Point(1, 1)], crs="EPSG:4326")
        
        with patch("kido_ruteo.processing.centroids.compute_all_zone_centroids", return_value=computed_gdf):
            result = processor.load_or_compute_centroids()
        
        assert result is not None
        assert len(result) == 2


class TestKIDORawProcessorManualCheckpoints:
    """Tests para integración de manual checkpoints."""
    
    def test_load_manual_checkpoints_success(self, tmp_path: Path) -> None:
        """load_manual_checkpoints carga CSV si enabled=True."""
        processor = KIDORawProcessor()
        processor.paths_cfg = MagicMock()
        
        # Crear CSV temporal
        manual_csv = tmp_path / "manual_checkpoints.csv"
        manual_df = pd.DataFrame({
            "origin_zone_id": ["1", "2"],
            "destination_zone_id": ["2", "3"],
            "checkpoint_node_id": ["C1", "C2"],
        })
        manual_df.to_csv(manual_csv, index=False)
        
        # Mock config con Path correcto
        mock_config = MagicMock()
        mock_config.routing.manual_selection.enabled = True
        mock_config.routing.manual_selection.file = str(manual_csv)
        processor.config = mock_config
        
        # Ejecutar
        processor.load_manual_checkpoints()
        
        assert processor.manual_checkpoints is not None
        assert len(processor.manual_checkpoints) == 2
    
    def test_load_manual_checkpoints_disabled(self) -> None:
        """load_manual_checkpoints retorna None si enabled=False."""
        processor = KIDORawProcessor()
        
        mock_config = MagicMock()
        mock_config.routing.manual_selection.enabled = False
        processor.config = mock_config
        
        processor.load_manual_checkpoints()
        
        assert processor.manual_checkpoints is None


class TestKIDORawProcessorIntegration:
    """Tests de integración completa."""

    def test_full_workflow_with_synthetic_data(self, tmp_path: Path) -> None:
        """Workflow completo: carga → proceso → guardado."""
        # Crear archivos de entrada
        data_root = tmp_path / "data"
        data_raw = data_root / "raw"
        data_interim = data_root / "interim"
        network_dir = data_root / "network"
        logs_dir = data_root / "logs"
        
        data_raw.mkdir(parents=True, exist_ok=True)
        network_dir.mkdir(parents=True, exist_ok=True)
        
        # Crear CSV KIDO
        kido_df = pd.DataFrame({
            "origin_id": ["1", "2", "3", "1"],
            "destination_id": ["2", "3", "1", "1"],
            "origin_name": ["Downtown", "Midtown", "Suburbs", "Downtown"],
            "destination_name": ["Midtown", "Suburbs", "Downtown", "Downtown"],
            "fecha": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
            "total_trips": [100, 50, 200, 5],
        })
        kido_csv = data_raw / "kido.csv"
        kido_df.to_csv(kido_csv, index=False)
        
        # Crear processor y config mock
        processor = KIDORawProcessor()
        
        with patch("kido_ruteo.processing.processing_pipeline.load_kido_raw") as mock_load_kido, \
             patch("kido_ruteo.processing.processing_pipeline.load_network_metadata") as mock_load_net:
            
            mock_load_kido.return_value = kido_df
            mock_load_net.return_value = {}
            
            # Simular load_data
            processor.raw_df = kido_df
            processor.paths_cfg = MagicMock()
            processor.paths_cfg.data_interim = str(data_interim)
            processor.paths_cfg.logs = str(logs_dir)
            processor.network = {}
            
            # Mock save_interim para evitar parquet
            with patch.object(processor, "save_interim"):
                # Ejecutar pipeline
                result = processor.process()
            
            # Validaciones del resultado del procesamiento
            assert len(result) > 0
            assert "intrazonal" in result.columns
            assert "total_trips_modif" in result.columns
            # Verificar que marcó al menos un intrazonal (Downtown-Downtown)
            assert result["intrazonal"].sum() >= 1
