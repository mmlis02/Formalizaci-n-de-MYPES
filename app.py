"""App Streamlit de Formaliza (SOLO interfaz). Toda la lógica está en src/:
  - pestaña 1, "Formalizar mi negocio": 3 pasos que llaman a src/motor.py
      1. Cuéntame        -> procesar_audio / procesar_texto (voz -> ficha verificada)
      2. Revisa tus datos -> el usuario corrige y confirma (los ⚠️ necesitan un clic)
      3. Tu plan         -> diagnosticar (reglas fijas) y generar_formulario (PDF)
  - pestaña 2, "Preguntas sobre trámites": chat que llama a src/motor_rag.responder

Todos los textos vienen de config.yaml > app. La app nunca construye el índice ni lee los PDFs.

Ejecutar (desde la raíz del proyecto):
    streamlit run app.py
"""
import os
import sys
import tempfile
from pathlib import Path

# --- Parche de SQLite para Streamlit Community Cloud ------------------------------------
# ChromaDB necesita SQLite >= 3.35. Si el servidor trae uno más viejo, se usa el de
# pysqlite3-binary (requirements.txt lo instala solo en Linux). En local no hace nada.
# Tiene que ir ANTES de importar cualquier cosa que importe chromadb.
try:
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

import streamlit as st  # noqa: E402

from src.config import BASE, cargar_config  # noqa: E402

cfg = cargar_config()
A = cfg["app"]
st.set_page_config(page_title=A["titulo"], page_icon=A["icono"])


def cargar_clave() -> bool:
    """La clave viene de st.secrets (Streamlit Cloud) o, si no hay, del .env (local)."""
    try:
        if "OPENAI_API_KEY" in st.secrets:
            os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
    except FileNotFoundError:
        pass  # en local no hay secrets.toml: se usa el .env
    from dotenv import load_dotenv
    load_dotenv()
    return bool(os.environ.get("OPENAI_API_KEY"))


@st.cache_resource(show_spinner=A["cargando"])
def obtener_responder():
    """Importa el motor RAG y lo inicializa una sola vez (embeddings + índice ya construido)."""
    from src.motor_rag import responder
    responder(" ")  # pregunta vacía: inicializa el motor sin buscar ni llamar a la IA
    return responder


def estado_inicial():
    for clave, valor in {"paso": 1, "resultado": None, "datos": {}, "costo": 0.0, "pdf": None}.items():
        st.session_state.setdefault(clave, valor)


def ir_a(paso: int):
    st.session_state.paso = paso
    st.session_state.pdf = None


def reiniciar():
    for clave in list(st.session_state):
        del st.session_state[clave]


# ---------------------------------------------------------------------------
# Piezas pequeñas
# ---------------------------------------------------------------------------
def a_numero(x):
    """number_input devuelve float: 25.0 -> 25 (así se ve igual en el PDF)."""
    return int(x) if isinstance(x, float) and x.is_integer() else x


def widget_campo(nombre: str, tipo: str, etiqueta: str, valor, clave: str):
    """Un campo de la ficha con el widget que corresponde a su tipo. Devuelve el valor elegido."""
    if tipo == "texto":
        return st.text_input(etiqueta, value=valor or "", key=clave).strip() or None
    if tipo == "numero":
        return a_numero(st.number_input(etiqueta, value=None if valor is None else float(valor),
                                        min_value=0.0, step=1.0, key=clave))
    opciones = [A["si"], A["no"]]
    defecto = None if valor is None else (A["si"] if valor else A["no"])
    elegido = st.segmented_control(etiqueta, opciones, default=defecto, key=clave)
    return None if elegido is None else elegido == A["si"]


def texto_fuente(fuente: dict | None) -> str | None:
    if not fuente:
        return None
    corta = cfg["motor"]["citas_cortas"].get(fuente["documento"], fuente["documento"])
    return A["plan"]["fuente"].format(corta=corta, pagina=fuente["pagina"])


