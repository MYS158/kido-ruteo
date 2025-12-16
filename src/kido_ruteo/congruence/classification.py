import pandas as pd
import numpy as np

def classify_congruence(df: pd.DataFrame) -> pd.DataFrame:
    """
    Classifies congruence based on E1, E2 and id_potential.
    
    1 → Extremely possible
    2 → Possible
    3 → Unlikely
    4 → Impossible
    
    If id_potential = 0 → congruence_id = 4.
    """
    
    conditions = [
        (df['id_potential'] == 0),
        # Example rules (adjust based on specific business logic if provided, otherwise standard KIDO)
        # Standard KIDO usually:
        # E1 close to 1.0 (+- 10-20%) AND E2 close to 1.0 (+- 5-10%) -> 1
        # E1 acceptable AND E2 acceptable -> 2
        # Outliers -> 3
        
        # Implementemos una lógica robusta:
        # 1: E1 en [0.9, 1.2] Y E2 >= 0.8 (Alta congruencia)
        # 2: E1 en [0.8, 1.5] Y E2 >= 0.5 (Congruencia media)
        # 3: E1 < 2.0
        # 4: Resto
        
        (df['e1_route_score'].between(0.9, 1.2) & (df['e2_capacity_score'] >= 0.8)),
        (df['e1_route_score'].between(0.8, 1.5) & (df['e2_capacity_score'] >= 0.5)),
        (df['e1_route_score'] < 2.0)
    ]
    
    choices = [4, 1, 2, 3]
    
    df['congruence_id'] = np.select(conditions, choices, default=4)
    
    labels = {
        1: 'Extremely possible',
        2: 'Possible',
        3: 'Unlikely',
        4: 'Impossible'
    }
    
    df['congruence_label'] = df['congruence_id'].map(labels)
    
    # Reason
    df['congruence_reason'] = 'Valid'
    df.loc[df['id_potential'] == 0, 'congruence_reason'] = 'Potential=0'
    df.loc[(df['id_potential'] == 1) & (df['congruence_id'] == 4), 'congruence_reason'] = 'Score Outlier'
    
    return df
