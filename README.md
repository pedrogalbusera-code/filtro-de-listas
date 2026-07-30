# Limpieza y priorización de listas de contactos — Etapa 1

Workflow de n8n que recibe un CSV de leads y devuelve la misma lista ordenada y
anotada. El entregable comercial no es la lista: es la cuenta del desperdicio.

Estado actual: **F09 cerrada** (ver `ESTADO.md`). Las fases están en `fases/`.

---

## Arrancar n8n en Windows

Abrí PowerShell **en la carpeta del proyecto** y corré esto, en este orden:

```powershell
$env:N8N_RESTRICT_FILE_ACCESS_TO = "C:\Users\pedro\OneDrive\Desktop\anaze\cosas\call center"
npx n8n
```

Después abrí http://localhost:5678 en el navegador.

### Por qué la primera línea no es opcional

Desde n8n 2.x, los nodos que tocan el disco **solo pueden leer y escribir dentro
de `~/.n8n-files`**. Sin esa variable, el workflow falla con:

```
Access to the file is not allowed. Allowed paths: C:\Users\pedro\.n8n-files
```

No es un error del workflow. Es una restricción de seguridad de n8n y hay que
levantarla apuntándola a la carpeta del proyecto. La variable dura lo que dura
esa ventana de PowerShell: si abrís una nueva, la tenés que volver a setear.

---

## Correr el workflow

1. En n8n: menú de arriba a la derecha → **Import from File** →
   `workflows/01-pasamanos.json`.
2. Botón **Execute Workflow**.
3. Se escribe `salidas/salida_f00.csv`.

## Verificar que salió bien

```powershell
python verificadores/v00_pasamanos.py
```

Devuelve una tabla de checks y exit code 0 si pasa, 1 si falla. **Una fase no
está cerrada hasta que su verificador da PASA.**

---

## Estructura

```
CLAUDE.md         reglas del proyecto y decisiones cerradas
ESTADO.md         qué fase está cerrada y qué falta decidir
fases/            F00 a F10, una fase = una sesión
data/             CSV de entrada (sintético, sin datos de personas reales)
workflows/        JSON de los workflows, versionado
salidas/          lo que produce n8n
verificadores/    checks en Python, uno por fase
herramientas/     generadores y utilidades
```

---

## Suite de regresión (F09)

### Correr la suite

```powershell
python verificadores/correr_todo.py
```

Tarda **~11 minutos**. Hace tres cosas en orden:

1. **Regenera los CSVs** de las fases F00-F04 y F06-F08 ejecutando n8n desde
   `gen_workflow.py`. Esto garantiza que los verificadores v00-v04 lean archivos
   frescos de esta corrida, no de corridas anteriores.
2. **Corre los 9 verificadores** (v00 a v08) en secuencia. Cada uno imprime su
   tabla de checks. v05-v08 ejecutan n8n por su cuenta (v05 hace 5 corridas).
3. **Compara contra los golden files** por SHA-256: `golden_2026-07-28.csv`
   (comercial, 9 columnas) y `golden_2026-07-28_auditoria.csv` (26 columnas).

Exit code 0 si todo pasa, 1 si algo falla.

### Regenerar los golden files

```powershell
python verificadores/correr_todo.py --golden
```

Comando separado, nunca parte de correr la suite. Ejecuta el pipeline completo
F08 con fecha de corte 2026-07-28 y sobreescribe los dos golden. Imprime los
SHA-256 nuevos.

**Cuándo regenerar:** después de un cambio de comportamiento **deliberado** (un
peso, un umbral, una regla nueva). Si el golden se pone rojo sin que hayas
tocado la lógica, el cambio no es deliberado y hay que investigar, no regenerar.

**Qué mirar cuando el golden falla:** `git diff` sobre `herramientas/gen_workflow.py`
muestra qué cambió en la lógica. Si el cambio es correcto, regenerar con
`--golden` y commitear los dos golden junto con el `gen_workflow.py` que los
produjo. Si no sabés por qué cambió, no regeneres.

---

## Regenerar el JSON del workflow

El JSON no se edita a mano. Se genera:

```powershell
python herramientas/gen_workflow.py workflows/01-pasamanos.json "<ruta CSV entrada>" "<ruta CSV salida>"
```

Motivo: las rutas absolutas quedan embebidas en el JSON. Si la carpeta se mueve
o el proyecto se prueba en otra máquina, se regenera en vez de buscar y
reemplazar dentro de un JSON de 100 líneas.
