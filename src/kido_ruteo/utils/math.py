"""
Utilidades de redes para KIDO-Ruteo.
"""

import networkx as nx
from typing import List, Tuple


def create_graph() -> nx.Graph:
    """
    Crea grafo vacío.
    
    Returns:
        Grafo de NetworkX
    """
    return nx.Graph()


def add_node_to_graph(G: nx.Graph, node_id: str, **attributes) -> None:
    """
    Añade nodo al grafo.
    
    Args:
        G: Grafo
        node_id: ID del nodo
        **attributes: Atributos del nodo
    """
    G.add_node(node_id, **attributes)


def add_edge_to_graph(G: nx.Graph, node1: str, node2: str, weight: float = 1.0) -> None:
    """
    Añade arista al grafo.
    
    Args:
        G: Grafo
        node1: ID del primer nodo
        node2: ID del segundo nodo
        weight: Peso de la arista
    """
    G.add_edge(node1, node2, weight=weight)


def is_connected(G: nx.Graph) -> bool:
    """
    Verifica si el grafo está conectado.
    
    Args:
        G: Grafo
        
    Returns:
        True si está conectado
    """
    return nx.is_connected(G)


def get_largest_connected_component(G: nx.Graph) -> nx.Graph:
    """
    Obtiene la componente conexa más grande.
    
    Args:
        G: Grafo
        
    Returns:
        Subgrafo de la componente más grande
    """
    largest_cc = max(nx.connected_components(G), key=len)
    return G.subgraph(largest_cc).copy()
