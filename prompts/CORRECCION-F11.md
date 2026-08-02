Estás trabajando en este repo. Antes de tocar nada, leé `CLAUDE.md`, `ESTADO.md`,
`fases/F11-puerta-de-entrada.md` y `fases/F14-lista-negra-optout.md` completos, y
`verificadores/v11_puerta.py` para ver qué chequea hoy el caso de rechazo.

# CORRECCION-F11 — endurecer la puerta de entrada tras la factorización de F14

Dos ítems chicos, los dos **aditivos**: ninguno cambia comportamiento del pipeline,
así que **el golden de F09 no se puede mover** (com `9a6884…dcb4`, aud `ae6fcc…9cd2`) y
`correr_todo.py` tiene que seguir 10/10. Si el golden se movió, algo de esto tocó lógica
que no debía y hay que encontrarlo.

## Antes de escribir una sola línea

Comprobá el entorno como siempre (Node 20+, Python 3.10+, n8n con `npx n8n`,
`N8N_RESTRICT_FILE_ACCESS_TO` a esta carpeta). Si falta una librería, proponé el comando
y **esperá el OK de Pedro**. Detalle en `prompts/SETUP.md`.

## Parte 1 — el assert que le falta a v11 (verificador, no código)

**El código ya está arreglado** (al factorizar `leerTabla()` la ficha del archivo
rechazado había perdido `tamaño` y `encoding`, y el lector ahora escribe a medida que
descubre). Lo que falta es que **el verificador no pueda dejar pasar esa clase de
regresión otra vez**: hoy el caso de rechazo de `v11_puerta.py` chequea el exit de error
y que no haya CSV de salida, pero **no mira la ficha**. Por eso la regresión la atrapó un
`git diff` humano y no la suite — exactamente el agujero de F05/F09.

Agregá al caso de rechazo (el `.txt` de prosa, `data/leads_adversario_5_prosa.txt`) dos
checks nuevos sobre la ficha `salidas/ficha_entrada_leads_adversario_5_prosa.md`
(o como se llame la ficha del rechazo):

- que la ficha reporte **`tamaño`** con el valor exacto **`199 bytes`**, y
- que reporte **`encoding`** con el valor exacto **`UTF-8 sin BOM`**.

Los dos valores van **como literales escritos a mano** en el test (el estándar de F05: el
esperado no se calcula con la lógica que lo produce). Si el día de mañana la ficha vuelve
a decir `n/d` en cualquiera de los dos, la suite tiene que ponerse roja sola.

> No relajes el check a "el campo existe": lo que se coló fue un `n/d` presente pero
> vacío de dato. El check compara contra el valor exacto.

## Parte 2 — la lista de baja de F14 puede venir en `.xlsx`

Hoy, si la lista de baja (`--lista-baja`) viene en `.xlsx`, el generador frena pidiendo
exportarla a CSV. Está bien como hard-stop, pero un opt-out de un cliente real es
probable que venga en Excel. Extendé la baja al **mismo path que F11 usa para el archivo
principal**: `.xlsx` por `extractFromFile` (operación spreadsheet), `.csv`/texto por
`leerTabla()`. Es el lector de F11 leyendo otro archivo de cliente — no escribas un
tercer camino.

**Criterio (calcado del criterio `.xlsx` de F11):** una baja en `.xlsx` con las mismas
filas que `data/lista_baja_1.csv`, aunque tenga las columnas renombradas y basura arriba,
produce **exactamente el mismo resultado de opt-out** sobre `leads_optout_1.csv` que la
baja en CSV — las mismas filas marcadas (O01, O02, O03, O07), por las mismas vías, y O05
sigue descartado por "sin teléfono", no por opt-out. Verificado por **contenido de celda**,
no por conteo de filas.

Creá `data/lista_baja_1.xlsx` con ese contenido (podés generarlo con un script chico en
`herramientas/`, como se hizo `gen_xlsx_adversario4.py` para F11). El `.csv` sigue siendo
el caso base; el `.xlsx` es un caso nuevo que da el mismo veredicto.

## Prohibido

- Tocar la lógica de normalización, scoring, o cualquier cosa que pueda mover el golden.
  Esto es aditivo: un assert nuevo y un formato de entrada nuevo para la baja.
- Relajar el assert de la Parte 1 a "el campo existe". Compara contra el valor exacto.
- Escribir un lector nuevo para el `.xlsx` de la baja. Es el path de F11.
- Adivinar el mapeo de columnas de la baja `.xlsx` por parecido. Va por `sinonimos.json`,
  igual que cualquier archivo de cliente; sin mapeo, frena.

## Terminado cuando

`python verificadores/v11_puerta.py` da verde **con los dos checks nuevos de la ficha de
rechazo**, `python verificadores/v14_optout.py` da verde **con el caso nuevo de baja
`.xlsx`** (mismo veredicto que la baja CSV, por celda), `python verificadores/correr_todo.py`
sigue 10/10 y **el golden no se movió** (com + aud, SHA intactos), y existe
`data/lista_baja_1.xlsx`.

En `ESTADO.md` queda anotado: que el rechazo de v11 ahora blinda `tamaño`+`encoding`, y
que la baja acepta `.xlsx` por el path de F11 con el mismo veredicto que el CSV.

---

## Qué sigue

`prompts/CORRECCION-F01b.md` (el `15` sin el `0`, que puede tocar el golden — corré esta
primero porque es la que NO lo toca), y después la **prueba de fuego** de punta a punta.
