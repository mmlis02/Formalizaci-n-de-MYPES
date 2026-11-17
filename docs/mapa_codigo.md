# Mapa del código

Para explicar y cambiar el código en vivo. Los números de línea son del commit en que se escribió este archivo (16/11/2026): si editas un archivo, las líneas de más abajo se corren.

## El flujo, en orden

```
app.py → src/motor.py → src/voz.py → src/ficha.py → src/reglas.py → src/formulario.py
   └──────────────────────────────────────────────→ src/motor_rag.py   (pestaña del chat)
```

| # | Archivo | Función principal | Qué hace |
|---|---|---|---|
| 1 | [app.py](../app.py) | `paso_cuentame` (133), `paso_revisa` (167), `paso_plan` (203), `chat` (284) | Solo interfaz: los 3 pasos y el chat. Llama únicamente a `src/motor.py` y `src/motor_rag.py`. |
| 2 | [src/motor.py](../src/motor.py) | `procesar_audio` (40), `procesar_texto` (24), `diagnosticar` (56), `generar_formulario` (61) | Une voz → ficha → reglas → formulario. Si falla el audio, no llama al LLM. |
| 3 | [src/voz.py](../src/voz.py) | `transcribir` (30) | Revisa el archivo (que exista, el formato, el tamaño) y llama a Whisper. |
| 4 | [src/ficha.py](../src/ficha.py) | `extraer_ficha` (126) | El LLM devuelve cada campo con su **valor** y su **cita**; `verificar_campo` (91) decide su estado. |
| 5 | [src/reglas.py](../src/reglas.py) | `diagnosticar` (112) | Reglas fijas: camino A/B/C, Nuevo RUS, checklist con fuentes y preguntas pendientes. |
| 6 | [src/formulario.py](../src/formulario.py) | `generar_pdf` (333) | PDF de la declaración jurada: bodegas (A, 1 pág.) o Anexo 1 (B, 2 págs.). |
| 7 | [src/motor_rag.py](../src/motor_rag.py) | `responder` (149) | Chat: busca fragmentos, se abstiene sin IA si no se parecen, y si no, llama al LLM y cita página. |

Piezas de apoyo:
- [src/llm.py](../src/llm.py): `llamar_llm_json` (26) y `transcribir_audio` (54).
- [src/costos.py](../src/costos.py): `registrar_llamada` (52).
- [config.yaml](../config.yaml): todo lo configurable.
- Proceso offline: [build_index.py](../build_index.py).
- Antes de presentar: `python scripts/prueba_demo.py` ([scripts/prueba_demo.py](../scripts/prueba_demo.py)) recorre el flujo real y muestra ✅/❌ por paso.
- Evaluación de la ficha: [eval/evaluar_ficha.py](../eval/evaluar_ficha.py), con los casos de [eval/casos_ficha.yaml](../eval/casos_ficha.yaml).

## «Si me preguntan X, está en…»

