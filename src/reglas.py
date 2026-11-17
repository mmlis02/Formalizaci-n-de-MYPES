"""Diagnóstico con REGLAS FIJAS en Python (no las decide la IA). Umbrales, textos y fuentes en
config.yaml > reglas; cada regla guarda su fuente (documento y página) para mostrarla.

`diagnosticar(ficha)` recibe los datos YA CONFIRMADOS por el usuario y responde:
  1. ¿Qué camino?  (en este orden, como en PLAN.md, sección 5)
       - no tiene local abierto al público               -> C
       - bodega que cumple TODAS las condiciones          -> A (licencia provisional gratuita)
       - cualquier otro negocio con local, o bodega que
         no cumple alguna condición                       -> B (licencia de funcionamiento)
  2. ¿Nuevo RUS categoría 1, 2 o fuera del Nuevo RUS?  (ventas Y compras del mes)
  3. Checklist de pasos, cada uno con su fuente, y avisos (riesgo, autorización sectorial).

Si falta un dato que la decisión necesita (por ejemplo, si tiene local abierto al público), NO se
supone: el camino queda en None y el dato va a `preguntas_pendientes` para que el usuario lo diga.
"""
from src.config import cargar_config
from src.ficha import normalizar


def valores(ficha: dict) -> dict:
    """Acepta el resultado de extraer_ficha ({'campos': {n: {'valor': ...}}}) o un dict nombre -> valor."""
    if "campos" in ficha:
        return {n: c["valor"] for n, c in ficha["campos"].items()}
    return dict(ficha)


def _contiene_alguna(texto: str | None, palabras: list[str]) -> bool | None:
    """¿El texto contiene alguna de las palabras? None si no hay texto."""
    if not texto:
        return None
    t = f" {normalizar(texto)} "
    return any(f" {normalizar(p)} " in t for p in palabras)


def condiciones_bodega(v: dict, rcfg: dict) -> list[dict]:
    """Las 4 condiciones del art. 19 del Reglamento que puede revisar la app. cumple = True/False/None."""
    b, textos = rcfg["bodega"], rcfg["condiciones_bodega"]

    def si_hay(campo, prueba):
        return None if v.get(campo) is None else prueba(v[campo])

    return [
        {"campo": "area_m2", "texto": textos["area"].format(area_max=b["area_max_m2"]),
         "cumple": si_hay("area_m2", lambda x: x <= b["area_max_m2"])},
        {"campo": "en_vivienda", "texto": textos["vivienda"], "cumple": si_hay("en_vivienda", lambda x: x is True)},
        {"campo": "piso", "texto": textos["piso"], "cumple": si_hay("piso", lambda x: x in b["pisos_permitidos"])},
        {"campo": "acceso_directo_via_publica", "texto": textos["acceso"],
         "cumple": si_hay("acceso_directo_via_publica", lambda x: x is True)},
    ]


def decidir_camino(v: dict, rcfg: dict) -> tuple[str | None, list[dict], list[str], str]:
    """Devuelve (camino, condiciones_bodega, campos_pendientes, explicacion_extra)."""
    local = v.get("tiene_local_al_publico")
    if local is False:
        return "C", [], [], ""

    pendientes = [] if local is True else ["tiene_local_al_publico"]
    es_bodega = _contiene_alguna(v.get("giro"), rcfg["bodega"]["palabras_giro"])
    if es_bodega is None:
        return None, [], pendientes + ["giro"], ""
    if not es_bodega:
        return (None if pendientes else "B"), [], pendientes, ""

    condiciones = condiciones_bodega(v, rcfg)
    no_cumple = [c["texto"] for c in condiciones if c["cumple"] is False]
    if no_cumple:  # una sola condición que falla basta para ir al camino B
        extra = rcfg["caminos"]["B"]["explicacion_bodega_no_cumple"].format(condiciones="; ".join(no_cumple))
        return (None if pendientes else "B"), condiciones, pendientes, extra
    pendientes += [c["campo"] for c in condiciones if c["cumple"] is None]
    return (None if pendientes else "A"), condiciones, pendientes, ""


