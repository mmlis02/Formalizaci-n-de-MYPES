# PLAN.md — Formaliza (proyecto final, Data Science con Python, UP 2026-II)

> Plan de trabajo para construir con Claude Code. Lo sigo en orden; cada bloque termina con un commit.
> Presento el **miércoles 18 de noviembre, 7:55 a. m. (turno 16)**. El link va en el issue #205 **hoy lunes 16 antes de las 11:59 p. m.**

---

## 1. La idea en una frase

**One-liner (borrador):** Ayudamos a los bodegueros del Perú a formalizarse: cuentan su negocio en un audio y reciben qué trámites les tocan, con la ley citada, y la declaración jurada de su licencia ya llena.

**Usuario inicial:** persona natural con una bodega de barrio (en su vivienda, ≤ 50 m²) que no tiene RUC o no tiene licencia.
Empezamos solo con bodegas porque tienen un camino legal especial y más simple (Ley 30877, Ley General de Bodegueros): licencia **provisional gratuita**, con un formulario de **una sola página**.

**Herramientas del curso dentro del producto (2):**

| Herramienta | Sesión | Para qué |
|---|---|---|
| **Whisper (voz a texto)** | 13 | El bodeguero habla en vez de llenar un formulario largo |
| **LLM con salidas estructuradas + RAG** | 08 | Sacar los datos del negocio en JSON, y responder dudas solo con las leyes, citando documento y página |

---

## 2. El flujo (lo que tengo que saber explicar sin mirar código)

```
🎤 audio (o texto escrito)
   │
   ▼  src/voz.py ............ Whisper (API OpenAI) → transcripción
   │
   ▼  src/ficha.py .......... LLM con esquema JSON → campos del negocio
   │                          + números en palabras → dígitos ("cuatro mil" → 4000)
   │                          + VERIFICACIÓN: cada valor debe aparecer en la transcripción;
   │                            si no, queda "por confirmar" (la IA nunca inventa un dato)
   ▼
 usuario revisa y confirma los campos en pantalla  (DNI y nombre los escribe él: no pasan por la IA)
   │
   ▼  src/reglas.py ......... reglas fijas en Python (umbrales en config.yaml, cada una con su fuente)
   │                          → ¿le toca licencia provisional de bodega? ¿Nuevo RUS categoría 1 o 2?
   │                          → checklist: RUC → régimen → licencia → condiciones de seguridad
   ▼
 ├─► src/formulario.py ...... PDF: Declaración Jurada para Licencia Provisional de Funcionamiento para Bodegas
 └─► src/motor_rag.py ....... chat de dudas: responder(pregunta) con citas (ley, pág.) y abstención
```

**Dos procesos separados (igual que en mi HW_03):**
- **Offline, una vez:** `build_index.py` → lee los PDFs de las leyes, limpia, fragmenta con la página como metadato y guarda el índice.
- **Online, en cada uso:** `app.py` llama a funciones del motor; nunca relee PDFs ni reconstruye el índice.

**Reglas de arquitectura (las mismas de HW_03):**
- Un módulo por responsabilidad; `app.py` solo es interfaz. Ningún archivo de `src/` importa Streamlit.
  Verificación: `grep -rn "streamlit" src/` no debe devolver nada.
- Todo lo configurable vive en `config.yaml` (modelos, umbrales, prompts, mensajes, montos del NRUS, rutas).
- La clave vive en `.env` (nunca en git). Pre-commit de `.githooks/` activado.
- Cada llamada a la IA queda en `logs/costos_llm.csv` (fecha, modelo, tokens, latencia, costo, éxito o error).

---

## 3. Qué reuso de mi repo `HW_03_202602` y qué es nuevo

