# KIDO Data Contract

The output CSV MUST contain AT LEAST the following columns. If a column exists, it must be explainable by a business rule.

| Column | Description | Source/Rule |
|--------|-------------|-------------|
| origin_id | Origin Zone ID | Input OD |
| destination_id | Destination Zone ID | Input OD |
| checkpoint_id | Checkpoint ID (Identity) | Input Filename (Immutable) |
| sense_code | Direction Code | Input OD or Mapping |
| trips_person | Person Trips | Input OD (Cleaned) |
| mc_distance_m | Free Flow Distance (m) | Routing (Shortest Path) |
| mc2_distance_m | Constrained Distance (m) | Routing (Constrained Path) |
| e1_route_score | Route Feasibility Score | MC2 / MC |
| e2_capacity_score | Capacity Score | Demand / Capacity (Normalized) |
| id_potential | Potential Flag (0/1) | Rule: Sense Valid & E1>0 & E2>0 |
| congruence_id | Congruence Class (1-4) | Classification Rule |
| congruence_label | Congruence Label | 1:Extremely, 2:Possible, 3:Unlikely, 4:Impossible |
| veh_moto | Motorcycle Trips | Formula (only if potential=1) |
| veh_auto | Auto Trips | Formula (only if potential=1) |
| veh_bus | Bus Trips | Formula (only if potential=1) |
| veh_cu | Utility Vehicle Trips | Formula (only if potential=1) |
| veh_cai | Truck 2 Axle Trips | Formula (only if potential=1) |
| veh_caii | Truck 3+ Axle Trips | Formula (only if potential=1) |
| tpdm | Total Person Trips Daily | Aggregation |
| tpda | Total Person Trips Annual | Aggregation |
