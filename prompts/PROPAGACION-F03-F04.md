Estás trabajando en este repo. Antes de tocar nada, leé `CLAUDE.md` y `ESTADO.md`
completos, con atención a la sección "Propagación de la regla de CUIL a F03 y F04".

# PROPAGACIÓN — llevar la regla corregida de CUIL a F03 y F04

No es una fase nueva. Es terminar de aplicar la corrección de F02, que quedó a
medio propagar y está bien que haya quedado así: se frenó a propósito.

## Antes de escribir una sola línea

Comprobá el entorno y **pedí instalar lo que falte AHORA**: Node 20+,
Python 3.10+, git, y n8n con `npx n8n` (nunca global). Comprobá que
`N8N_RESTRICT_FILE_ACCESS_TO` apunte a esta carpeta. Detalle en
`prompts/SETUP.md`.

## El problema

`workflows/04-dedup.json` y el workflow de F04 llevan embebida la regla **vieja**
de CUIL (`resto 1 → DV 9`). Sus salidas muestran los 19 casos como válidos,
mientras que `salida_f02.csv` ya los muestra como inválidos. El repo se
contradice a sí mismo en la misma columna.

No afecta la lógica de esas fases —F03 dedupa por `cuil_norm` y F04 por
localidad y teléfono, ninguna usa `cuil_valido`— por eso v03 y v04 siguen en
verde. Pero el golden de F09 se va a congelar sobre estas salidas, y un golden
armado sobre datos inconsistentes no detecta nada: consagra el error.

## Qué hacer

1. Regenerá los workflows de F03 y F04 desde `herramientas/gen_workflow.py`, que
   ya tiene la regla corregida. **No edites los JSON a mano.**
2. Reimportalos en n8n y reejecutalos.
3. Verificá que `salida_f03.csv` y `salida_f04.csv` ahora muestren **181
   válidos / 19 inválidos** y tengan la columna `cuil_dudoso`.
4. Corré `v03_dedup.py` y `v04_cobertura.py`. **Tienen que seguir en verde con
   los mismos números de siempre**: 14 duplicados por CUIL, 8 por teléfono, 161
   en zona / 39 fuera. Si alguno cambia, **frená y explicá por qué**: significa
   que esa fase sí dependía de `cuil_valido` sin que nadie lo hubiera notado, y
   eso es un hallazgo que hay que anotar antes de tocar nada.

## Verificación de que la propagación fue completa

Buscá en **todos** los workflows si quedó alguna copia de la regla vieja:

```
grep -rn "resto === 1" workflows/
```

Toda ocurrencia tiene que ser la versión que rechaza, ninguna la que devuelve 9.
Pegá el resultado del grep en la bitácora.

## Lo que hay que anotar, y es más importante que el fix

Este episodio dejó a la vista un problema de arquitectura: **la lógica de cada
fase queda copiada dentro de cada workflow posterior.** Un cambio de una línea en
F02 obliga a regenerar todos los workflows aguas abajo. Con dos es molesto; con
ocho va a ser el motivo por el que nadie quiera corregir nada.

En esta sesión **no se resuelve**. Solo dejá anotado en `ESTADO.md`, en
decisiones pendientes, que antes de F07 hay que decidir entre mantener un único
workflow acumulativo o seguir con uno por fase generado desde una única fuente.

## Criterio de aceptación

1. `salida_f03.csv` y `salida_f04.csv` regeneradas, con 181/19 y con
   `cuil_dudoso`.
2. `v03_dedup.py` y `v04_cobertura.py` en verde, con los mismos números de antes.
3. El `grep` no encuentra ninguna copia de la regla vieja.
4. Bitácora de `ESTADO.md` actualizada, y la decisión de arquitectura anotada
   como pendiente.

## Prohibido

- Editar los JSON a mano en vez de regenerarlos.
- Cambiar un esperado de v03 o v04 para que pase. Si cambian, es un hallazgo.
- Resolver el problema de arquitectura en esta sesión.

## Terminado cuando

Las tres salidas dicen lo mismo sobre los mismos 19 CUILs. **La sesión siguiente
es F05.**