def audio_de_ejemplo() -> Path | None:
    """El primero que exista: el audio grabado por Michelle o, si aún no está, el sintético."""
    return next((BASE / r for r in A["cuentame"]["audio_ejemplo"] if (BASE / r).exists()), None)


def procesar(audio: bytes | None = None, nombre_audio: str = "", texto: str = ""):
    """Llama al motor y guarda el resultado. El audio se escribe en un archivo temporal y se borra."""
    from src.motor import procesar_audio, procesar_texto

    with st.spinner(A["cuentame"]["procesando"]):
        if audio is not None:
            sufijo = Path(nombre_audio).suffix or ".wav"
            with tempfile.NamedTemporaryFile(suffix=sufijo, delete=False) as tmp:
                tmp.write(audio)
            try:
                r = procesar_audio(tmp.name, cfg)
            finally:
                os.remove(tmp.name)
        else:
            r = procesar_texto(texto, cfg)
    st.session_state.costo += r["costo_usd"]
    if r["error"]:
        st.error(r["error"])
        return
    st.session_state.resultado = r
    st.session_state.datos = {n: c["valor"] for n, c in r["ficha"]["campos"].items()}
    ir_a(2)
    st.rerun()


# ---------------------------------------------------------------------------
# Paso 1: Cuéntame
# ---------------------------------------------------------------------------
def paso_cuentame():
    C = A["cuentame"]
    st.subheader(C["titulo"])
    st.write(C["instrucciones"])
    st.warning(C["aviso_privacidad"], icon="🔒")

    modo = st.segmented_control(C["etiqueta_modo"], C["modos"], default=C["modos"][0], key="modo")
    audio, nombre, texto = None, "", ""
    if modo == C["modos"][0]:
        grabado = st.audio_input(C["etiqueta_grabar"])
        if grabado:
            audio, nombre = grabado.getvalue(), grabado.name or "grabacion.wav"
    elif modo == C["modos"][1]:
        subido = st.file_uploader(C["etiqueta_subir"], type=cfg["voz"]["formatos"])
        if subido:
            audio, nombre = subido.getvalue(), subido.name
    else:
        texto = st.text_area(C["etiqueta_texto"], placeholder=C["ejemplo_texto"], height=130)

    c1, c2 = st.columns(2)
    if c1.button(C["boton_procesar"], type="primary", width="stretch"):
        if audio is None and not texto.strip():
            st.error(C["falta_entrada"])
        else:
            procesar(audio, nombre, texto)
    ejemplo = audio_de_ejemplo()
    if ejemplo and c2.button(C["boton_ejemplo"], width="stretch",
                             help=C["ayuda_ejemplo"].format(archivo=ejemplo.relative_to(BASE))):
        procesar(ejemplo.read_bytes(), ejemplo.name)


# ---------------------------------------------------------------------------
# Paso 2: Revisa tus datos
# ---------------------------------------------------------------------------
def paso_revisa():
    R = A["revisa"]
    r = st.session_state.resultado
    st.subheader(R["titulo"])
    st.write(R["instrucciones"])
    with st.expander(R["transcripcion"]):
        st.write(r["transcripcion"])

    datos, sin_confirmar = {}, 0
    for nombre, campo in r["ficha"]["campos"].items():
        icono = R["iconos"][campo["estado"]]
        valor_actual = st.session_state.datos.get(nombre, campo["valor"])
        izquierda, derecha = st.columns([3, 2], vertical_alignment="center")
        with izquierda:
            datos[nombre] = widget_campo(nombre, campo["tipo"], f"{icono} {campo['etiqueta']}", valor_actual, f"v_{nombre}")
        with derecha:
            st.caption(R["cita"].format(cita=campo["cita"]) if campo["cita"] else R["sin_cita"])
            if campo["estado"] == "por_confirmar":
                if not st.checkbox(R["confirmar"], key=f"c_{nombre}"):
                    sin_confirmar += 1

    if sin_confirmar:
        st.info(R["faltan_confirmar"].format(n=sin_confirmar))
    c1, c2 = st.columns(2)
    if c1.button(R["boton_continuar"], type="primary", disabled=bool(sin_confirmar), width="stretch"):
        st.session_state.datos = datos
        ir_a(3)
        st.rerun()
    if c2.button(R["boton_volver"], width="stretch"):
        ir_a(1)
        st.rerun()


