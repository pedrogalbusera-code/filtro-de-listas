Estás trabajando en este repo. Leé `CLAUDE.md`, `ESTADO.md` y
`prompts/CORRECCION-F09.md` antes de tocar nada.

# CIERRE F09 — sesión corta, solo cerrar lo que quedó abierto

La sesión anterior hizo la corrección de F09 completa: pasada de regeneración,
golden de auditoría, comando `--golden`, `git init`, `.gitattributes` y la prueba
de aislamiento con output real. **Quedaron cuatro cosas sin terminar.** Esta sesión
es solo eso. No se construye nada nuevo.

## Estado al arrancar

Dos commits hechos: `d1c8927` (estado completo) y `d1da0d3` (`.gitattributes`).
`ESTADO.md` y `README.md` modificados sin commitear, esperando el número real.

**Ojo con lo que dice hoy la tabla de `ESTADO.md`:** F09 figura como
`CERRADA (corregida 2026-07-30) | correr_todo: 10/10 PASA (660s)`. Ese 660 es de la
corrida **anterior** a romper la regla en la prueba de aislamiento. El verde
posterior al revert todavía no lo confirmó nadie. Hasta que lo confirmes, tratá esa
línea como no verificada.

## 1. Confirmar la suite en verde, de verdad

Corré la suite entera hasta el final:

```powershell
python verificadores/correr_todo.py
```

**Pegá la tabla completa que imprime**, con los tiempos por verificador y el total.
No la resumas ni la describas.

Si no da 10/10, pará y mostrame qué falló. No ajustes ningún verificador.

## 2. Limpiar los finales de línea que quedaron en el índice

`git status --short` muestra como modificados los CSV de `data/` y los JSON de
`workflows/`. Ya está comprobado que **es solo CRLF/LF, cero contenido**
(`git diff --ignore-cr-at-eol` vuelve vacío). El `.gitattributes` se agregó después
del primer commit, así que el índice todavía tiene la versión vieja:

```powershell
git add --renormalize .
git status --short
```

Tiene que quedar limpio salvo `ESTADO.md` y `README.md`.

## 3. Comprobar que los golden quedaron byte a byte en git

Es el punto entero del `.gitattributes` y todavía no se verificó. Los dos golden se
commitearon **antes** de que existiera, así que pueden haber quedado normalizados:

```powershell
git show HEAD:salidas/golden_2026-07-28.csv | Get-FileHash -Algorithm SHA256
Get-FileHash salidas/golden_2026-07-28.csv -Algorithm SHA256
```

Lo mismo con `golden_2026-07-28_auditoria.csv`. Los cuatro hashes tienen que
coincidir de a pares. **Si no coinciden, el golden en git no es el que la suite
compara**, y la suite se rompería en cualquier clon nuevo. Arreglalo con el
renormalize del punto 2 y volvé a comprobar.

## 4. Actualizar los documentos con el número real y commitear

- `ESTADO.md`: reemplazá el `660s` de la tabla de fases por el total real de la
  corrida del punto 1, y pegá esa tabla en la bitácora al lado de la de la prueba
  de aislamiento. Que quede claro cuál es cuál: una es con la regla rota, la otra
  es la confirmación después de revertir.
- `README.md`: los dos comandos (`correr_todo.py` y `correr_todo.py --golden`), el
  tiempo real, y qué hacer cuando el golden se pone rojo.
- Segundo commit, separado del primero.

## Terminado cuando

`git status --short` sale limpio, `ESTADO.md` tiene las dos tablas con sus números
reales, y los hashes de los golden coinciden entre git y disco.

## Prohibido

- Tocar `correr_todo.py`, los verificadores o `gen_workflow.py`. Si algo falla,
  pará y mostrámelo.
- Empezar los pendientes conocidos de los hallazgos adversarios: van en su propia
  sesión.
- Avanzar a F10.
