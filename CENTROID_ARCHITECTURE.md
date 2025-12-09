# Centroid System Architecture - Before vs After

## BEFORE (Broken)

```
OD Data (64,098 trips)
    ↓
Processing Pipeline
    ├─ Clean data
    └─ Assign nodes from centroids.gpkg  ← PROBLEM: ALL zones → node 144
    ↓
Processed Data: (27,913 trips)
    origin_node_id: ALL = 144.0
    destination_node_id: ALL = 144.0
    ↓
Routing Pipeline
    ├─ All routes: 144 → 144
    ├─ Distance: 0 km
    └─ Time: 0 min
    ↓
Routing Results: (12,711 routes)
    Every route: 144→144 (meaningless!)
    ↓
Validation Pipeline
    ├─ Try to merge routing × processed
    ├─ Cartesian product: 12,711 × 12,711 = 161 MILLION records
    └─ Memory explosion: 12 GB needed
    ↓
CRASH: "Unable to allocate 12.0 GiB"
```

## AFTER (Fixed)

```
OD Data (64,098 trips)
    ↓
Processing Pipeline
    ├─ Clean data
    ├─ PRIMARY: Assign nodes from od_with_nodes.csv ✓
    │   └─ 6,623 OD pairs → correct diverse nodes (63 origins, 58 dests)
    └─ FALLBACK: Assign nodes from centroids.gpkg (new)
        └─ Regenerated with recompute=true
            └─ Uses centrality algorithm (degree, betweenness, etc.)
            └─ Result: Each zone → its most central node
    ↓
Processed Data: (64,098 trips)
    origin_node_id: 63 unique nodes (diverse!)
    destination_node_id: 58 unique nodes (diverse!)
    ↓
Routing Pipeline
    ├─ Real routes: 46 → 64 → 104 (25.8 + 30.8 km)
    ├─ Real routes: 78 → 32 → 45 (15.2 + 20.1 km)
    ├─ Real routes: 154 → 84 → 45 (35.5 + 35.9 km)
    └─ 1,465 unique OD pairs routed
    ↓
Routing Results: (11,814 routes)
    Each route: Realistic paths with varying distance/time
    ↓
Validation Pipeline
    ├─ Merge routing × processed
    ├─ Safe merge: 11,814 × 11.5 ≈ 136,000 records
    └─ Memory: ~500 MB (no crash)
    ↓
SUCCESS: 136,324 validation records
    ✓ Full validation scores calculated
    ✓ Congruence levels assigned
    ✓ All metrics available
```

## Node Assignment Logic Flow

```
┌─────────────────────────────────────────────────────┐
│ Input: OD pair (origin_id=25, destination_id=100)  │
└─────────────────────────────────────────────────────┘
                      ↓
         ┌─────────────────────────────┐
         │ Try od_with_nodes.csv first │ (PRIMARY)
         └─────────────────────────────┘
                      ↓
        ┌──────────────────────────────┐
        │ Found in od_with_nodes.csv?  │
        └──────────────────────────────┘
              ↙              ↘
            YES              NO
             ↓                ↓
       ┌─────────┐    ┌──────────────────┐
       │Found:   │    │ Try centroids.gpk│
       │origin→78│    └──────────────────┘
       │dest→154 │           ↓
       └─────────┘    ┌─────────────────┐
             ↓        │Validate diversity│
      ✓ASSIGN         └─────────────────┘
                            ↓
                    ┌──────────────────┐
                    │Valid (>30% unique)
                    └──────────────────┘
                            ↓
                    ┌──────────────────┐
                    │origin→zone25_node│
                    │dest→zone100_node │
                    └──────────────────┘
                            ↓
                      ✓ASSIGN
                            ↓
           ┌─────────────────────────────┐
           │Output: Routable OD pair     │
           │(origin_node_id=78,          │
           │ destination_node_id=154)    │
           └─────────────────────────────┘
```

## Centroid Calculation (When Regenerated)

```
For each zone (e.g., zone_id=25):
    1. Find all nodes within zone polygon
    2. Find all edges intersecting zone
    3. Build subgraph from zone nodes/edges
    4. Calculate node centrality using:
       - degree: How many neighbors each node has
       - betweenness: How often each node is on shortest paths
       - closeness: How central each node is in distance
       - eigenvector: How connected to other central nodes
    5. Select node with highest centrality
    6. Return: zone_id → centroid_node_id mapping

Example:
    Zone 25: nodes = [11, 45, 67, 89, 112]
    Edges: 11-45, 45-67, 67-89, 89-112
    Centrality scores: {11: 1.2, 45: 2.5, 67: 2.8, 89: 2.5, 112: 1.2}
    Highest: node 67 with score 2.8
    Result: Zone 25 → Centroid node 67 ✓
```

## Data Diversity Comparison

### BEFORE (Broken)
```
centroids.gpkg content:
Zone 1    → Node 144
Zone 2    → Node 144
Zone 3    → Node 144
...
Zone 154  → Node 144

Diversity: 1 unique node for 154 zones = 0.65%
Result: All OD pairs → node 144→144
```

### AFTER (Fixed via od_with_nodes.csv)
```
od_with_nodes.csv content:
Zone 1   + Zone 2   → Nodes 78 → 154
Zone 1   + Zone 3   → Nodes 78 → 72
Zone 2   + Zone 4   → Nodes 154 → 46
...
Unique origins: 63 nodes
Unique destinations: 58 nodes

Diversity: 63×58 = 3,654 possible pairs
Result: Real routes with realistic distances/times
```

## File Dependencies

```
Pipeline Execution:
    ↓
config/routing.yaml
    ├─ routing.centroids.recompute = true  ← Forces regeneration
    └─ routing.centroids.output = data/network/centroids.gpkg
         ↓
    Processing Pipeline loads:
         ├─ data/interim/od_with_nodes.csv       (PRIMARY SOURCE)
         │  └─ 6,623 OD → correct node mappings
         └─ data/network/centroids.gpkg          (FALLBACK SOURCE)
            └─ Regenerated with diverse nodes (if od_with_nodes missing)
```

## Key Metrics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Unique origin nodes | 1 | 63 | +6,200% |
| Unique destination nodes | 1 | 58 | +5,700% |
| Unique OD pairs | 1 | 1,465 | +146,400% |
| Route diversity | 0% | 100% | ✓ |
| Validation records | 0 (crashed) | 136,324 | ✓ |
| Memory usage | 12 GB (crash) | ~500 MB | -95% |
| Pipeline status | ❌ FAILED | ✅ SUCCESS | ✓ |

---

**Implementation Date**: 2025-12-08  
**Status**: ✅ All three solutions implemented and tested
