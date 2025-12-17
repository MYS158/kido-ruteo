# RESUMEN DE CORRECCIONES - STRICT MODE V2.0

## 📋 CAMBIOS REALIZADOS

Se corrigió el código para que coincida **exactamente** con la guía detallada de creación de archivos de salida, implementando STRICT MODE sin desviaciones.

---

## ✅ ARCHIVOS MODIFICADOS

### 1. **src/kido_ruteo/trips/calculation.py**
**Cambios críticos:**
- ❌ Eliminado: Shares, Focup, FA (Factor de Ajuste)
- ✅ Implementado: Ocupación fija por categoría
  - AU (Auto): 1.5 personas/vehículo
  - CU (Camioneta Utilitaria): 2.5 personas/vehículo
  - CAI (Camión Articulado I): 12.0 personas/vehículo
  - CAII (Camión Articulado II): 25.0 personas/vehículo

**Fórmula nueva:**
```python
veh_X = (trips_person / ocupacion_X) × intrazonal_factor
```

**Regla STRICT:**
- Si `cap_total` es NaN → TODOS los `veh_*` = NaN (NUNCA 0)
- `veh_total` = suma SOLO si todas las categorías son válidas
- Si alguna categoría es NaN → `veh_total` = NaN

**Eliminado:**
- ❌ veh_moto
- ❌ veh_bus
- ❌ Lógica de shares (cap_X / TOTAL)
- ❌ Lógica de focup (factores de ocupación por aforo)
- ❌ capacity_fa (Factor de Ajuste)

---

### 2. **src/kido_ruteo/capacity/matcher.py**
**Cambios críticos:**
- ✅ Match EXACTO: `(checkpoint_id, sense_code)` con `(Checkpoint, Sentido)`
- ❌ Eliminado: Fallback a sentido '0'
- ❌ Eliminado: Agregación de capacidades
- ❌ Eliminado: cap_available, sense_valid (banderas auxiliares)

**Columnas de capacity usadas:**
```python
# De summary_capacity.csv:
'A' → cap_au      # Autos
'CU' → cap_cu     # Camioneta Utilitaria
'CAI' → cap_cai   # Camión Articulado I
'CAII' → cap_caii # Camión Articulado II
```

**Cálculo de cap_total:**
```python
cap_total = cap_au + cap_cu + cap_cai + cap_caii
# Si todas son NaN → cap_total = NaN
```

**Regla STRICT:**
- Si no hay match exacto → `cap_au`, `cap_cu`, `cap_cai`, `cap_caii`, `cap_total` = NaN
- NUNCA se usa sentido '0' como fallback
- NUNCA se agregan múltiples sentidos

---

### 3. **src/kido_ruteo/routing/constrained_path.py**
**Cambios críticos:**
- ✅ `sense_code` se deriva EXCLUSIVAMENTE de la geometría de la ruta MC2
- ✅ Formato: "origen-destino" (ej: "1-3", "4-2")
- ✅ Cardinalidad: 1=Norte, 2=Este, 3=Sur, 4=Oeste

**Proceso de derivación:**
```python
1. Calcular bearings en el checkpoint:
   - Bearing de entrada (nodo anterior → checkpoint)
   - Bearing de salida (checkpoint → nodo siguiente)

2. Mapear bearings a cardinalidad:
   - 0-45° y 315-360° → 1 (Norte)
   - 45-135° → 2 (Este)
   - 135-225° → 3 (Sur)
   - 225-315° → 4 (Oeste)

3. Formar código: f"{origen_card}-{dest_card}"
   Ejemplo: "1-3" = Viene del Norte, va al Sur
```

**Regla STRICT:**
- NUNCA se lee `sense_code` del input
- Si no hay ruta MC2 válida → `sense_code` = None
- El código resultante ES el `sense_code` (sin lookup adicional)

---

### 4. **src/kido_ruteo/pipeline.py**
**Cambios críticos:**
- ✅ Agregado: `import numpy as np`
- ✅ Salida con EXACTAMENTE 7 columnas:
  1. `Origen`
  2. `Destino`
  3. `veh_AU`
  4. `veh_CU`
  5. `veh_CAI`
  6. `veh_CAII`
  7. `veh_total`

**Columnas eliminadas de la salida:**
- ❌ veh_bus
- ❌ veh_moto
- ❌ Todas las columnas intermedias (sense_code, checkpoint_id, cap_*, congruence_*, mc2_*, etc.)

---

### 5. **tests/test_strict_mode_v2.py** (NUEVO)
**Tests implementados:**

✅ **test_rule1_input_cannot_define_sense**
- Valida que columnas 'sentido', 'sense', 'sense_code' se eliminan del input

✅ **test_rule2_sense_only_from_geometry**
- Valida que sin ruta geométrica no hay sense_code válido

✅ **test_rule3_no_fallback_to_sentido_0**
- Valida que sense_code='0' NO hace match → cap_total = NaN

✅ **test_rule4_no_exact_match_means_nan**
- Valida que sin match exacto → todos veh_* = NaN

✅ **test_rule5_output_exactly_7_columns**
- Valida que la salida tiene EXACTAMENTE las 7 columnas especificadas

✅ **test_rule6_veh_total_nan_if_all_categories_nan**
- Valida que veh_total = NaN si todas las categorías son NaN

✅ **test_vehicle_calculation_with_capacity**
- Valida fórmulas de cálculo con ocupación fija

✅ **test_intrazonal_factor_zeros_vehicles**
- Valida que intrazonal_factor=0 anula viajes

✅ **test_exact_match_checkpoint_and_sense**
- Valida que el match es EXACTO por (checkpoint_id, sense_code)

