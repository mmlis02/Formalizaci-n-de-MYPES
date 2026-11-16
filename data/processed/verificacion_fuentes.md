# Verificación de fuentes (Bloque 1, paso 3)

Página sin texto = menos de 200 caracteres extraíbles. Un PDF se descarta como escaneo si más del 50% de sus páginas no tiene texto.
orden_* = % de veces que el número de 'Artículo N.' siguiente es mayor o igual al anterior (en todo el PDF y solo en el texto de la norma, tras recortar las normas vecinas).

| id | paginas_pdf | paginas_con_texto_de_la_norma | chars_pagina_min | chars_pagina_mediana | chars_pagina_max | paginas_sin_texto | chars_de_otras_normas | articulos_detectados | orden_pdf_completo | orden_solo_la_norma | paginas_con_encabezado_elperuano | ligaduras_rotas | usable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ley30877 | 2 | 2 | 5636 | 5870 | 6104 | ninguna | 5352 | 10 | 85% | 100% | 2 | 0 | SÍ, recortando otras normas |
| ley31866 | 1 | 1 | 4587 | 4587 | 4587 | ninguna | 1860 | 1 | n/a | revisión manual (pocos artículos) | 1 | 0 | SÍ, recortando otras normas |
| ds010_2020_produce | 6 | 6 | 2797 | 6183 | 7337 | ninguna | 3736 | 27 | 93% | 96% | 6 | 0 | SÍ, recortando otras normas |
| ds003_2024_produce | 2 | 2 | 6313 | 6529 | 6746 | ninguna | 5459 | 6 | 75% | revisión manual (pocos artículos) | 2 | 0 | SÍ, recortando otras normas |
| tupa_bodegas | 2 | 2 | 1223 | 1722 | 2222 | ninguna | 0 | 0 | n/a | revisión manual (pocos artículos) | 0 | 0 | SÍ |
| tuo_ley28976 | 14 | 14 | 162 | 5375 | 6666 | 1 | 0 | 29 | 96% | 96% | 14 | 0 | SÍ |
| tupa_riesgo_bajo | 2 | 2 | 1505 | 2372 | 3239 | ninguna | 0 | 0 | n/a | revisión manual (pocos artículos) | 0 | 0 | SÍ |
| sunat_nuevos_inscritos | 0 | — | — | — | — | — | — | — | — | — | — | — | NO (no se pudo descargar) |
| sunat_nuevo_rus | 9 | 9 | 86 | 2153 | 3839 | 1 | 0 | 0 | n/a | revisión manual (pocos artículos) | 0 | 1 | SÍ |
| sunat_formalizar_negocio | 11 | 11 | 80 | 4248 | 4978 | 1,11 | 0 | 0 | n/a | revisión manual (pocos artículos) | 0 | 3 | SÍ |

## Páginas con poco texto (revisión manual)

- **tuo_ley28976**
  - pág. 1: «TUO de la Ley Nº 28976, Ley Marco de Licencia de Funcionamiento DECRETO SUPREMO N° 163-2020-PCM Editora Perú ACTUALIZADA»
- **sunat_nuevo_rus**
  - pág. 1: «Nuevo Régimen Único Simplificado 1 Nuevo Régimen Único Simpliﬁcado (Nuevo Rus) Carpeta»
- **sunat_formalizar_negocio**
  - pág. 1: «1 ¿Cómo formalizar tu negocio? ¿Cómo formalizar tu negocio? ASPECTOS TRIBUTARIOS»
  - pág. 11: «20 01/2020 www.sunat.gob.pe 0801-12-100 / (01) 315-0730 / *4000 Más información en: Central de consultas:»
