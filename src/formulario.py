"""PDF de la declaración jurada que corresponde al camino del diagnóstico.

    generar_pdf(camino, ficha, datos_personales) -> bytes
      - camino A: Formato de DJ para Licencia Provisional de Funcionamiento para Bodegas (1 página)
      - camino B: Formato de DJ para Licencia de Funcionamiento (Anexo 1 del D.S. 163-2020-PCM)
      - camino C: no hay formulario (ValueError)

Misma estructura de secciones, etiquetas y casillas que el formato oficial, sin logo de ninguna
municipalidad. Lo que decide la municipalidad (CIIU, giro, zonificación, nivel de riesgo) y lo que
el usuario debe decidir o firmar (casillas de la declaración, firma, croquis) queda en blanco.

`ficha` son los datos YA CONFIRMADOS por el usuario (nombre -> valor, o la salida de extraer_ficha).
`datos_personales` (nombre_completo, dni, telefono, correo) los escribe el usuario en la app: van
solo a este PDF y nunca pasan por la IA.

Las etiquetas del formato están aquí, no en config.yaml, a propósito: copian el formato oficial y
no deben cambiarse. Los textos propios (nota al pie, mensajes) sí están en config.yaml > formulario.
"""
import io
from urllib.parse import unquote
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.config import cargar_config
from src.reglas import valores

ANCHO = 18 * cm          # ancho útil de la página A4 con márgenes de 1.5 cm
GRIS = colors.HexColor("#D9D9D9")
GRIS_CLARO = colors.HexColor("#F2F2F2")
OBLIGATORIOS = ["nombre_completo", "dni"]

E_TITULO = ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=9.5, leading=12, alignment=TA_CENTER)
E_SUBTITULO = ParagraphStyle("subtitulo", fontName="Helvetica-Oblique", fontSize=8, leading=10, alignment=TA_CENTER)
E_SECCION = ParagraphStyle("seccion", fontName="Helvetica-Bold", fontSize=8, leading=10, alignment=TA_CENTER)
E_ETIQUETA = ParagraphStyle("etiqueta", fontName="Helvetica", fontSize=6.5, leading=8, alignment=TA_CENTER)
E_VALOR = ParagraphStyle("valor", fontName="Helvetica", fontSize=9, leading=11)
E_TEXTO = ParagraphStyle("texto", fontName="Helvetica", fontSize=7, leading=9)
E_NEGRITA = ParagraphStyle("negrita", fontName="Helvetica-Bold", fontSize=7, leading=9)
E_NOTA = ParagraphStyle("nota", fontName="Helvetica-Oblique", fontSize=6.5, leading=8, textColor=colors.HexColor("#444444"))


# ---------------------------------------------------------------------------
# Piezas de la tabla (todas devuelven un Table de reportlab)
# ---------------------------------------------------------------------------
def _p(texto, estilo=E_VALOR) -> Paragraph:
    texto = "" if texto is None else str(texto)
    # Un espacio duro da a las casillas vacías la altura de una línea, para escribir a mano
    return Paragraph(escape(texto) or " ", estilo)


def _tabla(filas, anchos, estilos=()) -> Table:
    t = Table(filas, colWidths=anchos)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                           *estilos]))
    return t


def encabezado(titulo: str, subtitulo: str, casillas: list[str]) -> Table:
    """Título a la izquierda; a la derecha, lo que llena la municipalidad (expediente, fecha...)."""
    filas = [[[_p(titulo, E_TITULO), _p(subtitulo, E_SUBTITULO)] if i == 0 else "", _p(c, E_TEXTO)]
             for i, c in enumerate(casillas)]
    return _tabla(filas, [12.5 * cm, 5.5 * cm], [("SPAN", (0, 0), (0, -1))])


def seccion(titulo: str) -> Table:
    return _tabla([[_p(titulo, E_SECCION)]], [ANCHO], [("BACKGROUND", (0, 0), (-1, -1), GRIS)])


def campos(etiquetas: list[str], valores_: list, anchos_cm: list[float]) -> Table:
    """Una fila de etiquetas (gris claro, letra chica) y debajo la fila de valores.
    La fila de valores crece si el texto no entra (p. ej. un distrito largo); vacía mide ~0.7 cm."""
    anchos = [a * cm for a in anchos_cm]
    filas = [[_p(e, E_ETIQUETA) for e in etiquetas], [_p(v) for v in valores_]]
    return _tabla(filas, anchos, [("BACKGROUND", (0, 0), (-1, 0), GRIS_CLARO),
                                  ("TOPPADDING", (0, 1), (-1, 1), 4), ("BOTTOMPADDING", (0, 1), (-1, 1), 4)])


