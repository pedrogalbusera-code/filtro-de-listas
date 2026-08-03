Estás trabajando en este repo. Antes de tocar nada, leé `CLAUDE.md`, `ESTADO.md`,
`fases/F04-completitud-y-cobertura.md`, `verificadores/v04_cobertura.py` y la entrada del
filtro 4 en `CATALOGO-FILTROS.md` completos.

# CORRECCION-F04 — localidad con paréntesis, y "sin localidad" ≠ "fuera de zona"

## De dónde sale

F04 compara la localidad con match **exacto** sobre el normalizado
(`en_zona = norm_loc(localidad) in zona_set`). Eso deja dos defectos medidos y todavía
abiertos, los dos que un archivo real dispara el primer día:

1. **Paréntesis / sufijo de provincia (T19).** `Morón (Buenos Aires)` normaliza a
   `moron (buenos aires)`, que no está en el set `{moron, …}` → cae **fuera de zona**. Y
   así es como buena parte de las listas reales escriben la localidad: `Localidad
   (Provincia)` o `Localidad, Provincia`.
2. **Vacío tratado como lejos (T21).** Localidad vacía normaliza a `""`, tampoco está en
   el set → cae con motivo **"fuera de zona de cobertura"**. O sea "no sé dónde vive" se
   marca igual que "sé que vive lejos". Es el pecado que el producto dice que no comete
   (descartar mal en silencio) y el mismo principio que F12 ya respeta con `desconocida`.

La zona en sí es de la demo, pero estos dos son bugs **estructurales**: pasan con cualquier
zona que se configure.

## Antes de escribir una sola línea

Entorno como siempre (Node 20+, Python 3.10+, n8n con `npx n8n`,
`N8N_RESTRICT_FILE_ACCESS_TO` a esta carpeta). Detalle en `prompts/SETUP.md`.

## Paso 1 — MEDIR el impacto en el golden. Frená y mostrame.

Sobre `data/leads_prueba_SINTETICO_1.csv` (las 200) y los adversarios, contá y reportá,
**antes de cambiar nada**:

- cuántas filas tienen una localidad con **paréntesis o sufijo `, provincia`** que hoy cae
  fuera y con la Parte A pasaría a estar en zona;
- cuántas filas tienen la localidad **vacía** y hoy están marcadas "fuera de zona".

Ese segundo número es el que mueve el golden: esas filas dejan de ser "fuera de zona"
(que es descarte) y pasan a "sin localidad" (que no descarta — ver Parte B). Cambia su
puntaje y su prioridad.

- **Si las dos cuentas dan 0 en el canónico:** aditivo, el golden no se mueve.
- **Si la de vacías es > 0 (lo más probable):** es un **cambio de comportamiento
  deliberado**. **Frená y mostrame** el conteo y qué filas son; regeneramos el golden a
  propósito y documentado, como en CORRECCION-F02 (los 19 CUIL) y como estaba previsto para
  F01b. **No regeneres el golden por tu cuenta.**

## Parte A — la localidad con paréntesis/sufijo matchea

Antes de comparar contra la zona, sacá de la localidad un **paréntesis final `(...)`** y un
**sufijo `, <resto>`**, y después exigí **match exacto** sobre el núcleo limpio:

- `Morón (Buenos Aires)` → `moron` → en zona.
- `Morón, Buenos Aires` → `moron` → en zona.
- `Moreno` → `moreno` → sigue fuera (no está en la zona). No se toca.

**Match exacto sobre el núcleo, no substring ni prefijo.** Nada de "contiene". Es la misma
disciplina que F13 (explícito o nada): un prefijo haría que `castelar` matchee cualquier
cosa que empiece con castelar.

**Fuera de alcance, dejalo anotado:** esto NO desambigua por provincia. Si existiera un
`San Justo (Santa Fe)` distinto del San Justo de la zona (Buenos Aires), lo daría en zona
igual — pero ese agujero **ya existe hoy** (el `San Justo` pelado ya matchea), así que esta
corrección no lo empeora. Desambiguar por provincia necesita que la zona lleve provincia en
el `config`, y es otra sesión.

