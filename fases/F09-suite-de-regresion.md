# F09 — Suite de regresión

## Objetivo
Un solo comando que corre los verificadores v00 a v08 y dice pasa o falla. Es la
red que permite tocar el workflow sin miedo cuando aparezca el primer cliente.

## Qué construir
- `verificadores/correr_todo.py` — ejecuta cada verificador, junta resultados,
  imprime una tabla y devuelve exit code 1 si alguno falla.
- Un **golden file**: la salida esperada del CSV de prueba con fecha de corte
  fija, congelada en `salidas/golden_2026-07-28.csv`. Cualquier diferencia
  contra el golden es un cambio de comportamiento y hay que justificarlo.
- Un README de dos párrafos: cómo correr n8n, cómo correr la suite.

## Criterio de aceptación
1. `python verificadores/correr_todo.py` corre todo y devuelve exit code correcto.
2. Romper a propósito una regla del workflow hace fallar al verificador
   correspondiente, y **solo** a ese. Si falla todo, los verificadores están
   acoplados y hay que separarlos.
3. La tabla de salida dice qué falló y con qué número, no solo "FAIL".
4. El golden está versionado junto con el JSON del workflow que lo produjo.

## Por qué esta fase importa más de lo que parece
Es lo que separa "hice un script" de "tengo un producto". Cuando un cliente pida
un cambio de pesos, esto es lo que confirma en 10 segundos que no se rompió nada
más. Y es exactamente el método que ya funcionó en el videojuego.
