# F05 — Antigüedad del lead

## Objetivo
Convertir `fecha_carga` en un valor de frescura utilizable por el puntaje.

## Reglas
- **Fecha de corte parametrizada.** Nunca `new Date()` dentro del nodo. El
  workflow recibe la fecha de referencia como parámetro; por defecto, hoy.
  Motivo: sin esto, el mismo CSV da resultados distintos según el día y ningún
  verificador puede ser determinista.
- Decaimiento por tramos, no lineal continuo: es más fácil de explicar en una
  reunión y de auditar.

Tramos propuestos (a confirmar con Pedro en F06):

| Antigüedad        | Frescura |
|-------------------|----------|
| 0 a 15 días       | alta     |
| 16 a 45 días      | media    |
| 46 a 90 días      | baja     |
| más de 90 días    | fría     |

Rango real del CSV de prueba: 2026-04-10 a 2026-07-28, o sea ~110 días. Con
fecha de corte 2026-07-28 los cuatro tramos quedan poblados, que es justo lo que
hace falta para probarlos.

## Criterio de aceptación
1. Los 200 items tienen `dias_antiguedad` y `frescura`.
2. Con fecha de corte fija, correr el workflow dos veces da resultados idénticos.
3. Cambiar la fecha de corte mueve contactos de tramo de forma predecible.
4. Fechas malformadas o vacías -> `frescura` sin dato + motivo, nunca un crash.
5. Los cuatro tramos tienen al menos un contacto con el CSV de prueba.

## Verificador
`verificadores/v05_antiguedad.py` — corre dos veces con la misma fecha de corte y
compara hashes de salida (determinismo), y verifica el poblado de los 4 tramos.