| Pregunta | Dónde |
|---|---|
| ¿Dónde se abstiene **sin llamar a la IA**? | [src/motor_rag.py:168](../src/motor_rag.py#L168): `if aplicar_umbral and r.similitud_max < umbral:`. El umbral (0.474) está en [config.yaml:291](../config.yaml#L291). |
| ¿Dónde se abstiene **con** la IA? | [src/motor_rag.py:187](../src/motor_rag.py#L187): `if datos.get("fuera_de_corpus"):` |
| ¿Dónde un campo queda **por confirmar**? | [src/ficha.py:97](../src/ficha.py#L97) (la cita no está en la transcripción), [src/ficha.py:100](../src/ficha.py#L100) (el valor no está en la cita) y [src/ficha.py:154](../src/ficha.py#L154) (los 3 sí/no que deciden el camino; lista en [config.yaml:389](../config.yaml#L389)). |
| ¿Dónde se normalizan los **números en palabras**? | [src/ficha.py:65](../src/ficha.py#L65): `normalizar()` («cuatro mil quinientos» → 4500, «4,500» → 4500, «primer» → 1). |
| ¿Dónde se decide el **camino**? | [src/reglas.py:52](../src/reglas.py#L52): `decidir_camino()`. C en la línea 56, B cuando una condición de bodega falla en la 69 y A en la 71. |
| ¿Dónde se calcula el **Nuevo RUS**? | [src/reglas.py:74](../src/reglas.py#L74): `decidir_regimen()`. El monto que manda es `max(ventas, compras)` (línea 80); las categorías están en [config.yaml:427](../config.yaml#L427). |
| ¿Dónde se registra el **costo** de cada llamada? | [src/costos.py:52](../src/costos.py#L52): `registrar_llamada()`. La llaman [src/llm.py:50](../src/llm.py#L50) (LLM), [src/llm.py:75](../src/llm.py#L75) (Whisper) y [src/embeddings.py:68](../src/embeddings.py#L68) (embeddings). Todo va a `logs/costos_llm.csv`. |
| ¿Cómo sé que **los datos personales no van a la IA**? | No son campos de la ficha (`CAMPOS`, [src/ficha.py:34](../src/ficha.py#L34)). Los pide `paso_plan` en [app.py:203](../app.py#L203) y solo llegan a `generar_pdf`. Lo prueba `test_esquema_tiene_todos_los_campos_y_ninguno_personal` en `tests/test_ficha.py`. |
| ¿Dónde se pone la **cita (documento, pág.)** en el chat? | `_poner_citas` en [src/motor_rag.py](../src/motor_rag.py): cambia cada `[Fn]` por la página que dicen los metadatos del fragmento; el LLM nunca escribe páginas. |
| ¿Cómo se comprueba que `src/` no importa Streamlit? | `grep -rn streamlit src/` no devuelve nada. |

## 3 cambios para practicar en vivo

Con la app corriendo en local (`streamlit run app.py`; Streamlit recarga solo al guardar).

**1. Subir el umbral de abstención del chat** — [config.yaml:291](../config.yaml#L291)
```yaml
    openai: 0.474   →   openai: 0.65
```
Pregunta en el chat: «Vendo como 4 mil soles al mes en mi tiendita, ¿cuánto tendría que pagarle a la SUNAT cada mes?». Su similitud es 0.616, así que ahora **se abstiene sin llamar a la IA** (costo 0). Vuelve a 0.474 y responde con cita.

**2. Bajar el área máxima de una bodega** — [config.yaml:421](../config.yaml#L421)
```yaml
    area_max_m2: 50   →   area_max_m2: 20
```
Pulsa «Usar audio de ejemplo» (bodega de 25 m²), confirma los datos y mira el plan: pasa del **camino A al camino B**, con el ❌ en la condición del área y el PDF del Anexo 1 en lugar del de bodegas. Lo mismo comprueba `test_cambiar_el_area_maxima_en_config_cambia_el_camino`.

**3. Agregar un campo a la ficha** — [src/ficha.py:48](../src/ficha.py#L48) y [config.yaml:386](../config.yaml#L386)
```python
    "tiene_ruc": "si_no",
    "numero_trabajadores": "numero",        # ← línea nueva en CAMPOS
```
```yaml
    tiene_ruc: {etiqueta: "¿Tiene RUC?", ...}
    numero_trabajadores: {etiqueta: "N.° de trabajadores", descripcion: "Cuántas personas trabajan en el negocio, sin contar al dueño."}   # ← línea nueva
```
El esquema JSON se arma solo con esas dos líneas, y el campo aparece en «Revisa tus datos» con su estado y su cita.

Al correr `python -m pytest` pasan 63 y **falla 1, y es lo esperado**: `test_extraer_ficha_marca_lo_inventado_como_por_confirmar` cuenta los estados, y el campo nuevo (que la respuesta simulada no trae) suma un «no mencionado». Se arregla cambiando `"no_mencionado": 2` por `3` en `tests/test_ficha.py`. Si agregas solo una de las dos líneas, falla además `test_esquema_tiene_todos_los_campos_y_ninguno_personal`, que comprueba que el código y el config tienen los mismos campos.