def casillas_declaro(textos: list[str], marcadas: set[int] = frozenset()) -> Table:
    """Lista "Declaro (DE CORRESPONDER MARCAR CON X)": texto a la izquierda, casilla a la derecha."""
    filas = [[_p("Declaro (DE CORRESPONDER MARCAR CON X)", E_NEGRITA), ""]]
    filas += [[_p(t, E_TEXTO), _p("X" if i in marcadas else "", E_SECCION)] for i, t in enumerate(textos)]
    return _tabla(filas, [16.8 * cm, 1.2 * cm], [("SPAN", (0, 0), (-1, 0))])


def bloque_firma(datos_personales: dict) -> Table:
    """Observaciones, fecha y firma. La firma y la fecha se llenan a mano."""
    nombre = datos_personales.get("nombre_completo", "")
    dni = datos_personales.get("dni", "")
    filas = [[_p("Observaciones o comentarios del solicitante:", E_NEGRITA), ""],
             ["", ""],
             [_p("Fecha:", E_NEGRITA), ""],
             [_p("Firma del solicitante / Representante legal / Apoderado", E_NEGRITA), ""],
             ["", ""],
             [_p(f"DNI: {dni}", E_TEXTO), _p(f"Nombres y Apellidos: {nombre}", E_TEXTO)]]
    unir = [("SPAN", (0, i), (1, i)) for i in range(5)]
    t = _tabla(filas, [5 * cm, 13 * cm], unir)
    t._argH[1] = 1.2 * cm
    t._argH[4] = 1.2 * cm
    return t


def croquis(etiqueta_area: str, area) -> Table:
    """Área a la izquierda y el recuadro del croquis (en blanco) a la derecha."""
    filas = [[_p(etiqueta_area, E_ETIQUETA), _p("Croquis de ubicación", E_ETIQUETA)],
             [_p(area), ""]]
    t = _tabla(filas, [5 * cm, 13 * cm], [("BACKGROUND", (0, 0), (-1, 0), GRIS_CLARO),
                                         ("VALIGN", (0, 1), (0, 1), "TOP")])
    t._argH[1] = 4 * cm
    return t


def instrucciones(lineas: list[tuple[str, str]]) -> Table:
    contenido = [_p("INSTRUCCIONES PARA EL LLENADO", E_NEGRITA)]
    contenido += [Paragraph(f"<b>{escape(s)}</b> {escape(t)}", E_TEXTO) for s, t in lineas]
    return _tabla([[contenido]], [ANCHO])


# ---------------------------------------------------------------------------
# Datos que se repiten en los formatos
# ---------------------------------------------------------------------------
def _numero(valor) -> str:
    if valor is None:
        return ""
    return f"{valor:g}" if isinstance(valor, (int, float)) else str(valor)


def _ubicacion(v: dict, partes=("distrito", "provincia", "departamento")) -> str:
    return " / ".join(str(v[p]) for p in partes if v.get(p))


def _solicitante(dp: dict) -> list:
    """Sección "Datos del solicitante" (igual en los dos formatos). El RUC y el domicilio se llenan a mano."""
    return [
        campos(["Apellidos y Nombres / Razón social"], [dp.get("nombre_completo")], [18]),
        campos(["N° DNI / N° C.E.", "N° RUC", "N° Teléfono", "Correo electrónico"],
               [dp.get("dni"), "", dp.get("telefono"), dp.get("correo")], [4, 4, 4, 6]),
    ]


def _representante() -> Table:
    """Sección "Representante legal o apoderado": en blanco (la persona natural tramita por sí misma)."""
    return campos(["Apellidos y Nombres", "N° DNI / N° C.E.",
                   "N° de partida electrónica y asiento de inscripción SUNARP (de corresponder)",
                   "Carta Poder Simple para persona natural (de corresponder)"],
                  ["", "", "", ""], [6, 3, 4.5, 4.5])


