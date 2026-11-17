"""Costo de IA de una sesión típica, a partir de las llamadas REALES de logs/costos_llm.csv.

Sesión típica (config.yaml > costo_por_usuario): 1 audio de ~30 s (Whisper) + 1 extracción de la
ficha (LLM) + 3 preguntas al chat (embedding de la pregunta + LLM).
  - Whisper: precio por minuto de config.yaml x duración (cobra por minuto, no por tokens).
  - Ficha y chat: costo PROMEDIO de las llamadas exitosas que hay en el log.
  - Supuesto conservador: las 3 preguntas pasan el umbral y llaman al LLM (si se abstiene, cuesta menos).

Uso (desde la raíz del proyecto):
    python scripts/costo_por_usuario.py
"""
import csv
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import BASE, cargar_config  # noqa: E402


def main():
    cfg = cargar_config()
    filas = [f for f in csv.DictReader(open(BASE / cfg["precios"]["log_llamadas"], encoding="utf-8"))
             if f["exito"] == "True"]

    def promedio(condicion) -> tuple[float, int]:
        costos = [float(f["costo_usd"]) for f in filas if condicion(f)]
        return statistics.mean(costos), len(costos)

    sesion = cfg["costo_por_usuario"]["sesion_tipica"]
    por_minuto = cfg["precios"]["modelos"][cfg["voz"]["modelo"]]["franjas"][0]["por_minuto"]
    voz = sesion["segundos_audio"] / 60 * por_minuto
    ficha, n_ficha = promedio(lambda f: f["pregunta"].startswith("[ficha]"))
    llm_chat, n_chat = promedio(lambda f: f["modelo"] == cfg["llm"]["modelo"] and not f["pregunta"].startswith("["))
    emb_chat, n_emb = promedio(lambda f: f["pregunta"] == "[embeddings] lote de 1 textos")
    chat = sesion["preguntas_chat"] * (llm_chat + emb_chat)
    total = voz + ficha + chat

    tc = cfg["costo_por_usuario"]["tipo_cambio"]
    filas_tabla = [
        (f"Audio de {sesion['segundos_audio']} s (Whisper, US$ {por_minuto}/min)", voz, "precio x duración"),
        ("Extracción de la ficha (LLM)", ficha, f"promedio de {n_ficha} llamadas"),
        (f"{sesion['preguntas_chat']} preguntas al chat (embedding + LLM)", chat,
         f"promedio de {n_chat} llamadas al LLM y {n_emb} embeddings"),
    ]
    print("| Parte de la sesión | US$ | S/ | Cómo se calculó |")
    print("|---|---|---|---|")
    for nombre, usd, como in filas_tabla:
        print(f"| {nombre} | {usd:.5f} | {usd * tc['soles_por_dolar']:.4f} | {como} |")
    print(f"| **Total por sesión** | **{total:.4f}** | **{total * tc['soles_por_dolar']:.4f}** | |")
    print(f"| Por 1,000 sesiones | {total * 1000:.2f} | {total * 1000 * tc['soles_por_dolar']:.2f} | |")
    print(f"\nTipo de cambio: S/ {tc['soles_por_dolar']} por US$ ({tc['fuente']}, {tc['fecha']}).")
    print(f"Llamadas exitosas en el log: {len(filas)}.")


if __name__ == "__main__":
    main()
