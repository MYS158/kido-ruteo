"""Cargador de configuración YAML para kido-ruteo.

Proporciona métodos convenientes para cargar paths, routing y validation con
valores por defecto, convirtiendo rutas a objetos ``pathlib.Path`` y validando
la estructura mínima esperada.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping

import yaml

from .defaults import (
    INPUTS_DEFAULT,
    PATHS_DEFAULT,
    ROUTING_DEFAULT,
    VALIDATION_DEFAULT,
    merge_all,
    merge_inputs,
    merge_paths,
    merge_routing,
    merge_validation,
)


# Directorio real de configuraciones YAML (raíz del proyecto /config).
CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"

def _read_yaml(file_path: Path) -> dict[str, Any]:
    """Lee un YAML en disco y devuelve un dict. Maneja errores comunes."""
    if not file_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo de configuración: {file_path}")

    try:
        content = file_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content) or {}
    except yaml.YAMLError as exc:  # type: ignore[catching-non-exception]
        raise ValueError(f"YAML inválido en {file_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"El YAML debe ser un mapeo (dict) en {file_path}")

    return data

def _to_path(value: Any) -> Path:
    """Convierte strings a Path; si ya es Path lo retorna."""
    return value if isinstance(value, Path) else Path(str(value))

@dataclass
class PathsConfig:
    data_raw: Path
    data_interim: Path
    data_processed: Path
    network: Path
    logs: Path
    outputs: Dict[str, Path]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PathsConfig":
        outputs_raw = data.get("outputs", {}) or {}
        outputs = {key: _to_path(val) for key, val in outputs_raw.items()}
        return cls(
            data_raw=_to_path(data["data_raw"]),
            data_interim=_to_path(data["data_interim"]),
            data_processed=_to_path(data["data_processed"]),
            network=_to_path(data["network"]),
            logs=_to_path(data["logs"]),
            outputs=outputs,
        )


@dataclass
class RoutingConfig:
    algoritmo: str
    velocidad_default: float
    max_k_routes: int
    ponderadores: Dict[str, float]
    restricciones: Dict[str, Any]
    network: Dict[str, Path]
    centroids: CentroidsConfig
    manual_selection: ManualSelectionConfig
    mc: Dict[str, Any]
    mc2: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RoutingConfig":
        routing_block = data.get("routing", {})
        network_block = data.get("network", {})
        network_paths = {key: _to_path(val) for key, val in network_block.items()}
        return cls(
            algoritmo=str(routing_block.get("algoritmo", ROUTING_DEFAULT["routing"]["algoritmo"])),
            velocidad_default=float(
                routing_block.get("velocidad_default", ROUTING_DEFAULT["routing"]["velocidad_default"])
            ),
            max_k_routes=int(routing_block.get("max_k_routes", ROUTING_DEFAULT["routing"]["max_k_routes"])),
            ponderadores=dict(routing_block.get("ponderadores", ROUTING_DEFAULT["routing"]["ponderadores"])),
            restricciones=dict(routing_block.get("restricciones", ROUTING_DEFAULT["routing"]["restricciones"])),
            network=network_paths,
            centroids=CentroidsConfig.from_dict(data),
            manual_selection=ManualSelectionConfig.from_dict(data),
            mc=dict(data.get("mc", ROUTING_DEFAULT["mc"])),
            mc2=dict(data.get("mc2", ROUTING_DEFAULT["mc2"])),
        )


@dataclass
class ValidationConfig:
    pesos_componentes: Dict[str, float]
    umbrales_congruencia: Dict[str, float]
    calibracion: Dict[str, Any]
    checks_logicos: Dict[str, Any]
    campos_salida: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ValidationConfig":
        return cls(
            pesos_componentes=dict(data.get("pesos_componentes", VALIDATION_DEFAULT["pesos_componentes"])),
            umbrales_congruencia=dict(
                data.get("umbrales_congruencia", VALIDATION_DEFAULT["umbrales_congruencia"])
            ),
            calibracion=dict(data.get("calibracion", VALIDATION_DEFAULT["calibracion"])),
            checks_logicos=dict(data.get("checks_logicos", VALIDATION_DEFAULT["checks_logicos"])),
            campos_salida=dict(data.get("campos_salida", VALIDATION_DEFAULT["campos_salida"])),
        )


@dataclass
class CentroidsConfig:
    method: str
    recompute: bool
    output: Path

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CentroidsConfig":
        centroids_block = data.get("centroids", ROUTING_DEFAULT.get("centroids", {}))
        return cls(
            method=str(centroids_block.get("method", "degree")),
            recompute=bool(centroids_block.get("recompute", False)),
            output=_to_path(centroids_block.get("output", "data/network/centroids.gpkg")),
        )


@dataclass
class ManualSelectionConfig:
    enabled: bool
    file: Path
    matching_keys: list[str]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ManualSelectionConfig":
        manual_block = data.get("manual_selection", ROUTING_DEFAULT.get("manual_selection", {}))
        return cls(
            enabled=bool(manual_block.get("enabled", True)),
            file=_to_path(manual_block.get("file", "data/raw/inputs/manual_pair_checkpoints.csv")),
            matching_keys=list(manual_block.get("matching_keys", ["origin_zone_id", "destination_zone_id"])),
        )


@dataclass
class InputsConfig:
    od_dir: Path
    od_files: list[str]
    geografia_zonas: Path
    aforo_factors: Path

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "InputsConfig":
        od_files_raw = data.get("od_files", INPUTS_DEFAULT["od_files"]) or []
        od_files = [str(f) for f in od_files_raw]
        return cls(
            od_dir=_to_path(data.get("od_dir", INPUTS_DEFAULT["od_dir"])),
            od_files=od_files,
            geografia_zonas=_to_path(data.get("geografia_zonas", INPUTS_DEFAULT["geografia_zonas"])),
            aforo_factors=_to_path(data.get("aforo_factors", INPUTS_DEFAULT["aforo_factors"])),
        )

@dataclass
class Config:
    """Contenedor de toda la configuración del proyecto."""
    paths: PathsConfig
    routing: RoutingConfig
    validation: ValidationConfig
    inputs: InputsConfig

class ConfigLoader:
    """Carga YAML desde el directorio config/ aplicando defaults y validaciones básicas."""
    base_dir: Path = CONFIG_DIR

    @classmethod
    def load_paths(cls, file_path: Path | str | None = None) -> PathsConfig:
        target = _normalize_path(file_path, "paths.yaml")
        data = merge_paths(_read_yaml(target))
        return PathsConfig.from_dict(data)

    @classmethod
    def load_routing(cls, file_path: Path | str | None = None) -> RoutingConfig:
        target = _normalize_path(file_path, "routing.yaml")
        data = merge_routing(_read_yaml(target))
        return RoutingConfig.from_dict(data)

    @classmethod
    def load_validation(cls, file_path: Path | str | None = None) -> ValidationConfig:
        target = _normalize_path(file_path, "validation.yaml")
        data = merge_validation(_read_yaml(target))
        return ValidationConfig.from_dict(data)

    @classmethod
    def load_all(
        cls,
        paths_file: Path | str | None = None,
        routing_file: Path | str | None = None,
        validation_file: Path | str | None = None,
        inputs_file: Path | str | None = None,
    ) -> Config:
        """Carga y combina paths, routing y validation en un solo objeto Config."""
        paths_cfg = cls.load_paths(paths_file)
        routing_cfg = cls.load_routing(routing_file)
        validation_cfg = cls.load_validation(validation_file)
        inputs_cfg = cls.load_inputs(inputs_file)
        return Config(paths=paths_cfg, routing=routing_cfg, validation=validation_cfg, inputs=inputs_cfg)

    @classmethod
    def load_inputs(cls, file_path: Path | str | None = None) -> InputsConfig:
        target = _normalize_path(file_path, "paths.yaml")  # inputs vienen dentro de paths.yaml por simplicidad
        yaml_data = _read_yaml(target)
        merged = merge_inputs(yaml_data.get("inputs")) if "inputs" in yaml_data else merge_inputs(None)
        return InputsConfig.from_dict(merged)

def _normalize_path(path: Path | str | None, default_name: str) -> Path:
    """Resuelve la ruta al archivo de configuración desde la base config/."""
    if path is None:
        return CONFIG_DIR / default_name
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = CONFIG_DIR / candidate
    return candidate

# Nota: El alias Config apunta al dataclass Config (no al loader).
