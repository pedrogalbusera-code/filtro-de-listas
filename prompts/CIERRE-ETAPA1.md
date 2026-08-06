Estás trabajando en este repo. Antes de tocar nada, leé `CLAUDE.md`, `ESTADO.md`,
`fases/PRUEBA-DE-FUEGO.md`, `verificadores/correr_todo.py`, `verificadores/v_fuego.py`
(en particular `correr_caso()`) y `herramientas/gen_workflow.py` (los argumentos que acepta).

# Cierre de Etapa 1 — commitear, un solo comando de regresión, un solo comando de uso

## Qué es en una línea

Empaquetar lo que ya funciona: asegurar la prueba de fuego en git, un `--full` que corra
TODA la regresión con un comando, un `procesar.py` que procese cualquier archivo de cliente
con un comando, y README/workflow versionado puestos al día. **No se escribe lógica de nodo
nueva.** Si algo no pasa sin tocar un nodo, frená y mostrámelo.

## Parte 0 — El commit de la prueba de fuego (PRIMERO, antes de tocar cualquier archivo)

El estado actual del repo: ~17 archivos sin trackear + `.gitignore` y `ESTADO.md`
modificados. Ese trabajo hoy vive solo en este disco.

1. **Agregá `Propuesta-Filtro-de-Listas.pdf` al `.gitignore`**, junto a `guion-de-venta.md`
   y `CATALOGO-FILTROS.md` (es documento comercial; la decisión de dejarlos fuera del repo
   público ya está tomada).
2. **Commit 1 — la prueba de fuego.** Entra todo lo de la fuego: los 2 CSVs y el `.xlsx` de
   `data/`, los 2 configs (`mapeo_fuego.json`, `segmentacion_fuego.json`),
   `herramientas/gen_fuego.py` y `gen_xlsx_lista_baja_fuego.py`, `verificadores/v_fuego.py`,
   `prompts/PRUEBA-DE-FUEGO.md`, `fases/PRUEBA-DE-FUEGO.md`, las 2 fichas de
   `salidas/`, `.gitignore` y `ESTADO.md`.
3. **Commit 2 — portfolio.** Los 3 archivos `portfolio-*` (`.html` x2, `.pdf`) van en su
   propio commit, separado: son material público de portfolio, no parte del pipeline.
4. Push de los dos.

**Criterio:** pegá el output real de `git log --oneline -4` y de `git status` al final.
`git status` tiene que quedar limpio (solo este prompt sin trackear, si querés dejarlo para
el commit final).

## Parte 1 — `correr_todo.py --full`

Hoy la default corre v00–v08 + pendientes + golden (~11 min). v11–v14 y `v_fuego` quedan
afuera y pueden romperse en silencio — ya pasó dos veces con checks que no corrían de verdad.

- Agregá el flag `--full`: corre la default **más** `v11_puerta`, `v12_persona`,
  `v13_basura`, `v14_optout` y `v_fuego`, en ese orden, con el mismo loop y la misma tabla
  de resultados (sin duplicar código del runner).
- La default **no cambia en nada**: mismos verificadores, mismo orden, mismo tiempo.
- Al final de una corrida default, una línea que recuerde: los verificadores de archivo
  (v11–v14, fuego) corren con `--full`.

**Criterio:** pegá el output real de LAS DOS corridas — `correr_todo.py` (default, verde) y
`correr_todo.py --full` (verde). No lo describas: el output pegado, con los tiempos.

## Parte 2 — `herramientas/procesar.py`: una lista de cliente, un comando

Hoy procesar un archivo nuevo son 3–4 pasos manuales (regenerar workflow con rutas
absolutas, import, execute). La prueba de fuego demostró que todo archivo se resuelve con
config; falta el comando que lo haga en un paso.

```
python herramientas/procesar.py <archivo> [--mapeo config/X.json] [--baja archivo.xlsx]
       [--segmentacion config/Y.json] [--fecha-corte AAAA-MM-DD] [--salida-dir salidas/]
```

- **Reusá lo que existe.** El mecanismo es el mismo de `correr_caso()` en `v_fuego.py`:
  `gen_workflow.py` apuntando al archivo (rutas absolutas resueltas por el script) +
  `npx n8n import:workflow` + `npx n8n execute`. Nada de reimplementar; si hace falta,
  factorizá `correr_caso()` a un módulo compartido y que el verificador y `procesar.py`
  usen el mismo.
