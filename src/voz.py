"""Voz a texto con Whisper (API de OpenAI). Primer paso del flujo: audio -> transcripción.

`transcribir(ruta_audio)` revisa el archivo ANTES de llamar a la API (si no existe, si el
formato no se admite o si pesa demasiado, devuelve el error sin gastar nada) y luego llama
a src/llm.transcribir_audio, que registra el costo por minuto en logs/costos_llm.csv.

Siempre devuelve un diccionario con `error`: la app muestra el error, nunca lo confunde con
una transcripción.
"""
from pathlib import Path

from src.config import cargar_config
from src.llm import cliente_openai, transcribir_audio


def revisar_archivo(ruta: Path, cfg: dict) -> str | None:
    """Devuelve el mensaje de error si el archivo no sirve, o None si se puede enviar."""
    m = cfg["voz"]["mensajes"]
    if not ruta.is_file():
        return m["no_existe"]
    formato = ruta.suffix.lower().lstrip(".")
    if formato not in cfg["voz"]["formatos"]:
        return m["formato"].format(formato=formato or "sin extensión", formatos=", ".join(cfg["voz"]["formatos"]))
    mb = ruta.stat().st_size / 1_000_000
    if mb > cfg["voz"]["tamano_max_mb"]:
        return m["muy_grande"].format(mb=mb, max_mb=cfg["voz"]["tamano_max_mb"])
    return None


def transcribir(ruta_audio: str | Path, cfg: dict | None = None, cliente=None) -> dict:
    """audio -> {'texto', 'duracion_s', 'costo_usd', 'latencia_s', 'modelo', 'error'}.

    `cliente` se puede inyectar (cliente falso) para probar sin gastar.
    """
    cfg = cfg or cargar_config()
    ruta = Path(ruta_audio)
    vacio = {"texto": "", "duracion_s": 0.0, "costo_usd": 0.0, "latencia_s": 0.0,
             "modelo": cfg["voz"]["modelo"], "error": None}

    error = revisar_archivo(ruta, cfg)
    if error:  # no se llama a la API: costo 0
        return {**vacio, "error": error}

    with open(ruta, "rb") as archivo:
        r = transcribir_audio(cliente or cliente_openai(cfg), cfg, archivo, ruta.name)
    if r["error"]:
        r["error"] = f"{cfg['voz']['mensajes']['error_api']} ({r['error']})"
    elif not r["texto"]:
        r["error"] = cfg["voz"]["mensajes"]["vacio"]
    return r
