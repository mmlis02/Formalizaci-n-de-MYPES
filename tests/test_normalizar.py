"""Números en palabras -> dígitos y demás normalización (src/ficha.normalizar)."""
import pytest

from src.ficha import normalizar


@pytest.mark.parametrize("entrada, esperado", [
    ("cuatro mil quinientos soles", "4500 soles"),
    ("ocho mil quinientos cincuenta", "8550"),
    ("veinticinco metros cuadrados", "25 metros cuadrados"),
    ("veintitrés", "23"),                       # con tilde
    ("dieciséis mil", "16000"),
    ("Vendo 4 mil soles", "vendo 4000 soles"),  # así suele escribirlo Whisper
    ("4,500", "4500"),                          # separador de miles con coma
    ("S/ 4.500", "s 4500"),                     # ... y con punto
    ("25,5 m2", "25.5 m2"),                     # decimal con coma
    ("en el primer piso", "en el 1 piso"),      # ordinales
    ("el segundo piso", "el 2 piso"),
    ("Jirón Doña Rosa", "jiron dona rosa"),     # sin tildes ni mayúsculas
    ("¡Hola, vecino!", "hola vecino"),          # sin puntuación
])
def test_normalizar(entrada, esperado):
    assert normalizar(entrada) == esperado


def test_misma_normalizacion_en_palabras_y_digitos():
    assert normalizar("vendo cuatro mil quinientos") == normalizar("Vendo 4,500")
