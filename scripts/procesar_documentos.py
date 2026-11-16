"""Bloque 1, paso 4: extrae y limpia los documentos del corpus, y escribe el reporte de calidad.

Salidas en data/processed/:
  <id>.jsonl                       una línea por página: documento, página y texto limpio
  versiones_<id>.json              cada nota "(*)" de Editora Perú etiquetada (norma y fecha)
  reporte_calidad_extraccion.md    reporte legible (también lo mostrará la app)
  reporte_calidad_extraccion.json  lo mismo en formato para programas
  ejemplos_limpieza.md             ejemplos antes/después de cada regla

Copiado de HW_03_202602 (tarea1_rag_normativo/scripts/procesar_documentos.py) y
adaptado a las reglas y documentos de este corpus.

Uso (desde la raíz del proyecto):
    python scripts/procesar_documentos.py
"""
import json
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import cargar_config, ruta  # noqa: E402
from src.extraccion import extraer_paginas  # noqa: E402
from src.limpieza import limpiar_documento  # noqa: E402

DESCRIPCION_REGLAS = {
    "R1_encabezado_elperuano": "R1 Encabezado de página de El Peruano eliminado",
    "R2_sello_firma": "R2 Sello 'Firmado por: Editora Peru' eliminado",
    "R3_codigo_publicacion": "R3 Código de publicación de cierre eliminado",
    "R4_ligaduras": "R4 Ligaduras rotas corregidas",
    "R5_encabezado_editora_peru": "R5 Encabezado de Editora Perú (TUO) eliminado",
    "R5_encabezado_sunat_nuevo_rus": "R5 Encabezado del folleto Nuevo RUS eliminado",
    "R5_encabezado_sunat_numeros_pagina": "R5 Números de página impresos del folleto SUNAT eliminados",
    "R7_nota_editora_etiquetada": "R7 Notas (*) de Editora Perú convertidas en etiqueta de texto vigente",
    "R7_nota_no_reconocida": "R7 Notas (*) NO reconocidas (revisar)",
}

# Ejemplos antes/después: (título, documento, página, texto donde centrar la muestra o None = inicio)
EJEMPLOS = [
    ("R1 + R6 — Encabezado de El Peruano y líneas cortadas por la columna", "ds010_2020_produce", 3, None),
    ("R1 — Encabezado de El Peruano con fecha y diario en la misma línea", "ley30877", 1, None),
    ("Recorte + R3 — Fin de la norma y código de publicación", "ley31866", 1, "Presidente del Consejo"),
    ("R5 — Encabezado de Editora Perú (TUO actualizado)", "tuo_ley28976", 4, None),
    ("R7 — Nota '(*)' de Editora Perú convertida en etiqueta de texto vigente", "tuo_ley28976", 3, "(*)"),
    ("R5 — Título repetido y números de página del folleto Nuevo RUS", "sunat_nuevo_rus", 5, None),
    ("R4 — Ligadura rota en el folleto Nuevo RUS", "sunat_nuevo_rus", 1, "Simpli"),
]


def muestra(texto: str, centro: str | None, n: int = 420) -> str:
    """Trozo de `texto` alrededor de `centro` (o el inicio si es None)."""
    i = texto.find(centro) if centro else 0
    i = max(0, i - 150) if i > 0 else 0
    return texto[i:i + n].strip()


