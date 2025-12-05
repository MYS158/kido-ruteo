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

1. **Carga de datos**  
    - KIDO raw, red vial, cardinalidad, zonificación y aforos.

2. **Procesamiento de OD**  
    - Limpieza de viajes  
    - Detección intrazonal  
    - Vector de acceso  
    - Asignación de sentido (cardinalidad)  

3. **Generación de matrices**  
    - **MC**: shortest path entre todos los pares  
    - Selección del 80% de viajes más representativos  
    - **MC2**: rutas obligadas por checkpoint (constrained/k-shortest-path)

4. **Evaluación de congruencias**  
    Los viajes se clasifican en:
    - **1 — Seguro**  
    - **2 — Probable**  
    - **3 — Poco probable**  
    - **4 — Imposible**  

Basado en mapa, desviación de tiempo/distancia, paso por checkpoint, volumen, consistencia y atributos.

5. **Cálculo de métricas finales**  
    - Viajes persona  
    - Transformación a viajes vehículo (TPDA)  
    - Factores de validación KIDO vs dato vial  
    - Revisiones E1, E2 y confiabilidad final

6. **Exportación**  
    - Tablas procesadas  
    - Matrices MC / MC2  
    - GeoJSON de rutas  
    - Resultados de congruencias  

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
python src/scripts/run_pipeline.py
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
python src/scripts/generate_matrices.py
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