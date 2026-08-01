# Estado del proyecto

Última actualización: 2026-08-01

| Fase | Título                          | Estado    | Verificador |
|------|---------------------------------|-----------|-------------|
| F00  | Entorno y workflow pasamanos    | **CERRADA** | v00: 10/10 PASA |
| F01  | Normalización de teléfono       | **CERRADA (corregida 2026-07-31)** | v01: 42/42 PASA |
| F02  | Validación de CUIL              | **CERRADA** | v02: 22/22 PASA (regla corregida) |
| F03  | Deduplicación                   | **CERRADA** | v03: 29/29 PASA |
| F04  | Completitud y cobertura         | **CERRADA** | v04: 18/18 PASA |
| F05  | Antigüedad del lead             | **CERRADA** | v05: 51/51 PASA (corregido) |
| F06  | Puntaje explicable              | **CERRADA** | v06: 24/24 PASA |
| F07  | Salida ordenada                 | **CERRADA** | v07: 23/23 PASA |
| F08  | El número (reporte de impacto)  | **CERRADA** | v08: 31/31 PASA |
| F09  | Suite de regresión              | **CERRADA (corregida 2026-07-30)** | correr_todo: 10/10 PASA + 3 pendientes OK |
| F10  | Empaquetado y portfolio         | **CERRADA** | correr_todo: 10/10 PASA, n8n limpio OK, SHA-256 golden OK |
| F11  | Puerta de entrada               | **CERRADA (commiteada 2026-08-01)** | v11: 70/70 PASA + suite 10/10 + golden intacto |
| F12  | Persona física vs. jurídica     | **CERRADA** | v12: 102/102 PASA + suite 10/10 + golden intacto |

## Decisiones pendientes de Pedro

- **Supuesto de tiempo por llamada (F08):** el valor actual es **4 min/llamada**,
  hardcodeado en `herramientas/gen_workflow.py` (línea 669). `prompts/F08.md`
  decía 3 min y mencionaba un `config/supuestos.json` que nunca se creó. No
  hay registro en git de cuándo cambió de 3 a 4 (el primer commit ya tiene 4).
  El reporte ahora incluye banda de sensibilidad (2 a 5 min → 3,8 h a 9,5 h).
  Costo horario del operador: sigue en 0, "a definir con el cliente".

## Decisiones tomadas

- **Repo público en GitHub — RESUELTA (2026-08-01).** El repo
  `github.com/pedrogalbusera-code/filtro-de-listas` existe, `origin` está
  configurado por HTTPS y `master` quedó en sync. F10 cerrada al 100%.
- **Zona de cobertura (F04) — RESUELTA (2026-07-27).**
  - **Dentro (8):** Castelar, Haedo, Morón, Hurlingham, Ituzaingó, Ramos Mejía,
    Villa Luzuriaga, San Justo.
  - **Fuera (2):** Moreno, Merlo.
  - Sobre el CSV: **161 dentro, 39 fuera** (Moreno 21 + Merlo 18).
  - **Es un escenario para la demo, no un requisito de un cliente real:** todavía
    no hay cliente. Por eso la zona va como **parámetro del workflow**, en un
    objeto de configuración (`CONFIG.zona` arriba del nodo Code de F04),
    **cambiable desde un solo lugar**. El próximo cliente tiene otra zona y no se
    toca el algoritmo.
- **Pesos del puntaje (F06) — RESUELTA (2026-07-28).** Se usó la propuesta de
  arranque de `fases/F06-puntaje-explicable.md`. Los pesos y umbrales viven en
  `CONFIG` al inicio del nodo Code, cambiables desde un solo lugar. La
  distribución (48/38/114) valida que los umbrales están calibrados. Ajustable
  sin tocar lógica cuando haya datos de un cliente real.
- **Match de teléfono en F03 (últimos 10 dígitos) — RESUELTA (2026-07-27).**
  Ver bitácora de F03.

## Notas para F08 (reporte de impacto) — anotar ahora, usar después

Estas dos cosas condicionan cómo se presenta el número. Se escriben acá para no
inflar el ahorro sin querer cuando lleguemos a F08.

### Los descartes por zona van SEPARADOS de los descartes por calidad de dato

- **Calidad de dato** (teléfono inválido, CUIL inválido, duplicado): son
  **hechos del archivo**. Se pueden defender mirando el CSV.
- **Zona** (fuera de cobertura): depende de una **suposición nuestra** (qué
  localidades entran), y encima es un escenario de demo, no un cliente real.
- **Mezclarlos sería vender un ahorro inventado.** F08 reporta las dos columnas
  por separado: "contactos no llamables por dato" y "contactos fuera de zona".
  El separador limpio ya existe en los datos: zona vía `en_zona`, calidad vía
  `telefono_tipo=invalido` (y `cuil_valido=false`).

### Los duplicados se cuentan UNA sola vez (nunca 14 + 8)

Sobre este CSV, la unión de duplicados es **14**, no 22. Ver corrección de F03
abajo. En F08, el ahorro por deduplicación se calcula sobre **14 filas**, nunca
sumando 14 (CUIL) + 8 (teléfono): serían los mismos contactos contados dos veces.

## Limitaciones conocidas

### F03 — La deduplicación por teléfono no aporta detección única en este archivo

La unión de duplicados da **14** porque los **8** detectados por teléfono están
**todos contenidos** en los **14** detectados por CUIL. En este archivo, dedupar
por teléfono **no encuentra ni un solo contacto que CUIL no encuentre ya**.

Dos consecuencias:

1. **F08 cuenta los duplicados una sola vez:** 14, nunca 14 + 8.
2. **El trabajo de F01 no se puede presentar como ahorro de llamadas sobre estos
   datos:** no elimina ninguna llamada que la dedup por CUIL no elimine igual.

**Por qué F01 igual sirve, y por qué esto es propiedad del ARCHIVO y no del
mundo:** el CSV sintético tiene los **200 CUILs completos**. En una lista real de
leads el CUIL suele venir **vacío en buena parte** de los registros, y ahí el
teléfono pasa a ser la **única identidad disponible** para deduplicar. O sea: la
normalización de teléfono es la que sostiene la dedup cuando no hay CUIL — que es
el caso común en producción, aunque no en esta muestra.

### F02 — Regla del CUIL: `resto 1 → inválido` (corregido 2026-07-27)

**Regla aplicada:** módulo 11 con pesos `5 4 3 2 7 6 5 4 3 2`; `resto 0 → DV 0`,
**`resto 1 → INVÁLIDO`**, resto → `11 − resto`.

**Por qué resto 1 se rechaza.** Un CUIL que da resto 1 **con su propio prefijo**
no puede existir bajo AFIP: lo habría reemitido con prefijo **23**. Y la
reemisión **no es una excepción al algoritmo, es consistente con él** — cambiar
el prefijo altera el dígito que pesa 4 y el resto deja de ser 1:

- `27 → 23`: la diferencia es `(7−3)×4 = 16`, `16 mod 11 = 5`. Si con `27` el
  resto era 1, con `23` pasa a **7**, y `11 − 7 = 4`: sale el **DV 4** (femenino).
- `20 → 23`: la diferencia es `12`, `12 mod 11 = 1`. El resto pasa de 1 a **2**,
  y `11 − 2 = 9`: sale el **DV 9** (masculino).

Verificado por fuerza bruta sobre 300 000 DNI: **27 272/27 272** reemisiones
femeninas (`23-DNI-4`) y **27 273/27 273** masculinas (`23-DNI-9`) validan con
este mismo algoritmo simple. **Cero excepciones.** O sea: los CUIL reemitidos
pasan bien, no hay falsos inválidos, y no hace falta modelar sexo ni prefijos.