**Resultado:** ✅ 9/9 tests pasando

---

## 🎯 VALIDACIÓN DE CUMPLIMIENTO

### Regla 1: Sentido NO se lee del input
✅ `normalize_column_names()` elimina columnas 'sentido', 'sense', 'sense_code'
✅ Test: `test_rule1_input_cannot_define_sense` - PASA

### Regla 2: Sentido SOLO desde geometría
✅ `derive_sense_from_path()` calcula desde bearings en MC2
✅ Test: `test_rule2_sense_only_from_geometry` - PASA

### Regla 3: NO fallback a sentido 0
✅ `match_capacity_to_od()` NO agrega filas, NO busca sentido '0'
✅ Test: `test_rule3_no_fallback_to_sentido_0` - PASA

### Regla 4: Sin match exacto → veh_* = NaN
✅ `calculate_vehicle_trips()` propaga NaN correctamente
✅ Test: `test_rule4_no_exact_match_means_nan` - PASA

### Regla 5: Output de 7 columnas
✅ `pipeline.py` extrae exactamente: Origen, Destino, veh_AU, veh_CU, veh_CAI, veh_CAII, veh_total
✅ Test: `test_rule5_output_exactly_7_columns` - PASA

### Regla 6: veh_total = NaN si todas categorías NaN
✅ `calculate_vehicle_trips()` verifica que todas sean válidas antes de sumar
✅ Test: `test_rule6_veh_total_nan_if_all_categories_nan` - PASA

---

## 📊 COMPARACIÓN ANTES/DESPUÉS

### ANTES (versión anterior)
```python
# Capacidad con shares y focup
share_auto = cap_auto / cap_total
trips_adjusted = trips_person * FA
veh_auto = (trips_adjusted * share_auto) / focup_auto

# Fallback a sentido 0
if sense_code not in capacity:
    use sense_code = '0'

# Salida con 9+ columnas
veh_moto, veh_auto, veh_bus, veh_cu, veh_cai, veh_caii, ...
```

### DESPUÉS (STRICT MODE V2.0)
```python
# Ocupación fija
veh_auto = (trips_person / 1.5) * intrazonal_factor

# Sin fallback
if sense_code not in capacity:
    cap_total = NaN → veh_* = NaN

# Salida con EXACTAMENTE 7 columnas
Origen, Destino, veh_AU, veh_CU, veh_CAI, veh_CAII, veh_total
```

---

## 🔍 EJEMPLO DE FLUJO COMPLETO

### Input: checkpoint2002.csv
```csv
origin,destination,total_trips
1001,1002,250
1002,1001,<10
```

### Paso 1: Preprocessing
```python
trips_person = 250  # (de 250)
trips_person = 1    # (de "<10")
intrazonal_factor = 1  # (origen ≠ destino)
```

### Paso 2-4: Routing y Sentido
```python
# Calcular MC2: origen → checkpoint → destino
mc2_path = [nodo_A, checkpoint_node, nodo_B]

# Derivar sentido geométricamente
bearing_in = 80°   # Norte
bearing_out = 85°  # Norte
sense_code = "1-3" # Norte → Sur
```

### Paso 5: Capacidad
```python
# Match EXACTO (checkpoint='2002', sense='1-3')
cap_au = 1200
cap_cu = 300
cap_cai = 150
cap_caii = 50
cap_total = 1700  # suma
```

### Paso 7: Viajes Vehiculares
```python
# Fila 1 (trips_person=250)
veh_AU = 250 / 1.5 × 1 = 166.67
veh_CU = 250 / 2.5 × 1 = 100.00
veh_CAI = 250 / 12.0 × 1 = 20.83
veh_CAII = 250 / 25.0 × 1 = 10.00
veh_total = 166.67 + 100 + 20.83 + 10 = 297.50

# Fila 2 (trips_person=1, "<10")
veh_AU = 1 / 1.5 × 1 = 0.67
veh_CU = 1 / 2.5 × 1 = 0.40
veh_CAI = 1 / 12.0 × 1 = 0.08
veh_CAII = 1 / 25.0 × 1 = 0.04
veh_total = 0.67 + 0.40 + 0.08 + 0.04 = 1.19
```

### Output: processed_checkpoint2002.csv
```csv
Origen,Destino,veh_AU,veh_CU,veh_CAI,veh_CAII,veh_total
1001,1002,166.67,100.00,20.83,10.00,297.50
1002,1001,0.67,0.40,0.08,0.04,1.19
```

---

## ⚠️ NOTA IMPORTANTE

El pipeline ahora está **completamente alineado** con la guía detallada. Sin embargo, debido al problema geográfico identificado (checkpoints a 40-150 km de la red), **todos los resultados actuales serán NaN** porque:

1. ❌ No hay rutas MC2 válidas (distancias irreales)
2. ❌ No se puede derivar `sense_code` (sin geometría válida)
3. ❌ Sin `sense_code` → sin match de capacidad
4. ❌ Sin capacidad → `veh_*` = NaN

**Solución requerida:** Obtener red vial que cubra geográficamente los checkpoints, O checkpoints ubicados dentro del área de la red actual.

---

## ✨ CONCLUSIÓN

✅ **Código corregido al 100%** según especificación STRICT MODE  
✅ **Tests implementados y pasando** (9/9)  
✅ **Sin lógica adicional** - implementación exacta de la guía  
✅ **Sin simplificaciones** - todos los pasos preservados  
✅ **Sin "mejoras"** - comportamiento contractual respetado  

El pipeline ahora produce **exactamente** lo especificado en la guía detallada.
