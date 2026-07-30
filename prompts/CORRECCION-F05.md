Estás trabajando en este repo. Antes de tocar nada, leé `CLAUDE.md`, `ESTADO.md`,
`fases/F05-antiguedad.md` y `data/TRAMPAS.md` completos.

# CORRECCIÓN F05 — El verificador no ejecuta el workflow

Esta no es una fase nueva. Es una corrección sobre F05, que ya está cerrada.
Corrala en su propia sesión, sin mezclarla con F06.

## Antes de escribir una sola línea

Comprobá el entorno y **pedí instalar lo que falte AHORA**: Node 20+,
Python 3.10+, git, y n8n con `npx n8n` (nunca global). Comprobá que
`N8N_RESTRICT_FILE_ACCESS_TO` apunte a esta carpeta. Detalle en
`prompts/SETUP.md`.

---

## El problema

`v05_antiguedad.py` da 23/23 en verde, pero **tres de sus checks no pueden
fallar**, porque no tocan n8n:

1. **"el calculo es determinista"** (líneas 169–174) corre el oráculo Python dos
   veces y lo compara contra sí mismo. El workflow nunca se ejecuta dos veces.
2. **"cambiar fecha de corte redistribuye los tramos"** (líneas 179–190)
   recalcula con el oráculo. Nunca re-ejecuta n8n con otro `CONFIG.fecha_corte`,
   así que nada prueba que la fecha de corte sea realmente un parámetro.
3. **Los cuatro checks de fechas malformadas** (líneas 208–215) son unit tests de
   la función Python. El CSV de prueba no tiene ni una fecha rota, así que la
   rama de error del nodo n8n **nunca se ejecutó**.

La consecuencia concreta: la fecha de corte del verificador es `2026-07-28`, que
era el día en que se corrió. Si el nodo hubiera usado `new Date()` —lo único que
el prompt de F05 declaró innegociable— el verificador habría dado 23/23 igual.
No lo usa, ya lo revisé. Pero el verificador no lo podía haber detectado, y es el
mismo patrón que la corrección de F02: un test en verde que no podía fallar.

**Lo que sí está bien y no se toca:** los conteos. Recalculados de forma
independiente desde `data/leads_prueba_SINTETICO_1.csv` con corte 2026-07-28 dan
alta 39, media 42, baja 65, fría 54, mínimo 0 días, máximo 109. Correcto.

---

## Parte 1 — La fecha de corte tiene que ser parámetro de verdad

Hoy `CONFIG.fecha_corte` está hardcodeada dentro del nodo Code. Eso alcanza para
que sea determinista, pero no para que el verificador pueda correr el mismo
workflow con **otra** fecha y comparar.

Hacé que la fecha de corte se pueda fijar desde afuera del nodo. El repo ya tiene
`herramientas/gen_workflow.py`, que genera los JSON: si el camino más limpio es
darle un parámetro y regenerar un workflow temporal por corrida, hacelo así. Si
preferís otra vía (variable de entorno leída con `$env`, un nodo Set arriba),
está bien, pero **decí cuál elegiste y por qué** antes de implementarla.

Requisitos, sea cual sea la vía:

- Si no se pasa fecha, el default sigue siendo hoy. Un cliente real quiere eso.
- **Pero la fecha efectivamente usada se escribe en la salida**, en una columna
  nueva `fecha_corte_usada`, igual en las 200 filas. Motivo: un CSV de salida
  tiene que poder auditarse solo, sin saber qué día se generó.
- Nunca `new Date()` dentro de la lógica de cálculo.

## Parte 2 — El verificador ejecuta n8n, tres veces

Reescribí `v05_antiguedad.py` para que **corra el workflow de verdad** vía
`n8n import:workflow --input=X.json` + `n8n execute --id=<id>` (ver README; el
JSON necesita `id` en la raíz o el import falla).

Tres corridas, con estos esperados **exactos**:

**Corrida A y B — corte `2026-07-28`, dos veces.** Determinismo real: los dos CSV
de salida tienen que dar el **mismo hash**. Y los conteos son los de siempre:
alta 39, media 42, baja 65, fría 54, sin dato 0, mín 0 días, máx 109.

**Corrida C — corte `2026-07-29`** (un día después):

| frescura | esperado |
|---|---|
| alta | 34 |
| media | 44 |
| baja | 68 |
| fría | 54 |

**Corrida D — corte `2026-09-30`:** alta **0**, media **0**, baja **43**,
fría **157**. Dos tramos vacíos es lo que hace fuerte a este check: si el
parámetro no estuviera llegando al nodo, seguirían saliendo 39 y 42.

**El contacto concreto que cruza el borde.** `id_fila = 103` (Emilia Núñez,
`fecha_carga = 2026-07-13`, es el único contacto a 15 días con nombre no
repetido). Con corte 2026-07-28: **15 días, alta**. Con corte 2026-07-29:
**16 días, media**. Assertion sobre ese id_fila puntual, no sobre el conteo
agregado.

## Parte 3 — La rama de fechas rotas se ejecuta en n8n, no en Python

Corré el workflow sobre `data/leads_adversario_1.csv` (48 filas). Las filas 32 a
38 son las trampas de fecha de `data/TRAMPAS.md` y el campo `nombre` lleva el ID
de la trampa, así que se puede assertear una por una.

