# Prompts para Claude Code — una fase por sesión

Cada archivo `FXX.md` de esta carpeta **es** el prompt. Se copia entero y se
pega en Claude Code, en una sesión nueva, parado en la carpeta del proyecto.

## Qué adjuntar: nada

Claude Code lee el repo solo. Abrís una terminal **parada en esta carpeta**,
corrés `claude`, y pegás el prompt. Lee `CLAUDE.md` automáticamente, y el propio
prompt le dice que abra `ESTADO.md` y el documento de su fase.

No adjuntes archivos sueltos ni le pegues el contexto a mano: si el contexto
vive en el repo, todas las sesiones ven lo mismo y `ESTADO.md` es la única
fuente de verdad sobre qué está cerrado.

## El ciclo

```
sesión nueva de Claude Code
   -> pegar prompts/FXX.md
   -> Claude Code construye y corre su verificador
   -> vos revisás el diff y el output del verificador
   -> si pasa: cerrar la fase, siguiente
   -> si no pasa: no avanzar
```

**No pegues dos fases en la misma sesión.** El motivo no es ceremonia: cuando
algo falla en F03, querés saber si lo rompió F03 o si venía roto de F02. Si las
dos se construyeron juntas, no lo podés saber.

## Qué revisás vos en cada fase

1. Que el verificador **corra y dé verde**, no que Claude Code diga que da verde.
   Corrélo vos: `python verificadores/vXX_*.py`.
2. Que los números del verificador sean los del CSV de prueba, no números que
   Claude Code ajustó para que pasen. Si un verificador espera "más de 0
   duplicados" en vez de "8 duplicados", el verificador está domesticado.
3. Que `ESTADO.md` haya quedado actualizado con lo que pasó.

### Tres formas de check que parecen prueba y no prueban nada

Aparecieron de verdad revisando F01. Buscalas en cada verificador:

- **El check tautológico.** `all(f(x) == f(x))` para comprobar que una función
  es determinista. Compara algo consigo mismo: pasa siempre, por construcción.
  El determinismo real se prueba **corriendo el workflow dos veces** y
  comparando las dos salidas.
- **El caso trampa probado contra el oráculo y no contra n8n.** Si el
  verificador reimplementa la regla en Python y después prueba el caso difícil
  llamando a su propia función, no probó el nodo Code. El caso difícil tiene que
  estar **en los datos** o entrar por una corrida real.
- **El oráculo transliterado.** Reimplementar la regla en Python línea por
  línea desde el mismo JS, en la misma sesión, no es una segunda opinión: es la
  misma opinión escrita dos veces. Atrapa que n8n corrompa un valor al escribir
  el CSV, que no es poco, pero **no atrapa que la regla esté mal pensada**. Eso
  lo tenés que mirar vos.

## Orden

| # | Prompt | Qué es | Estado |
|---|--------|--------|--------|
| 0 | `SETUP.md` | Entorno, una sola vez | cerrado |
| 1 | `F00.md` | Entorno y pasamanos | cerrado |
| 2 | `F01.md` | Normalización de teléfono | cerrado |
| 3 | `F02.md` | Validación de CUIL | cerrado |
| 4 | `F03.md` | Deduplicación | cerrado |
| — | `CORRECCION-F02.md` | Arregló la regla del CUIL y borró un dato mal documentado | cerrado |
| — | **`PROPAGACION-F03-F04.md`** | **Lleva la regla corregida de CUIL a los workflows de F03 y F04** | **pendiente, corré esto** |
| 5 | `F04.md` | Completitud y cobertura | cerrado |
| 6 | `F05.md` | Antigüedad | — |
| 7 | `F06.md` | Puntaje explicable | falta decidir los pesos |
| 8 | `F07.md` | Salida ordenada | — |
| — | **`ADVERSARIO.md`** | **Corrida contra los archivos hechos para romper** | **va entre F07 y F09** |
| 9 | `F08.md` | El número | supuestos declarados, sin cliente real |
| 10 | `F09.md` | Suite de regresión | usa los hallazgos adversarios |
| 11 | `F10.md` | Empaquetado y portfolio | — |

Los prompts sin número **no son fases**: son sesiones sueltas que se corren en
ese punto del orden. La que está pendiente ahora es `PROPAGACION-F03-F04.md`.

De las tres decisiones que dependían de vos, **dos ya están tomadas y escritas
dentro del prompt**: la zona de cobertura en F04 y los supuestos de tiempo en
F08. Queda una sola: **los pesos del puntaje en F06**, y ahí el prompt te va a
frenar a mostrarte la propuesta antes de aplicar nada.
