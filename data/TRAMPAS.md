# Archivos adversarios — qué trampa tiene cada fila

Estos tres archivos **no están hechos para que el pipeline los limpie bien**.
Están hechos para romperlo.

El archivo `leads_prueba_SINTETICO_1.csv` fue construido sabiendo la solución:
200 CUILs completos y válidos, ninguna fecha vacía, las columnas con el mismo
nombre que las variables. Por eso todo pasa a la primera. Estos archivos son lo
contrario.

**Ningún dato corresponde a una persona real.** Los nombres arrancan con `T##`
para poder rastrear cada trampa en la salida sin agregar columnas.

## Cómo se usan

**Entre F07 y F09.** Antes no: hasta que la salida ordenada no exista, no hay
qué mirar. Después de F09 tampoco: el objetivo es que la lista de lo que rompe
alimente la suite de regresión, no que la audite cuando ya está cerrada.

El procedimiento importa:

1. Pasá cada archivo por el pipeline **sin tocar una línea de código**.
2. Anotá **todo lo que rompe, se cuelga, o devuelve algo raro.**
3. **No arregles nada en el momento.** Primero la lista completa, después se
   decide qué se arregla, qué se documenta como limitación y qué se ignora.
4. Esa lista va al README. Es una de las piezas más fuertes del proyecto: casi
   nadie muestra cómo se rompe lo que construyó.

Arreglar sobre la marcha arruina el ejercicio, porque terminás con un pipeline
que pasa el archivo adversario y sin registro de qué le costó.

---

## Archivo 1 — `leads_adversario_1.csv`

Mismas 6 columnas que el original. 48 filas. Lo que ataca son los **valores**.

### Teléfonos

| Fila | Valor | Qué prueba | Qué debería pasar |
|------|-------|-----------|-------------------|
| T01 | `+54 11 4161-7956` | Formato internacional **sin el 9** | Es un fijo escrito en internacional. Hoy cae en `invalido` porque no arranca con `+549` ni tiene 11 dígitos con 0. **Falso inválido esperado.** |
| T02 | `+54 9 11 4161 7956` | El 9 separado por espacios | Mismo número que un celular normal. `startsWith('+549')` falla por un espacio. **Falso inválido esperado, y es el más grave: un espacio cambia el resultado.** |
| T03 | `549 11 4161 7956` | Internacional sin el `+` | Debería ser celular. Hoy: `invalido`. |
| T04 | `011 15 4161-7956` | Formato viejo con 15, muy común | Es un celular. 13 dígitos arrancando en 0 → hoy `invalido`. |
| T05 | `15-4161-7956` | 15 sin código de área | Sin área no se puede resolver. `invalido` es correcto, pero debería quedar distinguido de "número roto". |
| T06 | `4161-7956` | 8 dígitos, sin área | `invalido` correcto. |
| T07 | `(011) 4161-7956` | Paréntesis | Debería dar `fijo`. Si da inválido, el limpiador de no-dígitos falla. |
| T08 | `1141617956.0` | Excel lo convirtió a decimal | 11 dígitos arrancando en 1 → `invalido`. Correcto pero silencioso: convendría un motivo específico. |
| T09 | `1.14162E+09` | Notación científica de Excel | El número real se perdió. `invalido` es lo único posible, pero **tiene que quedar dicho** que el archivo de origen está dañado. |
| T10 | `1141617956 / 1165385561` | Dos teléfonos en una celda | Hoy `invalido`. Se pierden dos números buenos. |
| T11 | `  1155551111  ` | Espacios alrededor | `ambiguo`. Si falla, no se está haciendo trim. |
| T12 | `+549 11 5555-1111` | El mismo número que T11 en celular | **T11 y T12 tienen que deduplicarse** por `telefono_match`. Es el test directo de la decisión de F03. |
| T13 | `011-45551111` | Fijo | |
| T14 | `1145551111` | El mismo que T13 pelado | **T13 y T14 tienen que deduplicarse.** El ganador debe quedar con tipo `fijo` por la precedencia. |
| T44 | `sin  dato` | Dos espacios en el medio | `invalido`. |
| T45 | `N/D` | Otra forma de decir sin dato | `invalido`. Si el código busca literalmente "sin dato", esto pasa igual por no tener dígitos — verificar que sea por la razón correcta. |
| T46 | `0` | Un solo cero | `invalido`. |

