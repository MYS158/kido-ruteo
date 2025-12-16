# KIDO Business Rules (Single Source of Truth)

## 1. Checkpoint semantics
- A checkpoint is NOT inferred.
- A checkpoint is NOT spatially selected.
- A checkpoint comes from the OD input file.
- Each OD row is already observed at that checkpoint.

## 2. Sense (cardinality)
- sense_code comes from catalogs/sense_cardinality.csv
- sense_code == 0 means INVALID SENSE.
- Invalid sense implies:
  - id_potential = 0
  - congruence_id = 4 (Impossible)
  - No routing relevance
  - No capacity usage

## 3. Capacity usage
- Capacity is defined at (checkpoint_id, sense_code) level.
- Capacity is NEVER OD-specific.
- If no capacity match exists → E2 = 0.

## 4. Trip calculation
- Trips are calculated ONLY if id_potential == 1.
- Categories are fixed:
  veh_auto, veh_moto, veh_bus, veh_cu, veh_cai, veh_caii
- No aggregated or invented categories are allowed.

## 5. Congruence levels
1 - Extremely possible
2 - Possible
3 - Unlikely
4 - Impossible
