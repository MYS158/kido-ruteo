import sys
import os
import pandas as pd
import numpy as np

# Add src to path to import the package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from kido_ruteo.preprocessing import create_intrazonal, create_total_trips_modif
from kido_ruteo.viajes import calculate_viajes

def test_equivalence():
    print("=== Iniciando Prueba de Equivalencia: Documentación vs Código ===\n")

    # 1. Setup Data
    # Row 1: Intrazonal (Origin A -> A)
    # Row 2: Interzonal (Origin A -> B)
    data = {
        'origin_name': ['A', 'A'],
        'destination_name': ['A', 'B'],
        'total_trips': [100, 100],
        'id_congruencia': [1, 1],
        'id_potencial': [1, 1]
    }
    df_base = pd.DataFrame(data)
    
    print("Datos de entrada:")
    print(df_base)
    print("\n--------------------------------------------------\n")

    # ---------------------------------------------------------
    # 2. Apply Documentation Logic (Manual Implementation)
    # ---------------------------------------------------------
    print(">>> Aplicando Lógica de Documentación (flow.md)...")
    df_docs = df_base.copy()
    
    # Step 2: total_trips_modif (Simplified for this test, assuming >= 10)
    df_docs['total_trips_modif'] = df_docs['total_trips'] 

    # Step 3: Identificar intrazonales
    # Docs: SI (origin==dest) -> intrazonal = 0, NO -> intrazonal = 1
    df_docs['intrazonal_doc'] = np.where(
        df_docs['origin_name'] == df_docs['destination_name'], 
        0, 
        1
    )
    
    # Step 11: Crear columna Viajes
    # Viajes = id_congruencia * id_potencial * intrazonal * total_trips_modif
    df_docs['Viajes_doc'] = (
        df_docs['id_congruencia'] * 
        df_docs['id_potencial'] * 
        df_docs['intrazonal_doc'] * 
        df_docs['total_trips_modif']
    )
    
    print("Resultados Documentación:")
    print(df_docs[['origin_name', 'destination_name', 'intrazonal_doc', 'Viajes_doc']])
    print("\n--------------------------------------------------\n")

    # ---------------------------------------------------------
    # 3. Apply Code Logic (Actual Functions)
    # ---------------------------------------------------------
    print(">>> Aplicando Lógica del Código Actual (src/kido_ruteo)...")
    df_code = df_base.copy()
    
    # Step 2 (Code)
    df_code = create_total_trips_modif(df_code)
    
    # Step 3 (Code): create_intrazonal
    # Code: SI (origin==dest) -> intrazonal = 1, NO -> intrazonal = 0
    df_code = create_intrazonal(df_code)
    
    # Step 11 (Code): calculate_viajes
    # Code: Viajes = ... * (1 - intrazonal) * ...
    df_code = calculate_viajes(df_code)
    
    print("Resultados Código:")
    print(df_code[['origin_name', 'destination_name', 'intrazonal', 'Viajes']])
    print("\n--------------------------------------------------\n")

    # ---------------------------------------------------------
    # 4. Comparison
    # ---------------------------------------------------------
    print(">>> Comparación Final")
    
    # Check Intrazonal Trip (A->A)
    # Docs: Viajes should be 0
    # Code: Viajes should be 0
    doc_intra = df_docs.loc[0, 'Viajes_doc']
    code_intra = df_code.loc[0, 'Viajes']
    
    # Check Interzonal Trip (A->B)
    # Docs: Viajes should be 100
    # Code: Viajes should be 100
    doc_inter = df_docs.loc[1, 'Viajes_doc']
    code_inter = df_code.loc[1, 'Viajes']
    
    print(f"Caso Intrazonal (A->A): Docs={doc_intra}, Code={code_intra} -> {'EQUIVALENTE' if doc_intra == code_intra else 'DIFERENTE'}")
    print(f"Caso Interzonal (A->B): Docs={doc_inter}, Code={code_inter} -> {'EQUIVALENTE' if doc_inter == code_inter else 'DIFERENTE'}")
    
    if doc_intra == code_intra and doc_inter == code_inter:
        print("\nCONCLUSIÓN: El flujo implementado ES matemáticamente equivalente a la documentación.")
    else:
        print("\nCONCLUSIÓN: Hay discrepancias entre el código y la documentación.")

if __name__ == "__main__":
    test_equivalence()
