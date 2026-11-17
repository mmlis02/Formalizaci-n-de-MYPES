"""Regla de verificación: un valor solo es 'verificado' si su cita está en la transcripción
y el valor está dentro de la cita (src/ficha.verificar_campo)."""
import pytest

from src.ficha import normalizar, verificar_campo
from tests.conftest import TRANSCRIPCION

T = normalizar(TRANSCRIPCION)


@pytest.mark.parametrize("tipo, valor, cita, esperado", [
    # Datos dichos en el audio: verificados, aunque vengan en otro formato
    ("numero", 4500, "Vendo unos 4,500 soles al mes", "verificado"),
    ("numero", 4500.0, "Vendo unos 4,500 soles al mes", "verificado"),
    ("numero", 1, "en el primer piso de mi casa", "verificado"),
    ("texto", "Bodega Doña Rosa", "Bodega Doña Rosa", "verificado"),
    ("si_no", True, "la puerta da directo a la calle", "verificado"),
    ("si_no", False, "Todavía no tengo RUC", "verificado"),
    # La IA corrigió un nombre: ya no es lo que dijo el usuario
    ("texto", "San Juan de Lurigancho", "distrito de San Juan de Lurigancho", "por_confirmar"),
    ("texto", "San Juan de Lurigancho", "distrito de San Juan del Urigancho", "por_confirmar"),
    # La IA dedujo un dato que no se dijo (sin cita)
    ("texto", "Lima", "", "por_confirmar"),
    # La IA inventó la cita
    ("si_no", True, "tengo local abierto al público", "por_confirmar"),
    # El número no coincide con la cita (45 no es 4500; 5000 no es 4500)
    ("numero", 45, "Vendo unos 4,500 soles al mes", "por_confirmar"),
    ("numero", 5000, "Vendo unos 4,500 soles al mes", "por_confirmar"),
    # No se mencionó
    ("texto", None, "", "no_mencionado"),
    ("numero", None, "", "no_mencionado"),
])
def test_verificar_campo(tipo, valor, cita, esperado):
    assert verificar_campo(tipo, valor, cita, T) == esperado
