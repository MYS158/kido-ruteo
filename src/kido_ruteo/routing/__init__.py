"""Módulo de routing: algoritmos de caminos, selección de checkpoints y matrices MC/MC2."""

try:
    from .manual_selection import (
        load_manual_selection,
        get_checkpoint_override,
        get_node_overrides,
    )

    __all__ = [
        "load_manual_selection",
        "get_checkpoint_override",
        "get_node_overrides",
    ]
except ImportError:
    __all__ = []