Aceptar resto 1 como DV 9 (la regla vieja) sólo creaba una **colisión** —el DV 9
salía tanto de resto 1 como de resto 2— que debilitaba el verificador.

**Consecuencia sobre el CSV:** **19 de los 200** pasan de válidos a inválidos.
Es esperable: ese archivo se generó con la regla vieja. Clasificación nueva:
**181 válidos, 19 inválidos por resto 1**. Los typos de un dígito no detectados
**bajan de 1,58 % a 0 %** (confirmado con `herramientas/medir_typos.py`: regla
"estricta" vs "simplificada").

**`cuil_dudoso`** se mantiene, pero **cambia de significado**: ahora marca los
**rechazados por resto 1** (antes marcaba los aceptados con reserva). Son los
mismos 19, ahora todos `cuil_valido=FALSE`.

**Propagado (2026-07-28):** los workflows de F03 y F04 se regeneraron,
reimportaron y reejecutaron. Sus `salida_f03/f04.csv` ahora muestran los 19
como `cuil_valido=FALSE` y `cuil_dudoso=TRUE`, consistentes con `salida_f02.csv`.
Los 5 verificadores (v00–v04) pasan.

---

## Corrección del 2026-07-27 — el número era 0 %, no 0,93 %

La cifra "0,93 % de typos no detectados con la regla estricta" que circuló en las
notas anteriores **está mal medida y queda anulada**. El número correcto es **0 %**.

**El error de medición.** El script original mutaba un dígito de los 200 CUILs y
contaba cuántos mutados seguían dando válidos. Pero bajo la regla corregida, 19 de
esos 200 ya son inválidos de base. Mutar un CUIL que ya era inválido y que por
casualidad caiga en válido **no es un typo no detectado**: es basura que se volvió
válida, que es otro fenómeno y mucho menos frecuente. La base tiene que ser
únicamente los CUIL válidos.

**Medición correcta** (base = solo los válidos bajo cada regla):

| Regla | Base válida | Typos probados | No detectados |
|-------|-------------|----------------|---------------|
| simplificada (`resto 1 → DV 9`) | 200 | 18.000 | 284 — **1,58 %** |
| estricta (`resto 1 → inválido`) | 181 | 16.290 | **0 — 0,00 %** |

Coincide con el 13032/13032 que dio el test del medio del verificador
(181 × 8 posiciones × 9 dígitos = 13.032). Los dos caminos dan lo mismo.

**Y no es casualidad, es demostrable.** Bajo la regla estricta el mapeo
resto → DV es inyectivo: `0→0, 2→9, 3→8, 4→7, 5→6, 6→5, 7→4, 8→3, 9→2, 10→1`, y
el resto 1 se rechaza. Cambiar un dígito altera la suma en `peso × delta`, con
peso entre 2 y 7 y delta distinto de 0; como 11 es primo y el peso es menor que
11, el resto **siempre** cambia, y por lo tanto el DV esperado también. Todo typo
de un dígito se detecta, sin excepción.

Eso es exactamente lo que un dígito verificador módulo 11 garantiza por diseño.
**La regla `resto 1 → DV 9` rompía esa garantía**, porque hacía que el DV 9
saliera de dos restos distintos (1 y 2) y creaba una colisión. Corregirla no
"mejoró un porcentaje": restauró la propiedad que el algoritmo tiene que tener.

`herramientas/medir_typos.py` fue corregido para medir sobre la base correcta.

---

## Propagación de la regla de CUIL a F03 y F04 — HECHO (2026-07-28)

Los workflows de F03 y F04 se regeneraron desde `gen_workflow.py` (que ya tenía
la regla corregida), se reimportaron y reejecutaron. Los CSVs ahora son
consistentes con F02: **181 válidos / 19 inválidos** en las tres salidas.
Los 5 verificadores (v00–v04) pasan sin cambios.

**Lo que este episodio deja al descubierto, y es más importante que el fix:** la
lógica de cada fase queda **copiada dentro de cada workflow posterior**. Un
cambio de una línea en F02 obliga a tocar todos los workflows aguas abajo. Con
dos es molesto; con ocho es el motivo por el que nadie va a querer corregir nada.
Conviene resolverlo antes de F07 — evaluar si el proyecto mantiene un único
workflow acumulativo en vez de uno por fase, o si los nodos Code se generan
siempre desde una única fuente. **No se decide en esta sesión**: se anota acá y
se decide aparte.

---

## Archivos adversarios — CORRIDOS el 2026-07-28 (antes de F07, no después)

En `data/` hay tres archivos escritos **por alguien que no vio la
implementación**, a propósito, para romper el pipeline:

- `leads_adversario_1.csv` — 48 filas, mismas columnas, valores sucios.
- `leads_adversario_2.csv` — otras columnas, basura arriba, columna de más.
- `leads_adversario_3.csv` — separador punto y coma (Excel en español).

`data/TRAMPAS.md` documenta fila por fila qué trampa tiene y qué debería pasar.
El prompt de la corrida es `prompts/ADVERSARIO.md`.

**Regla de esa sesión: no se arregla nada, solo se anota.** El entregable es
`salidas/HALLAZGOS_ADVERSARIO.md` con la gravedad de cada hallazgo, y `git diff`
sobre `workflows/` y `verificadores/` tiene que salir vacío. Arreglar sobre la
marcha deja un pipeline que pasa el archivo y ningún registro de qué le costó, y
ese registro es una de las piezas fuertes del README.

---

## Nota de mercado — cómo trabajan hoy los call centers (2026-07-27)

Los call centers del rubro consultan **manualmente**, contacto por contacto, tres
sitios distintos para revisar cuestiones de obra social: AFIP "Aportes en línea",
el padrón de la Superintendencia de Servicios de Salud, y el CODEM de ANSES.

Si eso son dos minutos por contacto, en una lista de 200 son casi siete horas de
trabajo humano por lista. **Es un dolor más caro que el que resuelve la limpieza**,
y es la mejor pregunta de apertura para una charla con alguien del rubro: *"vi que
chequean obra social a mano en tres sitios, ¿cuánto tiempo les come eso?"*.

**Automatizar esas consultas está descartado y no se reevalúa.** Tres motivos, y
el tercero es el que manda:

1. No son APIs: son pantallas de consulta personal. El padrón de la SSS tiene
   captcha puesto justamente para impedir el procesamiento masivo.
2. Usar la clave fiscal propia para consultar a terceros es usar mal la credencial.
3. **La obra social es dato de salud**, la categoría más protegida de la Ley
   25.326. La consulta masiva la haría Pedro, no el call center: la
   responsabilidad queda de su lado, con su CUIL en los registros del organismo.

**El camino legítimo ya está en el plan: Etapa 3**, preguntarle a la persona con
consentimiento. Es mejor dato que el padrón —más fresco, y filtra intención además
de condición— y sigue bloqueado hasta tener WhatsApp Business API.

Camino intermedio, sin bloqueo: si el cliente **ya tiene** esos datos por su
propia relación con los contactos, Pedro los procesa por encargo, con eso por
escrito. Ahí no obtiene nada: ordena lo que el cliente ya tiene.

---

## Hallazgos adversarios — estado de los 13