# ---------------------------------------------------------------------------
# Camino A: DJ para Licencia Provisional de Funcionamiento para Bodegas
# ---------------------------------------------------------------------------
def _formato_bodegas(v: dict, dp: dict) -> list:
    return [
        encabezado("FORMATO DE DECLARACIÓN JURADA PARA LICENCIA PROVISIONAL DE FUNCIONAMIENTO PARA BODEGAS",
                   "LEY Nº 30877 - Ley General de Bodegueros y su Reglamento",
                   ["N° de expediente:", "Página: 1 de 1", "Fecha de recepción:"]),
        _p("VER INSTRUCCIONES PARA EL LLENADO (al final)", E_NOTA),
        seccion("I DATOS DEL SOLICITANTE"),
        *_solicitante(dp),
        campos(["Dirección: Av./Jr./Ca./Pje./Otros", "N°/Int./Mz/Lt./Otros", "Urb./AA.HH./Otros",
                "Distrito / Provincia / Departamento"], ["", "", "", ""], [5, 3.5, 4, 5.5]),
        seccion("II DATOS DEL REPRESENTANTE LEGAL O APODERADO"),
        _representante(),
        seccion("III DATOS DEL ESTABLECIMIENTO BODEGUERO"),
        campos(["Nombre de la Bodega"], [v.get("nombre_comercial")], [18]),
        # La dirección dicha en el audio va completa (calle y número) en la primera casilla
        campos(["Dirección: Av./Jr./Ca./Pje./Otros", "N°/Int./Mz/Lt./Otros", "Urb./AA.HH./Otros",
                "Distrito / Provincia / Departamento"],
               [v.get("direccion"), "", "", _ubicacion(v)], [5, 3.5, 4, 5.5]),
        croquis("Área total de la bodega (m²)", _numero(v.get("area_m2"))),
        seccion("IV DECLARACIÓN JURADA"),
        casillas_declaro([
            "Cuento con poder suficiente vigente para actuar como representante legal de la persona jurídica "
            "titular de la bodega (alternativamente, de la persona natural que represento).",
            "El establecimiento cumple con la dotación reglamentaria de estacionamientos, de corresponder de "
            "acuerdo con lo previsto en la ley.",
        ]),
        _tabla([[_p("Tengo conocimiento de que la presente declaración jurada y documentación está sujeta a la "
                    "fiscalización posterior. En caso de haber proporcionado información, documentos, formatos o "
                    "declaraciones que no corresponden a la verdad, se me aplicarán las sanciones administrativas y "
                    "penales correspondientes. Asimismo, brindaré las facilidades necesarias para las acciones de "
                    "control de la autoridad municipal competente.", E_TEXTO)]], [ANCHO]),
        bloque_firma(dp),
        instrucciones([
            ("Sección I:", "En caso de persona natural, consignar los datos personales del solicitante. En caso de "
                           "persona jurídica, consignar la razón social y el número de RUC."),
            ("Sección II:", "En caso de representación de personas naturales, adjuntar carta poder simple firmada "
                            "por el poderdante indicando de manera obligatoria su número de documento de identidad. "
                            "En caso de representación de personas jurídicas consignar los datos del representante "
                            "legal, número de partida electrónica y asiento de inscripción en la Superintendencia "
                            "Nacional de Registros Públicos (SUNARP)."),
            ("Sección III:", "Consignar los datos del establecimiento, el tipo de actividad a desarrollar. Consignar "
                             "el área total para la que solicita la licencia de funcionamiento. Consignar en el "
                             "croquis la ubicación exacta del establecimiento."),
            ("Sección IV:", "De corresponder, marcar con una X."),
        ]),
    ]


# ---------------------------------------------------------------------------
# Camino B: DJ para Licencia de Funcionamiento (Anexo 1 del D.S. 163-2020-PCM)
# ---------------------------------------------------------------------------
def _casilla(texto: str, marcada: bool = False) -> Paragraph:
    return _p(f"[{'X' if marcada else '   '}] {texto}", E_TEXTO)


def modalidad() -> Table:
    """Sección I. Se marca solo "Licencia de funcionamiento - Indeterminada": es una licencia nueva y la
    vigencia indeterminada es la regla general (TUO de la Ley 28976, art. 11). Lo demás queda en blanco."""
    columnas = [
        [_p("Licencia de funcionamiento", E_NEGRITA), _casilla("Indeterminada", True),
         _casilla("Temporal  (indicar el plazo: ____________)"),
         _casilla("Licencia de funcionamiento más autorización de anuncio publicitario (tipo de anuncio: ________)"),
         _casilla("Licencia para Cesionario"),
         _casilla("Licencias para mercados de abastos, galerías comerciales y centros comerciales")],
        [_p("Cambios o modificaciones", E_NEGRITA),
         _casilla("Cambio de denominación o nombre comercial de la persona jurídica (sólo completar secciones I, "
                  "II y III). N° de licencia: ________  Nueva denominación: ____________"),
         _casilla("Transferencia de Licencia de Funcionamiento (sólo completar secciones I, II y III y adjuntar "
                  "copia simple de contrato de transferencia). N° de licencia: ________")],
        [_p("Otros", E_NEGRITA),
         _casilla("Cese de Actividades (sólo completar secciones I, II y III). N° de licencia: ________"),
         _casilla("Otros (especificar): ____________")],
    ]
    return _tabla([columnas], [6.5 * cm, 6.5 * cm, 5 * cm], [("VALIGN", (0, 0), (-1, -1), "TOP")])