- **Id de workflow propio** para no pisar el canónico ni los de los verificadores.
- **Salidas con nombre derivado del archivo de entrada** (ej. `lista_acme.csv` →
  `salidas/lista_acme_comercial.csv`, `_auditoria.csv`, `_reporte.md`,
  `ficha_entrada_lista_acme.md`). Jamás pisar `salida_comercial.csv` ni los golden.
- **Fecha de corte:** parámetro; default = hoy. Se imprime SIEMPRE en el output (regla 6
  de `CLAUDE.md`: nada de fechas escondidas).
- **Al terminar imprime:** la ruta de los 4 archivos + el número del reporte (entraron /
  llamables / descartados / horas ahorradas). Es lo que se lee en voz alta en una reunión.
- **Si la puerta (F11) rechaza el archivo:** exit ≠ 0 con el MOTIVO del rechazo legible,
  no un stacktrace. El rechazo es un resultado, no un crash.

### El verificador: `verificadores/v_procesar.py`

Corre `procesar.py` DE VERDAD (subprocess, como haría un usuario) en tres casos:

1. **Canónico:** `procesar.py data/leads_prueba_SINTETICO_1.csv --fecha-corte 2026-07-28`
   → comercial y auditoría **byte a byte idénticos a los golden** (SHA-256). Si esto pasa,
   `procesar.py` es el mismo pipeline y no una copia que va a divergir.
2. **Fuego:** `procesar.py data/leads_fuego_1.csv` con el mapeo, la baja y la segmentación
   fuego, fecha de corte la misma que usa `v_fuego.py` → byte a byte contra la salida que
   produce la corrida de `v_fuego` (comercial + auditoría + reporte).
3. **Rechazo:** el archivo de prosa (`data/leads_adversario_5.txt` o el que use v11 para el
   rechazo duro) → exit ≠ 0, el motivo aparece en stdout/stderr, y NO se escribió ninguna
   salida a medias.

`v_procesar` entra en la lista de `--full` (después de `v_fuego`).

**Criterio:** pegá el output real de `python verificadores/v_procesar.py` en verde y de una
corrida de `procesar.py` sobre el archivo fuego mostrando el resumen final impreso.

## Parte 3 — README y workflow versionado al día (ÚLTIMO, con todo lo anterior verde)

- **Regenerá `workflows/etapa1-final.json`** con el `gen_workflow.py` actual (el versionado
  quedó viejo) y commitealo.
- **README:** "Cómo se corre" pasa a tener `procesar.py` como camino principal (el flujo
  manual queda como apéndice). En "Limitaciones conocidas", borrá SOLO lo que hoy es falso,
  y cada borrado tiene que estar respaldado por un verificador en verde que lo pruebe:
  la de "solo CSV de 6 columnas, sin basura arriba" (F11, v11), la de localidades con
  paréntesis (CORRECCION-F04, v04) y lo que CORRECCION-F01/F01b ampliaron de teléfonos
  (revisá `v01_telefono.py` para escribir lo que HOY reconoce, no lo que te acordás).
  La de duplicados que no transfieren datos sigue siendo verdad: se queda.
  Agregá una línea sobre la prueba de fuego (archivo sucio realista procesado solo con
  config, 68/68).
- Regla de siempre: **nada en presente sobre algo que no esté verificado.** El README se
  escribe al final, cuando todo lo de arriba ya está en verde — no antes.

## Prohibido

- **Tocar lógica de nodos en `gen_workflow.py`.** Esto es empaquetado. Si un caso te obliga
  a tocar un nodo, es un filtro incompleto: frená y mostrámelo.
- Que `--full` cambie el comportamiento o el tiempo de la corrida default.
- Que `procesar.py` reimplemente el runner: reusá `correr_caso()`/`gen_workflow.py`.
- Contestar un criterio con prosa. Cada criterio pide output pegado: pegalo.
- Mover, regenerar o "actualizar" los golden. Si un golden difiere, algo se rompió.
- Escribir el README antes de que `v_procesar.py` esté verde.

## Terminado cuando

`correr_todo.py` default verde, `correr_todo.py --full` verde (con `v_procesar` adentro),
los commits de la Parte 0 pusheados, y un commit final con `procesar.py` + `v_procesar.py` +
README + workflow regenerado + este prompt + `ESTADO.md`, también pusheado.

En `ESTADO.md`: fila nueva "CIERRE-ETAPA1" con los conteos de `v_procesar`, el tiempo de
`--full`, y una línea que diga cuál es ahora el comando para procesar una lista de cliente.
