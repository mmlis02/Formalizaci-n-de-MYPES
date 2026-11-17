"""Reporte del paso 5: fragmentos por documento y distribución de longitudes.

Lee data/processed/fragmentos_<alias>.json (lo escribe build_index.py).
Escribe data/processed/reporte_fragmentos.md y distribucion_fragmentos.png

Adaptado de HW_03_202602 (tarea1_rag_normativo/scripts/reporte_fragmentos.py). Allí se
comparaban cinco configuraciones de fragmentos con el set de evaluación; aquí se usa una
sola (la que ganó en HW_03), así que el reporte describe esa configuración por documento.

Uso (desde la raíz del proyecto):
    python scripts/reporte_fragmentos.py
"""
import json
import statistics
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import cargar_config, ruta  # noqa: E402
from src.fragmentos import fragmentar_documento  # noqa: E402


def main():
    cfg = cargar_config()
    mcfg = cfg["embeddings"]["modelos"][cfg["embeddings"]["modelo_activo"]]
    elegida = cfg["fragmentos"]["elegida"]
    conf = cfg["fragmentos"]["configuraciones"][elegida]
    frag = json.loads((ruta(cfg, "processed") / f"fragmentos_{mcfg['alias']}.json").read_text(encoding="utf-8"))[elegida]
    docs = [d for d in cfg["documentos"] if d["incluir"]]

    # Longitudes por documento (se vuelven a fragmentar: es barato y no llama a la API)
    por_doc = {}
    for d in docs:
        chars = [f["metadatos"]["chars"] for f in fragmentar_documento(d, ruta(cfg, "processed"), conf["tamano"], conf["solape"])]
        por_doc[d["id"]] = chars

    L = ["# Fragmentos e índice (Bloque 1, paso 5)", "",
         f"Modelo de embeddings: `{mcfg['nombre']}` (límite {mcfg['max_tokens']} tokens). "
         f"Configuración: **{elegida}** (tamaño {conf['tamano']} caracteres, solape {conf['solape']}).", "",
         f"Total: **{frag['fragmentos_total']} fragmentos** (la colección tiene {frag['coleccion_count']}).", "",
         "## Fragmentos por documento", "",
         "| Documento | Fragmentos | Páginas | chars mín / mediana / máx |", "|---|---|---|---|"]
    for d in docs:
        ch = por_doc[d["id"]]
        paginas = sum(1 for _ in open(ruta(cfg, "processed") / f"{d['id']}.jsonl", encoding="utf-8"))
        L.append(f"| {d['id']} | {frag['fragmentos_por_documento'][d['id']]} | {paginas} | "
                 f"{min(ch)} / {int(statistics.median(ch))} / {max(ch)} |")
    ch, tk = frag["chars"], frag["tokens"]
    L += ["", "## Distribución de longitudes (todo el corpus)", "",
          "| Medida | mín | mediana | p90 | máx |", "|---|---|---|---|---|",
          f"| caracteres | {ch['min']} | {ch['mediana']} | {ch['p90']} | {ch['max']} |",
          f"| tokens | {tk['min']} | {tk['mediana']} | {tk['p90']} | {tk['max']} |", "",
          f"Fragmentos sobre el límite de {tk['limite']} tokens: **{tk['sobre_limite']}**.",
          "Tokens = lo que realmente ve el modelo: encabezado corto del documento + texto.", "",
          "![Distribución](distribucion_fragmentos.png)"]
    (ruta(cfg, "processed") / "reporte_fragmentos.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    fig, ax = plt.subplots(figsize=(7, 3.4))
    ax.hist(frag["tokens_lista"], bins=25, color="#4C78A8")
    ax.set_title(f"{elegida}: {frag['fragmentos_total']} fragmentos")
    ax.set_xlabel("tokens por fragmento")
    ax.set_ylabel("n.º de fragmentos")
    fig.tight_layout()
    fig.savefig(ruta(cfg, "processed") / "distribucion_fragmentos.png", dpi=120)
    print("\n".join(L))


if __name__ == "__main__":
    main()
