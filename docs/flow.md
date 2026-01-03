# FLOW.md — Flujo Normativo KIDO‑Ruteo (Versión Actualizada)

> **Principio rector:** el pipeline debe reflejar la naturaleza real del aforo.
> El sentido **solo** se deriva cuando el aforo es direccional.
> Si el aforo es agregado (`Sentido = 0`), **no existe sentido geométrico operativo**.

---

## 1. Tipos de queries soportadas

### 1.1 Queries de checkpoint (`checkpointXXXX.csv`)
- Representan flujos OD que **cruzan un punto de control físico**.
- Pueden usar capacidad **agregada** o **direccional**, según el checkpoint.

### 1.2 Queries generales (`general.csv`)
- **No usan checkpoints**.
- **No calculan ruteo restringido (MC2)**.
- **No generan viajes vehiculares modelados**.
- La salida contractual fija todos los `veh_*` en **0**.

---

## 2. Ingesta OD (checkpoint queries)

1. Se lee el archivo `checkpointXXXX.csv`.
2. Si el input contiene columnas:
   - `sense`, `sentido`, `sense_code`, `direction`
   → **se eliminan inmediatamente**.
3. Normalización de columnas:
   - `origin` → `origin_id`
   - `destination` → `destination_id`
4. Inferencia de `checkpoint_id` a partir del nombre del archivo.

---

## 3. Preparación de viajes

### 3.1 Conversión a viajes de personas

- `<10` → `trips_person = 1`
- valores numéricos `< 10` → `1`
- `NaN` → `1`

### 3.2 Intrazonales

- Si `origin_id == destination_id`:
  - `intrazonal_factor = 1`
- En otro caso:
  - `intrazonal_factor = 0`

Interpretación normativa:
- `intrazonal_factor = 1` significa **intrazonal** ⇒ **0 viajes**.
- `intrazonal_factor = 0` significa **no intrazonal** ⇒ viajes normales.

---

## 4. Construcción geométrica

### 4.1 Red vial

- Se carga `red.geojson`.
- Se construye un **grafo dirigido** con pesos métricos.

### 4.2 Zonas

- Desde `zonification.geojson`:
  - Se filtran polígonos `poly_type = 'Core'`.
  - Cada zona se asigna al **nodo real más cercano** al centroide.

### 4.3 Checkpoints

- Desde `zonification.geojson`:
  - Se filtran polígonos `poly_type = 'Checkpoint'`.
  - Cada checkpoint se asigna al **nodo real más cercano** en la red.

---

## 5. Ruteo

### 5.1 MC — Camino mínimo libre

- Se calcula `MC = origin → destination`.
- Si no existe ruta:
  - el viaje queda **no viable**.

### 5.2 MC2 — Camino mínimo restringido (checkpoint)

- Se calcula `MC2 = origin → checkpoint → destination`.
- Si no existe MC2:
  - el viaje queda **no viable**.

---

## 6. Clasificación del checkpoint (PASO CLAVE)

A partir de `summary_capacity.csv`, para cada `checkpoint_id`:

- **Checkpoint direccional**
  - Existe al menos un registro con `Sentido != '0'`.

- **Checkpoint agregado**
  - **Todos** los registros tienen `Sentido = '0'`.

Esta clasificación gobierna **todo lo que sigue**.

---

## 7. Derivación de sentido

### 7.1 Checkpoint direccional

- Se deriva `sense_code` **geométricamente** a partir de la ruta MC2:
  - nodo anterior → checkpoint → nodo posterior
  - cálculo de bearings de entrada y salida
  - mapeo a cardinalidad
  - construcción del código (`"4-2"`, `"1-3"`, etc.)
- Se valida contra `sense_cardinality.csv`.
- Si no se puede derivar o validar:
  - `sense_code = NaN`.

### 7.2 Checkpoint agregado

- ❌ **NO se deriva sentido**.
- ❌ **NO se calculan bearings**.
- Se fija conceptualmente:
  - `sense_code = '0'`.

---

## 8. Capacidad (STRICT MODE)

### 8.1 Checkpoint direccional

- Merge exacto:
  ```python
  merge(
      left_on=['checkpoint_id', 'sense_code'],
      right_on=['Checkpoint', 'Sentido'],
      how='left',
      validate='many_to_one'
  )
  ```
- Si no hay match:
  - todas las capacidades → `NaN`.

### 8.2 Checkpoint agregado

- Merge exacto solo por:
  ```python
  left_on='checkpoint_id', right_on='Checkpoint'
  ```
- Se usa la fila con `Sentido = '0'`.

---

## 9. Congruencia

Se asigna `congruence_id = 4 (Impossible)` si ocurre cualquiera:

- No existe MC o MC2.
- Checkpoint direccional y `sense_code` es `NaN`.
- Cualquier capacidad requerida es `NaN`.
- `cap_total == 0`.

En caso contrario, se clasifica según scores internos.

---

## 10. Cálculo de viajes vehiculares

### 10.1 Condición de cálculo

Los viajes vehiculares **solo se calculan si**:

- `congruence_id != 4`
- `cap_total` existe y es `> 0`

Además:
- Si `intrazonal_factor == 1` (intrazonal), el resultado vehicular es **0**.

### 10.2 Fórmula general

Para cada categoría `k ∈ {M, A, B, CU, CAI, CAII}`:

```text
veh_k = (trips_person × (1 - intrazonal_factor) × FA × (cap_k / cap_total)) / Focup_k
```

### 10.3 Propagación estricta

- Si `congruence_id == 4` → **todos los `veh_*` = 0** y `veh_total = 0`.
- Si `cap_total` es `NaN` (caso no esperado si la congruencia se clasificó correctamente) → `veh_*` pueden quedar `NaN`.

---

## 11. Salida contractual (checkpoint)

El CSV final contiene **exactamente**:

```
Origen, Destino,
veh_M, veh_A, veh_B, veh_CU, veh_CAI, veh_CAII,
veh_total
```

- Sin columnas intermedias.
- Sin rutas, distancias, checkpoint_id ni sense_code.

---

## 12. Salida contractual (general)

Para queries generales:

- Todas las columnas `veh_* = 0`.
- `veh_total = 0`.

Esto es una **salida determinista**, no modelada.

---

## 13. Principios finales

1. El modelo **no inventa direcciones**.
2. La geometría **no contradice al aforo**.
3. Un aforo agregado se respeta como agregado.
4. Si el dato no existe, el resultado es `NaN`, no una aproximación.

---

**Este FLOW.md es normativo.**
Cualquier implementación que no lo siga es considerada incorrecta.