| #  | Id  | Categoría | Estado | Detalle |
|----|-----|-----------|--------|---------|
| 1  | T01 | teléfono  | **corregido** | Fijo internacional (`+54 11 …`) → ahora fijo. CORRECCION-F01. |
| 2  | T02 | teléfono  | **corregido** | Celular con espacio (`+54 9 11 …`) → ahora celular. CORRECCION-F01. |
| 3  | T03 | teléfono  | **corregido** | Internacional sin `+` (`549 …`) → ahora celular. CORRECCION-F01. |
| 4  | T04 | teléfono  | **corregido** | Formato viejo con 15 (`011 15 …`) → ahora celular. CORRECCION-F01. |
| 5  | T05 | teléfono  | **corregido** | `15-…` sin área → ahora invalido (antes ambiguo con norm incorrecta). CORRECCION-F01. |
| 6  | T10 | teléfono  | **corregido** | Dos teléfonos en una celda → ahora toma el primero. CORRECCION-F01. |
| 7  | T19 | localidad | **registrado** | `Morón (Buenos Aires)` → fuera de zona. Comparación literal. |
| 8  | T21 | localidad | **registrado** | Localidad vacía → fuera de zona. Indistinguible de "vive lejos". |
| 9  | T31 | dedup     | **registrado** | Perdedor con tel válido: se pierde. No transfiere al ganador. Dedup cambió de CUIL directo a transitivo (consecuencia de CORRECCION-F01). |
| 10 | T08 | cosmético | no incluido | `.0` de Excel → invalido correcto, sin motivo específico. |
| 11 | T09 | cosmético | no incluido | Notación científica → invalido correcto, sin aviso de archivo dañado. |
| 12 | —   | archivo 2 | **corregido** | Basura arriba del header → ahora se saltea y reporta (encabezado detectado en línea 4). F11. |
| 13 | —   | archivo 3 | **corregido** | Separador `;` → ahora detectado; 5 filas pobladas, 3 en zona, 2 fuera. F11. |

**Registrados (9):** en `verificadores/pendientes_conocidos.py`, verificados por
`v09_pendientes.py`. La suite los reporta en su propia sección.

**Corregidos por F11 (12 y 13):** la puerta de entrada detecta separador y
encabezado, mapea columnas por config y rechaza fuerte lo que no entiende.
Verificados por `v11_puerta.py` (48/48).

**No incluidos (2):** cosméticos. El pipeline los clasifica correctamente
(invalido), pero no avisa del motivo específico (artefacto de Excel).

---

## Bitácora

**2026-08-01 — F12 cerrada: persona física vs. jurídica.** Primer filtro nuevo
de Nivel 1 del catálogo (filtro 8). Etiqueta cada contacto `fisica` /
`juridica` / `desconocida` por el **prefijo de `cuil_norm`** que F02 ya
calcula —20/23/24/27 física, 30/33/34 jurídica, sin prefijo utilizable
desconocida— y permite descartar el tipo que el cliente no busca. No consulta
ninguna fuente externa: sale gratis del dato que la lista ya trae.

**Está apagado por defecto y esa es la decisión de diseño principal.**
`config/segmentacion.json` va al repo con `{"etiquetar": false,
"descartar": null}`; con esa config el nodo devuelve los items tal cual, sin
agregar ni una clave, y las dos salidas del CSV canónico quedan **byte a byte
idénticas al golden de F09** (verificado: com=`9a6884603f91...`
aud=`ae6fcc5f146d...`). Segmentar es la decisión comercial de **un** cliente,
no del producto.

**Las cuatro reglas que fija la fase:**

1. **Clasifica por prefijo, aunque el DV sea inválido.** Una empresa `30-…` con
   un typo en el dígito verificador sigue siendo jurídica; que el DV falle ya
   lo dice `cuil_valido`. Son dos preguntas distintas.
2. **`desconocida` nunca se descarta.** Sería repetir el error que F04 tiene
   medido con la localidad vacía (T21): "no sé qué es" no es "sé que no sirve".
   Pedir `descartar: "desconocida"` **frena el generador** con el motivo escrito.
3. **Descartar es marcar, no borrar.** Motivo:
   `persona jurídica (segmento no buscado) +0 → descarte`. Las filas siguen ahí.
4. **`tipo_persona` no suma ni resta puntaje.** Verificado por proyección: con
   `{etiquetar:true, descartar:null}`, sacando esa columna la auditoría vuelve a
   ser el golden celda por celda y el comercial no se movió ni un byte.

**Dónde vive cada cosa:** nodo `n8b-persona` entre F05 y F06 (necesita
`cuil_norm`, y tiene que llegar antes del puntaje). F12 solo marca
`descarte_segmento` + `motivo_segmento`; **la decisión de prioridad sigue
estando en un solo nodo** (F06), junto a los otros tres descartes directos. La
fase 11 quedó **intacta**: F12 es una entrada nueva en `FASES`
(`workflows/11-persona.json`), no una modificación de F11, así que
`v11_puerta.py` sigue verificando exactamente lo que cerró. La columna
`tipo_persona` sale solo en la auditoría, por el mismo mecanismo de columnas
opcionales que ya usaban `extra_*` y `advertencia_entrada`.

**Verificador `v12_persona.py`: 102/102 PASA** (4 corridas reales de n8n).
Esperados escritos a mano desde la tabla de la fase, nunca calculados con la
lógica del nodo. Dos archivos de entrada:

- **`data/leads_segmento_1.csv`** (11 filas, nuevo). Cubre los **siete**
  prefijos y los tres bordes que ningún archivo del repo tenía: un `33-…`, un
  `34-…` y un `30-…` con DV roto. Filas limpias a propósito para que el único
  descarte posible sea el del segmento: con `descartar:"juridica"` da 4
  descartadas (las 3 jurídicas + la del DV roto), 4 alta y 3 media — las 3
  desconocidas pierden 10 puntos por CUIL inválido pero **ninguna se descarta**.
- **`data/leads_adversario_1.csv`** (48 filas). Contadas a mano: **44 física,
  1 jurídica (T30), 3 desconocidas** (T23 sin CUIL, T24 de 9 dígitos, T25
  prefijo 99). El motivo del segmento aparece en una sola fila y es T30.

Suite completa después del cambio: **10/10 PASA**, golden intacto.

**Limitación registrada, no parcheada:** el reporte de F08 **no cuenta los
descartes por segmento**. Con la segmentación encendida esas filas suman al
total de descartados pero no aparecen en ninguna de las dos subtablas de
motivos (el reporte busca "sin teléfono", "fuera de zona" y "duplicado"). Hoy
no molesta porque la segmentación está apagada y ningún cliente la usa, pero
**hay que agregarle su fila al reporte antes de vendérsela a alguien**. Está
anotado en `fases/F12-persona-fisica-juridica.md` y en el catálogo.

**2026-08-01 — F11 commiteada y pusheada; hueco T01–T10 cerrado.** F11 había
corrido 5 archivos por el nodo real de n8n pero nunca `leads_adversario_1.csv`:
los arreglos de CORRECCION-F01 sobre los formatos T01–T10 estaban verificados
solo contra el oráculo Python de `v01_telefono.py` — el mismo patrón que el
hallazgo de F05 (oráculo comparado contra sí mismo), justo en la normalización
de teléfonos. Se agregó un **sexto caso** a `v11_puerta.py`: corre
`leads_adversario_1.csv` por el nodo real (import + execute) y verifica por
**contenido de celda** del CSV de auditoría que T01–T10 dan exactamente la
tabla de `prompts/CORRECCION-F01.md`, con los esperados transcriptos **a mano**
desde esa tabla (prohibido sacarlos del oráculo o del pipeline). T05 dio
`invalido` con norm vacía en el nodo real: el bug del número inventado no está
vivo. `v11_puerta.py`: **70/70 PASA** (48 anteriores + 22 nuevos: corrida,
presencia de las 10 filas, y 20 checks de celda). Suite completa después del
cambio: **10/10 PASA (681s)**, golden intacto (com=`9a6884603f91...`
aud=`ae6fcc5f146d...`). Los 14 archivos de F11 + el verificador ampliado + la
ficha de la sexta corrida quedaron commiteados y pusheados arriba de `cbebea8`.

