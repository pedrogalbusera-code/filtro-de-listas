Estás trabajando en este repo. Antes de tocar nada, leé `CLAUDE.md`, `ESTADO.md`,
`fases/F01-normalizacion-telefono.md` y `salidas/HALLAZGOS_ADVERSARIO.md` completos.

# CORRECCIÓN F01 — Formatos de teléfono que hoy se pierden o se leen mal

Esta no es una fase nueva. Es una corrección sobre F01, que ya está cerrada.
Corrandola en su propia sesión, sin mezclarla con ninguna fase.

## Antes de escribir una sola línea

Comprobá el entorno y **pedí instalar lo que falte AHORA, no en la mitad**:
Node 20+, Python 3.10+, git, y n8n con `npx n8n` (nunca global). Comprobá que
`N8N_RESTRICT_FILE_ACCESS_TO` apunte a esta carpeta. Detalle en `prompts/SETUP.md`.
Si necesitás una librería nueva, proponé el comando exacto y **esperá el OK antes
de instalar**.

Esta corrección depende de que **F09 esté cerrada y el golden exista**
(`salidas/golden_2026-07-28.csv` y `_auditoria.csv`). El golden es el instrumento
principal de esta sesión. Si no está, frená y decilo.

## Qué es esto en una línea

El normalizador de F01 reconoce solo 3 formatos (`+549…`, `0XX-…` de 11 díg, 10
díg pelados). Todo lo demás cae en `invalido`, y hay un caso que es peor que
perderse: lo acepta con un número **equivocado**. Esta sesión enseña al parser los
formatos que trae cualquier lista argentina real, **sin tocar el comportamiento
sobre el archivo limpio**.

## El criterio que manda sobre todo lo demás — leelo primero

Los formatos rotos (T01–T10) **no están en `data/leads_prueba_SINTETICO_1.csv`**:
ese archivo solo tiene `011-…`, `+549…` y 10 dígitos pelados, que ya se manejan
bien. Están todos en `data/leads_adversario_1.csv`.

**Consecuencia, y es el criterio 1:** después de esta corrección, con el CSV limpio
y la misma fecha de corte, las dos salidas tienen que quedar **byte a byte idénticas
al golden de F09** (mismos SHA-256:
`9a6884603f9128c29a7503cb25b8417ceb233b58bdd89e9053bf4f486a61dcb4` comercial,
`ae6fcc5f146d6ec59395b3fb09a5bbdfcd764303e762a287dfe6a44623fd9cd2` auditoría).

Si el golden **se mueve**, tu refactor le cambió el comportamiento a un formato que
sí está en el archivo limpio: **frená y mostrame el diff**, no regeneres el golden
para taparlo. Que el golden no se mueva es lo que prueba que corregiste los formatos
nuevos sin romper F02–F08. Por eso esta corrección se puede hacer sola, sin
re-verificar toda la cadena.

## Qué tiene que pasar con cada caso — la tabla es el spec

Verificá por **contenido de celda** contra estos valores, escritos a mano en el
test. No alcanza con contar filas.

| Fila | Entrada | `telefono_tipo` esperado | `telefono_norm` esperado | Nota |
|------|---------|--------------------------|--------------------------|------|
| T01 | `+54 11 4161-7956` | `fijo` | `+541141617956` | Internacional sin el 9. Hoy: invalido. |
| T02 | `+54 9 11 4161 7956` | `celular` | `+5491141617956` | El 9 separado por espacios. **El más grave: un espacio lo perdía.** |
| T03 | `549 11 4161 7956` | `celular` | `+5491141617956` | Internacional sin el `+`. |
| T04 | `011 15 4161-7956` | `celular` | `+5491141617956` | Formato viejo con 15. El 15 marca celular. |
| T05 | `15-4161-7956` | `invalido` | *(vacío)* | 15 sin código de área: **no se puede resolver**. Hoy lo acepta como `ambiguo` con un número inventado (`+541541617956`) → llamada a un número equivocado. Motivo: "sin código de área". |
| T06 | `4161-7956` | `invalido` | *(vacío)* | 8 díg sin área. Ya correcto. |
| T07 | `(011) 4161-7956` | `fijo` | `+541141617956` | Ya correcto. No lo rompas. |
| T08 | `1141617956.0` | `invalido` | *(vacío)* | Artefacto de Excel: el `.0` mete un dígito de más. Motivo específico: "artefacto de Excel (.0)". |
| T09 | `1.14162E+09` | `invalido` | *(vacío)* | Notación científica: el número se perdió en el archivo. Motivo: "notación científica: número dañado en origen". |
| T10 | `1141617956 / 1165385561` | `ambiguo` | `+541141617956` | Dos teléfonos en la celda. Tomá el **primero**, clasificalo, y dejá el motivo "celda con 2 teléfonos: se tomó el primero". No se pierden los dos. |

