"""Evalúa la ficha: ¿la IA extrae bien cada campo, y la verificación detecta cuándo no?

Corre procesar_texto (el mismo que usa la app) sobre los casos de eval/casos_ficha.yaml, cada uno
2 veces (el LLM no siempre responde igual), y compara cada campo con su valor correcto.

Por campo reporta:
  - % correcto       : el valor extraído es el correcto (null cuenta como correcto si el texto no lo dice)
  - % verificado     : quedó "verificado" (su cita y su valor están en el texto)
  - % por confirmar  : quedó "por_confirmar" (el usuario tiene que revisarlo)
  - verificado e INCORRECTO: el caso peligroso; la verificación no lo detectó
  - cambios          : casos en que las 2 corridas dieron valores distintos
Los 3 sí/no que deciden el camino siempre quedan "por_confirmar" (config.yaml > ficha), así que
en ellos solo importa el % correcto.

Cuesta centavos: 8 casos x 2 corridas = 16 llamadas al LLM (~US$ 0.004).

Uso (desde la raíz del proyecto):
    python -m eval.evaluar_ficha
"""
import csv
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import BASE, cargar_config  # noqa: E402
from src.ficha import CAMPOS, _contiene, normalizar  # noqa: E402
from src.motor import procesar_texto  # noqa: E402


def es_correcto(tipo: str, obtenido, esperado) -> bool:
    """Compara un valor extraído con el correcto.

    - null: correcto solo si la IA también lo dejó vacío.
    - números: iguales (28 == 28.0).
    - sí/no: iguales.
    - textos: iguales tras normalizar (sin tildes ni mayúsculas), o uno contiene al otro como
      palabras completas ("Los Pinos 245" dentro de "jirón Los Pinos 245").
    - lista: basta con que coincida con uno de los valores aceptados.
    """
    if isinstance(esperado, list):
        return any(es_correcto(tipo, obtenido, e) for e in esperado)
    if esperado is None or obtenido is None:
        return esperado is None and obtenido is None
    if tipo == "numero":
        return abs(float(obtenido) - float(esperado)) < 0.01
    if tipo == "si_no":
        return obtenido == esperado
    o, e = normalizar(str(obtenido)), normalizar(str(esperado))
    return o == e or _contiene(o, e) or _contiene(e, o)


def correr(casos: list[dict], repeticiones: int, cfg: dict) -> tuple[list[dict], list[dict]]:
    """Devuelve (filas por campo, filas por corrida)."""
    filas, corridas = [], []
    for caso in casos:
        for corrida in range(1, repeticiones + 1):
            r = procesar_texto(caso["texto"], cfg)
            camino = r["diagnostico"]["camino"] if r["diagnostico"] else None
            corridas.append({"caso": caso["id"], "corrida": corrida, "error": r["error"] or "",
                             "camino_esperado": caso["camino_esperado"], "camino_preliminar": camino,
                             "costo_usd": r["costo_usd"]})
            print(f"{caso['id']} corrida {corrida}: camino {camino} (esperado {caso['camino_esperado']})"
                  + (f" ERROR {r['error']}" if r["error"] else ""))
            if r["error"]:
                continue
            for nombre, tipo in CAMPOS.items():
                c = r["ficha"]["campos"][nombre]
                filas.append({"caso": caso["id"], "corrida": corrida, "campo": nombre,
                              "esperado": caso["esperado"][nombre], "obtenido": c["valor"],
                              "estado": c["estado"],
                              "correcto": es_correcto(tipo, c["valor"], caso["esperado"][nombre]),
                              "cita": c["cita"]})
    return filas, corridas


def resumir(filas: list[dict]) -> list[dict]:
    """Una fila por campo con los porcentajes y los conteos."""
    resumen = []
    for nombre in list(CAMPOS) + ["TOTAL"]:
        f = [x for x in filas if nombre == "TOTAL" or x["campo"] == nombre]
        n = len(f)
        # ¿Cambió el valor entre corridas? (se compara por caso)
        valores_por_caso = {}
        for x in f:
            valores_por_caso.setdefault((x["caso"], x["campo"]), set()).add(repr(x["obtenido"]))
        resumen.append({
            "campo": nombre,
            "n": n,
            "correcto_pct": round(100 * sum(x["correcto"] for x in f) / n),
            "verificado_pct": round(100 * sum(x["estado"] == "verificado" for x in f) / n),
            "por_confirmar_pct": round(100 * sum(x["estado"] == "por_confirmar" for x in f) / n),
            "verificado_incorrecto": sum(x["estado"] == "verificado" and not x["correcto"] for x in f),
            "cambios_entre_corridas": sum(len(v) > 1 for v in valores_por_caso.values()),
        })
    return resumen


def tabla_markdown(resumen: list[dict], corridas: list[dict], filas: list[dict], n_casos: int) -> str:
    lineas = ["| Campo | % correcto | % verificado | % por confirmar | Verificado pero incorrecto | Casos que cambian entre corridas |",
              "|---|---|---|---|---|---|"]
    for r in resumen:
        nombre = f"**{r['campo']}**" if r["campo"] == "TOTAL" else f"`{r['campo']}`"
        lineas.append(f"| {nombre} | {r['correcto_pct']} % | {r['verificado_pct']} % | {r['por_confirmar_pct']} % "
                      f"| {r['verificado_incorrecto']} | {r['cambios_entre_corridas']} de {n_casos if r['campo'] != 'TOTAL' else n_casos * len(CAMPOS)} |")
    ok = [c for c in corridas if not c["error"]]
    caminos_bien = sum(c["camino_preliminar"] == c["camino_esperado"] for c in ok)
    lineas += ["", f"Camino preliminar correcto: {caminos_bien} de {len(ok)} corridas. "
               f"Errores de API: {len(corridas) - len(ok)}. Costo total: US$ {sum(c['costo_usd'] for c in corridas):.4f}."]
    errores = [x for x in filas if x["estado"] == "verificado" and not x["correcto"]]
    if errores:
        lineas += ["", "Verificados con valor incorrecto:"]
        lineas += [f"- {x['caso']} (corrida {x['corrida']}) `{x['campo']}`: dio {x['obtenido']!r}, "
                   f"lo correcto es {x['esperado']!r} (cita: «{x['cita']}»)" for x in errores]
    return "\n".join(lineas)


def main():
    cfg = cargar_config()
    ecfg = cfg["evaluacion_ficha"]
    casos = yaml.safe_load(open(BASE / ecfg["casos"], encoding="utf-8"))
    filas, corridas = correr(casos, ecfg["repeticiones"], cfg)
    resumen = resumir(filas)

    salida = BASE / ecfg["resultados"]
    with open(salida / "ficha_detalle.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    texto = tabla_markdown(resumen, corridas, filas, len(casos))
    (salida / "ficha_resumen.md").write_text(
        f"# Evaluación de la ficha ({len(casos)} casos inventados x {ecfg['repeticiones']} corridas)\n\n"
        f"Muestra pequeña: sirve para ver patrones, no para dar una tasa de error confiable.\n\n{texto}\n",
        encoding="utf-8")
    print("\n" + texto)
    print(f"\nDetalle: {ecfg['resultados']}/ficha_detalle.csv | resumen: {ecfg['resultados']}/ficha_resumen.md")


if __name__ == "__main__":
    main()
