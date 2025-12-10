# KIDO OD Routing & Congruence v2.0

**Sistema completo de ruteo y evaluación de congruencia para matrices Origen-Destino siguiendo metodología KIDO**

## 📋 Descripción

KIDO-Ruteo v2.0 implementa el flujo metodológico completo KIDO para:
- Procesar matrices OD desde múltiples fuentes
- Calcular rutas óptimas considerando checkpoints
- Evaluar congruencia de viajes mediante métricas específicas
- Generar matrices finales por tipología

## 🔵 FLUJO METODOLÓGICO KIDO

### 1. Preparación de Datos

**Entradas:**
- `red.geojson`: Red vial completa
- `zonificacion.geojson`: Polígonos de zonas (con `poly_type` para checkpoints)
- `extraccion.csv`: Matrices OD extraídas
- `cardinalidad.csv`: Sentidos viales

**Proceso:**
- Crear `total_trips_modif`:
  - Si `total_trips < 10`: `total_trips_modif = 1`
  - Si `total_trips >= 10`: `total_trips_modif = total_trips`
- Crear `intrazonal`:
  - Si `origin_name == destination_name`: `intrazonal = 1`
  - En otro caso: `intrazonal = 0`

**Salida:** `data/interim/od_preparado.csv`

### 2. Centralidad y Centroides

**Proceso:**
- Calcular centralidad de nodos de la red vial
- En cada zona, elegir como centroide el nodo con mayor centralidad
- Generar coordenadas: `x-o`, `y-o`, `x-d`, `y-d`

**Salida:** `data/interim/centroides.csv`

### 3. Congruencia Etapa 1 - Vectores de Acceso

**Proceso:**
- Generar `V1`: vector con todos los orígenes
- Generar `V2`: vector con todos los destinos
- Si la zona NO está en `V1` → `Congruencia = 4`, `id_potencial = 1`

**Salida:** `data/interim/access_vectors.csv`

### 4. Validación KIDO vs Dato Vial

**Proceso:**
- Calcular `VolDV_personas = dato_vial × factor_ocupación` (por tipología A, B, C)
- Calcular `Factor = VolDV_personas / VolKIDO`
- Validación:
  - Si `0.95 < Factor < 1.05` → Válido
  - Si no → Consulta no confiable (preferir dato de campo)

**Salida:** `data/interim/validacion_vial.csv`

### 5. Matriz de Impedancia (MC)

**Proceso:**
- Generar matriz OD completa (todos los pares posibles)
- Atributos: tiempo, distancia, costo
- Algoritmo: **Shortest Path** (sin restricción de checkpoint)
- Crear identificador `zona_menor-zona_mayor`
- Identificar pares que cubren el 80% de viajes totales
- Exportar rutas nodo a nodo

**Salida:** 
- `data/processed/matriz_impedancia_mc.csv`
- `data/processed/rutas_mc.geojson`

### 6. Segunda Matriz de Impedancia (MC2)

**Proceso:**
- Algoritmo: **Constrained Shortest Path** o **K-Shortest Path**
- Restricción: Las rutas DEBEN pasar por el checkpoint

**Salida:** `data/processed/matriz_impedancia_mc2.csv`

### 7. Cálculo de Congruencia

**Fórmula:**
```
X = [(A-Checkpnt) + (Checkpnt-B)] / (A-B)
    Numerador: distancia de MC2
    Denominador: distancia de MC
```

**Reglas:**
- Si el viaje pasa por enlace del checkpoint → `Congruencia = 4`
- Si `-10% < X < 10%` → `Congruencia = 3`
- Si no cumple → `Congruencia = 4`

**Salida:** `data/processed/congruencia.csv`

### 8. Identificadores de Congruencia y Potencial

**Proceso:**
- Si `congruencia == 4` → `id_congruencia = 0`
- Si no → `id_congruencia = 1`
- `id_potencial` ya definido en Paso 3

**Salida:** Columnas añadidas a `congruencia.csv`

### 9. Cálculo de Viajes

**Fórmula:**
```
Viajes = id_congruencia × id_potencial × (1 - intrazonal) × total_trips_modif
```

**Salida:** `data/processed/viajes_final.csv`

### 10. Tablas Diarias

**Proceso:**
- Agregar columna `fecha`
- Calcular:
  - `tpdes`: Tráfico promedio día entre semana
  - `tpdfs`: Tráfico promedio día fin de semana
  - `tpds`: Tráfico promedio día sábado

**Salida:** `data/processed/tablas_diarias.csv`

### 11. Conversión a Viajes Vehículo

**Proceso:**
- Agregar dato vial por tipología A, B, C
- Multiplicar `dato_vial × factor_ocupación`
- Obtener `TPDA` (Tráfico Promedio Diario Anual)
- Comparar KIDO vs Vial: `E2/E1`

**Salida:** `data/processed/viajes_vehiculo.csv`

