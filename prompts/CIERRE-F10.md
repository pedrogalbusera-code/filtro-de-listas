Estás trabajando en este repo. Leé `CLAUDE.md`, `ESTADO.md` y `prompts/F10.md`
antes de tocar nada.

# CIERRE F10 — sesión corta, solo cerrar

La sesión anterior entregó las cuatro cosas de F10: `workflows/etapa1-final.json`,
`README.md`, `portfolio-entry.html` y `guion-de-venta.md`. **La revisión ya se
hizo y los números están bien.** Se verificó contra `salidas/salida_auditoria.csv`:
200 / 186 únicos / 86 llamables / 114 descartados / alta 48 / media 38 / 82 sin
teléfono / 14 duplicados / 39 fuera de zona / 3 por puntaje bajo. Todo cierra.
Los SHA-256 de las dos salidas son idénticos al golden.

**Esta sesión no reescribe ninguno de los cuatro entregables por estilo.** Son
siete puntos concretos. No se construye nada nuevo. No se toca la lógica del
pipeline.

---

## 1. El link del portfolio apunta a un repo que no existe

`portfolio-entry.html` linkea a
`https://github.com/pedrogalbusera-code/filtro-de-listas`, pero `git remote -v`
en este repo vuelve **vacío**: no hay remoto y el repo no está publicado. Es lo
único del entregable que un tercero puede clickear, y hoy da 404.

No crees el repo en GitHub vos. El repo lo crea Pedro (o Claude por fuera de esta
sesión). Lo que sí hacés:

- Dejá listo el comando exacto que hay que correr, con el nombre de repo que usa el
  link (`filtro-de-listas`), para copiar y pegar.
- Verificá que después de publicar el link resuelva, o dejá anotado que queda
  pendiente hasta que exista.

**Hasta que el repo exista, F10 no está cerrada.** Marcálo así en `ESTADO.md`.

## 2. Los finales de línea, otra vez — y el commit de F10

`git status --short` muestra 12 archivos modificados (`data/*.csv`,
`workflows/*.json`) con 2464 líneas cambiadas. Ya está comprobado que **es puro
CRLF/LF, cero contenido**: `git diff --ignore-cr-at-eol data/ workflows/` vuelve
vacío.

Esto ya se intentó arreglar en `CIERRE-F09` con `git add --renormalize .` y
**no quedó**. Hacelo con un add directo y verificá antes de commitear:

```powershell
git add -A data workflows
git diff --cached --ignore-cr-at-eol --stat data workflows
```

Ese segundo comando **tiene que volver vacío**. Pegá su salida. Si vuelve algo,
pará: hay contenido real mezclado y hay que mirarlo antes de commitear.

Después, dos commits separados:

- Uno solo para los finales de línea (mensaje que diga que no hay cambio de
  comportamiento).
- Otro para F10: `etapa1-final.json`, `README.md`, `portfolio-entry.html`,
  `prompts/CIERRE-F09.md`, `prompts/PENDIENTES-ADVERSARIO.md`,
  `prompts/CIERRE-F10.md`, `prompts/CORRECCION-F01.md`, `prompts/HOJA-DE-RUTA.md`,
  `ESTADO.md`. (`guion-de-venta.md` y `CATALOGO-FILTROS.md` **no** entran — ver
  punto 6.)

Motivo de separarlos: el primer commit del repo público no puede mostrar 2464
líneas cambiadas sin ningún cambio de comportamiento.

## 3. `salidas/reporte.md` ensucia el árbol en cada corrida

`.gitignore` ignora `salidas/reporte_*.md` (con guion bajo) pero **no**
`salidas/reporte.md`, que es el que genera el workflow final. Aparece como `??`
después de cada corrida de la suite.

Decidí una de las dos y dejá el motivo en el `.gitignore`:

- Ignorarlo, como el resto de lo generado; o
- Versionarlo a propósito como ejemplo de salida, y entonces sacarlo del patrón
  de generados y explicar por qué.

## 4. El supuesto de minutos por llamada está hardcodeado y cambió sin registro

`prompts/F08.md` decidió `config/supuestos.json` con `minutos_por_llamada: 3` y
`costo_hora_operador: null`, con la frase **"son parámetros, no constantes"**.

En el repo: `config/supuestos.json` **no existe**. Los supuestos viven
hardcodeados en `herramientas/gen_workflow.py` línea 669 con
`minutos_por_llamada: 4` y `costo_hora_operador: 0`. El 3 pasó a 4 en algún
momento y no está anotado en ningún lado. De ahí sale el 7,6 h que aparece en el
README, en el portfolio y en el guion de venta.

No crees el archivo de config ahora (eso arrastra scope). Hacé dos cosas:

