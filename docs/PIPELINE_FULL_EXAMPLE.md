# Ejemplo completo del pipeline (entrada → salida)

Este documento muestra un ejemplo **completo** del pipeline KIDO‑Ruteo para una **query de checkpoint direccional**, desde el CSV de entrada hasta el CSV contractual final.

> Nota: Este ejemplo usa números **sintéticos** (de juguete) para que el cálculo sea verificable a mano.
> La estructura/columnas y reglas siguen el flujo definido en [docs/FLOW.md](FLOW.md) y la implementación actual (módulos en `src/kido_ruteo`).

---

## 0) Escenario del ejemplo

- Tipo de query: `checkpointXXXX.csv`.
- Este documento incluye **dos mini‑ejemplos**:
  - **Ejemplo A (direccional):** usando `checkpoint2003.csv` (en `summary_capacity.csv` aparecen sentidos `4-2`, `2-4`).
  - **Ejemplo B (agregado):** usando `checkpoint2002.csv` (en `summary_capacity.csv` el `Sentido` es `0`).
- Se asume que existe ruta válida MC y MC2.

---

## 1) Entrada

### 1.1 Archivo OD de entrada (ejemplo genérico)

Ejemplo con **una fila**:

```csv
origin,destination,total_trips
1002,1001,250
```

Reglas relevantes:
- Si el input trajera columnas de sentido (`sense`, `sentido`, `sense_code`, `direction`), se eliminan inmediatamente.
- `origin`/`destination` se normalizan a `origin_id`/`destination_id`.

### 1.2 Capacidad (`data/raw/capacity/summary_capacity.csv`)

Para el **Ejemplo A (direccional)**, se asume que (tras agregación por loader) existe una fila como:

```csv
Checkpoint,Sentido,FA,M,A,B,CU,CAI,CAII,TOTAL,Focup_M,Focup_A,Focup_B,Focup_CU,Focup_CAI,Focup_CAII
2003,4-2,1.1,100,50,30,20,10,5,215,1.2,1.4,1.3,1.0,1.0,1.0
```

- `FA` y `Focup_*` se usan en el cálculo vehicular.
- `TOTAL` se reporta en capacidad, pero **el pipeline calcula `cap_total` como suma estricta** de `cap_M..cap_CAII` (si falta alguna categoría ⇒ `cap_total = NaN`).

Para el **Ejemplo B (agregado)**, en datos reales se observa algo como:

```csv
Checkpoint,Sentido,FA,M,A,B,CU,CAI,CAII,TOTAL,Focup_M,Focup_A,Focup_B,Focup_CU,Focup_CAI,Focup_CAII
2002,0,1.000,840,14905,265,2052,1220,23,19305,1.000,1.603,20.000,1.346,1.306,1.625
```

En este caso, el flujo normativo indica:
- **NO se deriva sentido geométrico**.
- Se fija `sense_code = '0'`.
- El match de capacidad es **solo por checkpoint**, usando la fila `Sentido='0'`.

---

## 2) Paso 1 — Normalización y preparación OD

Módulo: `src/kido_ruteo/processing/preprocessing.py`

### 2.1 Normalización (`normalize_column_names`)

Entrada:
- `origin`, `destination`, `total_trips`

Salida (nombres normalizados):
- `origin_id`, `destination_id`, `total_trips`

Además:
- Se infiere `checkpoint_id` desde el nombre del archivo (por ejemplo `"2003"` o `"2002"`).

### 2.2 Preparación (`prepare_data`)

- Conversión de `total_trips → trips_person`:
  - Si es `<10` ⇒ 1
  - Si es numérico y `< 10` ⇒ 1
  - Si es `NaN` ⇒ 1

En este ejemplo:
- `total_trips = 250` ⇒ `trips_person = 250`

- Factor intrazonal (`intrazonal_factor`):
  - Si `origin_id == destination_id` ⇒ 0
  - Si `origin_id != destination_id` ⇒ 1

En este ejemplo:
- `1002 != 1001` ⇒ `intrazonal_factor = 1`

Estado de la fila al final del Paso 1 (conceptual):

| origin_id | destination_id | checkpoint_id | trips_person | intrazonal_factor |
|---:|---:|---:|---:|---:|
| 1002 | 1001 | 2002 | 250 | 1 |

---

## 3) Paso 2 — Geometría (zonas y checkpoint → nodos de red)

Módulos:
- `src/kido_ruteo/routing/graph_loader.py` (carga de red)
- `src/kido_ruteo/processing/centroides.py` (zonas)
- `src/kido_ruteo/processing/checkpoint_loader.py` (checkpoints)

Resultado esperado (ejemplo simplificado):

| origin_node_id | destination_node_id | checkpoint_node_id |
|---|---|---|
| N_ORIG_1002 | N_DEST_1001 | N_CKP_2002 |

(Estos IDs son nodos reales del grafo; aquí se muestran como etiquetas.)

---

## 4) Paso 3 — Ruteo MC (camino mínimo libre)

Módulo: `src/kido_ruteo/routing/shortest_path.py` (`compute_mc_matrix`)

Se calcula la distancia del camino mínimo entre `origin_node_id → destination_node_id`.

Ejemplo:
- `mc_distance_m = 12000` (12 km)

> Si no existe ruta MC, el viaje se vuelve no viable más adelante.

---

## 5) Paso 4 — Ruteo MC2 + derivación de sentido

Módulo: `src/kido_ruteo/routing/constrained_path.py` (`compute_mc2_matrix`)

