"""Piezas comunes de las pruebas: config con el log de costos en una carpeta temporal y un
cliente falso de OpenAI (ninguna prueba llama a la API ni gasta dinero)."""
import copy
import json
from types import SimpleNamespace

import pytest

from src.config import cargar_config

TRANSCRIPCION = ("Hola, tengo una bodega que se llama Bodega Doña Rosa, en el distrito de San Juan del "
                 "Urigancho. Queda en el jirón Los Claveles 120, en el primer piso de mi casa, y la puerta "
                 "da directo a la calle. Mide como 25 metros cuadrados. Vendo unos 4,500 soles al mes y "
                 "compro como 3,000. Todavía no tengo RUC.")


@pytest.fixture
def cfg(tmp_path):
    """config.yaml real, pero el log de costos va a una carpeta temporal."""
    c = copy.deepcopy(cargar_config())
    c["precios"]["log_llamadas"] = str(tmp_path / "costos_prueba.csv")
    return c


class ClienteFalso:
    """Imita lo que usamos del cliente de OpenAI: chat.completions.create y audio.transcriptions.create."""

    def __init__(self, respuesta_json: dict | None = None, texto_audio: str = TRANSCRIPCION,
                 duracion: float = 21.8, falla: bool = False):
        self.llamadas_llm = 0
        self.llamadas_audio = 0

        def crear_chat(**kwargs):
            self.llamadas_llm += 1
            if falla:
                raise RuntimeError("API caída (simulado)")
            uso = SimpleNamespace(prompt_tokens=900, completion_tokens=300, prompt_tokens_details=None)
            mensaje = SimpleNamespace(content=json.dumps(respuesta_json))
            return SimpleNamespace(usage=uso, choices=[SimpleNamespace(message=mensaje)])

        def crear_transcripcion(**kwargs):
            self.llamadas_audio += 1
            if falla:
                raise RuntimeError("API caída (simulado)")
            return SimpleNamespace(text=texto_audio, duration=duracion)

        self.chat = SimpleNamespace(completions=SimpleNamespace(create=crear_chat))
        self.audio = SimpleNamespace(transcriptions=SimpleNamespace(create=crear_transcripcion))


def campo(valor=None, cita=""):
    return {"valor": valor, "cita": cita}


@pytest.fixture
def respuesta_llm():
    """Lo que devolvería el LLM para TRANSCRIPCION, con DOS datos malos a propósito:
    corrige el distrito (no está así en el texto) y deduce la provincia (no se dijo)."""
    return {
        "giro": campo("bodega", "tengo una bodega"),
        "tiene_local_al_publico": campo(),
        "nombre_comercial": campo("Bodega Doña Rosa", "Bodega Doña Rosa"),
        "direccion": campo("jirón Los Claveles 120", "jirón Los Claveles 120"),
        "distrito": campo("San Juan de Lurigancho", "distrito de San Juan de Lurigancho"),  # corregido por la IA
        "provincia": campo("Lima", ""),                                                     # deducido por la IA
        "departamento": campo(),
        "area_m2": campo(25, "Mide como 25 metros cuadrados"),
        "en_vivienda": campo(True, "en el primer piso de mi casa"),
        "piso": campo(1, "primer piso"),
        "acceso_directo_via_publica": campo(True, "la puerta da directo a la calle"),
        "ventas_mensuales": campo(4500, "Vendo unos 4,500 soles al mes"),
        "compras_mensuales": campo(3000, "compro como 3,000"),
        "tiene_ruc": campo(False, "Todavía no tengo RUC"),
    }
