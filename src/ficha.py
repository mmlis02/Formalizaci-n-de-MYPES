"""Ficha del negocio: transcripción -> campos en JSON, cada uno VERIFICADO contra la transcripción.

Flujo de `extraer_ficha(transcripcion)`:
  1. El LLM devuelve, con un esquema JSON estricto, cada campo como {"valor", "cita"}:
     la cita es el pedazo exacto de la transcripción de donde sacó el valor.
  2. Verificación SIN IA (`verificar_campo`), después de normalizar ambos textos
     (números en palabras -> dígitos, "4,500" -> 4500, "primer" -> 1, sin tildes ni puntuación):
       - valor null                                   -> "no_mencionado"
       - la cita NO aparece en la transcripción        -> "por_confirmar" (la IA la inventó o la cambió)
       - el valor NO aparece dentro de la cita          -> "por_confirmar" (p. ej. corrigió un nombre
                                                          o dedujo la provincia a partir del distrito)
       - si no                                          -> "verificado"
     En los campos sí/no no hay un "valor" que buscar en el texto: basta con que la cita exista.
     EXCEPCIÓN: los sí/no que deciden el camino (config.yaml > ficha > campos_siempre_por_confirmar)
     quedan siempre "por_confirmar", porque la cita no siempre prueba el valor.
  3. La app resalta los campos "por_confirmar" para que el usuario los corrija. La IA nunca
     corrige ni completa datos: en una declaración JURADA el usuario firma que todo es cierto.

Nombre, DNI, teléfono y correo NO son campos de la ficha: los escribe el usuario en la app y
nunca pasan por la IA.

Para agregar un campo: una línea en CAMPOS (aquí) + su etiqueta y descripción en
config.yaml > ficha > campos.
"""
import re
import unicodedata

from text_to_num import alpha2digit

from src.config import cargar_config
from src.llm import cliente_openai, llamar_llm_json

# Tipo de cada campo. El orden es el que se muestra en pantalla.
CAMPOS = {
    "giro": "texto",
    "tiene_local_al_publico": "si_no",
    "nombre_comercial": "texto",
    "direccion": "texto",
    "distrito": "texto",
    "provincia": "texto",
    "departamento": "texto",
    "area_m2": "numero",
    "en_vivienda": "si_no",
    "piso": "numero",
    "acceso_directo_via_publica": "si_no",
    "ventas_mensuales": "numero",
    "compras_mensuales": "numero",
    "tiene_ruc": "si_no",
}
TIPO_JSON = {"texto": "string", "numero": "number", "si_no": "boolean"}

# alpha2digit no convierte ordinales: "primer piso" -> "1 piso"
ORDINALES = {"primer": "1", "primero": "1", "primera": "1", "segundo": "2", "segunda": "2",
             "tercer": "3", "tercero": "3", "tercera": "3", "cuarto": "4", "cuarta": "4",
             "quinto": "5", "quinta": "5"}


# ---------------------------------------------------------------------------
# Normalización (la misma para la transcripción, la cita y el valor)
# ---------------------------------------------------------------------------
def _quitar_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def normalizar(texto: str) -> str:
    """'Vendo unos cuatro mil quinientos soles, en el Primer piso' -> 'vendo unos 4500 soles en el 1 piso'."""
    t = texto.lower()
    t = re.sub(r"(?<=\d)[.,](?=\d{3}(?!\d))", "", t)                     # 4,500 / 4.500 -> 4500
    t = re.sub(r"\b(\d+)\s+mil\b", lambda m: str(int(m.group(1)) * 1000), t)  # "4 mil" -> 4000
    t = alpha2digit(t, "es")                                            # "cuatro mil quinientos" -> 4500
    t = re.sub(r"\b(\d+)\s+1000\b", lambda m: str(int(m.group(1)) * 1000), t)  # por si quedó "4 1000"
    t = " ".join(ORDINALES.get(p, p) for p in t.split())
    t = _quitar_tildes(t)
    t = re.sub(r"(?<=\d),(?=\d)", ".", t)                               # decimal con coma: 25,5 -> 25.5
    t = re.sub(r"[^\w\s.]|(?<!\d)\.|\.(?!\d)", " ", t)                   # puntuación fuera (salvo 25.5)
    return " ".join(t.split())


