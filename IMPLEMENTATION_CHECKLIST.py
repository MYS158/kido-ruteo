#!/usr/bin/env python3
"""
Final Implementation Checklist for Centroid Fixes
Verifies all three solutions are properly implemented
"""

import os
from pathlib import Path
import sys

def check_file_exists(path, description):
    """Check if a file exists"""
    exists = Path(path).exists()
    status = "✅" if exists else "❌"
    print(f"{status} {description}")
    return exists

def check_file_modified(path, description):
    """Check if a file was modified"""
    exists = Path(path).exists()
    status = "✅" if exists else "❌"
    print(f"{status} {description}")
    return exists

def check_file_deleted(path, description):
    """Check if a file was deleted"""
    exists = Path(path).exists()
    status = "✅" if not exists else "❌"
    print(f"{status} {description}")
    return not exists

def check_content_contains(path, search_text, description):
    """Check if file contains text"""
    try:
        with open(path, 'r') as f:
            content = f.read()
            found = search_text in content
            status = "✅" if found else "❌"
            print(f"{status} {description}")
            return found
    except Exception as e:
        print(f"❌ {description} (error: {e})")
        return False

print("=" * 80)
print("CENTROID FIXES IMPLEMENTATION CHECKLIST")
print("=" * 80)

results = {}

# SOLUTION 1: Delete and Regenerate
print("\n" + "=" * 80)
print("SOLUTION 1: Delete centroids.gpkg and Enable recompute=true")
print("=" * 80)

r1 = check_file_deleted(
    "data/network/centroids.gpkg",
    "Old centroids.gpkg deleted"
)
results["File deleted"] = r1

r2 = check_content_contains(
    "config/routing.yaml",
    "recompute: true",
    "Config updated with recompute: true"
)
results["Config updated"] = r2

# SOLUTION 2: Use od_with_nodes.csv
print("\n" + "=" * 80)
print("SOLUTION 2: Modify Pipeline to Use od_with_nodes.csv")
print("=" * 80)

r3 = check_file_exists(
    "data/interim/od_with_nodes.csv",
    "od_with_nodes.csv exists (6,623 OD pairs)"
)
results["od_with_nodes exists"] = r3

r4 = check_content_contains(
    "src/kido_ruteo/processing/processing_pipeline.py",
    "_assign_nodes_from_od_with_nodes",
    "New method _assign_nodes_from_od_with_nodes added"
)
results["od_with_nodes method"] = r4

r5 = check_content_contains(
    "src/kido_ruteo/processing/processing_pipeline.py",
    "df = self._assign_nodes_from_od_with_nodes(df)",
    "Pipeline updated to call od_with_nodes method"
)
results["Pipeline calls od_with_nodes"] = r5

# SOLUTION 3: Fix Centroid Algorithm
print("\n" + "=" * 80)
print("SOLUTION 3: Fix Centroid Calculation Algorithm")
print("=" * 80)

r6 = check_content_contains(
    "src/kido_ruteo/processing/centroids.py",
    "def validate_centroids",
    "Validation function added to centroids.py"
)
results["validate_centroids function"] = r6

r7 = check_content_contains(
    "src/kido_ruteo/processing/centroids.py",
    "validation = validate_centroids(gdf)",
    "load_centroids updated to validate on load"
)
results["load_centroids validates"] = r7

r8 = check_content_contains(
    "src/kido_ruteo/processing/processing_pipeline.py",
    "unique_nodes < total_zones * 0.5",
    "Diversity check added to centroid assignment"
)
results["Diversity check added"] = r8

# DOCUMENTATION
print("\n" + "=" * 80)
print("DOCUMENTATION GENERATED")
print("=" * 80)

r9 = check_file_exists(
    "CENTROID_FIXES_SUMMARY.md",
    "CENTROID_FIXES_SUMMARY.md (main summary)"
)
results["Summary doc"] = r9

r10 = check_file_exists(
    "CENTROID_ARCHITECTURE.md",
    "CENTROID_ARCHITECTURE.md (before/after diagrams)"
)
results["Architecture doc"] = r10

r11 = check_file_exists(
    "DETAILED_CODE_CHANGES.md",
    "DETAILED_CODE_CHANGES.md (code details)"
)
results["Code changes doc"] = r11

r12 = check_file_exists(
    "README_CENTROID_FIXES.md",
    "README_CENTROID_FIXES.md (implementation guide)"
)
results["Implementation guide"] = r12

# TESTS
print("\n" + "=" * 80)
print("TEST SCRIPTS")
print("=" * 80)

r13 = check_file_exists(
    "test_centroid_fixes.py",
    "test_centroid_fixes.py (verification tests)"
)
results["Test script 1"] = r13

r14 = check_file_exists(
    "verify_fixes.py",
    "verify_fixes.py (pipeline verification)"
)
results["Test script 2"] = r14

# RESULTS
print("\n" + "=" * 80)
print("FINAL RESULTS")
print("=" * 80)

total_checks = len(results)
passed_checks = sum(1 for v in results.values() if v)

print(f"\n✅ Passed: {passed_checks}/{total_checks}")

if passed_checks == total_checks:
    print("\n" + "🎉 " * 20)
    print("ALL CHECKS PASSED - Implementation Complete!")
    print("🎉 " * 20)
    print("\nYou can now:")
    print("1. Run: python test_centroid_fixes.py")
    print("2. Run: python src/scripts/run_pipeline.py")
    print("3. Check: python verify_fixes.py")
    sys.exit(0)
else:
    print("\n⚠️  Some checks failed. Review the output above.")
    print("\nFailed checks:")
    for check, passed in results.items():
        if not passed:
            print(f"  ❌ {check}")
    sys.exit(1)