## Parte B — "sin localidad" es un motivo propio, y no descarta

La localidad **vacía** (o solo espacios) deja de caer en "fuera de zona de cobertura" y pasa
a un motivo propio: **"sin localidad"**.

Y no se descarta por eso. Un contacto sin localidad pero con teléfono bueno **sigue siendo
llamable** — lo llamás y ahí te enterás dónde vive. Mismo trato que `desconocida` en F12 y
que "sin nombre" en F04: **marca, no descarte.** No puede llevarse el descuento de
fuera-de-zona ni quedar `descartado` solo por la localidad vacía; revisá que eso se respete
también aguas abajo (F06 puntaje, F07 orden, F08 reporte), no solo en el nodo de F04.

> El peso exacto de "sin localidad" en el puntaje es **[decisión de Pedro]**. Mi propuesta
> por defecto: que no descuente como fuera-de-zona (queda como marca informativa). Cuando
> traigas el conteo del Paso 1, decidimos el peso y ahí regeneramos el golden.

## El verificador

Extendé `verificadores/v04_cobertura.py`. Ojo con una trampa que ya tiene: su oráculo
`marcar_oraculo()` **replica la lógica del nodo** (es la 3ª forma de check falso — el
oráculo que copia lo que verifica). Para los casos nuevos **no uses ese oráculo**: agregá
checks con **esperados literales escritos a mano**, como F12/F13:

- una fila `Morón (Buenos Aires)` → `en_zona` en zona, sin motivo de zona;
- una fila `Morón, Buenos Aires` → igual;
- una fila con localidad **vacía** → motivo **"sin localidad"**, **NO** "fuera de zona", y
  **no** queda descartada solo por eso (mirá su prioridad end-to-end, no solo el motivo);
- una fila `Moreno` (realmente fuera) → sigue "fuera de zona de cobertura", descarte.

Actualizá también los conteos duros del verificador (`ESP_FUERA`, `ESP_SIN_TEL`, etc.) a lo
que de verdad mida el CSV después del cambio — no al revés. Si un conteo no cierra, es un
dato para traer, no un número para ajustar.

## Prohibido

- Match por substring o prefijo de localidad. Núcleo limpio + exacto, o nada.
- Descartar una fila por tener la localidad vacía. Sin localidad marca, no descarta.
- Regenerar o "actualizar" el golden sin frenar y mostrar primero el conteo del Paso 1.
- Ajustar los conteos esperados del verificador para que pasen sin entender por qué cambian.
- Meter desambiguación por provincia (otra sesión) ni tocar la lista de zona del `config`.
- Tocar otra cosa de F04 que no sean estas dos reglas de localidad.

## Terminado cuando

El Paso 1 está reportado (los dos conteos por archivo) y la decisión sobre el golden y el
peso de "sin localidad" están tomadas con Pedro; `python verificadores/v04_cobertura.py` da
verde con los casos nuevos (paréntesis, sufijo, vacío, fuera real) por esperados a mano;
`python verificadores/correr_todo.py` sigue verde; y el golden está en el estado acordado
(intacto si el canónico no tenía vacías/paréntesis; regenerado a propósito y documentado si
sí).

En `ESTADO.md` queda: los dos conteos del Paso 1, la decisión sobre el golden y el peso de
"sin localidad", y que el paréntesis/sufijo ahora matchea (con la limitación de provincia
anotada como fuera de alcance).

---

## Qué sigue

Con F04 corregida, el Nivel 1 queda limpio de verdad y recién ahí la **prueba de fuego** de
punta a punta cae sobre base sólida — donde el `15`, la baja `.xlsx`, la localidad con
paréntesis y las vacías ya están todas cubiertas y sirven como el archivo sucio realista que
la prueba necesita.
