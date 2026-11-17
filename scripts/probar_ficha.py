"""Prueba manual del flujo voz -> ficha (cuesta centavos: llama a Whisper y al LLM).

Muestra la transcripción, cada campo con su estado de verificación y el costo.

Uso (desde la raíz del proyecto):
    python scripts/probar_ficha.py tests/datos/audio_sintetico.m4a      # audio
    python scripts/probar_ficha.py --texto "Tengo una bodega de 30 m2..."  # texto
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.motor import procesar_audio, procesar_texto  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio", nargs="?")
    ap.add_argument("--texto")
    args = ap.parse_args()
    r = procesar_texto(args.texto) if args.texto else procesar_audio(args.audio)

    if r["error"]:
        print("ERROR:", r["error"])
        sys.exit(1)
    print(f"Duración del audio: {r['duracion_s']} s | costo: voz US${r['costos']['voz']:.6f} + "
          f"ficha US${r['costos']['ficha']:.6f} = US${r['costo_usd']:.6f}")
    print("TRANSCRIPCIÓN:", r["transcripcion"], "\n")
    for nombre, c in r["ficha"]["campos"].items():
        print(f"{c['estado']:14} {nombre:27} {c['valor']!r:26} cita={c['cita']!r}")
    print("\nResumen:", r["ficha"]["resumen"])


if __name__ == "__main__":
    main()
