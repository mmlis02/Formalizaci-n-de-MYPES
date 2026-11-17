"""Llamada al LLM con esquema JSON estricto.

Copiado de HW_03_202602 (comun/llm.py). Único cambio: el log de costos ya no recibe la
carpeta de la tarea (siempre es logs/costos_llm.csv de este proyecto). Nuevo (Bloque 3):
transcribir_audio() para Whisper, con el mismo registro de costo.

Devuelve SIEMPRE un diccionario; los errores de API o de formato no se lanzan: vuelven en
`error` (texto sin claves) para que la interfaz los muestre como error. Cada llamada, exitosa o
fallida, queda en logs/costos_llm.csv con su costo según la hora.
"""
import json
import os
import time

from src.costos import ahora_utc, calcular_costo, calcular_costo_audio, limpiar_error, registrar_llamada


def cliente_openai(cfg: dict):
    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv()
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), timeout=cfg["llm"]["timeout_segundos"])


def llamar_llm_json(cliente, cfg: dict, mensajes: list[dict], esquema: dict, etiqueta: str) -> dict:
    lcfg = cfg["llm"]
    momento, inicio = ahora_utc(), time.time()
    fila = {"fecha_hora_utc": momento.isoformat(timespec="seconds"), "modelo": lcfg["modelo"], "pregunta": etiqueta[:200]}
    r = {"datos": None, "tokens_entrada": 0, "tokens_salida": 0, "costo_usd": 0.0, "latencia_s": 0.0,
         "modelo": lcfg["modelo"], "error": None}
    try:
        resp = cliente.chat.completions.create(
            model=lcfg["modelo"], reasoning_effort=lcfg["reasoning_effort"],
            max_completion_tokens=lcfg["max_tokens_salida"],
            response_format={"type": "json_schema", "json_schema": esquema}, messages=mensajes)
        r["latencia_s"] = round(time.time() - inicio, 3)
        uso = resp.usage
        cache = getattr(getattr(uso, "prompt_tokens_details", None), "cached_tokens", 0) or 0
        r["tokens_entrada"], r["tokens_salida"] = uso.prompt_tokens, uso.completion_tokens
        r["costo_usd"], franja = calcular_costo(cfg, lcfg["modelo"], momento, r["tokens_entrada"], r["tokens_salida"], cache)
        fila.update(tokens_entrada=r["tokens_entrada"], tokens_entrada_cache=cache, tokens_salida=r["tokens_salida"],
                    latencia_s=r["latencia_s"], costo_usd=f"{r['costo_usd']:.8f}", franja=franja)
        r["datos"] = json.loads(resp.choices[0].message.content)
        fila["exito"] = True
    except Exception as ex:
        r["latencia_s"] = round(time.time() - inicio, 3)
        r["error"] = limpiar_error(ex)
        fila.update(latencia_s=r["latencia_s"], exito=False, error=r["error"])
    registrar_llamada(cfg, fila)
    return r


def transcribir_audio(cliente, cfg: dict, archivo, nombre: str) -> dict:
    """Llama a Whisper con un archivo abierto. Igual que llamar_llm_json: nunca lanza errores
    (vuelven en `error`) y cada llamada queda en logs/costos_llm.csv con su costo por minuto.
    En el log NO se guarda lo que se dijo en el audio, solo su duración."""
    vcfg = cfg["voz"]
    momento, inicio = ahora_utc(), time.time()
    fila = {"fecha_hora_utc": momento.isoformat(timespec="seconds"), "modelo": vcfg["modelo"], "pregunta": "[audio]"}
    r = {"texto": "", "duracion_s": 0.0, "costo_usd": 0.0, "latencia_s": 0.0, "modelo": vcfg["modelo"], "error": None}
    try:
        resp = cliente.audio.transcriptions.create(
            model=vcfg["modelo"], file=(nombre, archivo), language=vcfg["idioma"],
            prompt=vcfg["prompt"], response_format="verbose_json")
        r["latencia_s"] = round(time.time() - inicio, 3)
        r["texto"], r["duracion_s"] = resp.text.strip(), round(float(resp.duration), 2)
        r["costo_usd"], franja = calcular_costo_audio(cfg, vcfg["modelo"], momento, r["duracion_s"])
        fila.update(latencia_s=r["latencia_s"], costo_usd=f"{r['costo_usd']:.8f}", franja=franja, exito=True,
                    pregunta=f"[audio] {r['duracion_s']:.1f} s")
    except Exception as ex:
        r["latencia_s"] = round(time.time() - inicio, 3)
        r["error"] = limpiar_error(ex)
        fila.update(latencia_s=r["latencia_s"], exito=False, error=r["error"])
    registrar_llamada(cfg, fila)
    return r