| Archivo en Formaliza | Viene de | Cambios |
|---|---|---|
| `src/costos.py` | `comun/costos.py` | Ninguno, más el precio de Whisper por minuto |
| `src/llm.py` | `comun/llm.py` | Ninguno, más la función `transcribir()` que también registra costo |
| `src/embeddings.py` | `comun/embeddings.py` | Dejar solo la implementación OpenAI activa (sin PyTorch para el despliegue) |
| `src/extraccion.py`, `src/limpieza.py`, `src/fragmentos.py`, `src/indice.py` | `tarea1_rag_normativo/src/` | Adaptar las reglas de limpieza a los nuevos PDFs |
| `src/motor_rag.py` | `tarea1_rag_normativo/src/motor.py` | Mismo motor y dos defensas; cambiar prompt, mensajes y notas de versión |
| `build_index.py`, `eval/barrido_umbral.py`, `eval/evaluar_recuperacion.py` | `tarea1_rag_normativo/` | Rutas y nombres de documentos |
| `scripts/verificar_fuentes.py`, `scripts/descargar_fuentes.py` | `tarea1_rag_normativo/scripts/` | Nueva lista de documentos en `config.yaml` |
| `.githooks/pre-commit` | `.githooks/` | Ninguno |
| **`src/voz.py`** | **nuevo** | `transcribir(ruta_audio) -> dict` |
| **`src/ficha.py`** | **nuevo** | `extraer_ficha(transcripcion) -> dict` con verificación |
| **`src/reglas.py`** | **nuevo** | `diagnosticar(ficha) -> dict` (régimen, tipo de licencia, checklist con fuentes) |
| **`src/formulario.py`** | **nuevo** | `generar_pdf(ficha, datos_personales) -> bytes` |
| **`src/motor.py`** | **nuevo** | `procesar_audio(ruta)` y `procesar_texto(texto)`: unen voz → ficha → reglas; es lo único que llama la app |
| **`app.py`** | **nuevo** | Streamlit con 3 pasos: Cuéntame → Revisa tus datos → Tu plan y tu formulario (+ chat) |

---

## 4. Corpus de leyes (solo fuentes oficiales, como en HW_03)

Antes de construir nada: **verificación de fuentes** (páginas, caracteres por página, páginas sin texto, orden de lectura). Si un PDF no se puede leer, se descarta y se dice en el README.

| id | Documento | Fuente |
|---|---|---|
| `ley30877` | Ley N.° 30877, Ley General de Bodegueros (y su modificación por Ley N.° 31866, art. 6: trámite virtual) | El Peruano / gob.pe — Ley 31866: https://busquedas.elperuano.pe/download/url/ley-que-modifica-la-ley-30877-ley-general-de-bodegueros-a-ley-n-31866-2204313-3 |
| `ds010_2020_produce` | Reglamento de la Ley 30877 (D.S. N.° 010-2020-PRODUCE), modificado por D.S. N.° 003-2024-PRODUCE | El Peruano / gob.pe — D.S. 003-2024: https://www.congreso.gob.pe/Docs/DGP/DIDP/files/ds_003-2024-produce.pdf |
| `tupa_bodegas` | Formato TUPA estandarizado: licencia provisional de funcionamiento para bodegas | https://cdn.www.gob.pe/uploads/document/file/7923911/1430019-10-anexo-1-p10-formato-tupa_bodegas.pdf |
| `tuo_ley28976` | TUO de la Ley Marco de Licencia de Funcionamiento (D.S. N.° 163-2020-PCM), versión actualizada | https://diariooficial.elperuano.pe/Normas/obtenerDocumento?idNorma=30 |
| `tupa_riesgo_bajo` | Formato TUPA estandarizado: licencia de funcionamiento riesgo bajo (para negocios que no califican como bodega) | https://cdn.www.gob.pe/uploads/document/file/7923904/1430019-4-anexo-1-p2-formato-tupa-lfriesgo-bajo_actualizado.pdf |
| `sunat_nuevos_inscritos` | SUNAT: obligaciones de nuevos inscritos en el RUC con negocio (NRUS, RER, RMT) | https://charlas.sunat.gob.pe/sites/default/files/2024-11/Obligaciones%20de%20nuevos%20inscritos%20en%20el%20RUC%20con%20negocio.pdf |

Formulario que se llena (no va al índice, es la plantilla del PDF):
- Declaración Jurada para Licencia Provisional de Funcionamiento para Bodegas: https://cdn.www.gob.pe/uploads/document/file/3441919/Declaraci%C3%B3n%20jurada%20para%20licencia%20provisional%20de%20funcionamiento%20de%20bodegas.pdf.pdf

