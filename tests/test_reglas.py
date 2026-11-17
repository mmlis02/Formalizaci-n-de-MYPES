"""Reglas del diagnóstico: un caso de cada camino (A, B, C), la pregunta pendiente y el Nuevo RUS."""
import copy

import pytest

from src.reglas import diagnosticar

BODEGA_A = {  # bodega que cumple todo: camino A
    "giro": "bodega", "tiene_local_al_publico": True, "area_m2": 25, "en_vivienda": True, "piso": 1,
    "acceso_directo_via_publica": True, "ventas_mensuales": 4500, "compras_mensuales": 3000, "tiene_ruc": False,
}


def test_camino_A_bodega_que_cumple(cfg):
    d = diagnosticar(BODEGA_A, cfg)
    assert d["camino"] == "A" and d["completo"]
    assert d["formulario"] == "dj_bodegas"
    assert all(c["cumple"] for c in d["condiciones_bodega"])
    assert d["regimen"]["codigo"] == "nrus_1" and d["regimen"]["cuota"] == 20
    assert len(d["checklist"]) == 5          # RUC, régimen, licencia, seguridad, ITSE
    assert all(p["fuente"] for p in d["checklist"])
    assert cfg["reglas"]["aviso_riesgo_bodega"] in d["avisos"]


def test_camino_B_otro_negocio_con_local(cfg):
    d = diagnosticar({"giro": "peluquería", "tiene_local_al_publico": True,
                      "ventas_mensuales": 6000, "compras_mensuales": 2000}, cfg)
    assert d["camino"] == "B" and d["formulario"] == "dj_licencia_funcionamiento"
    assert d["condiciones_bodega"] == []     # no es bodega: no se revisan
    assert d["regimen"]["codigo"] == "nrus_2"


def test_camino_B_bodega_que_no_cumple_el_area(cfg):
    d = diagnosticar({**BODEGA_A, "area_m2": 80}, cfg)
    assert d["camino"] == "B"
    assert "50 m²" in d["explicacion"]       # dice qué condición falló


def test_camino_C_sin_local(cfg):
    d = diagnosticar({"giro": "venta de postres por Instagram", "tiene_local_al_publico": False,
                      "ventas_mensuales": 1500, "compras_mensuales": 600}, cfg)
    assert d["camino"] == "C" and d["formulario"] is None
    assert d["regimen"]["codigo"] == "nrus_1"
    assert len(d["checklist"]) == 3          # RUC, régimen, preguntar en la municipalidad


def test_sin_dato_de_local_queda_como_pregunta_pendiente(cfg):
    d = diagnosticar({**BODEGA_A, "tiene_local_al_publico": None}, cfg)
    assert d["camino"] is None and not d["completo"]
    assert [p["campo"] for p in d["preguntas_pendientes"]] == ["tiene_local_al_publico"]
    assert d["preguntas_pendientes"][0]["pregunta"] == cfg["reglas"]["preguntas"]["tiene_local_al_publico"]
    assert d["regimen"]["codigo"] == "nrus_1"   # el régimen no depende del local


def test_bodega_sin_area_pregunta_el_area(cfg):
    d = diagnosticar({**BODEGA_A, "area_m2": None}, cfg)
    assert d["camino"] is None
    assert [p["campo"] for p in d["preguntas_pendientes"]] == ["area_m2"]


@pytest.mark.parametrize("ventas, compras, codigo", [
    (5000, 1000, "nrus_1"),      # justo en el límite de la categoría 1
    (5001, 1000, "nrus_2"),
    (4000, 6000, "nrus_2"),      # las compras también cuentan
    (8000, 8000, "nrus_2"),
    (8001, 1000, "fuera_nrus"),
])
def test_categorias_del_nuevo_rus(cfg, ventas, compras, codigo):
    d = diagnosticar({**BODEGA_A, "ventas_mensuales": ventas, "compras_mensuales": compras}, cfg)
    assert d["regimen"]["codigo"] == codigo


def test_sin_compras_el_regimen_es_provisional(cfg):
    d = diagnosticar({**BODEGA_A, "compras_mensuales": None}, cfg)
    assert d["regimen"]["codigo"] == "nrus_1" and d["regimen"]["provisional"]
    assert "compras_mensuales" in [p["campo"] for p in d["preguntas_pendientes"]]


def test_aviso_de_autorizacion_sectorial(cfg):
    d = diagnosticar({"giro": "restaurante de comida criolla", "tiene_local_al_publico": True,
                      "ventas_mensuales": 7000, "compras_mensuales": 4000}, cfg)
    assert d["camino"] == "B"
    assert any("autorización sectorial" in a for a in d["avisos"])


def test_acepta_la_salida_de_extraer_ficha(cfg):
    ficha = {"campos": {n: {"valor": v, "estado": "verificado"} for n, v in BODEGA_A.items()}}
    assert diagnosticar(ficha, cfg)["camino"] == "A"


def test_cambiar_el_area_maxima_en_config_cambia_el_camino(cfg):
    """El cambio que se practica en vivo: config.yaml > reglas > bodega > area_max_m2."""
    otro = copy.deepcopy(cfg)
    otro["reglas"]["bodega"]["area_max_m2"] = 20
    assert diagnosticar(BODEGA_A, cfg)["camino"] == "A"
    assert diagnosticar(BODEGA_A, otro)["camino"] == "B"
