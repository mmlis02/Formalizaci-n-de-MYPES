"""procesar_audio / procesar_texto: unen voz -> ficha y suman los costos."""
from src.motor import procesar_audio, procesar_texto
from tests.conftest import ClienteFalso


def test_procesar_audio_completo(cfg, tmp_path, respuesta_llm):
    archivo = tmp_path / "audio.m4a"
    archivo.write_bytes(b"audio falso")
    cliente = ClienteFalso(respuesta_llm)
    r = procesar_audio(archivo, cfg, cliente)
    assert r["error"] is None
    assert r["ficha"]["campos"]["ventas_mensuales"]["estado"] == "verificado"
    assert r["costo_usd"] == r["costos"]["voz"] + r["costos"]["ficha"] > 0
    assert cliente.llamadas_audio == 1 and cliente.llamadas_llm == 1


def test_si_falla_el_audio_no_se_llama_al_llm(cfg, tmp_path):
    cliente = ClienteFalso({})
    r = procesar_audio(tmp_path / "no_existe.m4a", cfg, cliente)
    assert r["error"] and r["ficha"] is None
    assert cliente.llamadas_llm == 0


def test_procesar_texto_vacio(cfg):
    r = procesar_texto("", cfg, ClienteFalso({}))
    assert r["error"] == cfg["ficha"]["mensajes"]["texto_vacio"]
