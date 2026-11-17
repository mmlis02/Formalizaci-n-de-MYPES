"""extraer_ficha con un cliente falso: esquema, verificación de cada campo, errores y costo."""
import csv

from src.ficha import CAMPOS, esquema_ficha, extraer_ficha
from tests.conftest import TRANSCRIPCION, ClienteFalso


def test_esquema_tiene_todos_los_campos_y_ninguno_personal(cfg):
    esquema = esquema_ficha(cfg)["schema"]
    assert set(esquema["required"]) == set(CAMPOS) == set(cfg["ficha"]["campos"])
    for personal in ("nombre_completo", "dni", "telefono", "correo"):
        assert personal not in esquema["properties"]  # nunca se piden a la IA


def test_extraer_ficha_marca_lo_inventado_como_por_confirmar(cfg, respuesta_llm):
    r = extraer_ficha(TRANSCRIPCION, cfg, ClienteFalso(respuesta_llm))
    assert r["error"] is None
    estados = {n: c["estado"] for n, c in r["campos"].items()}
    assert estados["distrito"] == "por_confirmar"     # la IA lo "corrigió"
    assert estados["provincia"] == "por_confirmar"    # la IA lo dedujo
    assert estados["ventas_mensuales"] == "verificado"
    assert estados["piso"] == "verificado"
    assert estados["tiene_local_al_publico"] == "no_mencionado"
    assert r["resumen"] == {"verificado": 10, "por_confirmar": 2, "no_mencionado": 2}
    assert r["campos"]["area_m2"]["etiqueta"] == cfg["ficha"]["campos"]["area_m2"]["etiqueta"]


def test_texto_vacio_no_llama_a_la_ia(cfg):
    cliente = ClienteFalso({})
    r = extraer_ficha("   ", cfg, cliente)
    assert r["error"] == cfg["ficha"]["mensajes"]["texto_vacio"]
    assert cliente.llamadas_llm == 0


def test_error_de_api_vuelve_como_error(cfg):
    r = extraer_ficha(TRANSCRIPCION, cfg, ClienteFalso(falla=True))
    assert r["error"].startswith(cfg["ficha"]["mensajes"]["error_api"])
    assert r["campos"] == {}


def test_log_de_costos_no_guarda_lo_que_conto_el_usuario(cfg, respuesta_llm):
    extraer_ficha(TRANSCRIPCION, cfg, ClienteFalso(respuesta_llm))
    filas = list(csv.DictReader(open(cfg["precios"]["log_llamadas"], encoding="utf-8")))
    assert len(filas) == 1 and filas[0]["exito"] == "True"
    assert "Doña Rosa" not in filas[0]["pregunta"]
    assert float(filas[0]["costo_usd"]) > 0