Regla de formatos, ya decidida por Pedro:

- Se aceptan **`aaaa-mm-dd`** y **`dd/mm/aaaa`**. El `dd/mm/aaaa` se lee
  **día primero** — es Argentina, y el criterio queda declarado, que es lo que
  pide TRAMPAS para T33.
- Se marca `fecha ambigua` cuando los dos primeros componentes son ambos ≤ 12,
  o sea cuando la lectura inversa también daría una fecha válida. `10/04/2026`
  es ambigua; `25/12/2026` no lo es, no hay otra lectura posible.
- Todo lo demás es `fecha ilegible`. **No adivines** meses en texto ni años de
  dos dígitos.

Columna nueva `motivo_frescura`, vacía cuando la frescura es un tramo real.
Etiquetas: `fecha vacia`, `fecha ilegible`, `fecha ambigua`, `fecha futura`.
Se pueden acumular, separadas por `; `, en el orden de esa lista.

Esperado exacto con corte `2026-07-28`:

| fila | fecha_carga | dias_antiguedad | frescura | motivo_frescura |
|---|---|---|---|---|
| T32 | `10/04/2026` | 109 | fría | `fecha ambigua` |
| T33 | `04/10/2026` | -68 | sin dato | `fecha ambigua; fecha futura` |
| T34 | `10-abr-26` | *(vacío)* | sin dato | `fecha ilegible` |
| T35 | *(vacío)* | *(vacío)* | sin dato | `fecha vacia` |
| T36 | `2026-13-45` | *(vacío)* | sin dato | `fecha ilegible` |
| T37 | `2027-01-15` | -171 | sin dato | `fecha futura` |
| T38 | `2019-03-02` | 2705 | fría | *(vacío)* |

Entran 48 filas, salen 48, cero excepciones.

## Parte 4 — Matar el centinela `-1`

Hoy una fecha rota escribe `dias_antiguedad = -1`. Eso es una mina para F06: si
alguien hace aritmética con ese campo sin mirar `frescura`, un `-1` es "más
fresco que 0 días" y las fechas rotas quedan como los leads más calientes de la
lista.

Cambio: si no hay fecha usable, `dias_antiguedad` queda **vacío**, no `-1`. Las
fechas futuras sí conservan su número negativo real (`-68`, `-171`), porque ahí
el dato existe y es informativo: es un typo del operador, no un dato faltante.

## Parte 5 — El bug latente de zona horaria

El nodo hace `new Date(y, m-1, d)` y divide por `86400000`. Son fechas en hora
local: si el tramo cruza un cambio de horario de verano, pierde una hora y
`Math.floor` redondea para abajo — 46 días reportan 45 y el contacto salta de
`baja` a `media`. Argentina no tiene DST desde 2009 y Docker corre en UTC, así
que hoy no rompe, pero es un cliente en otra zona de distancia.

Fix: construir las dos fechas con `Date.UTC(y, m-1, d)`. Es una línea. El oráculo
Python usa `datetime.date`, que no tiene el problema, así que nunca lo iba a
delatar solo.

---

## Criterio de aceptación

1. `v05_antiguedad.py` **ejecuta n8n** y da verde con los cuatro esperados de la
   Parte 2, incluido el hash idéntico de las corridas A y B.
2. El contacto `id_fila = 103` cruza de `alta` a `media` al mover el corte un día.
3. El workflow corre sobre `leads_adversario_1.csv` sin una sola excepción, y las
   siete filas T32–T38 dan exactamente la tabla de la Parte 3.
4. `salida_f05.csv` sobre los 200 **no mueve ni un contacto**: alta 39, media 42,
   baja 65, fría 54. Las columnas nuevas son `motivo_frescura` y
   `fecha_corte_usada`, todo lo demás igual.
5. Los checks viejos que comparaban el oráculo contra sí mismo están **borrados**,
   no comentados ni dejados al lado de los nuevos.
6. Los unit tests del oráculo que quedan llevan el prefijo `(oraculo)` en el
   nombre, para que el reporte no parezca cobertura de n8n cuando es de Python.
7. `ESTADO.md` registra el cambio, el criterio `dd/mm/aaaa` día primero, y por qué
   se borraron los checks viejos.

## Prohibido

- Dejar cualquier check que compare el oráculo contra sí mismo. Un check que no
  puede fallar es peor que no tenerlo: ocupa un renglón verde en el reporte.
- `new Date()` sin parámetro dentro de la lógica de cálculo.
- Tocar los tramos. `0–15 / 16–45 / 46–90 / >90` se quedan como están; los pesos
  se discuten en F06.
- Que se mueva algún conteo del CSV principal. Si se mueve, es un bug de la
  corrección: **frená y avisá** en vez de reescribir el esperado.
- Adivinar formatos de fecha que no sean los dos declarados.
- Tocar F06 o cualquier fase posterior en esta sesión.

## Terminado cuando

`python verificadores/v05_antiguedad.py` da verde ejecutando n8n de verdad, el
adversario pasa las siete trampas de fecha, y `ESTADO.md` quedó actualizado.
