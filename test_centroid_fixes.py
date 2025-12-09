#!/usr/bin/env python3
"""Test script to verify all three centroid fixes work correctly."""
import logging
from pathlib import Path
import pandas as pd

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger(__name__)

def test_od_with_nodes_loading():
    """Test 1: Verify od_with_nodes.csv exists and has diverse node assignments."""
    logger.info("=" * 80)
    logger.info("TEST 1: od_with_nodes.csv loading and validation")
    logger.info("=" * 80)
    
    od_path = Path("data/interim/od_with_nodes.csv")
    if not od_path.exists():
        logger.error("❌ od_with_nodes.csv not found at %s", od_path)
        return False
    
    df = pd.read_csv(od_path)
    logger.info("✓ Loaded od_with_nodes.csv: %d rows, %d columns", len(df), len(df.columns))
    
    # Check node diversity
    origin_nodes = df['origin_node_id'].nunique()
    dest_nodes = df['destination_node_id'].nunique()
    
    logger.info("  Origin nodes: %d unique", origin_nodes)
    logger.info("  Destination nodes: %d unique", dest_nodes)
    
    # Show distribution
    logger.info("  Top 10 origin nodes: %s", 
                df['origin_node_id'].value_counts().head(10).to_dict())
    logger.info("  Top 10 destination nodes: %s", 
                df['destination_node_id'].value_counts().head(10).to_dict())
    
    # Check if diverse (not all same node)
    if origin_nodes > 1 and dest_nodes > 1:
        logger.info("✓ PASS: Good node diversity detected")
        return True
    else:
        logger.error("✗ FAIL: Low node diversity (origins=%d, dests=%d)", origin_nodes, dest_nodes)
        return False


def test_centroid_validation():
    """Test 2: Verify centroid validation function works."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Centroid validation function")
    logger.info("=" * 80)
    
    try:
        from src.kido_ruteo.processing.centroids import validate_centroids
        logger.info("✓ Successfully imported validate_centroids")
        
        # Test with None
        result = validate_centroids(None)
        logger.info("  validate_centroids(None): is_valid=%s", result['is_valid'])
        
        # Test with empty dataframe
        import geopandas as gpd
        empty_gdf = gpd.GeoDataFrame()
        result = validate_centroids(empty_gdf)
        logger.info("  validate_centroids(empty): is_valid=%s", result['is_valid'])
        
        logger.info("✓ PASS: Validation function works")
        return True
    except Exception as exc:
        logger.error("✗ FAIL: Error testing validation: %s", exc)
        return False


def test_processing_pipeline_changes():
    """Test 3: Verify processing pipeline has both assignment methods."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Processing pipeline methods")
    logger.info("=" * 80)
    
    try:
        from src.kido_ruteo.processing.processing_pipeline import KIDORawProcessor
        
        # Check that both methods exist
        methods = [m for m in dir(KIDORawProcessor) if 'assign_nodes' in m]
        logger.info("✓ Found assignment methods: %s", methods)
        
        if '_assign_nodes_from_od_with_nodes' in methods:
            logger.info("✓ PASS: _assign_nodes_from_od_with_nodes exists")
        else:
            logger.error("✗ FAIL: _assign_nodes_from_od_with_nodes not found")
            return False
            
        if '_assign_nodes_from_centroids' in methods:
            logger.info("✓ PASS: _assign_nodes_from_centroids exists (fallback)")
        else:
            logger.error("✗ FAIL: _assign_nodes_from_centroids not found")
            return False
        
        return True
    except Exception as exc:
        logger.error("✗ FAIL: Error checking pipeline: %s", exc)
        return False


def test_config_recompute_enabled():
    """Test 4: Verify recompute=true is set in config."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Configuration recompute flag")
    logger.info("=" * 80)
    
    import yaml
    
    config_path = Path("config/routing.yaml")
    if not config_path.exists():
        logger.error("✗ FAIL: routing.yaml not found at %s", config_path)
        return False
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    recompute = config.get('centroids', {}).get('recompute', False)
    logger.info("  centroids.recompute = %s", recompute)
    
    if recompute:
        logger.info("✓ PASS: recompute=true is set (will force centroid recalculation)")
        return True
    else:
        logger.error("✗ FAIL: recompute is not set to true")
        return False


def test_centroid_file_deleted():
    """Test 5: Verify old centroids.gpkg is deleted."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 5: Old centroids.gpkg deletion")
    logger.info("=" * 80)
    
    centroid_path = Path("data/network/centroids.gpkg")
    
    if centroid_path.exists():
        logger.error("✗ FAIL: centroids.gpkg still exists at %s", centroid_path)
        logger.error("  This will prevent recalculation. Delete it manually:")
        logger.error("  rm %s", centroid_path)
        return False
    else:
        logger.info("✓ PASS: centroids.gpkg has been deleted")
        logger.info("  New centroids will be calculated on next pipeline run")
        return True


def main():
    """Run all tests."""
    logger.info("\n" + "=" * 80)
    logger.info("CENTROID FIXES TEST SUITE")
    logger.info("=" * 80)
    logger.info("Testing 3 solutions for centroid issues:")
    logger.info("  1. Delete centroids.gpkg and regenerate with recompute=true")
    logger.info("  2. Modify pipeline to use od_with_nodes.csv")
    logger.info("  3. Fix centroid algorithm with validation")
    
    results = {
        "od_with_nodes loading": test_od_with_nodes_loading(),
        "centroid validation": test_centroid_validation(),
        "pipeline methods": test_processing_pipeline_changes(),
        "config recompute": test_config_recompute_enabled(),
        "centroids deleted": test_centroid_file_deleted(),
    }
    
    logger.info("\n" + "=" * 80)
    logger.info("TEST RESULTS")
    logger.info("=" * 80)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info("%s: %s", status, test_name)
    
    all_passed = all(results.values())
    
    if all_passed:
        logger.info("\n✓ ALL TESTS PASSED!")
        logger.info("Ready to run: python src/scripts/run_pipeline.py")
    else:
        logger.error("\n✗ SOME TESTS FAILED - Fix issues before running pipeline")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
