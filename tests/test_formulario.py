"""PDF de la declaración jurada: se lee el texto del PDF generado y se revisa qué quedó escrito."""
import pymupdf
import pytest

from src.formulario import generar_pdf

FICHA_BODEGA = {"giro": "bodega", "nombre_comercial": "Bodega Doña Rosa", "direccion": "jirón Los Claveles 120",
                "distrito": "San Juan de Lurigancho", "provincia": "Lima", "departamento": "Lima", "area_m2": 25}
# Datos personales INVENTADOS (nunca usar datos reales en pruebas)
PERSONA = {"nombre_completo": "Rosa Prueba Inventada", "dni": "00000000", "telefono": "900000000",
           "correo": "rosa@ejemplo.pe"}


def texto_pdf(pdf: bytes) -> tuple[int, str]:
    doc = pymupdf.open(stream=pdf)
    return len(doc), " ".join(" ".join(p.get_text().split()) for p in doc)


def test_pdf_bodegas_una_pagina_con_los_datos(cfg):
    paginas, texto = texto_pdf(generar_pdf("A", FICHA_BODEGA, PERSONA, cfg))
    assert paginas == 1                                     # como el formato oficial
    assert "LICENCIA PROVISIONAL DE FUNCIONAMIENTO PARA BODEGAS" in texto
    for dato in ["Bodega Doña Rosa", "jirón Los Claveles 120", "San Juan de Lurigancho / Lima / Lima",
                 "Rosa Prueba Inventada", "00000000", "900000000", "rosa@ejemplo.pe"]:
        assert dato in texto, dato
    for seccion in ["I DATOS DEL SOLICITANTE", "II DATOS DEL REPRESENTANTE", "III DATOS DEL ESTABLECIMIENTO",
                    "IV DECLARACIÓN JURADA"]:
        assert seccion in texto


def test_pdf_bodegas_no_marca_casillas_por_el_usuario(cfg):
    _, texto = texto_pdf(generar_pdf("A", FICHA_BODEGA, PERSONA, cfg))
    assert " X " not in f" {texto} "          # las casillas del "Declaro" las marca el usuario


def test_acepta_la_salida_de_extraer_ficha(cfg):
    ficha = {"campos": {n: {"valor": v, "estado": "verificado"} for n, v in FICHA_BODEGA.items()}}
    _, texto = texto_pdf(generar_pdf("A", ficha, PERSONA, cfg))
    assert "Bodega Doña Rosa" in texto


def test_camino_C_no_tiene_formulario(cfg):
    with pytest.raises(ValueError, match="camino C"):
        generar_pdf("C", FICHA_BODEGA, PERSONA, cfg)


def test_faltan_datos_personales(cfg):
    with pytest.raises(ValueError, match="dni"):
        generar_pdf("A", FICHA_BODEGA, {"nombre_completo": "Rosa Prueba Inventada"}, cfg)


FICHA_PELUQUERIA = {"giro": "peluquería y barbería", "nombre_comercial": "Estilos Marita",
                    "direccion": "avenida Los Próceres 456", "distrito": "Santiago de Surco", "provincia": "Lima",
                    "area_m2": 35}


def test_pdf_anexo1_dos_paginas_con_los_datos(cfg):
    paginas, texto = texto_pdf(generar_pdf("B", FICHA_PELUQUERIA, PERSONA, cfg))
    assert paginas == 2                                     # como el formato oficial
    assert "FORMATO DE DECLARACIÓN JURADA PARA LICENCIA DE FUNCIONAMIENTO" in texto
    for dato in ["Estilos Marita", "peluquería y barbería", "avenida Los Próceres 456",
                 "Municipalidad distrital de Santiago de Surco", "Rosa Prueba Inventada", "00000000"]:
        assert dato in texto, dato
    for seccion in ["I. MODALIDAD", "II. DATOS DEL SOLICITANTE", "III. DATOS DEL REPRESENTANTE",
                    "IV. DATOS DEL ESTABLECIMIENTO", "V. DECLARACIÓN JURADA", "VI. CLASIFICACIÓN DEL NIVEL DE RIESGO"]:
        assert seccion in texto


def test_pdf_anexo1_solo_marca_licencia_indeterminada(cfg):
    _, texto = texto_pdf(generar_pdf("B", FICHA_PELUQUERIA, PERSONA, cfg))
    assert texto.count("[X]") == 1 and "[X] Indeterminada" in texto
    assert "[ ] ITSE Riesgo bajo" in texto                  # el nivel de riesgo lo decide la municipalidad


def test_pdf_anexo1_deja_en_blanco_lo_que_llena_la_municipalidad(cfg):
    """Código CIIU, Giro/s y Zonificación: la fila de valores solo tiene la actividad."""
    doc = pymupdf.open(stream=generar_pdf("B", FICHA_PELUQUERIA, PERSONA, cfg))
    pagina = doc[0]
    fila_ciiu = pagina.search_for("Código CIIU")[0]
    actividad = pagina.search_for("peluquería y barbería")[0]
    # Todo el texto en la franja de la fila de valores (debajo de las etiquetas) es solo la actividad
    franja = pymupdf.Rect(0, fila_ciiu.y1 + 1, pagina.rect.width, actividad.y1 + 1)
    assert " ".join(pagina.get_text(clip=franja).split()) == "peluquería y barbería"