Casos que ya funcionan y **no** se tocan (deben seguir igual): T11/T12 y T13/T14
(dedup por teléfono con adopción de tipo), T44 `sin  dato`, T45 `N/D`, T46 `0` →
todos invalido. Si alguno cambia, rompiste algo.

## Cómo, sin adivinar

- El arreglo es del limpiador de entrada del nodo Code de F01, **no** de la
  detección de tipo posterior. La causa raíz de casi todos es la misma: se compara
  el string **crudo** (`startsWith('+549')`) en vez de normalizar espacios y
  símbolos **antes** de decidir. Sacá espacios internos y separadores primero,
  después clasificá.
- T05 es el que exige criterio, no solo limpieza: un `15` **sin** código de área no
  se puede completar. La regla es la de F11: **ante lo que no se puede resolver, se
  marca invalido con motivo, no se adivina.** Lo contrario es lo que hace hoy.
- **No inventes un código de área.** Si falta el área, es invalido. Punto.
- La función sigue siendo pura: mismo input, mismo output, sin estado.

## El verificador

Actualizá `verificadores/v01_telefono.py`:

1. Agregá los 10 casos de la tabla como entrada/salida esperada explícita (tipo y
   norm exactos), más los "no se tocan".
2. El conteo 118/82 de F01 era sobre el CSV limpio y **no cambia** (los formatos
   nuevos no están ahí). Dejalo como está; si cambia, hay un problema.
3. Corré el parser sobre `data/leads_adversario_1.csv` y compará contra el oráculo
   Python independiente, celda por celda.

Las tres formas de check falso de `prompts/README.md` aplican. En particular: un
test que solo cuente cuántos quedan `invalido` **pasa con el bug de T05 puesto**
(T05 seguiría contando como resuelto siendo que el número está mal). Verificá el
`telefono_norm`, no solo el tipo.

## Criterio de aceptación

1. Los dos SHA-256 sobre el CSV **limpio** siguen idénticos al golden de F09.
2. Las 10 filas T01–T10 dan exactamente lo de la tabla, verificado por celda.
3. `v01_telefono.py` pasa con los casos nuevos y el conteo 118/82 intacto.
4. `python verificadores/correr_todo.py` sigue en verde de punta a punta.
5. La bitácora de `ESTADO.md` registra qué formatos se agregaron, el arreglo de T05
   (de `ambiguo` equivocado a `invalido`) y por qué el golden no se movió.

## Prohibido

- Regenerar, relajar o "actualizar" el golden para que algo pase. Si el golden se
  mueve, el bug es de esta corrección.
- Adivinar un código de área o completar un número incompleto.
- Tocar la lógica de F02 a F08, ni la dedup de F03. Si un verificador de otra fase
  se pone rojo, **anotalo y frená**: es señal de que un formato nuevo sí estaba en
  el archivo limpio y hay que entenderlo, no parcharlo.
- Dejar el esperado del verificador como rango o "al menos". Va el valor exacto.

## Terminado cuando

`v01_telefono.py` da verde con los 10 casos nuevos, `correr_todo.py` sigue en
verde, los dos SHA-256 no se movieron, y `ESTADO.md` quedó con la bitácora.
