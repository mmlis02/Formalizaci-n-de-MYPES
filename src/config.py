"""Carga config.yaml y convierte las rutas relativas en rutas absolutas.

Copiado de HW_03_202602 (tarea1_rag_normativo/src/config.py). Por ahora sin
umbral_activo(): se agrega en el Bloque 2, cuando exista la sección "motor".
"""
from pathlib import Path

import yaml

# Raíz del proyecto (donde vive config.yaml)
BASE = Path(__file__).resolve().parent.parent


def cargar_config(ruta: Path = BASE / "config.yaml") -> dict:
    with open(ruta, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg


def ruta(cfg: dict, clave: str) -> Path:
    """Devuelve la ruta absoluta de cfg['rutas'][clave]."""
    return BASE / cfg["rutas"][clave]