def decidir_regimen(v: dict, rcfg: dict) -> tuple[dict | None, list[str]]:
    """Nuevo RUS: el monto que manda es el MAYOR entre ventas y compras del mes."""
    ventas, compras = v.get("ventas_mensuales"), v.get("compras_mensuales")
    if ventas is None:
        return None, ["ventas_mensuales"]
    pendientes = ["compras_mensuales"] if compras is None else []
    monto = max(ventas, compras or 0)
    textos = rcfg["regimen"]
    for cat in rcfg["nrus"]["categorias"]:
        if monto <= cat["hasta"]:
            regimen = {"codigo": f"nrus_{cat['categoria']}", "categoria": cat["categoria"], "cuota": cat["cuota"],
                       "texto": textos["nrus"].format(categoria=cat["categoria"], cuota=cat["cuota"])}
            break
    else:
        limite = rcfg["nrus"]["categorias"][-1]["hasta"]
        regimen = {"codigo": "fuera_nrus", "categoria": None, "cuota": None,
                   "texto": textos["fuera_nrus"].format(limite=limite)}
    regimen.update(provisional=bool(pendientes), fuente=rcfg["nrus"]["fuente"])
    if pendientes:
        regimen["nota"] = textos["provisional"]
    return regimen, pendientes


def armar_checklist(camino: str | None, regimen: dict | None, v: dict, rcfg: dict) -> list[dict]:
    pasos_cfg = rcfg["checklist"]
    pasos = [{"texto": pasos_cfg["ruc"]["hecho"] if v.get("tiene_ruc") else pasos_cfg["ruc"]["texto"],
              "hecho": v.get("tiene_ruc") is True, "fuente": pasos_cfg["ruc"]["fuente"]}]
    if regimen:
        pasos.append({"texto": pasos_cfg["regimen"]["texto"].format(regimen=regimen["texto"]),
                      "hecho": False, "fuente": pasos_cfg["regimen"]["fuente"]})
    claves = {"A": ["licencia_A", "seguridad_A", "itse_A"], "B": ["licencia_B", "seguridad_B", "itse_B"],
              "C": ["licencia_C"]}.get(camino, [])
    pasos += [{"texto": pasos_cfg[k]["texto"], "hecho": False, "fuente": pasos_cfg[k]["fuente"]} for k in claves]
    for n, p in enumerate(pasos, 1):
        p["paso"] = n
    return pasos


def diagnosticar(ficha: dict, cfg: dict | None = None) -> dict:
    """Datos confirmados del negocio -> camino, régimen, checklist, preguntas pendientes y avisos."""
    cfg = cfg or cargar_config()
    rcfg = cfg["reglas"]
    v = valores(ficha)

    camino, condiciones, pend_camino, extra = decidir_camino(v, rcfg)
    regimen, pend_regimen = decidir_regimen(v, rcfg)
    pendientes = list(dict.fromkeys(pend_camino + pend_regimen))

    avisos = []
    if camino == "A":
        avisos.append(rcfg["aviso_riesgo_bodega"])
    if _contiene_alguna(v.get("giro"), rcfg["palabras_autorizacion_sectorial"]):
        avisos.append(rcfg["aviso_autorizacion_sectorial"].format(giro=v["giro"]))

    ccfg = rcfg["caminos"].get(camino, {})
    return {
        "camino": camino,
        "titulo": ccfg.get("titulo"),
        "explicacion": " ".join(filter(None, [extra, ccfg.get("explicacion")])) or None,
        "formulario": ccfg.get("formulario"),
        "fuente": ccfg.get("fuente"),
        "condiciones_bodega": condiciones,
        "regimen": regimen,
        "checklist": armar_checklist(camino, regimen, v, rcfg),
        "preguntas_pendientes": [{"campo": c, "pregunta": rcfg["preguntas"][c]} for c in pendientes],
        "avisos": avisos,
        "completo": not pendientes,
    }