Anotar la fecha de descarga de cada archivo en `data/manifiesto_descargas.json` (como en HW_03).

---

## 5. Reglas del diagnóstico (`src/reglas.py`, valores en `config.yaml`)

Las reglas son **fijas y en Python**, no las decide la IA. Cada regla guarda su fuente para mostrarla en pantalla. **Verificar cada número contra el corpus antes de usarlo.**

**¿Licencia provisional de bodega?** Sí, si se cumple todo:
- giro bodega; área total **≤ 50 m²**; en uno o más ambientes de su **vivienda**, en **1.er o 2.º piso**, con **frente o acceso directo desde la vía pública** (Reglamento Ley 30877).
- Es gratuita, se otorga una sola vez y dura 12 meses; luego la municipalidad emite la definitiva (formato TUPA bodegas).
- Si no cumple → licencia de funcionamiento riesgo bajo/medio (TUO Ley 28976) y se avisa que el formulario es otro.

**¿Qué régimen tributario?** (persona natural)
- Ingresos **o** compras mensuales ≤ S/ 5,000 → **Nuevo RUS categoría 1**, cuota S/ 20.
- ≤ S/ 8,000 → **Nuevo RUS categoría 2**, cuota S/ 50.
- Más de S/ 8,000 (o S/ 96,000 al año) → no entra al NRUS: se sugiere RER o Régimen MYPE Tributario y hablar con un contador (fuera del alcance del MVP).
- Fuente: SUNAT (charla de nuevos inscritos y orientación NRUS). UIT 2026 = S/ 5,500 (D.S. N.° 301-2025-EF), solo como dato de referencia.

**Checklist de salida:** 1) RUC en SUNAT (gratis) → 2) acogerse al régimen → 3) licencia en la municipalidad con la DJ llena → 4) DJ de condiciones de seguridad → 5) ITSE posterior.

---

## 6. Campos de la ficha (`src/ficha.py`)

| Campo | Tipo | ¿Sale del audio? | Uso |
|---|---|---|---|
| `giro` | texto | sí | ¿es bodega? |
| `nombre_bodega` | texto | sí | formulario |
| `distrito`, `provincia`, `departamento` | texto | sí | formulario |
| `direccion` | texto | sí | formulario |
| `area_m2` | número | sí | regla ≤ 50 m² |
| `en_vivienda`, `piso`, `acceso_directo_via_publica` | sí/no, número | sí | regla bodega |
| `ventas_mensuales`, `compras_mensuales` | número (S/) | sí | régimen NRUS |
| `tiene_ruc` | sí/no | sí | checklist |
| `nombre_completo`, `dni`, `telefono`, `correo` | texto | **no**: los escribe el usuario | solo van al PDF; nunca se envían a la IA |

**Regla de verificación:** un valor extraído solo queda `verificado` si aparece en la transcripción (después de normalizar números y tildes). Si no aparece, queda `por_confirmar` y la app lo resalta para que el usuario lo corrija. La IA no "corrige" ni completa datos: en una declaración **jurada** el usuario firma que todo es cierto.

**Números en palabras:** "cuatro mil quinientos" → 4500 antes de verificar (librería `text2num`, función `alpha2digit(texto, "es")`, con pruebas).

---

## 7. Bloques de trabajo (cada uno = 1 o más commits)

### Lunes 16 (hoy)
- [ ] **Bloque 0 — Repo** (mañana): crear repo público, `LICENSE` MIT, `.gitignore`, `.env.example`, este `PLAN.md`, `CLAUDE.md`, estructura de carpetas, pre-commit activado. **Commit + push.**
- [ ] **Comentar en el issue #205** con la plantilla (ver final de este archivo). Se puede editar después.
- [ ] **Entrevistas** (durante el día): 3 conversaciones con la guía de `docs/research/`.
- [ ] **Bloque 1 — Corpus e índice:** config de documentos → descargar → verificar fuentes (tabla) → extraer y limpiar → fragmentar → índice con embeddings de OpenAI. **Commit.**
- [ ] **Bloque 2 — Motor RAG:** copiar el motor, adaptar prompt y mensajes, 15–20 preguntas de evaluación (5 dichas como un bodeguero, 5 fuera del corpus), barrido del umbral. **Commit.**
- [ ] **Despliegue de prueba (noche):** subir una app mínima a Streamlit Community Cloud que cargue el índice y responda una pregunta. Así descubro hoy los problemas del servidor, no mañana.
  - Si ChromaDB falla en el servidor por la versión de SQLite: agregar `pysqlite3-binary` y el parche de 3 líneas al inicio de `app.py`.

