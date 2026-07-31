Estás trabajando en este repo. Leé `CLAUDE.md`, `ESTADO.md`,
`salidas/HALLAZGOS_ADVERSARIO.md` y `data/TRAMPAS.md` antes de tocar nada.

# Pendientes conocidos — los hallazgos adversarios entran a la suite

Sesión corta. **No se arregla ningún bug.** Se registra el comportamiento actual
de cada hallazgo para que la suite avise si cambia sin que nadie lo documente.

## El problema

Los 13 hallazgos de `salidas/HALLAZGOS_ADVERSARIO.md` son bugs conocidos que se
decidió no arreglar (decisión del 2026-07-28 en `ESTADO.md`). Si los metés como
tests normales, la suite queda roja para siempre y en dos semanas la ignorás. Si los
marcás "skip", no prueban nada.

Van como **pendientes conocidos**: cada caso declara el comportamiento **correcto
esperado** y el comportamiento **actual medido**. La suite los corre siempre y los
reporta en su propia sección.

| Qué pasa con un pendiente | Qué hace la suite |
|---|---|
| Sigue fallando igual que lo medido | Verde. Lo lista y sigue. |
| **Empieza a pasar** | **ROJA.** Cambió el comportamiento y nadie lo documentó. |
| Falla **distinto** a lo medido | **ROJA.** Mismo motivo. |

Sacar un pendiente del registro es una acción manual, nunca automática.

## Qué construir

### 1. El registro

Un archivo de datos (JSON o Python, elegí y justificá en una línea) con los **9
hallazgos de fila del archivo 1**:

- Teléfonos: T01, T02, T03, T04, T05, T10
- Localidad: T19, T21
- Dedup: T31

Cada entrada: `id`, `entrada` (el valor crudo), `esperado_correcto` (qué debería
pasar), `actual_medido` (qué pasa hoy), y una línea de por qué importa.

Los valores de `actual_medido` **salen de correr el pipeline, no de copiarlos de
`HALLAZGOS_ADVERSARIO.md`**. Ese documento es del 28 y desde entonces cambió el
código: si algún valor no coincide con lo que da hoy, **pará y mostrámelo antes de
escribirlo** — significa que un hallazgo cambió sin que nadie lo notara, y eso es el
resultado más valioso de esta sesión.

### 2. El verificador

`verificadores/v09_pendientes.py`. Corre `data/leads_adversario_1.csv` por el
pipeline (fase 08, fecha de corte 2026-07-28), compara cada caso contra su
`actual_medido` y aplica las tres reglas de la tabla de arriba.

### 3. Integrarlo a la suite

`correr_todo.py` lo corre y lo reporta en **su propia sección**, con su propio
conteo. No lo mezcles en el 10/10: la suite tiene que seguir diciendo cuántos checks
de regresión pasa y, aparte, cuántos pendientes conocidos hay y en qué estado.

### 4. Los que NO van acá

- **Archivo 2** (basura arriba del header, crashea el parseo) y **archivo 3**
  (separador `;`): son trabajo de **F11**, entrada de archivo del cliente.
  Registralos en `ESTADO.md` como pendientes marcados `F11` y no los toques.
- Los 2 cosméticos (T08 `.0` de Excel, T09 notación científica): opcionales. Si los
  agregás, que sea en el mismo registro.

## Criterio de aceptación

1. La suite corre y reporta los pendientes en su propia sección, sin mezclarlos con
   los checks de regresión.
2. Romper a propósito **el arreglo** de un pendiente —o sea, arreglar el bug— pone
   la suite en rojo con el mensaje de "un pendiente empezó a pasar". Probalo de
   verdad con uno, **pegá el output**, revertí.
3. `ESTADO.md` queda con la lista de los 13, cuáles quedaron registrados, cuáles son
   de F11 y cuáles se dejaron afuera.
4. Commit propio.

## Prohibido

- Arreglar cualquiera de los hallazgos.
- Tocar `gen_workflow.py` salvo para la prueba del punto 2, que se revierte.
- Copiar los valores medidos desde `HALLAZGOS_ADVERSARIO.md` sin verificarlos
  corriendo el pipeline.
- Avanzar a F10.

## Terminado cuando

Los 9 casos están registrados con su valor medido hoy, la suite los reporta aparte,
la prueba del punto 2 está en `ESTADO.md` con el output pegado, y hay commit.
