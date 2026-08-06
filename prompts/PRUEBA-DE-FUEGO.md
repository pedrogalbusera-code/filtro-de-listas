Estás trabajando en este repo. Antes de tocar nada, leé `CLAUDE.md`, `ESTADO.md`,
`fases/PRUEBA-DE-FUEGO.md` completo, `fases/F11-puerta-de-entrada.md` (el truco de
equivalencia y el mapeo de columnas) y `fases/F14-lista-negra-optout.md` (la baja).

# Prueba de fuego — el pipeline entero sobre un archivo como lo manda un cliente

## Qué es en una línea

La prueba de integración de todo lo construido, de punta a punta, sobre un archivo **sucio y
realista** (`;`, columnas renombradas, basura arriba, teléfonos en cualquier formato,
localidades con paréntesis y vacías, basura, un duplicado, una jurídica, un opt-out). No es
un filtro nuevo: no se escribe **ni un nodo nuevo**. Se resuelve con **config**.

## Antes de escribir una sola línea

Entorno como siempre (Node 20+, Python 3.10+, n8n con `npx n8n`,
`N8N_RESTRICT_FILE_ACCESS_TO` a esta carpeta). Depende de que todo lo anterior esté cerrado
y el golden exista. Si algo falta, frená y decilo.

## La regla que manda

> Si escribís lógica de nodo nueva, esta fase salió mal.

El objetivo es exactamente el opuesto: probar que un archivo de cliente entero se procesa
agregando **solo** un mapeo de columnas y las decisiones comerciales del cliente en
`config/`. Si te encontrás editando un nodo Code para que el archivo pase, esa es la señal de
que hay un filtro incompleto — **frená y mostrámelo**, no lo parchees adentro de esta fase.

## Qué construir (todo es data + config + verificador)

1. **El archivo sucio** `data/leads_fuego_1.csv` y su **gemelo limpio**
   `data/leads_fuego_1_limpio.csv` — mismas filas y mismos valores de celda, el gemelo en
   forma canónica (coma, UTF-8 sin BOM, header fila 1, columnas canónicas). La tabla de filas
   firma G01–G15 está en `fases/PRUEBA-DE-FUEGO.md`: metelas todas, más ~unas filas limpias
   de relleno hasta ~25–30. El principal va en `;` con 2–3 filas de basura arriba **a
   propósito** (ese combo lo maneja `leerTabla()`).
2. **La baja** `data/lista_baja_fuego.xlsx` (header en fila 1, sin basura arriba — el path de
   planilla) con el teléfono/CUIL de G15.
3. **El config del cliente**: `config/mapeo_fuego.json` (columnas del cliente → canónicas,
   como `mapeo_adversario2.json`) y la segmentación del cliente (`etiquetar:true,
   descartar:"juridica"` — vende a individuos).
4. **El verificador** `verificadores/v_fuego.py`, cuatro bloques (ver la fase). Corre n8n de
   verdad; esperados de las celdas firma **literales a mano**, no contra un oráculo.

## Los cuatro criterios (detalle completo en la fase)

1. **Equivalencia:** sucio → salida byte a byte idéntica a limpio → salida, en comercial +
   auditoría + **reporte**. Misma baja y mismas configs en las dos corridas; solo cambia el
   principal. La ficha difiere a propósito y se chequea aparte.
2. **Celdas firma G01–G15** por el nodo real, esperado literal (la tabla de la fase).
3. **Reporte coherente:** las **cuatro** categorías de descarte con conteo ≥ 1 (calidad de
   dato, zona, segmento, opt-out), las subtablas suman al total, y el ahorro con
   `minutos_por_llamada: 4`.
4. **Ficha del sucio:** separador `;`, fila real del header, y el mapeo de columnas.

## Prohibido

- **Escribir lógica de nodo nueva.** Si un caso no pasa, es un filtro incompleto: frená y
  mostrame, no lo parchees acá.
- Que el gemelo limpio tenga **valores** distintos del sucio. La única diferencia es la
  superficie (separador, header, nombres de columna, encoding, tipo de archivo).
- Verificar las celdas firma contra un oráculo que replique el nodo. Literales a mano.
- Mover el golden del canónico. La prueba de fuego corre sobre sus propios archivos.
- Meter basura arriba en el `.xlsx` de la baja (limitación conocida de `leerPlanilla()`): el
  principal es el que lleva basura, y va en CSV.
- Un archivo de 200 filas. ~30 alcanzan; el archivo real grande es otro paso.

## Terminado cuando

`python verificadores/v_fuego.py` verde en los cuatro bloques, `python
verificadores/correr_todo.py` sigue verde, el golden del canónico intacto, y existen los
cuatro archivos nuevos (`leads_fuego_1.csv`, `leads_fuego_1_limpio.csv`,
`lista_baja_fuego.xlsx`, `config/mapeo_fuego.json`).

En `ESTADO.md`: el número del reporte de la prueba de fuego (entraron / quedan / ahorro en
horas) y la confirmación de que se resolvió **solo con config**, sin código de nodo nuevo.
Si algún caso obligó a tocar un nodo, anotá cuál y por qué — eso es un filtro incompleto que
encontró la prueba de fuego, y es el próximo trabajo.

---

## Qué sigue

Con la prueba de fuego en verde, el **Nivel 1 queda cerrado de punta a punta** sobre un
archivo de cliente: es el capstone que la hoja de ruta pedía para pasar de "procesá mi CSV" a
"procesá el tuyo". Lo que queda es opcional (F15 historial) o de trámites (Nivel 2), y la
prueba con un **archivo real** cuando un cliente traiga uno.
