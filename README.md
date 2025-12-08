# kido-ruteo
**kido-ruteo** es una implementación completa de un pipeline de procesamiento de datos,
ruteo y validación para flujos Origen–Destino (OD) generados por KIDO.  
Este proyecto es utilizado en consultoría de transporte y movilidad para:

- Depurar y estructurar viajes OD.
- Generar rutas basadas en redes viales (shortest path y constrained shortest path).
- Evaluar la congruencia de los viajes mediante reglas técnicas.
- Comparar el volumen KIDO contra el volumen vial real.
- Generar métricas finales como TPDS, TPDA y factores de validación.

El objetivo final es producir información confiable sobre patrones de viaje
a partir de datos KIDO enriquecidos con red vial y aforos.

---

## 📦 Estructura del proyecto

La arquitectura del repositorio sigue buenas prácticas de proyectos GIS + data engineering:
```
kido-ruteo/
├── data/
│   ├── raw/                     # Archivos originales (KIDO, cardinalidad, aforos, zonificación)
│   ├── interim/                 # Datos intermedios en procesos de limpieza
│   ├── processed/               # Outputs finales (viajes, matrices, TPDA)
│   └── network/                 # Red vial, nodos, centroides, geometrias
│
├── src/
│   ├── kido_ruteo/              # Paquete principal del proyecto
│   │   ├── init.py
│   │   ├── config/              # Lectura de YAML y parámetros
│   │   ├── utils/               # Funciones auxiliares (IO, geo, logging)
│   │   ├── processing/          # Limpieza OD, intrazonales, vector acceso
│   │   ├── routing/             # Ruteo (MC, MC2, shortest path)
│   │   ├── validation/          # Congruencias, puntuación, validación KIDO vs aforo
│   │   └── pipeline.py          # Pipeline principal que ejecuta todo el flujo
│   │
│   └── scripts/                 # Scripts CLI (ejecutables)
│       ├── run_pipeline.py
│       └── generate_matrices.py
│
├── notebooks/
│   ├── exploratory/             # Notebooks de análisis y depuración
│   └── reports/                 # Notebooks finales para entrega al cliente
│
├── tests/                       # Unit tests del paquete
│
├── docs/                        # Documentación (Markdown / Sphinx)
│   ├── api/
│   └── diagrams/
│
├── config/
│   ├── paths.yaml               # Rutas a archivos del proyecto
│   ├── routing.yaml             # Parámetros del ruteo (pesos, velocidad, algoritmos)
│   └── validation.yaml          # Umbrales y reglas de congruencias
│
├── requirements.txt
├── setup.py                     # Instalación con pip (opcional)
├── README.md
└── .gitignore
```

---

## 🚀 Pipeline del proyecto

El pipeline completo sigue esta secuencia:

### 1. **Carga de datos**  
- KIDO raw (viajes origen-destino)
- Red vial (nodos, arcos, geometrías)
- Zonas geográficas (polígonos)
- Cardinalidad (sentidos de vías)
- Aforos (factores de expansión)

### 2. **Procesamiento de OD (Fase B)**  
- **Limpieza de viajes**: Eliminar duplicados, normalizar tipos, validar columnas obligatorias
- **Cálculo de centroides por subred**: Los centroides **NO son geométricos**, se calculan por **centralidad de red** (degree, betweenness, closeness o eigenvector) dentro del subgrafo de cada zona
- **Asignación de nodos**: Cada viaje obtiene `origin_node_id` y `destination_node_id` desde los centroides calculados
- **Aplicación de `total_trips_modif`**: Viajes con `<10` se convierten a 1 para preservar privacidad
- **Detección intrazonal**: Identificar viajes donde origen == destino  
- **Vector de acceso**: Validación de zonas V1/V2  
- **Asignación de sentido**: Cardinalidad vial (dirección permitida)