def _texto_del_valor(valor) -> str:
    """4500.0 -> '4500'; 25.5 -> '25.5'; textos tal cual."""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor)


def _contiene(aguja: str, pajar: str) -> bool:
    """¿`aguja` aparece en `pajar` como palabras completas? ('45' no está dentro de '4500')."""
    return bool(aguja) and f" {aguja} " in f" {pajar} "


def verificar_campo(tipo: str, valor, cita: str, transcripcion_normalizada: str) -> str:
    """Devuelve 'verificado', 'por_confirmar' o 'no_mencionado' (ver docstring del módulo)."""
    if valor is None:
        return "no_mencionado"
    cita_n = normalizar(cita or "")
    if not _contiene(cita_n, transcripcion_normalizada):
        return "por_confirmar"
    if tipo == "si_no":
        return "verificado"
    return "verificado" if _contiene(normalizar(_texto_del_valor(valor)), cita_n) else "por_confirmar"


# ---------------------------------------------------------------------------
# Extracción con el LLM
# ---------------------------------------------------------------------------
def esquema_ficha(cfg: dict) -> dict:
    """Esquema JSON estricto: cada campo es {"valor": <tipo> o null, "cita": texto}."""
    descripciones = cfg["ficha"]["campos"]
    propiedades = {
        nombre: {
            "type": "object",
            "properties": {
                "valor": {"type": [TIPO_JSON[tipo], "null"], "description": descripciones[nombre]["descripcion"]},
                "cita": {"type": "string"},
            },
            "required": ["valor", "cita"],
            "additionalProperties": False,
        }
        for nombre, tipo in CAMPOS.items()
    }
    return {"name": "ficha_negocio", "strict": True,
            "schema": {"type": "object", "properties": propiedades,
                       "required": list(CAMPOS), "additionalProperties": False}}


def extraer_ficha(transcripcion: str, cfg: dict | None = None, cliente=None) -> dict:
    """transcripción -> {'campos': {nombre: {etiqueta, tipo, valor, cita, estado}}, 'resumen', costo..., 'error'}.

    `cliente` se puede inyectar (cliente falso) para probar sin gastar.
    """
    cfg = cfg or cargar_config()
    fcfg = cfg["ficha"]
    r = {"campos": {}, "resumen": {}, "modelo": cfg["llm"]["modelo"], "tokens_entrada": 0,
         "tokens_salida": 0, "costo_usd": 0.0, "latencia_s": 0.0, "error": None}
    if not transcripcion or not transcripcion.strip():
        r["error"] = fcfg["mensajes"]["texto_vacio"]
        return r

    mensajes = [{"role": "system", "content": fcfg["prompt_sistema"]},
                {"role": "user", "content": fcfg["prompt_usuario"].format(transcripcion=transcripcion)}]
    # En el log de costos va solo una etiqueta, nunca lo que contó el usuario
    ll = llamar_llm_json(cliente or cliente_openai(cfg), cfg, mensajes, esquema_ficha(cfg),
                         f"[ficha] {len(transcripcion)} caracteres")
    for clave in ("tokens_entrada", "tokens_salida", "costo_usd", "latencia_s"):
        r[clave] = ll[clave]
    if ll["error"]:
        r["error"] = f"{fcfg['mensajes']['error_api']} ({ll['error']})"
        return r

    transcripcion_n = normalizar(transcripcion)
    for nombre, tipo in CAMPOS.items():
        dato = ll["datos"].get(nombre) or {"valor": None, "cita": ""}
        estado = verificar_campo(tipo, dato["valor"], dato["cita"], transcripcion_n)
        if estado == "verificado" and nombre in fcfg["campos_siempre_por_confirmar"]:
            estado = "por_confirmar"   # deciden el camino: siempre los confirma el usuario
        r["campos"][nombre] = {
            "etiqueta": fcfg["campos"][nombre]["etiqueta"],
            "tipo": tipo,
            "valor": dato["valor"],
            "cita": dato["cita"],
            "estado": estado,
        }
    estados = [c["estado"] for c in r["campos"].values()]
    r["resumen"] = {e: estados.count(e) for e in fcfg["estados"]}
    return r
