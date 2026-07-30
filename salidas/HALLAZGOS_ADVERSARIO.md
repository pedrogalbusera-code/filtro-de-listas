# Hallazgos de la corrida adversaria

Fecha: 2026-07-28. Pipeline: F06 (puntaje explicable), fecha de corte 2026-07-28.

**No se modificó ningún workflow ni verificador.** Los archivos temporales de
workflow se generaron, ejecutaron y borraron. Las salidas quedan en
`salidas/salida_adv1.csv` y `salidas/salida_adv3.csv` (`salida_adv2.csv` no
existe porque el pipeline crasheó antes de escribir).

## Resumen

| Gravedad    | Cantidad |
|-------------|----------|
| **rompe**       | 1    |
| **silencioso**  | 10   |
| **cosmético**   | 2    |
| **total**       | 13   |

---

## Archivo 1 — `leads_adversario_1.csv` (48 filas)

48 filas entran, 48 salen. Cero excepciones. Los hallazgos son todos de
resultado incorrecto, no de crash.

### Teléfonos — falsos inválidos y falso ambiguo

| # | Fila | Entrada | Qué esperaba | Qué hizo | Gravedad |
|---|------|---------|-------------|----------|----------|
| 1 | T02 | `+54 9 11 4161 7956` | celular (el 9 separado por espacios) | **invalido** — `startsWith('+549')` falla por el espacio | **silencioso** — un espacio pierde un celular válido, el más grave de los previstos |
| 2 | T05 | `15-4161-7956` | invalido (15 sin código de área, no se puede resolver) | **ambiguo** con norm `+541541617956` — 10 dígitos por casualidad, normalización incorrecta | **silencioso** — peor que un falso inválido: el contacto suma 18 puntos y puede ser llamado a un número equivocado |
| 3 | T01 | `+54 11 4161-7956` | fijo en formato internacional | **invalido** — 12 dígitos, no matchea ningún patrón | **silencioso** |
| 4 | T03 | `549 11 4161 7956` | celular sin el `+` | **invalido** — 13 dígitos sin `+` al inicio | **silencioso** |
| 5 | T04 | `011 15 4161-7956` | celular en formato viejo con 15 | **invalido** — 13 dígitos empezando con 0, no es el patrón de fijo (11 díg) | **silencioso** |
| 6 | T10 | `1141617956 / 1165385561` | dos teléfonos válidos | **invalido** — la barra y los dígitos extras dan >10 dígitos | **silencioso** — se pierden dos números buenos |

### Localidad

| # | Fila | Entrada | Qué esperaba | Qué hizo | Gravedad |
|---|------|---------|-------------|----------|----------|
| 7 | T19 | `Morón (Buenos Aires)` | en zona (es Morón) | **fuera de zona** — `normLoc` produce `"moron (buenos aires)"`, no matchea `"moron"` | **silencioso** — una aclaración entre paréntesis descarta un contacto válido |
| 8 | T21 | *(vacío)* | indeterminado, distinguido de "fuera de zona" | **fuera de zona de cobertura** — mismo motivo que alguien de CABA | **silencioso** — "no sé dónde vive" y "sé que vive lejos" quedan indistinguibles; el contacto se descarta sin haber preguntado |

### Deduplicación

| # | Fila | Entrada | Qué esperaba | Qué hizo | Gravedad |
|---|------|---------|-------------|----------|----------|
| 9 | T31 | mismo CUIL que T01, otro teléfono | dedup por CUIL (correcto), pero el teléfono válido del perdedor debería poder recuperarse | T31 (tel válido, match `1168442753`) es perdedor; su teléfono **se pierde** — el ganador T26 conserva su propio teléfono | **silencioso** — el diseño actual no transfiere datos del perdedor al ganador; en este caso un teléfono utilizable desaparece |

### Cosmético

| # | Fila | Entrada | Qué esperaba | Qué hizo | Gravedad |
|---|------|---------|-------------|----------|----------|
| 10 | T08 | `1141617956.0` | invalido (correcto), con motivo que diga "artefacto de Excel" | **invalido** correcto pero sin motivo específico — el `.0` es un patrón reconocible de Excel que pierde el cero inicial | **cosmético** |
| 11 | T09 | `1.14162E+09` | invalido (correcto), con aviso de archivo dañado | **invalido** correcto pero sin motivo específico — la notación científica significa que el número se perdió en el archivo de origen | **cosmético** |

### Lo que SÍ funcionó bien en el archivo 1

- **T07** `(011) 4161-7956`: paréntesis → strip de no-dígitos → fijo. Correcto.
- **T11/T12** dedup por teléfono: `1155551111` (ambiguo) y `+5491155551111`
  (celular) comparten match `1155551111`. T12 gana, T11 es duplicado. Correcto.
