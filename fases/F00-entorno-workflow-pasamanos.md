# F00 — Entorno y workflow pasamanos

**Estado: CERRADA el 2026-07-27.** Verificador `v00_pasamanos.py`: 10 de 10 PASA.

## Objetivo
Tener n8n corriendo local y un workflow que lea `data/leads_prueba_SINTETICO_1.csv`
y devuelva los 200 contactos sin tocar nada. Cero lógica. Es la fase donde se
aprende el modelo mental: nodo, item, `$json`.

## Por qué esta fase existe
Si el pasamanos no funciona, cualquier bug posterior es ambiguo: no se sabe si
falla la regla o falla la lectura del archivo. Esta fase elimina esa ambigüedad
para siempre.

## Qué se construyó

`workflows/01-pasamanos.json` — seis nodos en línea:

| # | Nodo                      | Tipo                              |
|---|---------------------------|-----------------------------------|
| 1 | Ejecutar manualmente      | `manualTrigger`                   |
| 2 | Leer CSV de disco         | `readWriteFile` (read)            |
| 3 | CSV a items               | `extractFromFile` (csv)           |
| 4 | Pasamanos (todo string)   | `code` (typeVersion 2)            |
| 5 | Items a CSV               | `convertToFile` (csv, tv 1.1)     |
| 6 | Escribir CSV a disco      | `readWriteFile` (write)           |

El JSON **se genera**, no se edita: `herramientas/gen_workflow.py`. Las rutas
absolutas quedan embebidas, y regenerar es más barato que buscar y reemplazar.

## Criterio de aceptación — resultado

| # | Criterio                                              | Resultado |
|---|-------------------------------------------------------|-----------|
| 1 | El último nodo emite exactamente 200 items            | PASA      |
| 2 | El CSV escrito tiene 200 filas + encabezado           | PASA      |
| 3 | Las 6 columnas sobreviven con mismo nombre y valor    | PASA (celda por celda) |
| 4 | Los 45 teléfonos con cero inicial sobreviven          | PASA      |
| 5 | Los 200 CUIL conservan los guiones                    | PASA      |
| 6 | Los 41 `sin dato` sobreviven como texto               | PASA      |
| 7 | Tildes y eñes intactas (218 celdas)                   | PASA      |
| 8 | El JSON del workflow está versionado                  | PASA      |

## Verificador
`verificadores/v00_pasamanos.py` — compara entrada y salida celda por celda,
sin ordenar (el orden también tiene que sobrevivir: F03 lo usa como desempate).
Exit code 0 / 1.

---

## Lo que se aprendió ejecutándolo de verdad

Estas tres cosas se descubrieron corriendo n8n 2.31.7, no leyendo documentación.

### 1. n8n bloquea el disco fuera de `~/.n8n-files`

Es el primer muro y no está en ningún tutorial viejo. Sin
`N8N_RESTRICT_FILE_ACCESS_TO` apuntando a la carpeta del proyecto, el nodo de
lectura falla con `Access to the file is not allowed`. Está en el README.

### 2. `n8n execute --file` ya no existe

En la 2.x hay que importar primero y ejecutar por id:

```
n8n import:workflow --input=workflows/01-pasamanos.json
n8n execute --id=f00pasamanos001
```

Y el JSON **necesita un campo `id`** o el import falla con
`NOT NULL constraint failed: workflow_entity.id`. Por eso el generador lo emite.
Esto importa para F09: la suite de regresión va a correr por CLI, no a mano.

### 3. La trampa que había documentado no era real

La versión anterior de este archivo decía que el parser de CSV infiere tipos y
se come el cero inicial de `011-41617956`. **Es falso en n8n 2.31.7.** Se probó
de dos maneras: corriendo el workflow con el nodo Code reducido a `return items`
(los 45 ceros iniciales sobreviven igual), y midiendo `typeof` sobre los 200
items (los 6 campos llegan como `string`, cero excepciones).

El nodo Code queda igual, pero declarado por lo que es: un guardarrail, no un
arreglo. Deja el punto de entrada listo para F01 y, si una versión futura cambia
el parseo, v00 lo detecta y ahí se corrige.

### 4. El archivo de salida no es idéntico byte a byte, y está bien

n8n escribe UTF-8 **con BOM** y saltos de línea **LF**; la entrada venía sin BOM
y con CRLF. Son 14.680 bytes contra 14.879. Ninguna celda cambió — el
verificador compara contenido, no bytes. El BOM además es lo que hace que Excel
abra las tildes bien, así que conviene.

## Fuera de alcance
Normalizar, validar, puntuar, ordenar. Nada de eso acá. Sigue **F01**.
