# F11 — Puerta de entrada

## Por qué esta fase existe

F00 fijó la entrada como `data/leads_prueba_SINTETICO_1.csv`: seis columnas
conocidas, separador coma, UTF-8, encabezado en la fila 1. **Todo F01 a F10
cuelga de ese supuesto.** Las once fases resuelven qué hacer con los datos;
ninguna resuelve qué hacer con el **archivo**.

Eso alcanza para demostrar —en una demo el archivo lo elegimos nosotros— y no
alcanza para entregar. La corrida adversaria ya lo probó con dos archivos:

| Archivo | Qué pasó hoy | Gravedad |
|---------|--------------|----------|
| `leads_adversario_3.csv` (separador `;`) | 5 filas procesadas, **todos los campos vacíos**, las 5 `descartado`. El CSV de salida tiene cara de correcto: filas, columnas, puntaje, motivo. | **el peor de los 13** |
| `leads_adversario_2.csv` (basura arriba del header) | `Invalid Record Length: columns length is 1, got 7 on line 4`. Crash, sin salida. | rompe |

El `;` es el caso realista, no el exótico: **Excel en español guarda CSV con
punto y coma por defecto.** Es el archivo más probable que mande un cliente. Y
falla en silencio, que es peor que crashear.

## Objetivo

Aceptar el archivo real de un cliente —Excel o CSV, con cualquier separador,
columnas con otros nombres, basura arriba del encabezado— **o rechazarlo con un
error que se entienda**. Nunca procesar basura en silencio.

## La regla de oro

> Ante un archivo que no se entiende, **frenar fuerte antes que procesar en
> silencio.** Un error claro cuesta un mail. Una lista mal parseada entregada a
> un cliente cuesta el cliente.

Es la regla 4 del `CLAUDE.md` —nada se pierde en silencio— aplicada al archivo
en vez de a la fila.

## Qué construir

### 1. Detección de formato y separador

- `.xlsx` / `.xls` → rama de planilla. `.csv` / `.txt` → rama de texto.
- Separador: contar `,`, `;` y tab en las primeras 10 líneas no vacías,
  **fuera de comillas**. Gana el que produzca la **misma cantidad de campos en
  al menos el 80% de esas líneas**. Si ninguno lo logra, se rechaza el archivo.
- Detectar y sacar el BOM. No romperse con CRLF ni con LF.
- **Nada de adivinar con un solo criterio.** "Hay más comas que punto y comas"
  no es detección: un archivo con `;` y direcciones con coma adentro te gana.

### 2. Encontrar el encabezado

Saltar líneas de basura arriba: el encabezado es la primera línea cuya cantidad
de campos coincide con la de la mayoría de las líneas siguientes. Las líneas
salteadas se **reportan**, no se descartan mudas.

### 3. Mapeo de columnas — explícito, nunca adivinado

- Un archivo `config/mapeo_<cliente>.json` con la traducción a los seis nombres
  canónicos (`nombre`, `cuil`, `telefono`, `localidad`, `origen`, `fecha_carga`).
- Si no existe, se intenta un **mapeo automático por coincidencia exacta** contra
  una tabla de sinónimos versionada (`config/sinonimos.json`).
- **Toda columna canónica que quede sin resolver frena la corrida.** No se
  infiere por parecido, no se toma "la tercera columna porque suele ser el
  teléfono". Se pide el mapeo y listo.
- Las columnas que sobran (ej. `Observaciones`) se conservan en el archivo de
  auditoría y no se usan para nada más.

### 4. La reja anti-silencio

El check que habría atrapado el hallazgo 13. Después de parsear y antes de F01:

- Si **más del 50% de las filas tiene los seis campos canónicos vacíos** → se
  rechaza. Eso no es una lista mala, es un parseo mal hecho.
- Si el parseo detecta **una sola columna** en un archivo de más de una línea →
  se rechaza.
- Si quedan **cero filas de datos** → se rechaza.