**2026-07-31 — F11 cerrada: puerta de entrada.** El pipeline ahora acepta el
archivo de un cliente (CSV con cualquier separador, basura arriba del
encabezado, columnas renombradas, o .xlsx) o lo rechaza con un error que se
entiende. Nunca procesa basura en silencio. `v11_puerta.py`: **48/48 PASA**
(5 corridas reales de n8n). Suite completa después del cambio: **10/10 PASA
(762s)**, golden intacto (com=`9a6884603f91...` aud=`ae6fcc5f146d...`),
pendientes 3/3 sin cambio. n8n resolvió a 2.32.7 vía npx (antes 2.31.7); cero
diferencias.

**Qué se construyó** (fase `11` de `gen_workflow.py`, workflow
`workflows/10-puerta.json`):

- **Puerta de entrada** (nodo Code): decodifica el binario (UTF-8 con/sin BOM,
  fallback Latin-1), detecta separador, encuentra el encabezado salteando y
  REPORTANDO la basura de arriba, parsea RFC4180 (comillas con comas y saltos
  adentro), mapea columnas y aplica la reja anti-silencio.
- **Reja** (nodo aparte): si la puerta marcó rechazo, tira la excepción. Está
  separada para que la rama de la ficha se escriba ANTES de frenar.
- **Ficha de entrada**: `salidas/ficha_entrada_<archivo>.md`, generada por el
  workflow en las 5 corridas (también en el rechazo).
- **Auditoría F11**: las 26 columnas de F07 + las columnas extra del cliente
  (`extra_*`, `advertencia_entrada`) al final. Sin extras es byte a byte la de
  F07 — por eso el golden no se mueve.
- **Config versionada**: `config/sinonimos.json` (tabla general, coincidencia
  exacta normalizada) y `config/mapeo_adversario2.json` (por cliente).
  `Documento → cuil` vive en el mapeo del cliente a propósito: un "Documento"
  puede ser DNI, decidir que es CUIL no es generalizable.

**Decisiones de diseño que la fase no fijaba:**

1. **La rama de entrada (texto vs planilla) se decide al GENERAR el workflow**,
   por la extensión del path — que ya queda embebido en el JSON de todos modos.
   El `.xlsx` va por `extractFromFile` (operación xlsx); el texto va por el
   parser propio del nodo Code.
2. **Regla del 80% refinada** (documentado acá porque la fase decía solo "80%
   de las líneas"): las líneas con 1 solo campo no votan (no contienen el
   separador: son título/basura, no evidencia en contra), pero la moda tiene
   que aparecer en ≥50% del total muestreado (así un `;` perdido dentro de una
   celda no gana con una sola línea). Dos separadores igual de consistentes =
   ambiguo = rechazo.
3. **Teléfono guardado como número en la planilla** → se serializa como
   `1141617956.0` (el artefacto visible de Excel): si había un 0 inicial ya se
   perdió y no hay forma de saberlo, así que un teléfono numérico no es
   confiable. F01 lo marca `invalido` sin tocarlo, y el motivo queda en
   `advertencia_entrada` y en la ficha.
4. **El pasamanos (F00) ahora deja pasar `extra_*` y `advertencia_entrada`.**
   Con el CSV canónico esas claves no existen: cero cambio de comportamiento
   (verificado por el golden).
5. **`data/leads_adversario_4.xlsx` se genera con biblioteca estándar**
   (`herramientas/gen_xlsx_adversario4.py`, zipfile + XML): sin openpyxl, el
   repo sigue sin dependencias.

**Hallazgo técnico de la sesión:** en n8n 2.x el Code node corre en un task
runner y el binario NO llega como base64 en `items[].binary.data.data` (queda
una referencia); hay que pedirlo con `await helpers.getBinaryDataBuffer(0,
'data')`. El síntoma era venenoso: la puerta "veía" un archivo de 1 línea y
rechazaba todo. El nodo quedó con fallback al base64 para poder probar la
lógica fuera de n8n.

**Separador y encabezado detectados en las 5 corridas** (de las fichas):

| Archivo | Separador | Encabezado | Salteadas | Filas |
|---------|-----------|------------|-----------|-------|
| `leads_prueba_SINTETICO_1.csv` | coma | línea 1 | 0 | 200 |
| `leads_adversario_3.csv` | punto y coma | línea 1 | 0 | 5 (3 en zona, 2 fuera, todo poblado) |
| `leads_adversario_2.csv` | coma | **línea 4** | **3** (2 con texto + 1 vacía) | 7 (+1 vacía ignorada; T55 completada con vacíos) |
| `leads_adversario_4.xlsx` | n/a (planilla) | fila 1 | 0 | 4 (T71 invalido por artefacto de Excel) |
| `leads_adversario_5_prosa.txt` | — | — | — | RECHAZADO |

**Mensaje de error exacto del rechazo** (exit de error, sin archivo de salida,
con ficha):

> F11 RECHAZO — archivo: C:\\...\\data\\leads_adversario_5_prosa.txt —
> detectado: ningun separador (coma, punto y coma, tabulador) produce una
> cantidad estable de columnas (>=2) sobre las primeras 4 lineas no vacias —
> esperado: una tabla con separador consistente; esto no parece una tabla

**Valores distintos de `origen` en `leads_adversario_2.csv`** (insumo de la
próxima decisión de negocio — ninguno coincide con las etiquetas que puntúa
F06, así que hoy todos puntúan 0 en origen): `Referido` (2), `Web` (1),
`Meta` (1), `Evento` (1), `Base propia` (1), vacío (1).

**2026-07-31 — CORRECCIÓN F01: formatos de teléfono argentinos.** Se amplió
`normalizarTelefono` en `gen_workflow.py` (JS_F01) para reconocer 7 formatos
nuevos. v01 subió de 25 a 42 checks, todos PASA.

Formatos agregados:
- `+54 XX XXXX-XXXX` (fijo internacional sin el 9) → fijo
- `+54 9 XX XXXX XXXX` (celular con espacios entre +54 y 9) → celular
- `549 XX XXXX XXXX` (internacional sin `+`) → celular
- `0XX 15 XXXX-XXXX` (formato viejo con 15, área 2-4 díg) → celular
- `15-XXXX-XXXX` (15 sin código de área) → invalido (no se puede resolver)
- `XXXX.0` / notación científica → invalido (artefactos de Excel)
- `XXXXXXXXXX / XXXXXXXXXX` (dos teléfonos separados por `/`) → toma el primero

Arreglo de T05: antes `15-4161-7956` daba `ambiguo` con norm `+541541617956`
(un número inventado, llamable y equivocado). Ahora da `invalido`. Es el
cambio más importante porque corrige un falso positivo peligroso.

**Por qué el golden no se movió:** los formatos nuevos (T01-T10) no están en
`data/leads_prueba_SINTETICO_1.csv` — ese archivo solo tiene `011-…`, `+549…`
y 10 dígitos pelados. SHA-256 comercial y auditoría idénticos al golden de F09.

Consecuencia aguas abajo en el adversario: T31 (dedup) cambió de
`duplicado_de=26, motivo=cuil` a `duplicado_de=28, motivo=transitivo`. T01
ahora tiene teléfono fijo válido (`+541141617956`), lo que activa el match por
teléfono y cambia la cadena de dedup. v03 (29/29 PASA) no se vio afectado
porque es sobre el CSV limpio.

Pendientes conocidos: de 9 bajaron a 3 (T19, T21, T31). Los 6 de teléfono se
sacaron de `pendientes_conocidos.py` porque ahora dan el resultado correcto.

Suite: 10/10 PASA (870s), golden SHA-256 intacto, pendientes 3/3 OK.