- **Anotá en `ESTADO.md`** que los supuestos quedaron como constante en
  `gen_workflow.py`, no como archivo de config, y que el valor es 4 min. Si
  encontrás en el historial por qué cambió de 3 a 4, ponelo. Si no, decí que no
  quedó registrado.
- **Agregá la banda de sensibilidad al reporte.** Hoy el reporte muestra 7,6 h
  como número único, y ése es exactamente el número que un gerente discute ("a
  mí una llamada me lleva 2 minutos"). Con banda no hay discusión: agregá una
  línea que diga el rango a 2 y a 5 minutos (3,8 h a 9,5 h con este archivo).
  El texto tiene que dejar claro que el número del medio es el supuesto y la
  banda es la sensibilidad.

Después de tocar el nodo de reporte, **re-generá el workflow y corré la suite
entera**. Los dos SHA-256 de los CSV tienen que seguir dando
`9a6884603f9128c29a7503cb25b8417ceb233b58bdd89e9053bf4f486a61dcb4` (comercial) y
`ae6fcc5f146d6ec59395b3fb09a5bbdfcd764303e762a287dfe6a44623fd9cd2` (auditoría).
Pegá la tabla completa de la suite y los dos hashes. No los describas.

## 5. El criterio 1 de F10 no se ejecutó como está escrito

El criterio dice: *"Importar el JSON en un **n8n limpio** y correr el CSV de
prueba reproduce el golden de F09. Si no lo reproduce, el workflow depende de
algo que no está versionado."*

La corrida que se hizo fue sobre el n8n de siempre, que ya tiene importados los
nueve workflows anteriores. Eso no prueba lo que el criterio quiere probar.

Corrélo en limpio: apuntá `N8N_USER_FOLDER` a una carpeta nueva y vacía,
importá **solo** `workflows/etapa1-final.json`, ejecutalo y sacá los SHA-256.
Pegá los comandos y la salida. Si los hashes coinciden, el criterio 1 queda
ejecutado; si no coinciden, **pará y mostrame la diferencia** — encontraste
justo lo que el criterio buscaba.

## 6. Los documentos comerciales NO van al repo público — decisión tomada

`guion-de-venta.md` y `CATALOGO-FILTROS.md` (en la raíz) tienen el modelo de cobro
y la estrategia comercial. El repo va a estar linkeado desde el portfolio, así que
un cliente potencial los leería antes de hablar con Pedro. **Decisión ya tomada: no
van al repo público.** No preguntes, hacé:

- Agregá `guion-de-venta.md` y `CATALOGO-FILTROS.md` al `.gitignore`, con un
  comentario que diga que son documentos comerciales internos.
- Verificá que `git status` ya no los liste como para commitear.
- En la sección "Estructura del repo" del `README.md`, listá `portfolio-entry.html`
  (que sí va) y aclará en una línea que los documentos comerciales quedan fuera del
  repo a propósito.

## 7. Cerrar `ESTADO.md`

Hoy `ESTADO.md` solo tiene la fila de la tabla en `EN CURSO`. **No hay entrada de
bitácora de F10.** Escribila con el mismo formato que las otras: fecha, qué se
construyó, qué número dio el verificador, y los hallazgos de esta revisión
(el link al repo inexistente, el supuesto que cambió de 3 a 4 sin registro, el
criterio 1 que no se había ejecutado en limpio).

Un detalle cosmético para anotar, no para arreglar: `motivo_frescura` está vacío
en las 200 filas del CSV de auditoría. La frescura **sí** puntúa (aparece en
`motivo`, en las 200 filas), así que no es un bug de lógica: es una columna
muerta en el archivo que sirve para defender el resultado. Anotalo como
pendiente conocido.

---

## Reglas que no se rompen

- **No se toca la lógica del pipeline.** Los únicos cambios de código permitidos
  son el texto del reporte del punto 4.
- **La suite tiene que terminar 10/10 y los dos SHA-256 tienen que seguir
  iguales.** Si algo se pone rojo, pará y mostrámelo. No ajustes un verificador
  para que pase.
- **Pegá los outputs, no los cuentes.** Cada punto que dice "pegá" pide la salida
  literal del comando. Un criterio contestado con prosa en vez del output cuenta
  como no ejecutado.
- **No inventes capacidades** en el README, el portfolio ni el guion. Si algo no
  se usó, no va.

## Qué NO entra en esta sesión

F11 (puerta de entrada del archivo del cliente) y `CORRECCION-F01` (los dos
hallazgos de teléfono). Son sesiones propias y van después de que F10 cierre.
Ver `prompts/HOJA-DE-RUTA.md` para el orden completo.