def nivel_de_riesgo() -> Table:
    """Sección VI: la llena SOLO el calificador de la municipalidad. La app nunca decide el riesgo."""
    filas = [[_casilla("ITSE Riesgo bajo"), _casilla("ITSE Riesgo medio"),
              _casilla("ITSE Riesgo alto"), _casilla("ITSE Riesgo muy alto")],
             ["", "", "", ""],
             [_p("Firma y sello del calificador municipal", E_TEXTO), "", _p("Nombres y Apellidos:", E_TEXTO), ""]]
    t = _tabla(filas, [4.5 * cm] * 4, [("SPAN", (0, 1), (-1, 1)), ("SPAN", (0, 2), (1, 2)), ("SPAN", (2, 2), (3, 2))])
    t._argH[1] = 1.2 * cm
    return t


def _formato_anexo1(v: dict, dp: dict) -> list:
    municipalidad = f"Municipalidad distrital de {v['distrito']}" if v.get("distrito") else "Municipalidad: ____________"
    subtitulo = f"LEY N° 28976 - Ley Marco de Licencia de Funcionamiento y Modificatorias · {municipalidad}"
    titulo = "FORMATO DE DECLARACIÓN JURADA PARA LICENCIA DE FUNCIONAMIENTO"
    casillas_mun = ["N° de expediente:", "Fecha de recepción:", "N° de recibo de pago:", "Fecha de pago:"]
    return [
        # --- Página 1 ---
        encabezado(titulo, subtitulo, ["Página: 1 de 2", *casillas_mun]),
        _p("VER INSTRUCCIONES PARA EL LLENADO (Página 2)", E_NOTA),
        seccion("I. MODALIDAD DEL TRÁMITE QUE SOLICITA (marcar más de una alternativa si corresponde)"),
        modalidad(),
        seccion("II. DATOS DEL SOLICITANTE"),
        *_solicitante(dp),
        campos(["Dirección: Av. / Jr. / Ca. / Pje. / Otros", "N° / Int. / Mz. / Lt. / Otros", "Urb. / AA.HH. / Otros",
                "Distrito y Provincia"], ["", "", "", ""], [5, 3.5, 4, 5.5]),
        seccion("III. DATOS DEL REPRESENTANTE LEGAL O APODERADO"),
        campos(["Apellidos y Nombres", "N° DNI / N° C.E",
                "N° de partida electrónica y asiento de inscripción SUNARP (de corresponder)"],
               ["", "", ""], [8, 4, 6]),
        seccion("IV. DATOS DEL ESTABLECIMIENTO"),
        campos(["Nombre Comercial"], [v.get("nombre_comercial")], [18]),
        # CIIU, giro y zonificación los define la municipalidad: siempre en blanco
        campos(["Código CIIU *", "Giro/s *", "Actividad", "Zonificación"], ["", "", v.get("giro"), ""], [3.5, 4, 6.5, 4]),
        campos(["Dirección: Av. / Jr. / Ca. / Pje. / Otros", "N° / Int. / Mz. / Lt. / Otros", "Urb. / AA.HH. / Otros",
                "Provincia"], [v.get("direccion"), "", "", v.get("provincia")], [5, 3.5, 4, 5.5]),
        campos(["Autorización sectorial (de corresponder): Entidad que otorga autorización",
                "Denominación de la autorización sectorial", "Fecha de autorización", "Número de autorización"],
               ["", "", "", ""], [5.5, 5.5, 3.5, 3.5]),
        croquis("Área total solicitada (m²)", _numero(v.get("area_m2"))),
        _p("* Esta información es llenada por el representante de la municipalidad", E_NOTA),
        PageBreak(),
        # --- Página 2 ---
        encabezado(titulo, subtitulo, ["Página: 2 de 2", *casillas_mun]),
        seccion("V. DECLARACIÓN JURADA"),
        casillas_declaro([
            "Cuento con poder suficiente vigente para actuar como representante legal de la persona jurídica "
            "conductora (alternativamente, de la persona natural que represento).",
            "El establecimiento cumple con las condiciones de seguridad en edificaciones y me someto a la inspección "
            "técnica que corresponda en función al riesgo, de conformidad con la legislación aplicable.",
            "Cuento con título profesional vigente y estoy habilitado por el colegio profesional correspondiente "
            "(en el caso de servicios relacionados con la salud).",
        ]),
        _tabla([[_p("Tengo conocimiento de que la presente Declaración Jurada y documentación está sujeta a la "
                    "fiscalización posterior. En caso de haber proporcionado información, documentos, formatos o "
                    "declaraciones que no corresponden a la verdad, se me aplicarán las sanciones administrativas y "
                    "penales correspondientes, declarándose la nulidad o revocatoria de la licencia o autorización "
                    "otorgada. Asimismo, brindaré las facilidades necesarias para las acciones de control de la "
                    "autoridad municipal competente.", E_TEXTO)]], [ANCHO]),
        bloque_firma(dp),
        seccion("VI. CLASIFICACIÓN DEL NIVEL DE RIESGO (Para ser llenado por el calificador designado de la "
                "municipalidad) *"),
        nivel_de_riesgo(),
        _p("* Esta información debe ser llenada por el calificador designado por la municipalidad, de acuerdo con los "
           "anexos 2 y 3 del Manual de Ejecución de Inspección Técnica de Seguridad en Edificaciones", E_NOTA),
        instrucciones([
            ("Sección I:", "Marcar con una \"X\" en la casilla según la modalidad del trámite que solicita, en caso de "
                           "corresponder puede marcar más de una alternativa. De haber marcado \"Cambio de denominación "
                           "o nombre comercial de la persona jurídica\" o \"Cese de actividades\", solo debe completar "
                           "las secciones I, II y III. De haber marcado \"Transferencia de Licencia de Funcionamiento\", "
                           "debe adjuntar una copia simple del contrato de transferencia y solo debe completar las "
                           "secciones I, II y III."),
            ("Sección II:", "En caso de persona natural, consignar los datos personales del solicitante. En caso de "
                            "persona jurídica, consignar la razón social y el número de RUC."),
            ("Sección III:", "En caso de representación de personas naturales, adjuntar carta poder simple firmada por "
                             "el poderdante indicando de manera obligatoria su número de documento de identidad. En "
                             "caso de representación de personas jurídicas consignar los datos del representante legal, "
                             "número de partida electrónica y asiento de inscripción en la Superintendencia Nacional de "
                             "Registros Públicos (SUNARP)."),
            ("Sección IV:", "Consignar los datos del establecimiento, el tipo de actividad a desarrollar y la "
                            "zonificación. Los campos correspondientes al \"Código CIIU\" y \"Giro/s\" son completados "
                            "por el representante de la municipalidad. Para aquellas actividades que, conforme al "
                            "Decreto Supremo N° 006-2013-PCM, requieran autorización sectorial previa al otorgamiento "
                            "de la licencia de funcionamiento, consignar los datos de la autorización sectorial. "
                            "Consignar el área total para la que solicita la licencia de funcionamiento. Consignar en "
                            "el croquis la ubicación exacta del establecimiento."),
            ("Sección V:", "De corresponder, marcar con una X."),
            ("Sección VI:", "Sección llenada por el calificador designado de la municipalidad."),
        ]),
    ]


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------
FORMATOS = {"A": _formato_bodegas, "B": _formato_anexo1}