### 3. **Generación de matrices de caminos**  
- **MC (Matriz de Caminos)**: shortest path entre todos los pares origen-destino  
- **Selección del 80% de viajes más representativos** para MC2
- **MC2 (Matriz con Checkpoint)**: rutas A→C→B que pasan obligatoriamente por un checkpoint
  - **Selección manual de checkpoints**: Si existe override en `manual_pair_checkpoints.csv`, se usa el checkpoint especificado
  - **Checkpoint automático**: Si no hay override manual, se usa el algoritmo de selección automática
  - **Metadata**: Se guarda `checkpoint_source` = "manual" o "auto" para auditoría

### 4. **Cálculo de congruencias**  
Se calcula el ratio **X = (A→C + C→B) / (A→B)**

Los viajes se clasifican según umbrales:
- **1 — Seguro**: X dentro del rango esperado (típicamente 90%-110%)
- **2 — Probable**: X con desviación moderada  
- **3 — Poco probable**: X con desviación significativa  
- **4 — Imposible**: X fuera de rangos razonables o sin ruta válida

Basado en:
- Map matching
- Desviación de tiempo/distancia
- Paso por checkpoint requerido
- Volumen KIDO vs volumen vial
- Consistencia de atributos

### 5. **Cálculo de métricas finales**  
- Viajes persona  
- Transformación a viajes vehículo (TPDA)  
- Factores de validación KIDO vs dato vial  
- Revisiones E1, E2 y confiabilidad final

### 6. **Exportación**  
- Tablas procesadas en `data/interim/` y `data/processed/`
- Matrices MC / MC2  
- GeoJSON de rutas  
- Resultados de congruencias
- Centroides calculados en `data/network/centroids.gpkg`

---

## 🎯 Centroides representativos por subred

Los centroides **NO se calculan como el centro geométrico** de cada zona. En su lugar, se usa **análisis de red** para identificar el nodo más representativo:

### Métodos de centralidad disponibles:
- **`degree`** (por defecto): Nodo con más conexiones en la zona
- **`betweenness`**: Nodo que aparece en más caminos mínimos (intermediario crítico)
- **`closeness`**: Nodo con menor distancia promedio al resto
- **`eigenvector`**: Nodo con vecinos importantes (influencia en la red)

### Configuración en `routing.yaml`:
```yaml
centroids:
  method: degree                      # degree | betweenness | closeness | eigenvector
  recompute: false                    # true = forzar recálculo aunque exista centroids.gpkg
  output: data/network/centroids.gpkg
```

### Proceso de cálculo:
1. Filtrar nodos dentro del polígono de la zona
2. Construir subgrafo con edges que intersectan la zona
3. Calcular centralidad según método elegido
4. Seleccionar el nodo con mayor centralidad como centroide
5. Guardar resultados en `centroids.gpkg`

### Comportamiento:
- Si `recompute: false` y existe `centroids.gpkg` → se carga desde archivo
- Si `recompute: true` → se recalcula siempre
- Si no hay archivo → se calcula automáticamente
- Fallback a centroide geométrico si la zona no tiene nodos válidos

---

## 🎯 Selección manual de checkpoints

El sistema permite **overrides manuales** del checkpoint automático para pares origen-destino específicos mediante un archivo CSV.

### Formato del archivo `manual_pair_checkpoints.csv`:
```csv
origin_zone_id,destination_zone_id,origin_node_id,destination_node_id,checkpoint_node_id,author,timestamp,notes
Z1,Z2,N1,N2,C_manual_1,John Doe,2024-01-15,Ruta optimizada por análisis de campo
Z3,Z4,N3,N4,C_manual_2,Jane Smith,2024-01-20,Evitar zona de construcción
```

### Columnas obligatorias:
- `origin_zone_id`: ID de zona origen
- `destination_zone_id`: ID de zona destino
- `checkpoint_node_id`: Nodo que debe usarse como checkpoint

### Columnas opcionales:
- `origin_node_id`: Override del nodo origen (si difiere del centroide)
- `destination_node_id`: Override del nodo destino (si difiere del centroide)
- `author`: Responsable del override
- `timestamp`: Fecha de la especificación
- `notes`: Justificación técnica