### 5. La ficha de entrada

`salidas/ficha_entrada_<archivo>.md`, generada por el workflow. Es lo que se lee
**antes** de apretar correr, y es lo que convierte el onboarding de un cliente
en diez minutos de trabajo:

archivo y tamaño · formato y separador detectados · encoding · línea del
encabezado y cuántas líneas se saltearon · columnas encontradas · mapeo aplicado
· columnas canónicas sin resolver · filas leídas · filas con todo vacío ·
**lista de valores distintos de `origen`**.

## Fuera de alcance

- **Normalizar los valores de `origen`.** `Web` / `Meta` / `Base propia` no son
  las etiquetas del CSV de prueba y eso afecta el puntaje de F06, pero es otra
  fase. Acá solo se **listan** en la ficha para que se vea el problema.
- Arreglar T02 y T05 (formatos de teléfono). Es una corrección de F01, va en
  `prompts/CORRECCION-F01.md`, sesión aparte.
- Interfaz web para subir archivos. Sigue valiendo la regla 8 del `CLAUDE.md`.

## Criterio de aceptación

1. **F11 es transparente sobre el archivo canónico.** Con
   `data/leads_prueba_SINTETICO_1.csv` y la misma fecha de corte, la salida es
   **byte a byte idéntica al golden de F09**. Si el golden se mueve, F11 rompió
   algo aguas abajo y no se cierra la fase.
2. **`leads_adversario_3.csv` (`;`, 5 filas)** deja de dar basura. Resultado
   correcto exigido: **5 filas, 3 dentro de zona** (Castelar, Haedo, Morón) y
   **2 fuera** (Moreno, Merlo), con teléfono y CUIL poblados en las 5. Producir
   otra vez 5 `descartado` con campos vacíos es **fallar**, aunque el CSV se vea
   bien.
3. **`leads_adversario_2.csv`** deja de crashear. Se saltean las 3 líneas de
   arriba, se detecta el encabezado en la línea 4 con 7 columnas, se leen las
   **7 filas de datos**, se ignora la línea vacía del medio, y **T55 —que tiene
   4 campos de 7— entra con los que faltan vacíos, no se pierde.** El mapeo
   `Nombre y Apellido → nombre`, `Documento → cuil`, `Celular → telefono`,
   `Zona → localidad`, `Origen del lead → origen`, `Fecha de alta → fecha_carga`
   queda escrito en `config/`, no hardcodeado en el nodo.
4. **`.xlsx` se lee.** Construir `data/leads_adversario_4.xlsx` con encabezados
   canónicos y **un teléfono guardado como número** (la trampa clásica de Excel:
   pierde el cero inicial y puede salir en notación científica). Se lee, y ese
   teléfono queda marcado `invalido` con motivo específico de artefacto de Excel.
5. **Un archivo que no se entiende se rechaza con mensaje claro.** Armar un caso
   a propósito —un `.txt` de prosa, o un CSV de una sola columna— y comprobar
   que **no se genera archivo de salida** y que el error dice qué archivo, qué se
   detectó y qué se esperaba. Un archivo de salida vacío no es un rechazo.
6. La ficha de entrada se genera sola en las cinco corridas anteriores y todos
   sus números se recalculan desde el archivo de origen.

## Verificador

`verificadores/v11_puerta.py`, mismo estándar que v05/v06/v07: **corre n8n de
verdad** por CLI y compara contra un oráculo Python independiente. Los cinco
archivos del criterio son los casos. El criterio 1 se verifica por **hash contra
el golden**, no por comparación parseada.

## Dónde va en el orden

Después de F10, pero la línea que importa no es la numérica:

> **Con F10 se vende. Con F11 se entrega.**

F10 cierra la etapa como algo mostrable —demo, portfolio, guion de venta— y para
eso el archivo lo elegimos nosotros. F11 es requisito para tocar el primer
archivo de un cliente real. Ninguna de las dos se saltea.
