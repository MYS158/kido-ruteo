# 470-000 — Diagrama de Flujo KIDO  
_(versión en Markdown)_

## INICIO

### **Entradas**
- Red de modelación/OSM (enlaces y nodos)  
- Zonificación KIDO  
- Descarga OD KIDO  
- Archivo de cardinalidad  
- Factor de ocupación  
- Dato vial  

---

## **1. Procesamiento inicial OD KIDO**

### **Cálculo de centralidad**
- Calcular centralidad de todos los nodos.  
- En cada zona → definir como **centroide** el nodo con mayor centralidad  
  (nodo más conectado = nodo más central).

**Archivos:**  
`red.geojson`, `zonificacion.geojson`, `extraccion.csv`

---

## **2. Depuración por número de viajes**
### Condición:
```
total_trips < 10 ?
```

- **SI:**  
  `total_trips_modif = 1`

- **NO:**  
  `total_trips_modif = total_trips`

Crear columna **total_trips_modif**

---

## **3. Identificar intrazonales**
### Condición:
```
origin_name == destination_name ?
```

- **SI → intrazonal = 0**  
- **NO → intrazonal = 1**

Crear columna **intrazonal**

Guardar cambios en `extraccion.csv`.

---

## **4. Verificar zona de estación**
Usando `cardinalidad.geojson`.

### Pregunta:
```
¿El viaje es intrazonal en la zona de la estación?
```

- **SI → seguir**
- **NO → Congruencia = 4**

---

## **5. Generación de vectores de acceso**
- Generar vector V1 = todos los orígenes  
- Generar vector V2 = todos los destinos  

### Condición:
```
¿La zona del viaje se encuentra en el primer vector de acceso?
```

- **SI → continuar**
- **NO → Congruencia = 4, Id_potencial = 1**

---

## **6. Validación KIDO vs Dato vial**

1. Calcular **VolDV-personas**:  
   ```
   (dato vial) * (factor de ocupación por tipología) 
   ```
   Sumar tipologías A, B, C.

2. Factor:  
   ```
   Factor = VolDV-personas / Vol KIDO
   ```

### Condición:
```
0.95 < Factor < 1.05 ?
```

- **SI → FIN (validado)**
- **NO → No confiable**

---

## **7. Validación espacial**

### 7.1. Verificar paso por enlace de checkpoint
```
¿La ruta pasa por el enlace del checkpoint?
```

- **NO → Congruencia 4**
- **SI → continuar**

### 7.2. Generar centroides
- Coordenadas de nodo origen: `x-o, y-o`  
- Coordenadas de nodo destino: `x-d, y-d`

### 7.3. Comparar con matriz de conexión
```
-10% < X < 10% ?
```

- **NO → Congruencia 4**
- **SI → Congruencia 3**

### 7.4. Asignar sentido
Usar `cardinalidad.csv` para asignar el sentido por localización espacial.

---

## **8. Crear Matriz de Impedancia (MC)**

Características:
- Viajes posibles entre todos los pares OD  
- Atributos: tiempo, distancia, costo  
- Algoritmo: shortest path  
- Rutas en MC **NO requieren pasar por el checkpoint**  

Archivo: `mtx_impedancia.csv`

### Selección del 80%
1. Crear identificador zona-zona, ej. `1-2`.  
2. Sumar viajes por este ID.  
3. Identificar los pares que representan el **80% del total**.  
4. Exportar rutas nodo a nodo para esos viajes → `Rutas.geojson`.

---

## **9. Crear segunda Matriz de Impedancia (MC2)**

Características:
- Viajes posibles entre todos los pares OD  
- Atributos: tiempo, distancia, costo  
- Algoritmo: **Constrained shortest path / k-shortest path**  
- Las rutas **sí pasan por el checkpoint**

Archivo: `mtx_impedancia2.csv`

### Cálculo X
```
X = (A–Checkpoint + Checkpoint–B) / (A–B)
```

- Id_potencial = 1 en caso de valores anómalos  

---

## **10. Identificar Congruencia**
```
¿La congruencia es 4?
```

- **SI → Id_congruencia = 0**
- **NO → Id_congruencia = 1**

Actualizar `extraccion.csv`.

---

## **11. Crear columna Viajes**
```
Viajes =
id_congruencia * id_potencial * intrazonal * total_trips_modif
```

---

## **12. Cálculo por día**
- Con columna **fecha** + **Viajes**, generar tabla:  
  - **tpdes**  
  - **tpdfs**  
  - **tpds**  

---

## **13. Cálculo TPDA (viajes persona)**

Usando KIDO:
```
TPDA = volumen / factor de ocupación (A+B+C)
```

Desde dato vial (**E2**):
- `dato vial * factor de ocupación (A+B+C)`

KIDO produce **E1**.

---

## **14. Proporciones por tipo de vehículo**
- Obtener proporción por tipo  
- Multiplicar `tpds * proporción`  

Factor final:
```
Factor_kido_vs_dato_vial = E2 / E1
```

---

## **15. Comprobación de la estación**
```
Rev_final = Vol KIDO final / Vol KIDO inicial
```

### Condición:
```
Rev_final > 0.95 ?
```

- **SI → FIN**
- **NO → No confiable**

---

## FIN
