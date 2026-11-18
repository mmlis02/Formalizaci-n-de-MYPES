# CLAUDE.md — contexto para Claude Code

## Qué es este proyecto
**Formalízate**: app Streamlit que ayuda a bodegueros y pequeños emprendedores del Perú a formalizarse. El usuario cuenta su negocio por audio (o texto); la app transcribe (Whisper), extrae los datos en JSON (LLM con salidas estructuradas), los verifica contra la transcripción y aplica reglas fijas: camino A (bodega con licencia provisional), B (negocio con local, licencia de funcionamiento) o C (sin local), y Nuevo RUS 1 o 2. Genera en PDF la declaración jurada que corresponde (bodegas o Anexo 1 del D.S. 163-2020-PCM) y responde dudas con un RAG sobre leyes oficiales, citando documento y página. Los campos que decide la municipalidad (nivel de riesgo, CIIU, zonificación) nunca los llena la app.

Es el proyecto final individual de Michelle Li (Data Science con Python, Universidad del Pacífico). **Michelle tiene que poder explicar y modificar en vivo cada parte del código.** Por eso:
- Prefiere código simple y legible a código ingenioso. Funciones cortas, nombres en español, comentarios que digan *por qué*.
- Después de cada bloque, explícale en 5–8 líneas qué hiciste, en qué archivos y cómo se prueba.
- No agregues funciones que no estén en `PLAN.md` sin preguntarle.

## Plan
Sigue `PLAN.md` en orden. Marca las casillas al terminar cada bloque. Un commit por bloque (o más pequeños), con mensajes en español del estilo `feat: ...`, `fix: ...`, `docs: ...`, `test: ...`.

## Reuso
Gran parte del motor RAG viene del repo anterior de Michelle, `HW_03_202602` (carpetas `comun/` y `tarea1_rag_normativo/`). Copia y adapta esos archivos en vez de reescribirlos: ella ya los conoce y los defendió. La tabla de qué viene de dónde está en `PLAN.md`, sección 3.

## Reglas de arquitectura (obligatorias)
1. `app.py` es solo interfaz. Toda la lógica está en `src/`. **Ningún archivo de `src/` importa streamlit** (verificar con `grep -rn "streamlit" src/`).
2. La app llama solo a `src/motor.py` (`procesar_audio`, `procesar_texto`) y a `src/motor_rag.py` (`responder`). Las dos devuelven diccionarios con campos explícitos, incluido `error` (los errores de API se devuelven como error, nunca como respuesta normal).
3. Dos procesos: `build_index.py` (offline) construye el índice; la app solo lo abre, nunca lo reconstruye.
4. Todo lo configurable va en `config.yaml`: modelos, precios con fecha de verificación, umbrales, montos del NRUS, área máxima de bodega, prompts, mensajes y textos de la interfaz. Nada de valores escritos a mano en el código.
5. Credenciales solo en `.env` (`OPENAI_API_KEY`). Nunca imprimir ni registrar la clave. Pre-commit activado con `git config core.hooksPath .githooks`.
6. Cada llamada a OpenAI (chat, embeddings, transcripción) queda en `logs/costos_llm.csv`.
7. Las reglas del diagnóstico son código Python con su fuente legal, no decisiones de la IA.
8. **Verificación de la ficha:** un campo extraído solo es `verificado` si su valor aparece en la transcripción (tras normalizar números en palabras y tildes); si no, `por_confirmar`. La IA nunca inventa ni corrige datos.
9. Datos personales (nombre, DNI, teléfono, correo) los escribe el usuario en la app, van solo al PDF y **nunca se envían a la IA**. En demos y pruebas se usan datos inventados.

## Despliegue
Streamlit Community Cloud. `requirements.txt` **sin** torch ni sentence-transformers (embeddings por API de OpenAI). El índice (`data/index/`) se sube al repo porque el servidor no lo construye. La clave se configura en los *secrets* de Streamlit Cloud, no en el repo.

## Comandos
- Instalar: `pip install -r requirements.txt`
- Construir índice: `python build_index.py`
- Evaluar recuperación (sin costo de LLM): `python -m eval.evaluar_recuperacion`
- App: `streamlit run app.py`
- Pruebas: `pytest`