### Martes 17
- [ ] **Bloque 3 — Voz y ficha:** `voz.py` + `ficha.py` + verificación + números en palabras, con pruebas. Grabar `ejemplos/audio_ejemplo.m4a` con **datos inventados** (plan B del demo). **Commit.**
- [ ] **Bloque 4 — Reglas y PDF:** `reglas.py` + `formulario.py` (reportlab, misma estructura de secciones que el formato oficial). **Commit.**
- [ ] **Bloque 5 — App completa y despliegue final:** 3 pasos + chat + botón "usar audio de ejemplo" + mensajes de error claros. Que 2 personas la prueben. **Commit.**
- [ ] **Bloque 6 — README de 9 partes** + 3 capturas + diagrama + costo por usuario desde `logs/costos_llm.csv`. **Commit.**
- [ ] **Video de respaldo** (60–90 s) con el flujo completo; link en el README y en el issue.
- [ ] **Ensayo con cronómetro (3 min)** + practicar 3 cambios en vivo (ver sección 9).

### Miércoles 18
- [ ] 7:25 a. m. conectada, app pública y local abiertas, VS Code con el repo, video a la mano.

---

## 8. Costo por usuario (para el modelo de negocio)

Una sesión típica = 1 audio de ~1 min (Whisper) + 1 llamada de extracción (LLM) + ~3 preguntas al chat (embeddings + LLM).
Calcularlo con las llamadas reales de `logs/costos_llm.csv` y los precios de la página de OpenAI (anotar la fecha de verificación en `config.yaml`, como en HW_03). Poner un **tope de gasto** en la cuenta de OpenAI.

Modelo de negocio (hipótesis que validan las entrevistas): gratis para el bodeguero; pagan quienes ganan con que se formalice (municipalidades con metas de formalización, cajas municipales/fintech que necesitan clientes con RUC, distribuidoras que trabajan con bodegas). Poner un precio concreto en el README.

---

## 9. Preparación para los comentarios (me pueden pedir mostrar o cambiar código)

Mapa del código en el orden del flujo: `app.py` → `src/motor.py` → `src/voz.py` → `src/ficha.py` → `src/reglas.py` → `src/formulario.py` / `src/motor_rag.py`.

Cambios para practicar el martes, con la app corriendo en local (`streamlit run app.py`):
1. Cambiar el umbral de abstención del chat (`config.yaml` → `motor.umbral_similitud`) y probar una pregunta fuera del corpus.
2. Cambiar el límite del NRUS o del área de bodega (`config.yaml` → `reglas`) y ver cómo cambia el diagnóstico.
3. Agregar un campo a la ficha (esquema en `ficha.py` + etiqueta en `config.yaml`).
4. Explicar dónde decide el motor **no** llamar a la IA y dónde queda un campo "por confirmar".

---

## 10. Comentario para el issue #205 (borrador)

```
Nombre: Michelle Li
Startup y one-liner: Formaliza — Ayudamos a los bodegueros del Perú a formalizarse: cuentan su negocio en un audio y reciben qué trámites les tocan, con la ley citada, y la declaración jurada de su licencia ya llena.
Link del demo (URL pública, o "corre en local"): <URL de Streamlit Cloud>
Link del repo: <URL del repo>
Herramientas del curso que usa: Whisper, de voz a texto (sesión 13); LLM con salidas estructuradas y RAG sobre la Ley General de Bodegueros, su reglamento, la Ley Marco de Licencia de Funcionamiento y SUNAT (sesión 08)
Video de respaldo: se agrega antes del miércoles 18
```
