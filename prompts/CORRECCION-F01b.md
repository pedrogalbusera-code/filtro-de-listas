Estás trabajando en este repo. Antes de tocar nada, leé `CLAUDE.md`, `ESTADO.md`,
`prompts/CORRECCION-F01.md` (la corrección anterior de teléfono) y
`fases/F01-normalizacion-telefono.md` completos. El normalizador está factorizado
(F14): es `JS_NORM_TELEFONO`, una sola implementación compartida. Lo que toques acá lo
consume **todo el pipeline**.

# CORRECCION-F01b — aceptar el celular con `15` sin el `0` inicial

## De dónde sale

En F14, el spec pedía O02 como `11 15 6161 7956` y F01 lo tiró a `invalido`: reconoce el
formato viejo con `15` **solo con el 0 inicial** (`011 15 6161-7956`). Sin el 0 son 12
dígitos y no matchea ningún patrón. En F14 se ajustó el dato de prueba para no tocar F01;
esta corrección es para que F01 lo acepte de una.

El formato: un celular AMBA escrito `11 15 XXXX XXXX` (área `11` + marcador `15` + 8
dígitos = **12 dígitos**), con o sin separadores. Canónico destino: el **mismo** que
`+54 9 11 XXXX-XXXX` y que `011 15 XXXX-XXXX` (celular, con el `9`). Es el mismo número,
escrito sin el 0 de salida.

## Por qué es seguro (pero medilo, no lo argumentes)

`11 15` + 8 dígitos es **inequívocamente celular**: ningún fijo AMBA tiene 12 dígitos (el
fijo es `11 XXXX-XXXX`, 10). Así que aceptarlo no puede robarle un fijo a nadie. Pero
antes de escribir una línea de normalizador:

**Paso 1 — MEDIR el impacto en el golden. Frená y mostrame el número.**

Contá, sobre `data/leads_prueba_SINTETICO_1.csv` (las 200 canónicas) y sobre los
adversarios, cuántas filas tienen un teléfono que hoy cae en `invalido` **y** que con esta
regla pasaría a celular válido (patrón: 12 dígitos que empiezan en `1115`, o su forma con
separadores). Reportá el conteo por archivo **antes de cambiar el normalizador**.

- **Si el conteo en las 200 canónicas es 0:** la corrección es puramente aditiva, el golden
  **no se mueve**, y lo verificás como cualquier otra cosa (suite 10/10, SHA intactos).
- **Si el conteo es > 0:** esos números pasan de `invalido` (descartado, sin teléfono) a
  celular válido → cambia su puntaje → **el golden se mueve con razón**. Eso NO se arregla
  ni se esconde: es un cambio de comportamiento deliberado. **Frená y mostrame** el conteo
  y qué filas son; regeneramos el golden a propósito (como se hizo en CORRECCION-F02 con
  los 19 CUIL), documentando que el archivo tenía esos números mal clasificados, no el
  código. No regeneres el golden por tu cuenta.

## Qué construir (después del OK sobre el golden)

En `JS_NORM_TELEFONO`, sumá el reconocimiento del `15` sin 0, mapeando al **mismo canónico
celular** que ya produce la variante con 0. No dupliques la rama del `15`: es la misma
lógica con el 0 opcional.

## El criterio, calcado del de F01

- `011 15 6161-7956`, `11 15 6161 7956` y `+54 9 11 6161-7956` dan **el mismo canónico**
  (es el mismo celular escrito de tres formas).
- Ese canónico conserva el `9`: un fijo `11 6161-7956` da un canónico **distinto** (no se
  come el 15 como si fueran dígitos del número).
- Ningún inválido queda con canónico `+549` "a medias" ni `undefined`.
- El caso O02 de `data/leads_optout_1.csv`: si querés, revertí el dato a la forma sin 0
  para probar que ahora entra — pero eso mueve el archivo de F14; más limpio es agregar
  **un caso nuevo** al verificador de teléfono con el `15` sin 0 y dejar `leads_optout_1`
  como está. Vos decidís, pero dejá el `15`-sin-0 cubierto por un check.

## Prohibido

- Regenerar o "actualizar" el golden sin frenar y mostrar primero el conteo del Paso 1.
  Un golden que se mueve en silencio es indistinguible de un bug.
- Aceptar como celular cualquier cosa de 12 dígitos: tiene que empezar en `11 15` (área +
  marcador). Un `11` seguido de 10 dígitos cualesquiera no es esto.
- Duplicar la rama del `15`. El 0 es opcional, misma lógica.
- Tocar otra cosa del normalizador que no sea esta variante.

## Terminado cuando

El Paso 1 está reportado (conteo por archivo), la decisión sobre el golden está tomada con
Pedro, `python verificadores/v01_telefono.py` da verde con el caso nuevo del `15` sin 0,
`python verificadores/correr_todo.py` sigue verde, y el golden está en el estado acordado
(intacto si el conteo canónico fue 0; regenerado a propósito y documentado si fue > 0).

En `ESTADO.md` queda: el conteo del Paso 1, la decisión sobre el golden y por qué, y que el
`15` sin 0 quedó cubierto.

---

## Qué sigue

Con `CORRECCION-F11` y esta cerradas, el Nivel 1 queda limpio y factorizado. Próximo paso
fuerte: la **prueba de fuego** de punta a punta (`;`, columnas renombradas, basura arriba),
donde el `15` y la baja `.xlsx` ya van a estar cubiertos y sirven como formatos reales del
archivo sucio.