**2026-07-31 — F10 cerrada (revisión CIERRE-F10).** Entregables: `workflows/etapa1-final.json`,
`README.md`, `portfolio-entry.html`, `guion-de-venta.md`. Suite 10/10 PASA (623s).
SHA-256 idénticos al golden: com=`9a6884603f91...` aud=`ae6fcc5f146d...`.

Criterio 1 (n8n limpio) ejecutado: `N8N_USER_FOLDER` apuntado a carpeta vacía,
importado solo `etapa1-final.json`, ejecutado con `--id=f08reporte00001`. Los dos
SHA-256 coinciden con el golden. El workflow no depende de nada fuera del JSON.

Hallazgos de la revisión:

1. **Link al repo inexistente.** `portfolio-entry.html` linkea a
   `github.com/pedrogalbusera-code/filtro-de-listas` que no existe. Pendiente
   hasta que Pedro cree el repo y haga push. Comando anotado arriba.
2. **Supuesto de minutos cambió de 3 a 4 sin registro.** `prompts/F08.md`
   decía 3 min y `config/supuestos.json`; el código tiene 4 min hardcodeado en
   `gen_workflow.py`. No hay commit previo con 3 — cambió antes del primer
   commit. Anotado en decisiones pendientes. Se agregó banda de sensibilidad
   al reporte (2 a 5 min → 3,8 h a 9,5 h).
3. **ID del workflow en el README.** El README decía `--id=etapa1final0001`
   pero el JSON tiene `f08reporte00001`. Corregido.
4. **Documentos comerciales excluidos del repo.** `guion-de-venta.md` y
   `CATALOGO-FILTROS.md` agregados al `.gitignore` (modelo de cobro, estrategia
   comercial). El README menciona que quedan fuera a propósito.
5. **`salidas/reporte.md` agregado al `.gitignore`.** Era generado pero no
   matcheaba el patrón existente (`reporte_*.md`).
6. **`motivo_frescura` vacío en las 200 filas.** La frescura sí puntúa
   (aparece en `motivo`), pero `motivo_frescura` tiene 0/200 con valor.
   Es una columna muerta, no un bug de lógica. Pendiente cosmético.
7. **Finales de línea (CRLF).** El problema reportado (12 archivos data/workflows
   con 2464 líneas cambiadas puro CRLF) ya no existe en el árbol actual.

**2026-07-30 — Pendientes conocidos integrados a la suite.** 9 hallazgos del
archivo adversario 1 registrados en `verificadores/pendientes_conocidos.py`,
verificados por `v09_pendientes.py`. La suite (`correr_todo.py`) los reporta
en su propia sección, separados del conteo 10/10 de regresión.

Valores medidos corriendo `leads_adversario_1.csv` por F08 (corte 2026-07-28)
el 2026-07-30: los 9 coinciden con `HALLAZGOS_ADVERSARIO.md` del 2026-07-28.
Ningún comportamiento cambió entre sesiones.

**Prueba de aislamiento — arreglo de T02:**

Cambio: en `gen_workflow.py`, normalizarTelefono, se agregó
`const sNorm = s.replace(/\\s+/g, '');` y se cambió el check de `s.startsWith`
a `sNorm.startsWith`. Eso hace que `+54 9 11 4161 7956` (T02) pase de
`invalido` a `celular`.

Corrida con el arreglo (exit 1):

```
  OK      T01 (telefono): sigue igual
  CAMBIO  T02 (telefono): telefono_tipo: esperaba [invalido] pero dio [celular]; telefono_norm: esperaba [] pero dio [+5491141617956]
  OK      T03 (telefono): sigue igual
  OK      T04 (telefono): sigue igual
  OK      T05 (telefono): sigue igual
  OK      T10 (telefono): sigue igual
  OK      T19 (localidad): sigue igual
  OK      T21 (localidad): sigue igual
  OK      T31 (dedup): sigue igual

  Pendientes: 9 registrados, 8 sin cambio, 1 CAMBIARON
  ATENCION: algun pendiente cambio de comportamiento sin documentarlo.
```

Revertido: 9/9 sin cambio, exit 0.

**2026-07-29 — F09 cerrada.** Suite de regresión original, 10/10 PASA en 651s.

**2026-07-30 — CORRECCIÓN F09.** Cinco problemas corregidos:

1. **Pasada de regeneración.** v00-v04 leían CSVs de días anteriores (27-28/07)
   en vez de regenerarlos. Ahora `correr_todo.py` ejecuta F00-F04 y F06-F08
   desde `gen_workflow.py` antes del loop. F05 no se incluye (v05 la ejecuta
   sola). Si la regeneración falla, la suite aborta.

2. **Golden de auditoría.** El golden solo cubría el CSV comercial (9 columnas).
   Los campos internos (`es_duplicado`, `telefono_match`, `cuil_dudoso`, etc.)
   vivían únicamente en el de auditoría y no se verificaban. Ahora se comparan
   los dos por SHA-256: `golden_2026-07-28.csv` y
   `golden_2026-07-28_auditoria.csv`.

3. **Comando de regeneración del golden.** `python verificadores/correr_todo.py
   --golden` regenera los dos golden files sin correr la suite. Separado para
   que el golden nunca se regenere automáticamente.

4. **Repositorio git.** `git init` con `.gitignore`. Primer commit con todo el
   estado actual. Los dos golden están versionados junto con `gen_workflow.py`.

5. **Prueba de aislamiento (ejecutada, output abajo).**

**Tiempos por verificador (corrida post-revert durante corrección, 662s):**
- Regeneración: 271s (F00 34s, F01 31s, F02 36s, F03 32s, F04 33s, F06 35s, F07 34s, F08 35s)
- v00-v04: <1s (verificación Python sobre CSVs recién regenerados)
- v05: 201s (5 corridas de n8n)
- v06: 32s, v07: 74s, v08: 39s, golden: 43s
- **Total: 662s** (~11 min)

**Tiempos por verificador (confirmación de cierre, 734s):**
- Regeneración: 333s (F00 34s, F01 41s, F02 42s, F03 42s, F04 42s, F06 43s, F07 43s, F08 46s)
- v00-v04: <1s (verificación Python sobre CSVs recién regenerados)
- v05: 206s (5 corridas de n8n)
- v06: 33s, v07: 80s, v08: 42s, golden: 39s
- **Total: 734s** (~12 min)

La diferencia con la corrida anterior (662s → 734s, +72s) es varianza de I/O
de n8n: la regeneración tardó 333s vs 271s (+62s), el resto se distribuye
entre v05-v08. Cero diferencias funcionales.

La regeneración agrega ~300s pero v05 baja de 468s a ~200s (n8n ya está en
caché de la regeneración). Diferencia neta: ~30s.

**Corrección de la afirmación falsa:** la versión anterior decía "cada
verificador corre su propio --fase con su propia ejecución de n8n". Es falso
para v00-v04: son verificación Python pura sobre CSVs existentes, no ejecutan
n8n. La pasada de regeneración corrige esto generando esos CSVs antes del loop.

**Pendiente: los 13 hallazgos adversarios** no van en esta sesión. Van en su
propia sesión, antes de F10. Motivo: el trabajo de esta corrección es que la
suite deje de mentir; agregarle casos nuevos a una suite que todavía mentía es
construir arriba de algo que no se sostiene.

### Prueba de aislamiento — output real

**Cambio:** en `gen_workflow.py`, JS_F02, línea del `resto === 1`:
`cuil_valido: false` → `cuil_valido: true` (los 19 CUILs de resto 1 pasan
como válidos en vez de inválidos).

**Corrida con regla rota (5/10 PASA, 5 FALLA):**