# ---------------------------------------------------------------------------
# Paso 3: Tu plan
# ---------------------------------------------------------------------------
def paso_plan():
    from src.motor import diagnosticar, generar_formulario

    P = A["plan"]
    st.subheader(P["titulo"])
    campos = st.session_state.resultado["ficha"]["campos"]
    d = diagnosticar(st.session_state.datos, cfg)

    # Datos que faltan para decidir: se preguntan aquí mismo
    if d["preguntas_pendientes"]:
        with st.container(border=True):
            st.write(f"**{P['pendientes_titulo']}**")
            respuestas = {p["campo"]: widget_campo(p["campo"], campos[p["campo"]]["tipo"], p["pregunta"],
                                                   st.session_state.datos.get(p["campo"]), f"p_{p['campo']}")
                          for p in d["preguntas_pendientes"]}
            if st.button(P["boton_actualizar"], type="primary"):
                st.session_state.datos.update({k: v for k, v in respuestas.items() if v is not None})
                st.rerun()

    if d["camino"]:
        st.success(f"**{d['titulo']}**\n\n{d['explicacion']}")
        if texto_fuente(d["fuente"]):
            st.caption(texto_fuente(d["fuente"]))
    if d["condiciones_bodega"]:
        st.write(f"**{P['condiciones_titulo']}**")
        for c in d["condiciones_bodega"]:
            st.write(f"{P['iconos_condicion'][str(c['cumple']).lower()]} {c['texto']}")
    for aviso in d["avisos"]:
        st.warning(aviso)

    if d["regimen"]:
        st.write(f"**{P['regimen_titulo']}**")
        st.write(d["regimen"]["texto"] + (f" — {d['regimen']['nota']}" if d["regimen"].get("nota") else ""))
        fuente = d["regimen"]["fuente"]
        st.caption(texto_fuente(fuente))
        nota = next((doc.get("nota_fecha") for doc in cfg["documentos"] if doc["id"] == fuente["documento"]), None)
        if nota:
            st.caption(cfg["mensajes"]["nota_fecha_sunat"].format(fecha=nota))

    st.write(f"**{P['checklist_titulo']}**")
    for paso in d["checklist"]:
        marca = "✅" if paso["hecho"] else f"{paso['paso']}."
        st.write(f"{marca} {paso['texto']}")
        if texto_fuente(paso["fuente"]):
            st.caption(texto_fuente(paso["fuente"]))

    # Declaración jurada: los datos personales los escribe el usuario y solo van al PDF
    if d["formulario"]:
        st.divider()
        st.write(f"**{P['formulario_titulo']}**")
        st.caption(P["datos_personales_aviso"])
        E = P["etiquetas_personales"]
        with st.form("datos_personales"):
            personales = {c: st.text_input(E[c]).strip() for c in E}
            enviado = st.form_submit_button(P["boton_pdf"], type="primary")
        if enviado:
            dni = personales["dni"]
            if dni and not (dni.isdigit() and len(dni) == 8):
                st.error(P["dni_invalido"])
            else:
                try:
                    st.session_state.pdf = generar_formulario(d, st.session_state.datos, personales, cfg)
                except ValueError as e:
                    st.error(str(e))
        if st.session_state.pdf:
            st.download_button(P["boton_descargar"], st.session_state.pdf, mime="application/pdf",
                               file_name=P["nombre_archivo"].format(camino=d["camino"]), type="primary")
    elif d["camino"] == "C":
        st.info(cfg["formulario"]["sin_formulario"].format(camino="C"))

    st.divider()
    c1, c2 = st.columns(2)
    if c1.button(P["boton_volver"], width="stretch"):
        ir_a(2)
        st.rerun()
    c2.button(P["boton_reiniciar"], on_click=reiniciar, width="stretch")