### Configuración en `routing.yaml`:
```yaml
manual_selection:
  enabled: true
  file: data/raw/inputs/manual_pair_checkpoints.csv
  matching_keys: ["origin_zone_id", "destination_zone_id"]
```

### Lógica de integración en MC2:
1. Al calcular ruta para un par origen-destino:
   - Buscar override en `manual_pair_checkpoints.csv`
   - Si existe → usar `checkpoint_node_id` especificado
   - Si no existe → usar algoritmo automático de selección de checkpoint
2. Guardar metadata `checkpoint_source`:
   - `"manual"` si se usó override
   - `"auto"` si se usó algoritmo automático

### Ventajas:
- Permite incorporar conocimiento experto del terreno
- Auditable (se registra autor y justificación)
- No interfiere con rutas automáticas
- Fácil de actualizar (solo editar CSV)

---

## 🧮 Integración MC, MC2 y cálculo de congruencias

### Matriz MC (Caminos directos):
- Calcula shortest path A→B para todos los pares origen-destino
- Representa el camino **óptimo sin restricciones**
- Se usa como baseline para comparación

### Matriz MC2 (Caminos con checkpoint):
- Calcula rutas A→C→B donde C es un checkpoint obligatorio
- El checkpoint puede ser:
  - **Manual**: Especificado en `manual_pair_checkpoints.csv`
  - **Automático**: Seleccionado por algoritmo (ej: zona más transitada, punto de control vial)

### Cálculo del ratio X:
```
X = (distancia_A→C + distancia_C→B) / distancia_A→B
```

### Clasificación de congruencia:
```yaml
umbrales_congruencia:
  seguro: 0.85           # X en rango 85%-110% → congruencia = 1
  probable: 0.60         # X en rango 60%-140% → congruencia = 2
  poco_probable: 0.35    # X en rango 35%-200% → congruencia = 3
  imposible: 0.0         # X fuera de rango → congruencia = 4
```

### Ejemplo práctico:
- Ruta directa A→B: 10 km
- Ruta con checkpoint A→C→B: 11 km
- Ratio X = 11/10 = 1.1 (110%)
- Si umbral seguro ≥ 0.85 → **Congruencia = 1 (Seguro)**

### Factores adicionales considerados:
- **Map matching**: ¿La ruta KIDO coincide con la red vial?
- **Tiempo**: ¿La duración es consistente?
- **Checkpoint**: ¿Pasó por el punto requerido?
- **Volumen**: ¿El tráfico KIDO es comparable al aforo vial?
- **Validez**: ¿Los datos tienen errores de geocodificación?

---

## ▶️ Cómo usar el proyecto

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Instalar el paquete en modo desarrollo (opcional)
```bash
pip install -e .
```

### 3. Editar configuraciones
Los parámetros se encuentran en:
```
config/paths.yaml
config/routing.yaml
config/validation.yaml
```
Ejemplo (paths.yaml):
```yaml
data_raw: data/raw/
data_processed: data/processed/
network: data/network/
```

## ▶️ Ejecutar el pipeline completo
```bash
py src/scripts/run_pipeline.py
```
El script ejecutará:
- Limpieza →
- Matrices →
- Ruteo →
- Validación →
- Exportación
Los resultados aparecerán en `data/processed/`.

## ▶️ Ejecutar solo el ruteo
```bash
py src/scripts/generate_matrices.py
```

## 🧪 Pruebas
```bash
pytest tests/
```

## 📘 Documentación
La documentación extendida vive en:
```
docs/
├── api/
└── diagrams/
```
Incluye:
- Diagramas de flujo
- Descripción técnica de cada módulo
- Guía de calibración de congruencias
- Ejemplos de ruteo

## 👤 Autor
Miguel Antonio Muñoz Beltrán
2025

## 📝 Licencia
...