- **T13/T14** dedup por teléfono con adopción de tipo: T14 (ambiguo, 10 díg)
  adopta tipo `fijo` de T13 (`011-45551111`). Correcto.
- **T15–T18** normalización de localidad: MORÓN, moron, ` Haedo `, Ramos Mejia
  → todas en zona. Correcto.
- **T23** CUIL vacío: no crashea, procesable, cuil_valido=FALSE. Correcto.
- **T25** prefijo 99: inválido. Correcto.
- **T26/T27/T28** CUIL con puntos/espacios/sin guiones: normalización correcta.
- **T29** DV incorrecto a propósito: inválido. Correcto.
- **T30** prefijo 30 (jurídica): válido. Correcto.
- **T32–T38** fechas: todos los valores exactos de la corrección de F05.
- **T39** nombre vacío: marcado "sin nombre". Correcto.
- **T40** coma en nombre (`PEREZ, JUAN`): quoting CSV OK. Correcto.
- **T42/T43** duplicados con espacio trailing en nombre: dedup por cuil+teléfono
  los atrapa. Correcto.
- **T44** `sin  dato` (dos espacios): inválido. Correcto.
- **T45** `N/D`: inválido. Correcto.
- **T46** `0` (un solo cero): inválido. Correcto.
- **T48** `23-31000009-4` (reemisión femenina): válido. Correcto.
- **7 CUILs con resto 1** (T03, T14, T33, T37, T44, T47 + 1 más): todos
  cuil_valido=FALSE y cuil_dudoso=TRUE. Correcto.

---

## Archivo 2 — `leads_adversario_2.csv` (8 filas)

| # | Fila | Entrada | Qué esperaba | Qué hizo | Gravedad |
|---|------|---------|-------------|----------|----------|
| 12 | — | 3 filas de basura arriba del header, columnas renombradas | crash o error claro | **NodeOperationError: `Invalid Record Length: columns length is 1, got 7 on line 4`** — n8n toma la primera fila (`LISTADO DE CONTACTOS - PLANILLA COMERCIAL`) como header de 1 columna; la fila 4 tiene 7 campos y explota | **rompe** |

El error es claro y la ubicación es precisa. No se genera archivo de salida.

**Lo que no se pudo testear** (por el crash temprano):
- Mapeo de columnas renombradas (`Nombre y Apellido` → `nombre`, etc.)
- Fila vacía en el medio (línea 8 del CSV)
- T55 con menos columnas que el header
- Orígenes con otras etiquetas (`Web`, `Meta`, `Referido` vs `referido`)
- CUIL con DV incorrecto a propósito (T57, `27-40330288-1`)
- Columna extra `Observaciones` con comas en texto libre

Estos ítems son el trabajo real de "adaptar el pipeline a un cliente nuevo":
mapeo de columnas, tolerancia a filas sucias, sinónimos de origen.

---

## Archivo 3 — `leads_adversario_3.csv` (5 filas)

| # | Fila | Entrada | Qué esperaba | Qué hizo | Gravedad |
|---|------|---------|-------------|----------|----------|
| 13 | todas | CSV con separador `;` (Excel en español) | error, o detección del separador | **5 filas procesadas, todas con campos vacíos** — n8n parseó con coma, cada fila quedó como una sola columna; el pasamanos convirtió todo a string vacío; el scoring asignó puntaje -10 y prioridad "descartado" a las 5. **El output tiene cara de correcto: 5 filas, 26 columnas, puntaje, prioridad, motivo.** Un cliente recibe esto y no se entera. | **silencioso** — el peor hallazgo de los tres archivos |

---

## Clasificación de impacto para F09

Los hallazgos se pueden agrupar en tres ejes para decidir qué entra en la suite
de regresión:

**1. Formatos de teléfono no reconocidos** (T01, T02, T03, T04, T05, T10):
El pipeline solo reconoce 3 formatos (`+549...`, `0XX-...` de 11 díg, 10 díg
pelados). Todo lo demás cae en inválido. T02 es el más grave (un espacio). T05
es el más peligroso (acepta como ambiguo un número que no se puede resolver).

**2. Localidad: comparación demasiado literal** (T19) y **sin distinguir
vacío de fuera de zona** (T21). Son dos cosas distintas:
- T19 se arregla con lógica de matching más flexible (contains, startswith).
- T21 se arregla separando "sin localidad" de "fuera de zona" en F04.

**3. Tolerancia de archivo** (archivo 2 y archivo 3). No es un bug del pipeline,
es una funcionalidad que no existe: mapeo de columnas y detección de separador.
Es el trabajo de onboarding de un cliente nuevo.
