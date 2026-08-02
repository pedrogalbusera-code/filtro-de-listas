# F13 — Números y nombres basura

Filtro 9 del catálogo. Segundo filtro nuevo de Nivel 1: descarta teléfonos
claramente falsos y marca nombres de relleno, sobre el dato **ya normalizado**
por F01. Son contactos que un humano descarta de una ojeada y el operador igual
llama.

## En qué se diferencia de F12

**F12 (segmentación) va apagado por defecto** porque segmentar depende de a
quién le vende el cliente. **F13 va ENCENDIDO**: un teléfono `1111111111` no es
llamable para nadie. Es limpieza universal, no una decisión comercial.

`config/basura.json` existe igual, pero **no prende ni apaga el filtro**: solo
afina los patrones por cliente. El que quiera desactivar un patrón le vacía la
lista.

## La regla de oro: ante la duda, NO es basura

Un falso positivo tira un contacto real a la basura y **nadie se entera nunca**
— no hay operador que llame para descubrir el error. Es el riesgo asimétrico de
esta fase: dejar pasar un número trucho cuesta una llamada; marcar uno real
cuesta un cliente.

Por eso acá no hay ni una heurística. O el número tiene una cola de dígitos
idénticos más larga que cualquier número real medido, o está en una lista
escrita a mano.

### El dato que fija el umbral

Medido sobre `data/leads_prueba_SINTETICO_1.csv` (200 filas) y
`data/leads_adversario_1.csv` (48):

| Archivo | Corrida más larga de un mismo dígito | Basura detectada |
|---------|--------------------------------------|------------------|
| SINTETICO_1 (200 reales) | **3** (`+549 11 3992-7555`) | 0 |
| adversario_1 (48) | **4** (`1155551111`) | 0 |

El umbral es **7 dígitos iguales al final** de los 10 nacionales: tres de margen
sobre lo peor que se ve en datos reales. El generador **rechaza** un umbral menor
a 4.

## Criterio 1 — el golden es la prueba de "ningún número real cae por error"

La lista canónica no tiene **nada** de basura. Consecuencia: con los patrones
**encendidos**, las dos salidas quedan **byte a byte idénticas a los golden de
F09** (`9a6884…dcb4` comercial, `ae6fcc…9cd2` auditoría) y la regresión sigue
10/10.

Si el golden se mueve, un patrón tiene un falso positivo sobre datos reales.
Eso no se arregla relajando el golden: se arregla sacando el patrón.

El verificador además corre el **A/B**: la misma lista con los patrones vacíos
(el pipeline de antes de F13) produce el mismo reporte byte a byte. Si un patrón
se comiera una fila real, las dos corridas dividirían.

## Las dos reglas de comportamiento

| Qué | Consecuencia | Por qué |
|-----|--------------|---------|
| **Teléfono de relleno** | **Descarte duro**, motivo `teléfono de relleno +0 → descarte` | A un número inventado no se puede llamar: es tan no-llamable como uno truncado. |
| **Nombre de relleno** | **Marca, NO descarte**, motivo `nombre de relleno +0` | Un nombre trucho con un teléfono bueno **sigue siendo un contacto llamable**, igual que "sin nombre" en F04. El operador solo no va a saber a quién saluda. |

El motivo del nombre queda en la columna `motivo`, que es la que el cliente ve
en el CSV comercial — más visible que `motivo_descarte`, que es de auditoría.

## Dónde vive

En el **mismo nodo de F06** que los otros descartes directos (teléfono, zona,
duplicado, segmento). No hay nodo nuevo: F13 no deriva ningún dato, solo juzga
lo que F01 ya normalizó. La decisión de prioridad sigue estando en un solo lugar.

- El descarte por teléfono va **pegado al bloque del teléfono** (`1b`), para que
  las dos verdades del teléfono queden juntas en el motivo.
- La marca de nombre va al final (`8`), después de los descartes.

## Los patrones (config/basura.json)

