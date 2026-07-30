# F07 — Salida ordenada

## Objetivo
Dos archivos con las mismas 200 filas en el mismo orden: el **comercial**
(6 columnas originales + `puntaje`, `prioridad`, `motivo`) y el de **auditoría**
(las 26 columnas del pipeline). De mejor a peor.

## Reglas
- **Orden (decidido 2026-07-28):** bloque de prioridad `alta` → `media` →
  `descartado`; dentro del bloque `puntaje` descendente; empate →
  `dias_antiguedad` ascendente (más reciente primero, vacíos al final); empate
  de nuevo → `id_fila` (orden original del archivo, estable y reproducible).
  - *No es orden puro por puntaje.* 92 de los 114 descartados puntúan ≥ 40 y
    cinco llegan a 70–85: con orden puro, un descartado queda arriba de un alta
    real y el operador llama primero al que no hay que llamar.
  - El desempate por antigüedad usa `dias_antiguedad` (normalizado en F05), no
    el string de `fecha_carga`: `dd/mm/aaaa`, fechas ilegibles y vacías rompen
    la comparación de texto.
- Las columnas originales salen **idénticas a como entraron**.
- Los campos derivados no van al archivo comercial: viven en el de auditoría,
  fila por fila alineado por `id_fila`.
- `motivo` legible por un humano no técnico: es lo que va a leer un supervisor
  de call center cuando pregunte "¿y este por qué quedó abajo?".

## Criterio de aceptación
1. Filas de salida == filas de entrada == 200, en los dos archivos. Ninguna se
   perdió, ni siquiera las descartadas.
2. La distribución no se movió: alta 48, media 38, descartado 114.
3. El orden cumple la clave de 4 partes, comprobado fila por fila.
4. Correr el workflow dos veces con la misma entrada y la misma fecha de corte
   da archivos byte a byte idénticos.
5. Abre bien en Excel: UTF-8 con BOM, saltos `\n`, tildes intactas.
6. Un descartado leído por alguien ajeno al proyecto se entiende sin explicación.

## Verificador
`verificadores/v07_salida.py` — conteo, distribución, orden (recorrido del CSV
de n8n **y** comparación contra oráculo independiente), alineación entre los dos
archivos, determinismo entre dos corridas, y encoding. Más un caso chico armado
a mano con empate triple y `dias_antiguedad` vacío.