### 12. Exportar Matrices Finales por Tipología

**Salidas:**
- `data/processed/matriz_tipologia_A.csv`
- `data/processed/matriz_tipologia_B.csv`
- `data/processed/matriz_tipologia_C.csv`

## 🏗️ Estructura del Proyecto

```
kido-ruteo/
├── data/
│   ├── raw/              # Datos originales
│   ├── interim/          # Datos intermedios procesados
│   ├── processed/        # Resultados finales
│   └── external/         # Datos externos auxiliares
│
├── src/kido_ruteo/       # Paquete principal
│   ├── io.py             # Carga y escritura de datos
│   ├── preprocessing.py  # Paso 1: Preparación de datos
│   ├── centrality.py     # Paso 2: Cálculo de centralidad
│   ├── centroides.py     # Paso 2: Selección de centroides
│   ├── access_vectors.py # Paso 3: Vectores de acceso
│   ├── validation.py     # Paso 4: Validación KIDO vs Vial
│   ├── impedance.py      # Paso 5: Matriz MC (shortest path)
│   ├── constrained_paths.py # Paso 6: Matriz MC2 (constrained)
│   ├── congruence.py     # Paso 7-8: Cálculo de congruencia
│   ├── viajes.py         # Paso 9-12: Cálculo de viajes
│   └── utils/
│       ├── geo.py        # Utilidades geoespaciales
│       ├── network.py    # Utilidades de redes
│       └── math.py       # Utilidades matemáticas
│
├── scripts/              # Scripts ejecutables
│   ├── ingest.py         # Ingesta de datos desde kido-data2
│   ├── run_preprocessing.py    # Ejecutar Paso 1
│   ├── compute_centrality.py   # Ejecutar Paso 2
│   ├── compute_impedance.py    # Ejecutar Paso 5 (MC)
│   ├── compute_impedance2.py   # Ejecutar Paso 6 (MC2)
│   ├── compute_congruence.py   # Ejecutar Pasos 7-8
│   ├── compute_viajes.py       # Ejecutar Pasos 9-12
│   └── clean_branches.sh       # Limpieza de ramas Git
│
├── tests/                # Tests unitarios
│   └── test_placeholder.py
│
├── notebooks/            # Análisis exploratorio
│   └── exploracion.ipynb
│
├── README.md
├── requirements.txt
├── pyproject.toml
└── .gitignore
```

## 🚀 Instalación

### 1. Clonar repositorio
```bash
git clone https://github.com/MYS158/kido-ruteo.git
cd kido-ruteo
```

### 2. Crear entorno virtual
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
pip install -e .
```

## 📊 Uso

### Pipeline Completo

Ejecutar todos los pasos en secuencia:

```bash
# 1. Ingesta de datos
python scripts/ingest.py

# 2. Preparación de datos
python scripts/run_preprocessing.py

# 3. Cálculo de centralidad y centroides
python scripts/compute_centrality.py

# 4. Matrices de impedancia (MC y MC2)
python scripts/compute_impedance.py
python scripts/compute_impedance2.py

# 5. Cálculo de congruencia
python scripts/compute_congruence.py

# 6. Cálculo final de viajes y matrices
python scripts/compute_viajes.py
```

### Uso como Librería

```python
from kido_ruteo import preprocessing, centrality, congruence, viajes

# Cargar datos
df = preprocessing.load_od_data('data/raw/extraccion.csv')

# Preparar datos
df_prep = preprocessing.prepare_data(df)

# Calcular congruencia
df_cong = congruence.compute_congruence(df_prep, mc, mc2)

# Calcular viajes finales
df_viajes = viajes.compute_viajes(df_cong)
```

## 🧪 Testing

```bash
pytest tests/ -v
```

## 📚 Fuentes de Datos

El sistema espera datos en la estructura:

```
data/raw/kido-data2/
├── Consultas/
│   ├── General/*.csv
│   └── Checkpoint/*.csv
├── Geojson/
│   ├── red.geojson
│   └── zonificacion.geojson
└── Cardinalidad/
    └── cardinalidad.csv
```

## 📝 Metodología KIDO

Este proyecto implementa la metodología completa KIDO para:
- **Validación de datos OD** mediante comparación con datos viales
- **Cálculo de congruencia** usando métricas específicas (pasos por checkpoint)
- **Factorización de viajes** considerando intrazonal, potencial y congruencia
- **Generación de matrices** por tipología vehicular (A, B, C)

## 🤝 Contribución

1. Crear rama desde `main`
2. Seguir convenciones de código
3. Agregar tests para nuevas funcionalidades
4. Pull request con descripción detallada

## 📄 Licencia

MIT License

## 👥 Equipo

Proyecto KIDO - Análisis de Movilidad Urbana

---

**Versión**: 2.0.0  
**Última actualización**: Diciembre 2024  
**Rama**: `kido-v2`
