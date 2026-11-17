# Similitud top-1 de las 20 preguntas (oai3small_c500_s150)

Umbral elegido: **0.474** (defensa 1, sin IA). Ordenadas de mayor a menor similitud.

| # | id | Tipo | Similitud top-1 | Pregunta | Defensa 1 (umbral) |
|---|---|---|---|---|---|
| 1 | D09 | dentro | 0.8260 | ¿Qué cambió la Ley 31866 en la Ley General de Bodegueros? | pasa ✅ |
| 2 | D11 | dentro | 0.7794 | ¿Qué vigencia tiene la licencia de funcionamiento? | pasa ✅ |
| 3 | D13 | dentro | 0.7600 | ¿Cuáles son los límites de ingresos y de activos fijos para estar en el Nuevo RUS? | pasa ✅ |
| 4 | D07 | dentro | 0.7556 | ¿Qué es el Registro Nacional de Bodegueros y quién lo administra? | pasa ✅ |
| 5 | D10 | dentro | 0.7526 | Después de obtener la licencia provisional de bodega, ¿en qué plazo el gobierno local emite la licencia? | pasa ✅ |
| 6 | D12 | dentro | 0.7411 | Para un establecimiento con nivel de riesgo bajo, ¿en cuántos días hábiles se emite la licencia de funcionamiento? | pasa ✅ |
| 7 | D06 | dentro | 0.6999 | ¿Qué unidades económicas no se consideran actividad bodeguera según el Reglamento de la Ley 30877? | pasa ✅ |
| 8 | D15 | dentro | 0.6887 | ¿Qué beneficio tienen las bodegas formales en las tarifas de servicios públicos? | pasa ✅ |
| 9 | D08 | dentro | 0.6871 | ¿Qué día se celebra el Día del Bodeguero? | pasa ✅ |
| 10 | D02 | dentro | 0.6833 | Si saco la licencia provisional para mi bodega, ¿cuánto tiempo me dura? | pasa ✅ |
| 11 | D04 | dentro | 0.6727 | Una empresa me pide factura, ¿se la puedo dar si estoy en el Nuevo RUS? | pasa ✅ |
| 12 | D14 | dentro | 0.6381 | ¿Cada cuánto tiempo se renueva el certificado de inspección técnica de seguridad en edificaciones (ITSE)? | pasa ✅ |
| 13 | D01 | dentro | 0.6232 | Tengo mi bodeguita en la sala de mi casa, ¿hasta qué tamaño puede ser para sacar la licencia provisional? | pasa ✅ |
| 14 | D03 | dentro | 0.6156 | Vendo como 4 mil soles al mes en mi tiendita, ¿cuánto tendría que pagarle a la SUNAT cada mes? | pasa ✅ |
| 15 | F03 | fuera | 0.5391 | ¿Cuánto cuesta registrar la marca de mi negocio en Indecopi? | **pasa → defensa 2 (IA)** |
| 16 | F02 | fuera | 0.5003 | ¿Qué tasa de interés me cobra una caja municipal por un préstamo para mi bodega? | **pasa → defensa 2 (IA)** |
| 17 | F04 | fuera | 0.4885 | ¿Cómo se calcula la CTS de los trabajadores de una microempresa? | **pasa → defensa 2 (IA)** |
| 18 | F05 | fuera | 0.4845 | Quiero vender comida preparada, ¿qué requisitos sanitarios de DIGESA necesito? | **pasa → defensa 2 (IA)** |
| 19 | D05 | dentro | 0.4793 | Si alguien me compra un pan de 50 céntimos, ¿igual tengo que darle boleta? | pasa ✅ |
| 20 | F01 | fuera | 0.3375 | ¿Cómo se prepara un buen ceviche para vender en mi local? | detenida ✅ |

La pregunta legítima con menor similitud tiene **0.4793**. **4 preguntas fuera del corpus la superan**: F03 (0.5391), F02 (0.5003), F04 (0.4885), F05 (0.4845). Ningún umbral puede detenerlas sin detener también preguntas legítimas: por eso existe la defensa 2.