Se calcula:
- `MC2 = origin → checkpoint → destination`
- y se deriva `sense_code` **geométricamente** en el checkpoint:
  - se toma el nodo anterior y posterior al checkpoint dentro del path MC2
  - se calculan bearings entrada/salida
  - se mapean a cardinalidad (1=N, 2=E, 3=S, 4=W)
  - se construye `"<origen>-<destino>"` (ej: `"4-2"`)
  - se valida contra `data/catalogs/sense_cardinality.csv`

Ejemplo:
- `mc2_distance_m = 13000`
- `sense_code = "4-2"`

> Si no existe MC2 o no se puede derivar/validar el sentido ⇒ `sense_code = NaN`.

Además, el orquestador marca:

```text
has_valid_path = (mc_distance_m > 0) AND (mc2_distance_m > 0) AND mc2_distance_m notna
```

---

## 6) Paso 5 — Integración de capacidad

Módulos:
- `src/kido_ruteo/capacity/loader.py` (`load_capacity_data`)
- `src/kido_ruteo/capacity/matcher.py` (`match_capacity_to_od`)

### 6.1 Agregación (loader)

Se agrega `summary_capacity.csv` por `(Checkpoint, Sentido)`:
- capacidades (`M..CAII`, `TOTAL`) se **suman**
- `FA` se promedia
- `Focup_*` se calcula como promedio ponderado por la capacidad de su categoría

### 6.2 Match estricto (matcher)

Cruce **exacto**:
- `left_on=['checkpoint_id', 'sense_code']`
- `right_on=['Checkpoint', 'Sentido']`

Si hay match, se crean columnas internas:
- `fa`
- `cap_M, cap_A, cap_B, cap_CU, cap_CAI, cap_CAII`
- `focup_M, focup_A, focup_B, focup_CU, focup_CAI, focup_CAII`
- `cap_total = sum(cap_*)` pero **solo** si están las 6 categorías (si falta alguna ⇒ `NaN`)

En este ejemplo:
- `cap_total = 100 + 50 + 30 + 20 + 10 + 5 = 215`

---

## 7) Paso 6 — Congruencia (bloqueante)

Módulo: `src/kido_ruteo/congruence/classification.py` (`classify_congruence`)

En STRICT MODE, se marca `congruence_id = 4 (Impossible)` si ocurre cualquiera:
- ruta inválida (`has_valid_path = False`)
- `sense_code` inválido (`NaN`)
- capacidad inválida (`cap_total = NaN`) o `cap_total == 0`

En este ejemplo:
- hay MC y MC2
- `sense_code = "4-2"`
- `cap_total = 215 > 0`

⇒ `congruence_id = 1 (Valid)`

---

## 8) Paso 7 — Cálculo de viajes vehiculares

Módulo: `src/kido_ruteo/trips/calculation.py` (`calculate_vehicle_trips`)

### 8.1 Guard estricto

Solo se calculan `veh_*` si:

```text
cap_total notna AND cap_total > 0 AND congruence_id != 4
```

### 8.2 Fórmula

Para cada categoría `k ∈ {M, A, B, CU, CAI, CAII}`:

```text
veh_k = (trips_person × intrazonal_factor × fa × (cap_k / cap_total)) / focup_k
```

### 8.3 Cálculo numérico del ejemplo

Datos:
- `trips_person = 250`
- `intrazonal_factor = 1`
- `fa = 1.1`
- `cap_total = 215`
- Capacidades: M=100, A=50, B=30, CU=20, CAI=10, CAII=5
- Ocupaciones: focup_M=1.2, focup_A=1.4, focup_B=1.3, focup_CU=1.0, focup_CAI=1.0, focup_CAII=1.0

Resultados (aprox):

- `veh_M = 250 * 1 * 1.1 * (100/215) / 1.2 ≈ 106.589147`
- `veh_A = 250 * 1 * 1.1 * (50/215)  / 1.4 ≈ 45.681062`
- `veh_B = 250 * 1 * 1.1 * (30/215)  / 1.3 ≈ 29.517764`
- `veh_CU = 250 * 1 * 1.1 * (20/215) / 1.0 ≈ 25.581395`
- `veh_CAI = 250 * 1 * 1.1 * (10/215) / 1.0 ≈ 12.790698`
- `veh_CAII = 250 * 1 * 1.1 * (5/215) / 1.0 ≈ 6.395349`

`veh_total` se calcula **solo si** todas las categorías quedaron definidas (no `NaN`):

- `veh_total ≈ 226.555415`

---

## 9) Paso 8 — Salida contractual (CSV final)

Orquestador: `src/kido_ruteo/pipeline.py`

Se renombran columnas y se emite un CSV con exactamente:

```text
Origen, Destino,
veh_M, veh_A, veh_B, veh_CU, veh_CAI, veh_CAII,
veh_total
```

Ejemplo de salida (una fila):

```csv
Origen,Destino,veh_M,veh_A,veh_B,veh_CU,veh_CAI,veh_CAII,veh_total
1002,1001,106.589147,45.681062,29.517764,25.581395,12.790698,6.395349,226.555415
```

---

## 10) Notas rápidas para otros tipos de query

### 10.1 Query general (`general.csv`)

Según [docs/FLOW.md](FLOW.md) y `pipeline.py`:
- No calcula ruteo MC2 ni capacidad.
- Devuelve determinísticamente todos los `veh_* = 0` y `veh_total = 0`.

### 10.2 Checkpoint agregado (`Sentido = '0'`)

Normativamente (ver [docs/FLOW.md](FLOW.md)):
- no se deriva sentido geométrico
- `sense_code` se fija conceptualmente a `'0'`
- el merge de capacidad se hace solo por `Checkpoint` usando la fila `Sentido='0'`

Si quieres, puedo agregar un **segundo ejemplo completo** para este caso (con números) usando exactamente el formato anterior.
