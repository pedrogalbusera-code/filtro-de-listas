# F14 — Lista negra / opt-out del cliente

Filtro 10 del catálogo. Tercer filtro nuevo de Nivel 1. Cruza la lista principal
contra una **segunda lista que trae el cliente** — los que pidieron baja, pidieron
"no llamar", o que el cliente marcó como quemados — y **descarta** a todo contacto
que aparezca en ella, con motivo legible.

Sigue siendo **Nivel 1**: el dato lo aporta el cliente, no un organismo. No confundir
con el registro oficial "No Llame" (Ley 26.951), que es Nivel 2 (E del catálogo) y
necesita inscribirse como consultante. Esto cruza **solo la lista del propio cliente**.

## En qué se diferencia de F12 y F13

Los tres son filtros nuevos de Nivel 1 y los tres viven en el mismo nodo de F06, pero
el **gate** de cada uno es distinto, y no es un detalle:

| Fase | Gate | Por qué |
|------|------|---------|
| F12 segmento | booleano en config, **apagado** por defecto | segmentar es una decisión comercial de *un* cliente |
| F13 basura | **siempre encendido** | un `1111111111` no es llamable para nadie: limpieza universal |
| **F14 opt-out** | **presencia de la segunda lista** | sin lista de baja no hay nada que cruzar |

El gate de F14 es la presencia del archivo. Default del repo: `config/opt_out.json`
con la lista en `null` (y el pipeline corre **sin** `--lista-baja`) → el nodo es
transparente, no agrega ni una clave, y la salida queda **byte a byte idéntica al
golden de F09**. Recién con una lista de baja pasada por parámetro cruza y marca.

## La asimetría, INVERTIDA respecto de F13 — leelo antes de diseñar nada

En F13 el error caro es el **falso positivo**: tirar un número real a la basura y que
nadie se entere.

En F14 el error caro es el **falso negativo**: **no** excluir a alguien que pidió baja
→ el operador lo llama → es una infracción, no una molestia. Por eso el cruce tiene que
ser agresivo en **normalizar** antes de comparar (ver abajo).

Pero —y esto es lo que salva la fase— un falso negativo evitado **no** habilita a
matchear de más. Un cruce demasiado laxo barrería contactos inocentes por una colisión
de normalización, y ese contacto perdido tampoco se entera nadie. La regla que sirve
para los dos lados es una sola: **match exacto sobre la forma canónica.**

## El cruce: qué matchea y qué no

Un contacto de la lista principal es opt-out si:

- su **teléfono canónico** (el `telefono_norm` que ya produjo F01) **∈** el set de
  teléfonos canónicos de la lista de baja, **O**
- su **CUIL normalizado** (los 11 dígitos que ya produjo F02) **∈** el set de CUILs
  normalizados de la lista de baja.

Es **OR, no AND**: una lista de baja real suele traer *solo teléfonos* (un registro
"no llamar" es una columna de números), o *solo CUILs*. Cualquiera de las dos alcanza.

### El trap central — es el valor entero del filtro

El cruce vive **después** de la normalización de F01/F02, nunca antes. La lista de baja
del cliente trae los teléfonos escritos en cualquier formato (`11 4161-7956`,
`+54 9 11 4161 7956`, `011 15 4161-7956`), **igual que la lista principal**. Si comparás
strings crudos, no matchea casi nada y dejás pasar a la mayoría de los que pidieron baja
— el falso negativo caro, a escala.

Por eso la lista de baja se normaliza con **el mismo normalizador** que la principal, y
se compara **canónico contra canónico**. Es exactamente el argumento del filtro 2:
"2 de 8 duplicados solo aparecen *después* de normalizar". Acá es lo mismo, con una
segunda lista.

Corolario del canónico: un **fijo** y un **celular** con los mismos 8 dígitos finales
dan canónicos distintos (F01 conserva el `9`). Si el cliente pone en la baja un celular
y en la principal hay un fijo con esos dígitos, **no** matchea, y está bien: son dos
líneas distintas.

### El anti-footgun — criterio duro, va al verificador

