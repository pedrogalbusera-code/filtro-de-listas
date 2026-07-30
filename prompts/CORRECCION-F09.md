Estás trabajando en este repo. Antes de tocar nada, leé `CLAUDE.md`, `ESTADO.md` y
`prompts/F09.md` completos.

# CORRECCIÓN F09 — la suite dice 10/10 y cinco de esos diez leen archivos viejos

F09 se marcó cerrada el 2026-07-29 con `10/10 PASA (651s)`. La decisión central de
la fase **no se implementó**, y el criterio de aislamiento se contestó con un
argumento en vez de una prueba. Esta sesión lo corrige. No es una fase nueva.

## La evidencia, comprobala vos antes de empezar

```powershell
ls salidas\salida_f0*.csv | select Name, LastWriteTime
```

`salida_f00.csv` y `f01.csv` son del 27/07, `f02.csv` del 27/07 a la noche,
`f03.csv` y `f04.csv` del 28/07. La corrida de la suite fue el 29/07. **`v00` a
`v04` verificaron archivos de hace uno y dos días.**

En `verificadores/correr_todo.py`: el loop de las líneas 122–145 corre los 9
verificadores sin regenerar nada antes. La regeneración existe, pero vive adentro
de `correr_golden()` (líneas 50–109), escribe en archivos temporales y los borra en
el `finally`. Nunca toca los `salidas/salida_fXX.csv` que `v00`–`v04` leen.

`ESTADO.md` afirma que "cada verificador corre su propio `--fase` con su propia
ejecución de n8n". Es falso para `v00`–`v04`, y el mismo párrafo lo desmiente
cuatro líneas más arriba cuando dice "v00-v04 <1s (verificación Python pura sobre
CSVs existentes)". Corregí esa afirmación cuando actualices `ESTADO.md`.

## Lo que quedó bien y no se toca

El check del golden es real: regenera la cadena F00→F08 desde `gen_workflow.py` y
compara SHA-256 contra un archivo congelado. Rompés cualquier regla y el hash se
mueve. **No lo rediseñes.** La única modificación permitida está en el punto 2.

## Qué corregir

### 1. La pasada de regeneración (la decisión que faltó)

Antes del loop de verificadores, `correr_todo.py` regenera y ejecuta las fases F00
a F06 desde `gen_workflow.py` con `--fecha-corte 2026-07-28`, dejando escritos los
`salidas/salida_fXX.csv` que `v00`–`v04` leen. Recién después corre los
verificadores.

Si la regeneración falla en cualquier fase, la suite **corta ahí** y lo dice. No
tiene sentido verificar contra archivos a medio escribir.

Dos cosas a cuidar:

- **No dupliques trabajo.** `v05`–`v08` ya ejecutan n8n por su cuenta (v05 hace 5
  corridas y se come 468 de los 651 segundos). La pasada nueva es para alimentar a
  `v00`–`v04`; no hace falta regenerar lo que los otros ya rehacen solos. Decidí y
  **escribí en un comentario** qué fases regenera la pasada y por qué.
- **Medí el tiempo nuevo** y actualizá el número del README y de `ESTADO.md`.

### 2. El golden también tiene que cubrir la auditoría

Hoy `correr_golden()` hashea solo el CSV comercial (9 columnas). Los campos
internos —`es_duplicado`, `duplicado_de`, `telefono_match`, `telefono_tipo`,
`cuil_dudoso`, `dias_antiguedad`, `motivo_frescura`, `fecha_corte_usada`— viven
únicamente en el de auditoría. Un bug de deduplicación que no mueva el puntaje
final pasa limpio hoy.

El archivo de auditoría **ya se genera en esa misma corrida** (`tmp_aud`, línea 56,
pasado en línea 66) y se borra sin usarse en el `finally`. Congelá
`salidas/golden_2026-07-28_auditoria.csv` con el comando de regeneración y hasheá
los dos.

### 3. El comando de regeneración del golden

Criterio 5 de la fase, todavía no existe: regenerar el golden tiene que ser un
comando explícito y separado, nunca parte de correr la suite. Escribilo, corrélo, y
comprobá que el golden comercial que ya está en disco sale byte a byte idéntico. Si
sale distinto, **pará y mostrámelo antes de pisarlo**.

### 4. git

Sigue sin haber repositorio. Verificado el 2026-07-29: no hay `.git` en la carpeta
ni en ningún padre. Proponé `git init` con un `.gitignore` concreto y **esperá el
OK de Pedro**. Ojo: la carpeta está adentro de OneDrive, y `salidas/` es mezcla de
archivos generados (que no van) y de los dos golden (que sí van). Mostrá el
`.gitignore` antes de correr nada.

Primer commit con todo el estado actual, para que de acá en adelante `git diff`
signifique algo.

### 5. La prueba de aislamiento, ejecutada de verdad

Rompé una regla en `gen_workflow.py`, corré la suite entera, **pegá el output real
en `ESTADO.md`**, revertí, volvé a correr y confirmá que vuelve a verde.

El criterio es direccional: falla el verificador de la fase rota y **los anteriores
siguen en verde**. Que fallen los posteriores es la dependencia real del pipeline,
no acoplamiento.

Con la pasada de regeneración puesta, esto ahora prueba algo. Sin ella, `v00`–`v04`
daban verde pasara lo que pasara — que es exactamente por qué hay que correrlo
después de arreglar el punto 1 y no antes.

### 6. README

La sección de suite que está hoy en el README fue escrita **antes** de que la suite
existiera y describe en presente cosas que no pasan: que el golden "se regenera
cada vez que hay un cambio de comportamiento deliberado y se versionan ambos"
—no había repo— y no dice que la corrida tarda once minutos. Reescribila con los
dos comandos, los tiempos reales y qué mirar cuando el golden se pone rojo.

## Fuera de alcance de esta sesión

**Los pendientes conocidos con los 13 hallazgos adversarios no van acá.** Van en su
propia sesión, antes de F10. Motivo: el trabajo de esta sesión es que la suite deje
de mentir; agregarle casos nuevos a una suite que todavía miente es construir
arriba de algo que no se sostiene. Dejá anotado en `ESTADO.md` que queda pendiente.

Tampoco se arregla ningún hallazgo adversario, ni se avanza a F10.

## Criterio de aceptación

1. `ls salidas\salida_f0*.csv` después de correr la suite muestra **todos** los CSV
   con la fecha y hora de esa corrida. Ninguno de días anteriores.
2. La suite corre entera en verde, y la tabla dice cuántos checks son y cuánto
   tardó de verdad.
3. Los dos golden (comercial y auditoría) se comparan por SHA-256 y se regeneran
   con un comando propio y separado.
4. Hay repo git con el primer commit hecho, y los dos golden versionados junto al
   `gen_workflow.py` que los produjo.
5. La prueba de aislamiento está en `ESTADO.md` **con el output pegado**, no
   descrita.
6. La afirmación falsa sobre `v00`–`v04` que hoy está en `ESTADO.md` quedó
   corregida, y la fila de la tabla vuelve a decir la verdad sobre F09.

## Prohibido

- Marcar un verificador como skip, o bajarle la exigencia a uno existente para que
  entre en la suite. Si uno falla contra los CSV regenerados, **eso es el hallazgo**:
  pará, mostrámelo y esperá.
- Que la suite regenere los golden automáticamente.
- Contestar el criterio 5 con un párrafo explicando qué pasaría. Se corre y se pega.
