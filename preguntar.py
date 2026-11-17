"""Interfaz de línea de comandos: solo llama a src.motor_rag.responder (igual que la app).

Copiado de HW_03_202602 (tarea1_rag_normativo/preguntar.py).

Uso:  python preguntar.py "¿Hasta qué tamaño puede ser mi bodega?"
"""
import sys

from src.motor_rag import responder

if __name__ == "__main__":
    r = responder(" ".join(sys.argv[1:]))
    if r["error"]:
        print("ERROR:", r["error"])
        sys.exit(1)
    print(("[SE ABSTUVO: " + r["motivo_abstencion"] + "] ") if r["abstuvo"] else "", r["respuesta"], sep="")
    if r["explicacion_limite"]:
        print("Límite del corpus:", r["explicacion_limite"])
    for n in r["notas_version"]:
        print("Nota de versión:", n)
    print(f"\nSimilitud máxima {r['similitud_max']:.3f} (umbral {r['umbral']}) | costo US${r['costo_usd']:.6f}")
    for f in r["fuentes"]:
        print(f"  {'*' if f['citada'] else ' '} {f['documento']} pág. {f['pagina']} (sim. {f['similitud']:.3f}) {f['articulo']}")