```
  Verif    Estado   Tiempo   Detalle
  -------------------------------------------------------------
  v00      PASA        0s   RESULTADO: PASA (10 checks)
  v01      PASA        0s   RESULTADO: PASA (25 checks)
  v02      FALLA       0s   RESULTADO: FALLA (6 de 22 checks)
  v03      PASA        0s   RESULTADO: PASA (29 checks)
  v04      PASA        0s   RESULTADO: PASA (18 checks)
  v05      PASA      233s   RESULTADO: PASA (51 checks)
  v06      FALLA      35s   v06_puntaje: 21/24 PASA, 3 FALLA
  v07      FALLA      68s   v07_salida: 21/23 PASA, 2 FALLA
  v08      FALLA      42s   v08_reporte: 29/31 PASA, 2 FALLA
  golden   FALLA      37s   comercial difiere / auditoria difiere
  -------------------------------------------------------------
  Suite de regresion: 5/10 PASA, 5 FALLA  (total 763s)
```

**Lectura:** v00, v01 pasan (anteriores a F02, sin dependencia). v02 falla (la
fase rota). v03, v04, v05 pasan (no dependen de `cuil_valido`). v06-v08 y
golden fallan (dependen del puntaje, que usa `cuil_valido`). El patrón es
direccional: la rotura se propaga hacia adelante por dependencia real del
pipeline, no por acoplamiento de los verificadores.

**Corrida después de revertir:** `git checkout -- herramientas/gen_workflow.py`,
10/10 PASA (662s):

```
  Verif    Estado   Tiempo   Detalle
  -------------------------------------------------------------
  v00      PASA        0s   RESULTADO: PASA (10 checks)
  v01      PASA        0s   RESULTADO: PASA (25 checks)
  v02      PASA        0s   RESULTADO: PASA (22 checks)
  v03      PASA        0s   RESULTADO: PASA (29 checks)
  v04      PASA        0s   RESULTADO: PASA (18 checks)
  v05      PASA      201s   RESULTADO: PASA (51 checks)
  v06      PASA       32s   v06_puntaje: 24/24 PASA
  v07      PASA       74s   v07_salida: 23/23 PASA
  v08      PASA       39s   v08_reporte: 31/31 PASA
  golden   PASA       43s   SHA-256 coincide com=9a6884603f91... aud=ae6fcc5f146d...
  -------------------------------------------------------------
  Suite de regresion: 10/10 PASA  (total 662s)
```

**2026-07-28 — F08 cerrada.** Workflow `09-reporte` (8 nodos Code + 3 ramas de
salida: CSV comercial, CSV auditoría, reporte Markdown). Genera automáticamente
`reporte_f08.md` con todas las métricas recalculadas desde el CSV.

**Métricas del reporte (sobre CSV sintético de 200 filas):**
- 200 contactos procesados, 186 únicos (14 duplicados)
- **86 llamables** (48 alta + 38 media)
- **114 descartados**: 82 sin teléfono, 14 duplicados, 39 fuera de zona, 3 por
  puntaje bajo (un contacto puede tener más de un motivo)
- **7.6 horas de operador ahorradas** (supuesto: 4 min/llamada)
- Costo hora operador: "a definir con el cliente" (CONFIG = 0)

**Descartes separados por tipo** (como mandaba la nota de ESTADO.md): calidad de
dato (teléfono, duplicado) vs zona de cobertura (supuesto nuestro). La separación
es explícita en el reporte con dos subtablas.

**Supuestos visibles junto al número:** cada supuesto lleva la marca *(supuesto)*
en la misma fila de la tabla, no en notas al pie. El reporte cierra con la
pregunta sugerida para el cliente.

**Arquitectura:** `gen_workflow.py` refactorizado para soportar N ramas de salida
(antes hardcodeado a 2). El dict `salida_dual` ahora acepta N entradas; `build()`
itera sobre las que tienen path asignado. Nuevo argumento `--reporte-out`.

Verificador `v08_reporte.py`: **31/31 PASA** (3 archivos generados, CSVs intactos
con distribución correcta, 11 métricas del reporte comparadas contra recálculo
independiente desde CSV, supuestos visibles, porcentajes, secciones, fecha de
corte, separación calidad/zona).

**2026-07-28 — F07 cerrada.** Workflow `08-salida` (8 nodos Code: F00–F06 +
ordenamiento, más salida dual con branching). Dos archivos CSV con BOM UTF-8:

- **Comercial** (`salida_f07_comercial.csv`): 9 columnas (nombre, cuil, telefono,
  localidad, origen, fecha_carga, puntaje, prioridad, motivo). 200 filas.
- **Auditoría** (`salida_f07_auditoria.csv`): 26 columnas del pipeline. 200 filas.

**Orden (clave de 4 partes):** bloque prioridad (alta→media→descartado), puntaje
desc, dias_antiguedad asc (vacíos al final), id_fila. Los bloques aseguran que
un descartado con puntaje 85 NO aparezca antes de un alta con puntaje 70.

**Distribución invariante:** alta 48, media 38, descartado 114 (sin cambios
respecto a F06).

**Arquitectura:** el nodo de ordenamiento ordena in-place y conecta a DOS ramas
paralelas: una genera el CSV comercial (Code node con `Buffer` + BOM), la otra
el de auditoría. Cada rama escribe su archivo directamente. No se usa
`convertToFile` de n8n — el CSV se genera a mano para controlar BOM (EF BB BF)
y line endings (LF, no CRLF).

**Determinismo:** dos corridas producen archivos byte a byte idénticos (SHA-256).

Verificador `v07_salida.py`: **23/23 PASA** (conteo, distribución, orden fila por
fila, oráculo Python, alineación entre archivos, determinismo, BOM, encoding,
bloques, empate triple).

**2026-07-28 — Corrida adversaria.** Tres archivos pasados por el pipeline F06
sin tocar código. Resultados en `salidas/HALLAZGOS_ADVERSARIO.md`.

| Gravedad | Cantidad |
|----------|----------|
| rompe | 1 (archivo 2: basura arriba del header crashea el parseo CSV) |
| silencioso | 10 (6 formatos de tel no reconocidos, 2 localidad, 1 dedup, archivo 3 completo) |
| cosmético | 2 (artefactos de Excel sin motivo específico) |

**Los tres hallazgos más graves:**
1. **Archivo 3** (separador `;`): output con cara de correcto, 5 filas vacías con puntaje -10. Un cliente no se enteraría.
2. **T02** (`+54 9 11 4161 7956`): un espacio pierde un celular válido.
3. **T05** (`15-4161-7956`): aceptado como ambiguo (debería ser inválido), el contacto se llamaría a un número equivocado.

Cero cambios en `workflows/` y `verificadores/`.

**Decisión (2026-07-28): los 13 hallazgos NO se corrigen ahora.** Entran como
casos de la suite de regresión en **F09**. Motivo: la cadena de fases y los
verificadores en verde valen más que arreglar la demo; corregir F01 obligaría a
re-correr y re-verificar F01→F06 completo. Contra aceptada, escrita para no
olvidarla: mientras tanto la demo sigue perdiendo T02 (`+54 9 11 …`) y
aceptando T05 (`15-…`) como ambiguo con un número normalizado incorrecto. **Si
se muestra el pipeline a alguien antes de F09, no usar un archivo con esos
formatos.**

**2026-07-28 — F06 cerrada.** Workflow `07-puntaje` (7 nodos Code: F00–F06),
generado con `gen_workflow.py --fase 06 --fecha-corte 2026-07-28`. Escribió
`salidas/salida_f06.csv`. Agrega `puntaje` (entero), `prioridad`
(alta/media/descartado), `motivo` (suma auditable). 200 filas.

**Pesos usados (propuesta de arranque):** celular +30, fijo +10, ambiguo +18,
CUIL válido +15, CUIL inválido −10, en zona +20, frescura alta/media/baja/fría
+25/+15/+5/+0, referido +15, formulario web/evento +10, campaña Meta +5, base
propia +0. Descartes directos: teléfono inválido, fuera de zona, duplicado.
Umbrales: alta ≥ 70, media 40–69, descartado < 40 o descarte directo.

