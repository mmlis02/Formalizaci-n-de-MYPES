"""Motor del flujo principal: une voz -> ficha (-> reglas, en el Bloque 4). Es lo único que llama la app
para el flujo de "Cuéntame" (el chat de dudas llama a src/motor_rag.py).

  procesar_audio(ruta)  -> transcribe con Whisper y sigue con procesar_texto
  procesar_texto(texto) -> extrae la ficha verificada

Ambas devuelven un diccionario con campos explícitos y `error`. Si la transcripción falla, no se
llama al LLM (no se gasta en extraer una ficha de un texto vacío).
"""
from src.config import cargar_config
from src.ficha import extraer_ficha
from src.voz import transcribir


def _resultado_vacio() -> dict:
    return {"transcripcion": "", "duracion_s": 0.0, "ficha": None, "costo_usd": 0.0,
            "costos": {"voz": 0.0, "ficha": 0.0}, "error": None}


def procesar_texto(texto: str, cfg: dict | None = None, cliente=None) -> dict:
    """Texto escrito (o ya transcrito) -> ficha verificada."""
    cfg = cfg or cargar_config()
    r = _resultado_vacio()
    r["transcripcion"] = (texto or "").strip()
    ficha = extraer_ficha(r["transcripcion"], cfg, cliente)
    r["costos"]["ficha"] = ficha["costo_usd"]
    r["costo_usd"] = sum(r["costos"].values())
    if ficha["error"]:
        r["error"] = ficha["error"]
        return r
    r["ficha"] = ficha
    return r


def procesar_audio(ruta_audio, cfg: dict | None = None, cliente=None) -> dict:
    """Audio -> transcripción (Whisper) -> ficha verificada."""
    cfg = cfg or cargar_config()
    voz = transcribir(ruta_audio, cfg, cliente)
    if voz["error"]:
        r = _resultado_vacio()
        r["costos"]["voz"] = r["costo_usd"] = voz["costo_usd"]
        r["error"] = voz["error"]
        return r
    r = procesar_texto(voz["texto"], cfg, cliente)
    r["duracion_s"] = voz["duracion_s"]
    r["costos"]["voz"] = voz["costo_usd"]
    r["costo_usd"] = sum(r["costos"].values())
    return r
