"""transcribir(): revisa el archivo antes de llamar a la API y calcula el costo por minuto."""
from src.voz import transcribir
from tests.conftest import ClienteFalso


def test_archivo_inexistente_no_llama_a_la_api(cfg, tmp_path):
    cliente = ClienteFalso()
    r = transcribir(tmp_path / "no_existe.m4a", cfg, cliente)
    assert r["error"] == cfg["voz"]["mensajes"]["no_existe"]
    assert cliente.llamadas_audio == 0 and r["costo_usd"] == 0


def test_formato_no_admitido(cfg, tmp_path):
    archivo = tmp_path / "nota.txt"
    archivo.write_text("hola")
    r = transcribir(archivo, cfg, ClienteFalso())
    assert "txt" in r["error"]


def test_transcripcion_y_costo_por_minuto(cfg, tmp_path):
    archivo = tmp_path / "audio.m4a"
    archivo.write_bytes(b"audio falso")
    r = transcribir(archivo, cfg, ClienteFalso(texto_audio="Tengo una bodega.", duracion=30.0))
    precio = cfg["precios"]["modelos"][cfg["voz"]["modelo"]]["franjas"][0]["por_minuto"]
    assert r["error"] is None and r["texto"] == "Tengo una bodega."
    assert abs(r["costo_usd"] - 0.5 * precio) < 1e-12   # 30 s = medio minuto


def test_audio_sin_voz_es_error(cfg, tmp_path):
    archivo = tmp_path / "silencio.m4a"
    archivo.write_bytes(b"audio falso")
    r = transcribir(archivo, cfg, ClienteFalso(texto_audio="   "))
    assert r["error"] == cfg["voz"]["mensajes"]["vacio"]