- Solo se cruza por **teléfono canónico NO vacío**. Un número de la lista de baja que
  es inválido / no normaliza **no puede** matchear filas de la principal con teléfono
  vacío o inválido. **Vacío nunca matchea vacío.** (Mismo trap que "ningún grupo por
  teléfono junta inválidos entre sí" del filtro 2 / F03.)
- Solo se cruza por **CUIL de 11 dígitos**. Un CUIL roto en la baja no barre CUILs
  rotos de la principal. (No hace falta que el DV sea válido para cruzar —igual que en
  F12 el prefijo clasifica aunque el DV falle— pero sí que sean 11 dígitos: un `20-4412233`
  de 9 dígitos no es identidad de nadie y no cruza.)

## Descarte, no marca

Opt-out **descarta duro**, motivo `en lista de no llamar del cliente (opt-out)`. A
diferencia del nombre de relleno de F13 (que solo marca), acá el contacto **no se puede
llamar**: llamarlo es el error que el filtro existe para impedir.

## Dónde vive

Hacen falta **dos piezas**, como en F11:

1. **Un nodo de cabeza** que lee la lista de baja, la mapea y la normaliza, y construye
   los dos sets (teléfonos canónicos, CUILs de 11 dígitos). Reutiliza el **lector de
   F11** (formato/separador/encabezado) y el **mapeo de columnas de F11**
   (`config/sinonimos.json`): la lista de baja es *otro archivo de cliente*, se lee con
   las mismas reglas. Y reutiliza el **normalizador de teléfono de F01** y el de **CUIL
   de F02** — los mismos, no una copia.
2. **La decisión de descarte vive en el nodo de F06**, pegada a los otros descartes
   directos (teléfono, zona, duplicado, segmento, teléfono-basura). No hay lógica de
   prioridad nueva: F14 solo pregunta "¿este canónico está en el set de baja?".

> Nota técnica que probablemente te frene si no la ves venir: hoy el normalizador de
> teléfono (F01) y el de CUIL (F02) corren *inline* dentro de su propio nodo, sobre los
> items del pipeline. Para F14 tenés que poder invocarlos sobre **otra** lista sin
> duplicar la lógica. Un segundo normalizador "parecido" es el bug: si normaliza distinto
> aunque sea en un formato, el cruce falla justo en los formatos que importan. Si hay que
> factorizar el normalizador para que sea invocable, hacelo, y dejalo anotado.

## Criterio 1 — el golden no se mueve

Sin `--lista-baja`, la salida queda **byte a byte idéntica a los golden de F09**
(comercial `9a6884…dcb4`, auditoría `ae6fcc…9cd2`) y la regresión sigue 10/10. Si el
golden se movió, F14 le cambió el comportamiento al pipeline base **con el filtro
apagado**, que es imposible salvo bug. No se arregla tocando el golden.

Este check, además, **re-prueba de yapa que F13 no quedó movido**: es la misma corrida
default con una fase más encima.

## El reporte (F08) — una línea nueva, su propia categoría

El reporte ya separa (deuda cerrada en F13): calidad de dato / zona / segmento. Opt-out
es una **cuarta** categoría y va **en su propia línea**, no mezclada:

- **Por calidad de dato** — hechos del archivo: sin teléfono, teléfono de relleno, duplicado.
- **Por zona de cobertura** — supuesto nuestro.
- **Por segmento no buscado** — decisión comercial del cliente.
- **Por pedido de baja del titular (opt-out)** — dato que aporta el cliente. **Nuevo.**

No se mezcla con "segmento" aunque las dos las aporte el cliente: segmento es *"no le
quiero vender a este tipo"* (elección comercial), opt-out es *"este titular pidió que no
lo llamen"* (obligación). Y no se mezcla con calidad de dato: el contacto en baja puede
ser un lead perfecto que simplemente **no se puede** llamar — meterlo en "basura que
limpiamos" infla el número equivocado.

Misma regla que protege el golden que en F13: **la línea se muestra solo si cuenta ≥ 1.**
Con la lista canónica (sin baja) el conteo es 0, la línea no aparece, y el reporte del
golden no cambia ni un carácter.

## Archivos de prueba

Dos archivos, mismo criterio que F12/F13: la lista principal `data/leads_optout_1.csv`
tiene todas las filas **limpias salvo por lo que se prueba** (teléfono válido, en zona,
CUIL bien formado salvo donde se indique, fecha fresca, origen referido), así que el
**único** descarte posible es el de opt-out.

`data/lista_baja_1.csv` — la segunda lista (la que trae el cliente). A propósito trae los
teléfonos en formatos **distintos** de la principal, columnas con nombres de cliente, y
las dos trampas de vacío:

| Entrada baja | Qué trae | A quién apunta |
|--------------|----------|----------------|
| L1 | teléfono fijo `011 4161-7956` (mismo número que O01, otro formato) | O01, por teléfono |
| L2 | celular `+54 9 11 6161 7956` (mismo que O02, otro formato) | O02, por teléfono |
| L3 | **solo** CUIL `27-35110489-4`, sin teléfono | O03, por CUIL |
| L4 | teléfono basura/vacío (`s/d`) | **bait**: no debe matchear a O05 |
| L5 | CUIL de 9 dígitos `20-4412233` | **bait**: no debe matchear a O06 |
| L6 | teléfono `011 4242-4242` **y** CUIL `20-31445901-7` (ambos de O07) | O07, por ambos |
| L7 | teléfono `11 9999-0000` que no está en la principal | nadie: se ignora, sin error |

Lista principal `data/leads_optout_1.csv`:

| Fila | Qué prueba | Esperado |
|------|------------|----------|
| O01 | fijo `11 4161-7956`, escrito distinto que L1 | **opt-out** (por teléfono, prueba la normalización) |
| O02 | celular `11 15 6161 7956`, escrito distinto que L2 | **opt-out** (por teléfono; el `15`/`9` sobrevive el cruce) |
| O03 | teléfono bueno que NO está en baja, CUIL `27-35110489-4` | **opt-out** (por CUIL; prueba el OR) |
| O04 | teléfono y CUIL, ninguno en baja | **CONTROL**: intacto, alta |
| O05 | teléfono vacío/inválido, CUIL bueno no en baja | descartado por **sin teléfono**, **NO** por opt-out (vacío ≠ vacío) |
| O06 | teléfono bueno no en baja, CUIL inválido `20-4412233` | **NO** opt-out (CUIL roto no matchea roto) |
| O07 | teléfono `11 4242-4242` **y** CUIL `20-31445901-7`, ambos en L6 | **opt-out**, motivo **una sola vez** |

O01 y O02 son la prueba de que el cruce corre sobre el canónico y no sobre el string.
O05 y O06 son las dos trampas de vacío. O04 es el control de que no se matchea de más.

> **Desvío de esta tabla al construirla (2026-08-02).** O02 se escribió
> `011 15 6161-7956`, **no** `11 15 6161 7956` como decía el borrador. Motivo: el
> normalizador de F01 reconoce el formato viejo con `15` **solo con el 0 inicial**
> (`0` + área + `15` + abonado, 13 a 15 dígitos); sin ese 0, `11 15 6161 7956` son
> 12 dígitos que no caen en ninguna rama y F01 los marca `invalido`. Escrito como
> estaba, O02 habría quedado descartado por "sin teléfono" y no habría probado
> nada del cruce. Se eligió respetar F01 —tocar su lógica está prohibido en esta
> fase— y ajustar el dato de prueba. **Sigue probando exactamente lo que tenía que
> probar:** el `15` de la principal contra el `+54 9` de la baja, dos formatos
> distintos que dan el mismo canónico. Si algún día se quiere aceptar el `15` sin
> el 0 inicial, es una corrección de F01 con su propia sesión.
>
> Las otras dos parejas quedaron como estaban: O01 `11 4161-7956` contra
> `011 4161-7956`, y O07 `11 4242-4242` contra `011 4242-4242` — las dos cruzan
> 10 dígitos pelados contra el mismo número con 0 inicial.

## Verificador

`verificadores/v14_optout.py` — **corre n8n de verdad** (importar + `--id`), mismo
estándar que v11/v12/v13, oráculo Python **independiente**, esperados **literales
escritos a mano** desde las tablas de arriba (nunca calculados con la lógica del nodo:
ese es el hallazgo de F05). Tres bloques:

1. **Default (sin `--lista-baja`)** sobre el CSV canónico: los dos golden byte a byte, la
   columna/motivo de opt-out ausente, la regresión intacta. El check que manda.
2. **Con `lista_baja_1.csv` sobre `leads_optout_1.csv`**, por el nodo real: cheque de
   celda fila por fila O01–O07 — quién es opt-out y quién no, el motivo exacto, que
   aparezca una sola vez, y las dos trampas (O05 descartado por "sin teléfono" y sin el
   motivo opt-out; O06 sin opt-out). Más el conteo por vía de cruce (teléfono / CUIL /
   ambos).
3. **El reporte**: con la baja, la línea de opt-out aparece con el conteo correcto; sobre
   el canónico (sin baja) el reporte es byte a byte el del golden (A/B, la línea ausente).

## Fuera de alcance

- **Verificar contra el registro oficial "No Llame" (Ley 26.951) o RENAPER.** Eso es
  Nivel 2, necesita inscripción, y no se promete acá ni en el reporte ni en el pitch.
- **Deduplicar la lista de baja contra sí misma o "arreglarla".** Se lee, se normaliza,
  se cruza. Si viene sucia, sus filas ilegibles simplemente no matchean (y eso no puede
  hacer que un contacto real caiga: ver anti-footgun).
- **Match difuso / por parecido de teléfono o CUIL.** Exacto sobre el canónico, o nada.
- **Historial de llamados (filtro 11).** Es otro cruce con datos del cliente, va en F15.