### CUIL

| Fila | Valor | Qué prueba | Qué debería pasar |
|------|-------|-----------|-------------------|
| T23 | vacío | CUIL ausente | Debe seguir siendo procesable. En listas reales de leads el CUIL falta seguido. **Y sin CUIL, el teléfono es la única identidad para deduplicar.** |
| T24 | `20-4412233` | 10 dígitos, truncado | `invalido`, sin intentar completar. |
| T25 | prefijo `99` | DV aritméticamente correcto, **prefijo inexistente** | `invalido`. Si da válido, el código no está validando el prefijo. |
| T26 | sin guiones | `20314459025` | Debe normalizar igual. |
| T27 | con puntos | `20.31445902.5` | Debe normalizar igual. |
| T28 | con espacios | `24 34501277 6` | Debe normalizar igual. |
| T29 | DV forzado a 0 | DV incorrecto a propósito | `invalido`. |
| T30 | prefijo `30` | Persona jurídica | `valido`. Si lo rechaza, falta el prefijo en la lista. |
| T31 | mismo CUIL que T01, otro teléfono | Duplicado por CUIL con datos distintos | Deben fusionarse. **Y hay que mirar cuál sobrevive y si se pierde el teléfono del perdedor.** |
| T03, T14, T33, T37, T44, T47 | resto 1 | Casos que la regla vieja aceptaba con DV 9 | Con la regla corregida (2026-07-27) deben dar **inválidos** y quedar marcados `cuil_dudoso`. Ver la nota del final. |
| T48 | `23-31000009-4` | Reemisión femenina legítima | **Debe dar válido.** Ver nota. |

### Localidad

| Fila | Valor | Qué debería pasar |
|------|-------|-------------------|
| T15 | `MORÓN` | En zona. |
| T16 | `moron` | En zona: minúsculas y sin tilde. |
| T17 | `` ` Haedo ` `` | En zona: espacios alrededor. |
| T18 | `Ramos Mejia` | En zona: falta la tilde. |
| T19 | `Morón (Buenos Aires)` | En zona. Si no matchea, la comparación es demasiado literal. |
| T20 | `Ciudad de Buenos Aires` | Fuera de zona, con motivo. |
| T21 | vacío | Sin localidad. **No es lo mismo que "fuera de zona"** y el motivo tiene que distinguirlo. |
| T22 | `Merlo` | Fuera de zona. Ojo: existe Merlo en San Luis; una lista real puede traer las dos. |

### Fechas

| Fila | Valor | Qué debería pasar |
|------|-------|-------------------|
| T32 | `10/04/2026` | dd/mm/aaaa. |
| T33 | `04/10/2026` | **Ambigua**: puede ser 4 de octubre o 10 de abril. No hay respuesta correcta; lo que importa es que el criterio esté declarado. |
| T34 | `10-abr-26` | Mes en texto y año de 2 dígitos. |
| T35 | vacío | Sin fecha, con motivo, **sin crashear**. |
| T36 | `2026-13-45` | Mes 13 y día 45. Sin crashear. |
| T37 | `2027-01-15` | **Fecha futura**: antigüedad negativa. Muy común por error de tipeo. |
| T38 | `2019-03-02` | Muy vieja: frescura `fría`. |

### Nombre y estructura

| Fila | Qué prueba |
|------|-----------|
| T39 | Nombre vacío. |
| T40 | `PEREZ, JUAN` — coma adentro del campo, prueba el quoting del CSV. |
| T41 | Espacios múltiples adentro y alrededor. |
| T42 / T43 | **Fila duplicada exacta salvo un espacio al final del nombre.** Si la dedup no normaliza, no las ve. |

---

