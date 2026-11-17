"""App Streamlit de Formaliza (SOLO interfaz). Versión mínima: chat de dudas con el motor RAG.

Toda la lógica está en src/motor_rag.py: esta app solo llama a `responder(pregunta)` y muestra
el resultado. Nunca construye el índice ni lee los PDFs. Todos los textos vienen de config.yaml.

Ejecutar (desde la raíz del proyecto):
    streamlit run app.py
"""
import os
import sys

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
    """Importa el motor y lo inicializa una sola vez (embeddings + índice ya construido)."""
    from src.motor_rag import responder
    responder(" ")  # pregunta vacía: inicializa el motor sin buscar ni llamar a la IA
    return responder


st.title(f"{A['icono']} {A['titulo']}")
st.write(A["subtitulo"])
st.caption(A["aviso_legal"])

if not cargar_clave():
    st.error(A["sin_clave"])
    st.stop()
if not (BASE / cfg["indice"]["carpeta"]).exists():
    st.error(A["sin_indice"])
    st.stop()

responder = obtener_responder()

# Botones de ejemplo: llenan la caja de pregunta
st.write(f"**{A['ejemplos_titulo']}**")
for i, ejemplo in enumerate(A["ejemplos"]):
    if st.button(ejemplo, key=f"ejemplo_{i}"):
        st.session_state["pregunta"] = ejemplo

with st.form("formulario"):
    pregunta = st.text_area(A["etiqueta_pregunta"], key="pregunta", height=90)
    enviado = st.form_submit_button(A["boton_preguntar"], type="primary")

if enviado:
    with st.spinner(A["buscando"]):
        r = responder(pregunta)

    if r["error"]:  # errores de API o pregunta vacía: se muestran como error, nunca como respuesta
        st.error(r["error"])
        st.stop()

    c1, c2, c3 = st.columns(3)
    c1.metric(A["m_abstuvo"], A["si"] if r["abstuvo"] else A["no"])
    c2.metric(A["m_similitud"], f"{r['similitud_max']:.3f}", help=A["ayuda_umbral"].format(umbral=r["umbral"]))
    if r["llamo_llm"]:
        c3.metric(A["m_costo"], f"US$ {r['costo_usd']:.6f}",
                  help=A["ayuda_costo"].format(tokens_entrada=r["tokens_entrada"],
                                               tokens_salida=r["tokens_salida"], latencia=r["latencia_s"]))
    else:
        c3.metric(A["m_costo"], A["sin_llm"])

    if r["abstuvo"]:
        st.warning(f"**{A['abstencion_titulo']}:** {A['motivos'][r['motivo_abstencion']]}")
        st.write(r["respuesta"])
    else:
        st.subheader(A["titulo_respuesta"])
        st.write(r["respuesta"])
    if r["explicacion_limite"]:
        st.info(f"**{A['titulo_limite']}:** {r['explicacion_limite']}")
    if r["notas_version"]:
        st.write(f"**{A['titulo_notas']}**")
        for nota in r["notas_version"]:
            st.caption(nota)

    st.subheader(A["titulo_fuentes"])
    col = A["columnas_fuentes"]
    st.dataframe(
        [{col["documento"]: f["titulo"], col["pagina"]: f["pagina"], col["articulo"]: f["articulo"],
          col["similitud"]: round(f["similitud"], 3), col["citada"]: A["si"] if f["citada"] else A["no"]}
         for f in r["fuentes"]],
        hide_index=True, width="stretch",
    )