- **Teléfonos**, contra los **10 dígitos nacionales** del `telefono_norm` (no
  contra el string crudo: `11 1111-1111` y `+541111111111` son el mismo número
  inventado y tienen que caer los dos):
  - `min_digitos_iguales_al_final: 7`
  - lista **explícita** de secuencias: `1234567890`, `0123456789`, `0987654321`,
    `1234512345`, `1212121212`. Ninguna tiene código de área argentino válido.
    **Lo que no está en la lista no es basura.** Se descartó a propósito
    `1122334455`: tiene área 11 válida y podría ser el número de alguien.
- **Nombres:** lista explícita (`test`, `asdf`, `qwerty`, `xxx`, `prueba`,
  `sin nombre`, `nn`, `na`, `n/a`, `ninguno`, `sin dato`), comparada por
  **igualdad** sobre el nombre normalizado (minúsculas, sin tildes, sin espacios
  de más). **Nunca por substring:** `Ana Testa` es un apellido real y no puede
  caer por contener "test".

El generador valida fuerte: umbral entero entre 4 y 10, y cada secuencia un
string de exactamente 10 dígitos (si tuviera otro largo no matchearía nunca y
nadie se enteraría).

## Parte 2 — la deuda del reporte, cerrada

El reporte de F08 contaba solo "sin teléfono", "fuera de zona" y "duplicado".
Los descartes por **segmento** (deuda registrada en F12) y por **basura** habrían
sumado al total sin aparecer desglosados.

Ahora el reporte tiene las dos filas, con una regla que protege el golden:
**un motivo se muestra solo si cuenta ≥ 1.** Con la lista canónica los dos dan 0,
no aparece ninguna fila nueva y el reporte del golden no cambia ni un carácter.

El segmento va en **su propia subtabla**, no mezclado con la calidad de dato:

- **Por calidad de dato** — hechos del archivo: sin teléfono, **teléfono de
  relleno**, duplicado.
- **Por zona de cobertura** — supuesto nuestro.
- **Por segmento no buscado** — **decisión comercial del cliente**.

Mezclar la tercera con la primera inflaría el ahorro con algo que el cliente
eligió, no con basura que el archivo traía.

## Archivo de prueba

`data/leads_basura_1.csv` (7 filas). Todas limpias salvo por lo que se está
probando (teléfono válido, en zona, CUIL válido, fecha fresca, origen referido),
así que el **único** descarte posible es el de basura:

| Fila | Qué prueba | Esperado |
|------|------------|----------|
| B01 `1111111111` | teléfono todo un dígito | descarte, `teléfono de relleno` |
| B02 `1234567890` | secuencia de la lista | descarte, `teléfono de relleno` |
| B03 nombre `test` | relleno con teléfono bueno | **marca**, prioridad alta |
| B04 nombre `N/A` | relleno con barra, normalizado | **marca**, prioridad alta |
| B05 `1155551111` | **CONTROL**: repite dígitos pero es real | intacto, alta |
| B06 `Ana Testa` | **CONTROL**: apellido que contiene "test" | intacto, alta |
| B07 `1145111111` | **CONTROL**: 6 repetidos al final | intacto, alta |

Los tres controles son la prueba de cero falsos positivos **por celda**, además
del golden. B07 fija el umbral exacto: con seis no alcanza.

## Verificador

`verificadores/v13_basura.py` — **corre n8n de verdad**, tres bloques: golden
intacto + A/B del reporte; celdas del archivo de basura; y el reporte con sus
filas nuevas (basura y segmento). Los esperados son literales escritos a mano
desde las reglas de arriba.

## Fuera de alcance

- **Nombres de relleno en el reporte.** El reporte desglosa **descartes**, y el
  nombre de relleno no descarta. Queda visible en el `motivo` de la fila.
- **Detección de secuencias por algoritmo.** Explícito o nada: es lo que hace
  que el filtro no pueda comerse un número real.
- **Nombres de una sola letra, iniciales, empresas sin nombre de contacto.** No
  son relleno inequívoco; ante la duda, no es basura.