**Distribución:** alta **48**, media **38**, descartado **114** (82 sin teléfono,
39 fuera de zona, 14 duplicados — con superposiciones). Puntaje máximo 100
(celular+cuil ok+zona+alta+formulario web), mínimo 0.

**Formato del motivo:** cada regla deja `label +N` o `label −N`; descartes
directos: `label +0 → descarte`. La suma de los números del motivo da exactamente
el puntaje — verificado fila por fila por el oráculo Python.

**CONFIG** vive en un solo objeto al inicio del nodo Code. Cambiar un peso o
umbral no requiere tocar la lógica.

Verificador `v06_puntaje.py`: **24/24 PASA** (ejecuta n8n, oráculo independiente,
auditabilidad 200/200, consistencia de descarte, distribución exacta, CONFIG en
workflow).

**2026-07-28 — CORRECCIÓN F05.** Reescrito el nodo `Antiguedad del lead` y el
verificador `v05_antiguedad.py`. Cinco cambios:

1. **`fecha_corte` es parámetro real.** `gen_workflow.py` toma `--fecha-corte`;
   si no se pasa, el JS usa `new Date()` **sólo** para fijar el default (nunca
   dentro del cálculo). La fecha efectiva se escribe en `fecha_corte_usada` en
   cada fila, para que el CSV sea auditable sin saber qué día se generó.

2. **El verificador ejecuta n8n de verdad** — 5 corridas:
   - A y B (corte 07-28, misma entrada): **hash SHA-256 idéntico** → determinismo
     real, no oráculo contra sí mismo.
   - C (corte 07-29): alta 34, media 44, baja 68, fría 54. `id_fila 103`
     (Emilia Núñez, 2026-07-13) cruza de **alta** (15 días) a **media** (16).
   - D (corte 09-30): alta **0**, media **0**, baja 43, fría 157. Dos tramos
     vacíos, la prueba más fuerte de que el parámetro llega al nodo.
   - Adversario (`leads_adversario_1.csv`): 48 filas, 0 excepciones, T32–T38
     exactos (ver abajo).

3. **Soporte `dd/mm/aaaa`** (día primero, Argentina). Se marca `fecha ambigua`
   cuando ambos componentes ≤ 12. Criterio declarado: **día primero siempre**.
   `10/04/2026` → 10 de abril. No se adivinan meses en texto ni años de 2 dígitos.

4. **Matar el centinela `-1`.** Una fecha no parseable da `dias_antiguedad`
   **vacío** (no `-1`). Las fechas futuras conservan su negativo real (`-68`,
   `-171`): el dato existe y es informativo (typo del operador, no dato faltante).

5. **Date.UTC.** Todas las fechas se construyen con `Date.UTC(y, m-1, d)` en
   vez de `new Date(y, m-1, d)`. Evita que un cambio de horario de verano (en
   otra zona; Argentina no tiene DST desde 2009) haga que `Math.floor` pierda
   una hora y un contacto salte de tramo.

**Columnas nuevas:** `motivo_frescura` (vacía si todo OK; `fecha vacia`, `fecha
ilegible`, `fecha ambigua`, `fecha futura`, acumulables con `; `),
`fecha_corte_usada`. Los conteos del CSV principal **no se movieron**: alta 39,
media 42, baja 65, fría 54.

**Checks viejos borrados** (no comentados): los 3 que comparaban el oráculo
contra sí mismo (determinismo Python, redistribución Python, fechas malformadas
Python). Los unit tests del oráculo que quedan llevan prefijo `(oraculo)`.

**Adversario T32–T38 (ejecutados en n8n):**

| fila | fecha_carga  | dias | frescura | motivo_frescura               |
|------|-------------|------|----------|-------------------------------|
| T32  | 10/04/2026  | 109  | fría     | fecha ambigua                 |
| T33  | 04/10/2026  | -68  | sin dato | fecha ambigua; fecha futura   |
| T34  | 10-abr-26   | ''   | sin dato | fecha ilegible                |
| T35  | *(vacío)*   | ''   | sin dato | fecha vacia                   |
| T36  | 2026-13-45  | ''   | sin dato | fecha ilegible                |
| T37  | 2027-01-15  | -171 | sin dato | fecha futura                  |
| T38  | 2019-03-02  | 2705 | fría     | *(vacío)*                     |

Verificador `v05_antiguedad.py`: **51/51 PASA**.

**2026-07-28 — F05 cerrada (original, antes de corrección).** Conteos: alta 39,
media 42, baja 65, fría 54. Rango 0–109 días. Los 4 tramos poblados.

**2026-07-28 — Propagación de F02 a F03 y F04.** Regenerados `04-dedup.json` y
`05-cobertura.json` desde `gen_workflow.py` (que ya llevaba la regla corregida),
reimportados y reejecutados. `salida_f03.csv` y `salida_f04.csv` ahora muestran
181 válidos / 19 inválidos, consistente con `salida_f02.csv`. Verificadores
v03 (29/29) y v04 (18/18) sin cambios, siguen en PASA. v00, v01, v02 también
en verde — suite completa OK.

**2026-07-27 — CORRECCIÓN F02: `resto 1 → inválido`.** Se cambió una línea del
nodo `Validar CUIL` (antes `resto 1 → DV 9`). Motivo: un CUIL con resto 1 y su
propio prefijo no existe bajo AFIP (reemite con 23), y las reemisiones validan
solas con el algoritmo simple —verificado por fuerza bruta, 27 272/27 272 fem y
27 273/27 273 masc—. Se **borró** la consecuencia falsa que decía que un
`23-DNI-4` femenino caería inválido (es al revés: valida bien). Se regeneró,
reimportó y reejecutó **sólo** `03-cuil.json`. Clasificación nueva: **181
válidos / 19 inválidos** por resto 1 (el CSV se generó con la regla vieja).
`cuil_dudoso` ahora marca los rechazados por resto 1 (mismos 19, todos
inválidos). Verificador `v02_cuil.py` reescrito con esperados exactos: **22/22
PASA**; el test del medio ahora rompe el 100 % (desapareció la colisión resto
1↔2). Typos no detectados: **1,58 % → 0 %** (confirmado con `medir_typos.py`).
**F03/F04 no se tocaron**: siguen en verde (no dependen de `cuil_valido`), pero
hay que regenerarlos en su sesión para propagar la regla. Ver "Limitaciones
conocidas → F02".

**2026-07-27 — F04 cerrada.** Workflow `05-cobertura` (nodo Code `Completitud y
cobertura`), generado con `gen_workflow.py --fase 04`. Escribió
`salidas/salida_f04.csv`. Agrega `en_zona` (bool), `marcado` (bool) y
`motivo_descarte` (texto en castellano, motivos separados por `; `). 200 filas.
Verificador `v04_cobertura.py`: **18/18 PASA**.

**Conteos medidos:** 39 fuera de zona · 82 sin teléfono utilizable · 0 sin
nombre (el CSV no tiene campos vacíos) · **106 marcados** (unión) · 15 acumulan
dos motivos (sin teléfono + fuera de zona). La zona (`CONFIG.zona`) vive en un
solo lugar arriba del nodo; el verificador corre el oráculo con tres listas
(la real → 39 fuera, las 10 → 0, vacía → 200) para probar que es parámetro. La
comparación de localidades normaliza tildes/mayúsculas/espacios (probado con 5
variantes de "Morón"). La separación zona vs calidad para F08 ya está lista:
`en_zona` (zona) y `telefono_tipo=invalido` (calidad).

