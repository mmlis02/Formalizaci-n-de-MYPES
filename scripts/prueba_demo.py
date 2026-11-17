"""Prueba de la demo: recorre el flujo completo REAL (con la API) y muestra ✅/❌ por paso.

  1. Ficha: el texto de ejemplo de la app (una bodega) -> procesar_texto
  2. Diagnóstico: con los datos de la ficha "confirmados" (como si el usuario diera los clics y
     respondiera las preguntas pendientes) -> camino A
  3. PDF: la declaración jurada de bodegas, con datos personales INVENTADOS
  4. Chat: una pregunta del corpus que se responde con cita (documento, pág.)
  5. Chat: una pregunta fuera del corpus que se abstiene
Al final, el costo total: la suma de las filas nuevas de logs/costos_llm.csv (incluye embeddings).

Sirve para revisar, minutos antes de presentar, que todo funciona. Cuesta menos de US$ 0.001.

Uso (desde la raíz del proyecto):
    python scripts/prueba_demo.py
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import BASE, cargar_config  # noqa: E402
from src.motor import diagnosticar, generar_formulario, procesar_texto  # noqa: E402
from src.motor_rag import responder  # noqa: E402


def filas_del_log(cfg: dict) -> list[dict]:
    ruta = BASE / cfg["precios"]["log_llamadas"]
    return list(csv.DictReader(open(ruta, encoding="utf-8"))) if ruta.exists() else []


def paso(numero: int, nombre: str, ok: bool, detalle: str) -> bool:
    print(f"{'✅' if ok else '❌'} {numero}. {nombre}: {detalle}")
    return ok


def main():
    cfg = cargar_config()
    dcfg = cfg["demo"]
    filas_antes = len(filas_del_log(cfg))
    resultados = []

    # 1. Ficha
    r = procesar_texto(cfg["app"]["cuentame"]["ejemplo_texto"], cfg)
    ok = not r["error"] and r["ficha"] is not None
    detalle = r["error"] or ", ".join(f"{e}: {n}" for e, n in r["ficha"]["resumen"].items())
    resultados.append(paso(1, "Ficha", ok, detalle))

    # 2. Diagnóstico con los datos confirmados (los 3 sí/no "por confirmar" se aceptan tal cual)
    diag = None
    if ok:
        datos = {n: c["valor"] for n, c in r["ficha"]["campos"].items()}
        diag = diagnosticar(datos, cfg)
        # Si la IA dejó vacío un dato que decide el camino, la app se lo pregunta al usuario.
        # Aquí "responde" el usuario con los valores reales del ejemplo (config.yaml > demo).
        if diag["preguntas_pendientes"]:
            for p in diag["preguntas_pendientes"]:
                datos[p["campo"]] = dcfg["respuestas_usuario"][p["campo"]]
                print(f"   (pregunta pendiente «{p['campo']}»: el usuario responde {datos[p['campo']]})")
            diag = diagnosticar(datos, cfg)
        regimen = diag["regimen"]["texto"] if diag["regimen"] else "sin régimen"
        resultados.append(paso(2, "Diagnóstico", diag["camino"] == dcfg["camino_esperado"],
                               f"camino {diag['camino']} (esperado {dcfg['camino_esperado']}); {regimen}"))
    else:
        resultados.append(paso(2, "Diagnóstico", False, "no se pudo: falló la ficha"))

    # 3. PDF de la declaración jurada (datos personales inventados; nunca pasan por la IA)
    try:
        pdf = generar_formulario(diag, datos, dcfg["datos_personales"], cfg)
        resultados.append(paso(3, "PDF", pdf.startswith(b"%PDF") and diag["camino"] == "A",
                               f"{diag['formulario']}, {len(pdf) / 1024:.0f} KB"))
    except Exception as ex:   # sin diagnóstico (TypeError) o sin formulario para el camino (ValueError)
        resultados.append(paso(3, "PDF", False, f"no se generó ({ex})"))

    # 4. Pregunta con cita
    p = responder(dcfg["pregunta_con_cita"])
    citadas = [f"{f['documento']} pág. {f['pagina']}" for f in p["fuentes"] if f["citada"]]
    ok = not p["error"] and not p["abstuvo"] and bool(citadas)
    resultados.append(paso(4, "Pregunta con cita", ok, p["error"] or f"cita {', '.join(citadas) or 'ninguna'}"))
    if ok:
        print(f"     «{p['respuesta'][:160]}…»")

    # 5. Abstención
    p = responder(dcfg["pregunta_fuera"])
    detalle = p["error"] or (f"se abstuvo ({p['motivo_abstencion']}, similitud {p['similitud_max']:.3f}, "
                             f"umbral {p['umbral']}; {'llamó' if p['llamo_llm'] else 'no llamó'} a la IA)")
    resultados.append(paso(5, "Abstención", not p["error"] and p["abstuvo"], detalle))

    # Costo total: lo que se agregó al log durante esta prueba
    nuevas = filas_del_log(cfg)[filas_antes:]
    costo = sum(float(f["costo_usd"]) for f in nuevas)
    soles = costo * cfg["costo_por_usuario"]["tipo_cambio"]["soles_por_dolar"]
    print(f"\n{sum(resultados)} de {len(resultados)} pasos OK | {len(nuevas)} llamadas a la API | "
          f"costo total US$ {costo:.5f} (S/ {soles:.4f})")
    sys.exit(0 if all(resultados) else 1)


if __name__ == "__main__":
    main()