# ---------------------------------------------------------------------------
# Pestaña 2: chat de dudas (motor RAG)
# ---------------------------------------------------------------------------
def chat():
    Q = A["chat"]
    st.subheader(Q["titulo"])
    st.write(Q["subtitulo"])
    st.write(f"**{Q['ejemplos_titulo']}**")
    for i, ejemplo in enumerate(Q["ejemplos"]):
        if st.button(ejemplo, key=f"ejemplo_{i}"):
            st.session_state["pregunta"] = ejemplo

    with st.form("formulario_chat"):
        pregunta = st.text_area(Q["etiqueta_pregunta"], key="pregunta", height=90)
        enviado = st.form_submit_button(Q["boton_preguntar"], type="primary")
    if not enviado:
        return

    with st.spinner(Q["buscando"]):
        r = obtener_responder()(pregunta)
    st.session_state.costo += r["costo_usd"]
    if r["error"]:  # errores de API o pregunta vacía: se muestran como error, nunca como respuesta
        st.error(r["error"])
        return

    c1, c2, c3 = st.columns(3)
    c1.metric(Q["m_abstuvo"], A["si"] if r["abstuvo"] else A["no"])
    c2.metric(Q["m_similitud"], f"{r['similitud_max']:.3f}", help=Q["ayuda_umbral"].format(umbral=r["umbral"]))
    if r["llamo_llm"]:
        c3.metric(Q["m_costo"], f"US$ {r['costo_usd']:.6f}",
                  help=Q["ayuda_costo"].format(tokens_entrada=r["tokens_entrada"],
                                               tokens_salida=r["tokens_salida"], latencia=r["latencia_s"]))
    else:
        c3.metric(Q["m_costo"], Q["sin_llm"])

    if r["abstuvo"]:
        st.warning(f"**{Q['abstencion_titulo']}:** {Q['motivos'][r['motivo_abstencion']]}")
    else:
        st.write(f"**{Q['titulo_respuesta']}**")
    st.write(r["respuesta"])
    if r["explicacion_limite"]:
        st.info(f"**{Q['titulo_limite']}:** {r['explicacion_limite']}")
    if r["notas_version"]:
        st.write(f"**{Q['titulo_notas']}**")
        for nota in r["notas_version"]:
            st.caption(nota)

    st.write(f"**{Q['titulo_fuentes']}**")
    col = Q["columnas_fuentes"]
    st.dataframe(
        [{col["documento"]: f["titulo"], col["pagina"]: f["pagina"], col["articulo"]: f["articulo"],
          col["similitud"]: round(f["similitud"], 3), col["citada"]: A["si"] if f["citada"] else A["no"]}
         for f in r["fuentes"]],
        hide_index=True, width="stretch",
    )


# ---------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------
st.title(f"{A['icono']} {A['titulo']}")
st.write(A["subtitulo"])
st.caption(A["aviso_legal"])

if not cargar_clave():
    st.error(A["sin_clave"])
    st.stop()
if not (BASE / cfg["indice"]["carpeta"]).exists():
    st.error(A["sin_indice"])
    st.stop()

estado_inicial()
pestana_flujo, pestana_chat = st.tabs(A["pestanas"])
with pestana_flujo:
    paso = st.session_state.paso
    st.progress(paso / len(A["pasos"]), text=A["pasos"][paso - 1])
    {1: paso_cuentame, 2: paso_revisa, 3: paso_plan}[paso]()
with pestana_chat:
    chat()
st.caption(A["costo_sesion"].format(costo=st.session_state.costo))