def main():
    cfg = cargar_config()
    raw, processed = ruta(cfg, "raw"), ruta(cfg, "processed")
    processed.mkdir(parents=True, exist_ok=True)
    reglas = cfg["limpieza"]

    reporte, crudos, limpios_por_doc = [], {}, {}
    for doc in (d for d in cfg["documentos"] if d["incluir"]):
        pdf = pymupdf.open(raw / doc["archivo"])
        texto_pdf = [p.get_text() for p in pdf]
        paginas = extraer_paginas(raw / doc["archivo"], doc.get("recorte"))
        limpias, contador, registro = limpiar_documento(paginas, doc["id"], reglas)
        crudos[doc["id"]] = {p["pagina"]: p["texto"] for p in paginas}
        limpios_por_doc[doc["id"]] = {p["pagina"]: p["texto"] for p in limpias}

        # Salida principal: una línea JSON por página, con su número de página del PDF
        with open(processed / f"{doc['id']}.jsonl", "w", encoding="utf-8") as f:
            for p in limpias:
                f.write(json.dumps({"documento": doc["id"], "pagina": p["pagina"], "texto": p["texto"],
                                    "chars": len(p["texto"])}, ensure_ascii=False) + "\n")
        if registro:
            (processed / f"versiones_{doc['id']}.json").write_text(
                json.dumps(registro, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        # Páginas descartadas: en el PDF pero sin texto de la norma después de recortar/limpiar
        conservadas = {p["pagina"] for p in limpias}
        con_texto_norma = {p["pagina"] for p in paginas}
        descartadas = []
        for n in range(1, len(pdf) + 1):
            if n not in con_texto_norma:
                descartadas.append({"pagina": n, "motivo": "pertenece solo a otra norma (recorte El Peruano)"})
            elif n not in conservadas:
                descartadas.append({"pagina": n, "motivo": "quedó vacía tras la limpieza (solo ruido)"})

        medio = limpias[len(limpias) // 2]
        reporte.append({
            "documento": doc["id"],
            "titulo": doc["titulo"],
            "paginas_pdf": len(pdf),
            "paginas_conservadas": len(limpias),
            "paginas_descartadas": descartadas,
            "chars_pdf_completo": sum(len(t) for t in texto_pdf),
            "chars_de_la_norma_tras_recorte": sum(len(p["texto"]) for p in paginas),
            "chars_limpios": sum(len(p["texto"]) for p in limpias),
            "reglas_aplicadas": {k: v for k, v in contador.items() if v},
            "notas_de_version": len(registro),
            "muestra_pagina": medio["pagina"],
            "muestra_texto": medio["texto"][:700].strip(),
        })

    # --- Reporte legible ----------------------------------------------------------
    lineas = ["# Reporte de calidad de extracción (Bloque 1, paso 4)", "",
              "Generado por `scripts/procesar_documentos.py`. 'chars' = caracteres.", "",
              "| Documento | Págs. PDF | Págs. conservadas | Págs. descartadas | chars PDF completo | chars de la norma (tras recorte) | chars limpios |",
              "|---|---|---|---|---|---|---|"]
    for r in reporte:
        lineas.append(f"| {r['documento']} | {r['paginas_pdf']} | {r['paginas_conservadas']} | {len(r['paginas_descartadas'])} | "
                      f"{r['chars_pdf_completo']:,} | {r['chars_de_la_norma_tras_recorte']:,} | {r['chars_limpios']:,} |")
    for r in reporte:
        lineas += ["", f"## {r['documento']} — {r['titulo']}", ""]
        if r["paginas_descartadas"]:
            lineas += [f"- Página {d['pagina']} descartada: {d['motivo']}" for d in r["paginas_descartadas"]]
        else:
            lineas.append("- Páginas descartadas: ninguna.")
        if r["notas_de_version"]:
            lineas.append(f"- Notas de versión etiquetadas: **{r['notas_de_version']}** "
                          f"(detalle en `versiones_{r['documento']}.json`).")
        lineas += ["", "Reglas de limpieza aplicadas:", ""]
        lineas += [f"- {DESCRIPCION_REGLAS.get(k, k)}: **{v}**" for k, v in r["reglas_aplicadas"].items()] or ["- ninguna"]
        lineas += ["", f"Muestra del texto limpio (página {r['muestra_pagina']}, mitad del documento):", "",
                   "```text", r["muestra_texto"], "```"]
    (processed / "reporte_calidad_extraccion.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    (processed / "reporte_calidad_extraccion.json").write_text(
        json.dumps(reporte, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # --- Ejemplos antes / después ------------------------------------------------
    ej = ["# Ejemplos de limpieza: antes y después", ""]
    for titulo, doc_id, pagina, centro in EJEMPLOS:
        antes = crudos[doc_id][pagina]
        despues = limpios_por_doc[doc_id].get(pagina, "")
        # En el texto limpio la nota ya no dice "(*)": se centra en la etiqueta nueva
        centro_despues = "[Texto vigente" if centro and centro.startswith("(*)") else centro
        ej += [f"## {titulo} ({doc_id}, pág. {pagina})", "", "**Antes (texto crudo del PDF):**", "",
               "```text", muestra(antes, centro), "```", "", "**Después (texto limpio):**", "",
               "```text", muestra(despues, centro_despues), "```", ""]
    (processed / "ejemplos_limpieza.md").write_text("\n".join(ej), encoding="utf-8")

    print("\n".join(lineas[:6 + len(reporte)]))
    no_reconocidas = sum(r["reglas_aplicadas"].get("R7_nota_no_reconocida", 0) for r in reporte)
    print(f"\nNotas (*) no reconocidas: {no_reconocidas}")
    print(f"Archivos escritos en {processed}")


if __name__ == "__main__":
    main()
