"""
debug_config.py

Configuración global para modo de debugging focalizado en checkpoint 2030.

Permite activar/desactivar debug, especificar qué checkpoint debuggear, y configurar 
opciones de visualización.
"""

# Flag global de debug focalizado
DEBUG_MODE_ENABLED = False

# ID del checkpoint a debuggear (None = deshabilitado)
DEBUG_CHECKPOINT_ID = None

# Directorio de salida para artefactos de debug
DEBUG_OUTPUT_DIR = "./debug_output"

# Generar visualizaciones de rutas (requiere grafo y es computacionalmente intenso)
DEBUG_GENERATE_ROUTE_PLOTS = True

# Generar visualizaciones de sentido
DEBUG_GENERATE_SENSE_PLOTS = True

# Generar visualización de flujo lógico completo
DEBUG_GENERATE_LOGIC_FLOW = True

# Logging verbose
DEBUG_VERBOSE_LOGGING = True

# Máximo número de ODs a graficar (para evitar explosion de archivos)
DEBUG_MAX_ROUTE_PLOTS = 20

# Validaciones estrictas para checkpoint
DEBUG_STRICT_VALIDATIONS = True