## Archivo 2 — `leads_adversario_2.csv`

8 filas. Lo que ataca es **la lectura del archivo**, no las reglas.

- **Tres filas de basura arriba** del encabezado real (título, fecha de
  exportación, una vacía).
- **Otros nombres de columna:** `Nombre y Apellido`, `Documento`, `Celular`,
  `Zona`, `Origen del lead`, `Fecha de alta`.
- **Una columna de más:** `Observaciones`, con texto libre que incluye comas.
- **Una fila totalmente vacía** en el medio.
- **T55 tiene menos columnas** que el encabezado.
- **UTF-8 con BOM.**
- Fechas en `dd/mm/aaaa` y orígenes con otras etiquetas (`Web`, `Meta`).
- `27-40330288-1` tiene el DV mal **a propósito**.

Lo esperable es que el pipeline **no lo lea**. Está bien: el punto no es que
funcione, es medir **qué tan lejos llega y con qué mensaje falla**. Si tira un
error incomprensible o peor, procesa 3 filas y devuelve un resultado con cara de
correcto, eso es lo que hay que anotar.

Este archivo es el que representa el trabajo real de cada cliente nuevo: el
mapeo de columnas que se hace **una vez por cliente**.

---

## Archivo 3 — `leads_adversario_3.csv`

5 filas limpias, una sola diferencia: **el separador es punto y coma.**

Es lo que produce Excel en español al guardar como CSV. Pasa todo el tiempo.
Si el pipeline lo lee como una sola columna gigante y no avisa, es un fallo
silencioso: el cliente manda su archivo, recibe algo, y nadie se entera.

---

## Corrección importante sobre el CUIL

Al armar T48 salió un dato que **corrige lo que se documentó en `ESTADO.md`**
como limitación de F02.

Se creía que un CUIL femenino reemitido (`23-DNI-4`) sería marcado inválido por
el validador actual. **Es falso.** La reemisión no es una excepción al
algoritmo: es consistente con él.

La aritmética: cambiar el prefijo de `27` a `23` altera el segundo dígito, que
pesa 4. La diferencia es `(7-3) x 4 = 16`, y `16 mod 11 = 5`. Si con `27` el
resto era 1, con `23` pasa a ser 7, y `11 - 7 = 4`. Sale el DV 4 exacto. Lo
mismo de `20` a `23`: la diferencia es 12, `12 mod 11 = 1`, el resto pasa de 1 a
2, y `11 - 2 = 9`. Sale el DV 9.

Verificado por fuerza bruta sobre 300.000 DNI: **27.272 de 27.272** casos de
reemisión femenina validan como `23-DNI-4`, y **27.273 de 27.273** de la
masculina validan como `23-DNI-9`. Sin una sola excepción.

**Qué significa:**

1. **No hay falsos inválidos.** Los CUIL reemitidos pasan bien. Hay que borrar
   esa consecuencia de `ESTADO.md`.
2. **El único defecto real es aceptar `resto 1 → DV 9`.** Bajo la regla de
   AFIP, un CUIL que da resto 1 con su propio prefijo **no puede existir**:
   AFIP lo habría reemitido como 23. Aceptarlo crea una colisión —el DV 9 sale
   tanto de resto 1 como de resto 2— que rompe la garantía del módulo 11: con la
   regla vieja, **1,58% de los typos de un dígito no se detectan**; con la
   corregida, **0%**. Todo typo de un dígito se detecta, sin excepción.
3. **El arreglo es de una línea:** `resto 1 → inválido`. No hace falta modelar
   sexo ni cambiar prefijos. La "adopción de la regla completa de AFIP" que
   quedó postergada es mucho más chica de lo que parecía.
4. El costo de aplicarlo sobre el CSV sintético es que **19 de los 200 pasan de
   válidos a inválidos**, porque ese archivo los generó con la regla vieja. Eso
   no es un problema del código: es la prueba de que el archivo estaba mal
   generado.

Es una decisión de Pedro, no una corrección automática. Las dos opciones son
defendibles y las dos hay que documentarlas.