def generar_pdf(camino: str, ficha: dict, datos_personales: dict, cfg: dict | None = None) -> bytes:
    """Devuelve el PDF (bytes) del formato que corresponde al camino."""
    cfg = cfg or cargar_config()
    fcfg = cfg["formulario"]
    if camino not in FORMATOS:
        raise ValueError(fcfg["sin_formulario"].format(camino=camino))
    faltan = [c for c in OBLIGATORIOS if not datos_personales.get(c)]
    if faltan:
        raise ValueError(fcfg["datos_personales_faltan"].format(campos=", ".join(faltan)))

    id_formulario = cfg["reglas"]["caminos"][camino]["formulario"]
    url = next(f["url_pdf"] for f in cfg["formularios"] if f["id"] == id_formulario)
    contenido = FORMATOS[camino](valores(ficha), datos_personales)
    contenido += [Spacer(1, 0.2 * cm), _p(fcfg["nota_pie"].format(url=unquote(url)), E_NOTA)]

    salida = io.BytesIO()
    doc = SimpleDocTemplate(salida, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                            topMargin=1.2 * cm, bottomMargin=1.2 * cm,
                            title=cfg["formularios"][[f["id"] for f in cfg["formularios"]].index(id_formulario)]["titulo"])
    doc.build(contenido)
    return salida.getvalue()