**2026-07-27 — F03 cerrada.** Workflow `04-dedup` (nodo Code `Marcar
duplicados`), generado con `gen_workflow.py --fase 03`. Escribió
`salidas/salida_f03.csv`. Agrega `id_fila` (posición original 1..200, estable),
`telefono_match`, `es_duplicado`, `duplicado_de`, `motivo_duplicado`. Nada se
borra: siguen saliendo **200 filas**. Verificador `v03_dedup.py`: **29/29 PASA**.

**Conteos medidos:** 14 duplicados por CUIL · 8 por teléfono (clave de match) · 6
por teléfono crudo entre utilizables · 11 filas 100 % idénticas. Los **2 extra
(8 vs 6)** aparecen sólo al normalizar: prueba de que F01 sirve. **Conjunto
unión = 14** (los 8 pares por teléfono están contenidos en los 14 por CUIL; en
esta muestra phone ⊆ cuil, todos los grupos son de tamaño 2).

**Decisión de Pedro — match por 10 dígitos nacionales.** Se agrupa por
`telefono_match` = últimos 10 dígitos de `telefono_norm` (ignora el 9 del
celular), **no** por el canónico completo. Fundamento: en AMBA un mismo
`11-XXXX-XXXX` es una sola línea; el 9 marca el tipo, no la identidad. Así un
celular (`+549…`) y el mismo número pelado (ambiguo) colapsan. `telefono_norm`
de F01 queda intacto; `telefono_match` es derivado. Los inválidos tienen match
vacío y **no se agrupan entre sí**. *Contra aceptada:* un fijo y un celular que
compartan los 10 dígitos también colapsan (raro). Con esta clave el conteo sigue
dando **8**.

**Adopción de tipo.** El ganador de un grupo adopta el `telefono_tipo` más
específico de su misma línea, precedencia **celular > fijo > ambiguo**. Si el
ganador vino `ambiguo` pero otro de su línea era `celular`, queda `celular`.

**Qué NO ejercita la muestra** (implementado y unit-testeado igual, para datos
reales): el desempate del ganador por `fecha_carga`/completitud (los 14 pares
empatan y se deciden por posición) y la adopción de tipo (0 líneas con tipos
mixtos en la muestra).

**2026-07-27 — F02 cerrada.** Workflow `03-cuil` (nodo Code `Validar CUIL`
después de F01), generado con `gen_workflow.py --fase 02`. Escribió
`salidas/salida_f02.csv` con `cuil_norm` (11 dígitos string) y `cuil_valido`
(bool). Verificador `v02_cuil.py`: **17/17 PASA**.

**Módulo 11 calibrado contra los 200:** pesos `5 4 3 2 7 6 5 4 3 2`, resto de 11;
`resto 0 → DV 0`, **`resto 1 → DV 9`** (caso especial), resto → `11 − resto`. La
variante ingenua (siempre `11 − resto`) rechaza los 19 de resto 1. Los 200 dan
válidos (cero falsos inválidos). Prefijos en la muestra: 20/23/24/27; el nodo
soporta también 30/33/34. Hallazgo del módulo 11: `resto 1` y `resto 2` mapean
ambos a DV 9 (única colisión), así que cambiar un dígito del medio no siempre
invalida; por eso el test fuerte de rechazo flipa el dígito verificador
(1800/1800 inválidos) y el del medio exige que exista al menos una mutación que
rompa cada CUIL (rompe el 98,4%).

**2026-07-27 — F02: agregado `cuil_dudoso` y documentada la limitación.** Se
agregó el campo `cuil_dudoso` al nodo (marca los 19 casos de resto 1), se
regeneró/reejecutó el workflow y se extendió el verificador (ahora **21/21
PASA**). La clasificación de `cuil_valido` no cambió (200 válidos). Detalle en
"Limitaciones conocidas → F02". Los dos números quedaron reproducidos de forma
independiente: 1,58 % con la regla vieja y 0 % con la corregida.

**2026-07-27 — F01 cerrada.** Workflow `02-telefono` (7 nodos: pasamanos + nodo
Code `Normalizar teléfono`), generado extendiendo `gen_workflow.py` (ahora toma
`--fase`). Corrió en n8n 2.31.7 por CLI; escribió `salidas/salida_f01.csv` con
dos columnas nuevas (`telefono_norm`, `telefono_tipo`), sin tocar `telefono`.
Verificador `v01_telefono.py`: **25/25 PASA**. Conteos reales: celular 42, fijo
45, ambiguo 31 → **118 utilizables**; truncados 41 + texto 41 → **82 inválidos**.
Los 45 fijos son 43 con `011-…` + 2 con `011…` sin guión.

**Canónico elegido** (conserva el 9 sólo en celular, para que F03 no fusione un
fijo con un celular de mismos 8 finales):
- celular → `+549` + 10 nacionales (`+5491139927555`)
- fijo → `+54` + 10 nacionales (`+541141617956`)
- **ambiguo (10 dígitos pelados) → `+54` + los 10 dígitos** (`+541168442737`).
  No se afirma móvil; si coincide con un fijo real, colapsan, y eso es correcto.
- inválido → `""` (vacío exacto, nunca `"undefined"` ni `"+549"`).

**2026-07-27 — SETUP en la máquina de Pedro (Windows 11).** Versiones que
quedaron: Node v24.18.0 (mín. 20), npm 11.16.0 (mín. 10), Python 3.12.10
(mín. 3.10), git 2.55.0. Todo cumple; no hubo que instalar nada aparte. n8n
no se instala global: se corre con `npx n8n` (primera vez descarga). Se agregó
`arrancar-n8n.ps1` en la raíz para no tipear `N8N_RESTRICT_FILE_ACCESS_TO` cada
vez. Los verificadores andan con biblioteca estándar (`csv`, `pathlib`), sin
dependencias. **Ojo:** `salidas/` está vacío en esta máquina — el F00 marcado
como cerrado abajo corrió en OTRA máquina; falta la corrida de confirmación en
Windows (es el trabajo de la sesión F00, no del setup).

**2026-07-27 — F00 confirmada en Windows.** Corrió sobre n8n 2.31.7 por CLI
(`npx n8n import:workflow` + `npx n8n execute --id=f00pasamanos001`), no por el
navegador — así se evita la cuenta de owner y es la misma vía que usará F09. Las
rutas embebidas en el JSON ya coincidían con esta carpeta, no hubo que
regenerar. Se escribió `salidas/salida_f00.csv` (200 filas, UTF-8 con BOM).
`v00_pasamanos.py`: **10/10 PASA**, exit 0. Nada que ajustar. Nota operativa: hay
que parar el server de n8n antes de correr el CLI, o la base SQLite queda
bloqueada.

**2026-07-27 — F00 cerrada.** Workflow `01-pasamanos` de 6 nodos, generado con
`herramientas/gen_workflow.py`. Ejecutado en n8n 2.31.7: 200 items adentro,
200 afuera, todas las celdas idénticas. Verificador `v00_pasamanos.py`: 10/10.

Tres hallazgos del entorno, todos comprobados ejecutando:
1. n8n 2.x bloquea el disco fuera de `~/.n8n-files`. Hay que setear
   `N8N_RESTRICT_FILE_ACCESS_TO` antes de arrancar. Está en el README.
2. `n8n execute --file` ya no existe: se importa y se ejecuta por `--id`, y el
   JSON necesita campo `id`. Esto define cómo va a correr F09.
3. La "trampa" de inferencia de tipos que había documentado **es falsa** en
   2.31.7: `extractFromFile` entrega los 6 campos como string y los ceros
   iniciales sobreviven sin el nodo Code. El nodo queda como guardarrail, no
   como arreglo.

_(una línea por fase cerrada: qué se construyó y qué número dio el verificador)_
