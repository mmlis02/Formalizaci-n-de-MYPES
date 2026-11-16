"""Limpieza del texto extraído, sin perder nunca el número de página.

Unidad de trabajo: el PÁRRAFO, siempre con su página. Un párrafo que cruza de una
página a otra se deja partido en dos (uno por página) para que la cita sea exacta.

Reglas (los patrones están en config.yaml > limpieza):
  R1  Encabezado de página de El Peruano (n.° de página, "NORMAS LEGALES", fecha).
  R2  Sello de firma digital "Firmado por: Editora Peru / Fecha: ...".
  R3  Código de publicación que cierra la norma (p. ej. "2204313-3").
  R4  Ligaduras rotas ("Simpliﬁ cado" -> "Simplificado").
  R5  Encabezados de otros formatos: TUO de Editora Perú y folletos de SUNAT.
  R6  Re-armado de líneas: el PDF corta cada línea por el ancho de columna; se unen
      las líneas de un mismo párrafo.
  R7  Notas "(*)" de Editora Perú (TUO): se reescriben como etiqueta de texto vigente.

Copiado de HW_03_202602 (tarea1_rag_normativo/src/limpieza.py). Cambios:
- Nueva R5 (encabezados de Editora Perú y SUNAT).
- R7 es más simple: en el TUO de Editora Perú la nota va DESPUÉS del texto que ya está
  vigente, así que no hay texto antiguo que borrar (en HW_03, la versión SPIJ sí lo traía).
- Se quitaron los párrafos de concordancias SPIJ: ningún documento de este corpus los tiene.
"""
import re
from collections import Counter

# --- R7: notas de versión de Editora Perú ------------------------------------
# Ejemplo: "(*) Literal modificado por artículo 2 del Decreto Legislativo N° 1200 publicado el
#           23 de setiembre 2015."
NOTA_EDITORA = re.compile(
    r"\(\*\)\s*(?P<unidad>[A-ZÁÉÍÓÚ][a-záéíóú]+)\s+(?P<accion>modificad[oa]s?|incorporad[oa]s?)\s+por\s+"
    r"(?P<norma>.+?),?\s+publicad[oa]\s+el\s+(?P<fecha>\d{1,2}\s+de\s+\w+(?:\s+de)?\s+\d{4})"
    r"(?:\s*\([^)]*\))?\.?"
)

# --- Separación en párrafos para PDFs sin líneas en blanco -------------------
INICIO_ESTRUCTURAL = re.compile(
    r"^[“\"]?\s*(Artículo\s+\d+|\d+\.\d+\.?\s|[a-zñ]\)\s|\(…\)|\(\*\)|Que,|POR TANTO|DECRETA|SE DECRETA|"
    r"DISPOSICI|PRIMERA\.|SEGUNDA\.|TERCERA\.|CUARTA\.|QUINTA\.|SEXTA\.|SÉPTIMA\.|OCTAVA\.|NOVENA\.|DÉCIMA|ÚNICA\.)"
)


def limpiar_ruido_pagina(texto: str, reglas: dict, contador: Counter) -> str:
    """R1–R5 sobre el texto crudo de UNA página."""
    texto, n = re.subn(reglas["encabezado_elperuano"], "", texto)
    contador["R1_encabezado_elperuano"] += n
    texto, n = re.subn(reglas["sello_firma"], "", texto)
    contador["R2_sello_firma"] += n
    texto, n = re.subn(reglas["codigo_publicacion"], "", texto, flags=re.M)
    contador["R3_codigo_publicacion"] += n
    for mala, buena in reglas["ligaduras"].items():
        # la ligadura suele venir seguida de un espacio espurio: "Simpliﬁ cado"
        texto, n = re.subn(rf"{mala}\s*(?=[a-záéíóúñ])", buena, texto)
        contador["R4_ligaduras"] += n
        texto = texto.replace(mala, buena)
    for nombre, patron in reglas["encabezados_otros"].items():
        texto, n = re.subn(patron, "", texto)
        contador[f"R5_encabezado_{nombre}"] += n
    return texto


def _unir_lineas(lineas: list[str]) -> str:
    """R6: une las líneas de un párrafo. Si una línea termina en guion, se pega sin espacio."""
    salida = ""
    for linea in (l.strip() for l in lineas):
        if not linea:
            continue
        if salida.endswith("-"):
            salida += linea
        else:
            salida += (" " if salida else "") + linea
    return re.sub(r"\s{2,}", " ", salida).strip()


def partir_parrafos(texto: str) -> list[str]:
    """Divide el texto de una página en párrafos ya re-armados (R6).

    Ningún PDF del corpus separa párrafos con líneas en blanco: se corta cuando empieza
    una unidad (artículo, numeral, literal, nota "(*)"...) o cuando la línea anterior
    cerró una oración y la siguiente empieza con mayúscula.
    """
    grupos, actual = [], []
    for linea in texto.split("\n"):
        limpia = linea.strip()
        if not limpia:
            continue
        previo = actual[-1] if actual else ""
        cierra = re.search(r"[.:;][”\"]?$", previo)
        if actual and (INICIO_ESTRUCTURAL.match(limpia) or (cierra and limpia[:1].isupper())):
            grupos.append(actual)
            actual = []
        actual.append(limpia)
    if actual:
        grupos.append(actual)
    return [p for p in (_unir_lineas(g) for g in grupos) if p]


def etiquetar_notas_editora(parrafo: str, contador: Counter) -> tuple[str, list[dict]]:
    """R7: "(*) Literal modificado por X publicada el F." -> "[Texto vigente — Literal modificado por X, publicada el F]"."""
    registro = []

    def reemplazo(m):
        norma = " ".join(m["norma"].split())
        registro.append({"unidad": m["unidad"], "accion": m["accion"], "norma": norma, "fecha": m["fecha"]})
        return f"[Texto vigente — {m['unidad']} {m['accion']} por {norma}, publicada el {m['fecha']}]"

    parrafo, n = NOTA_EDITORA.subn(reemplazo, parrafo)
    contador["R7_nota_editora_etiquetada"] += n
    if "(*)" in parrafo:
        contador["R7_nota_no_reconocida"] += parrafo.count("(*)")
    return parrafo, registro


def limpiar_documento(paginas: list[dict], doc_id: str, reglas: dict) -> tuple[list[dict], Counter, list[dict]]:
    """Aplica R1–R7 a un documento. Devuelve (paginas_limpias, contador_de_reglas, registro_de_versiones)."""
    contador = Counter()
    con_notas = doc_id in reglas["documentos_con_notas_editora"]
    registro = []
    limpias = []
    for pag in paginas:
        texto = limpiar_ruido_pagina(pag["texto"], reglas, contador)
        parrafos = partir_parrafos(texto)
        if con_notas:
            etiquetados = []
            for par in parrafos:
                par, reg = etiquetar_notas_editora(par, contador)
                registro += [{**r, "pagina": pag["pagina"]} for r in reg]
                etiquetados.append(par)
            parrafos = etiquetados
        if parrafos:
            limpias.append({"pagina": pag["pagina"], "texto": "\n\n".join(parrafos)})
    return limpias, contador, registro
