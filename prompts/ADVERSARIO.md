Estás trabajando en este repo. Antes de tocar nada, leé `CLAUDE.md`, `ESTADO.md`
y **`data/TRAMPAS.md` completo**.

# CORRIDA ADVERSARIA — entre F07 y F09

Esta no es una fase de construcción. **En esta sesión no se arregla nada.**

## Antes de escribir una sola línea

Comprobá el entorno y **pedí instalar lo que falte AHORA**: Node 20+,
Python 3.10+, git, y n8n con `npx n8n` (nunca global). Comprobá que
`N8N_RESTRICT_FILE_ACCESS_TO` apunte a esta carpeta. Detalle en
`prompts/SETUP.md`.

## Qué hay

Tres archivos en `data/`, escritos **por alguien que no vio la implementación**,
a propósito:

- `leads_adversario_1.csv` — 48 filas, mismas 6 columnas, valores sucios. Ataca
  las reglas.
- `leads_adversario_2.csv` — 8 filas, otros nombres de columna, tres filas de
  basura arriba, una columna de más, una fila vacía, una fila corta. Ataca la
  lectura del archivo.
- `leads_adversario_3.csv` — 5 filas limpias con **separador punto y coma**, que
  es lo que produce Excel en español.

`data/TRAMPAS.md` documenta fila por fila qué trampa tiene cada una y qué
debería pasar. Leelo antes, no después.

## El procedimiento, y es lo más importante de esta sesión

1. Pasá cada archivo por el pipeline completo, **sin tocar una sola línea de
   código del workflow ni de los verificadores.**
2. Anotá todo lo que rompe, se cuelga, tira excepción, o devuelve algo que no
   corresponde.
3. **NO ARREGLES NADA.** Ni lo obvio. Ni lo que tarda dos minutos.
4. Producí `salidas/HALLAZGOS_ADVERSARIO.md` con una fila por hallazgo:

   | Fila | Entrada | Qué esperaba | Qué hizo | Gravedad |

   Gravedad en tres niveles: **rompe** (excepción o no procesa), **silencioso**
   (devuelve un resultado equivocado con cara de correcto), **cosmético**.

Arreglar sobre la marcha arruina el ejercicio: terminás con un pipeline que pasa
el archivo adversario y sin ningún registro de qué le costó. Ese registro es una
de las piezas más fuertes del proyecto para el portfolio, porque casi nadie
muestra cómo se rompe lo que construyó.

## Qué mirar con especial atención

**Los silenciosos son los peligrosos.** Que el archivo 2 no se pueda leer está
bien y es esperable — el punto es medir hasta dónde llega y con qué mensaje
falla. Lo grave sería que procese tres filas y devuelva un resultado que parece
correcto.

Casos concretos que ya están previstos en `TRAMPAS.md` y conviene verificar uno
por uno:

- **T02** (`+54 9 11 4161 7956`): un espacio de más y el número deja de ser
  celular. Es el más grave de los previstos.
- **T11 y T12**, y **T13 y T14**: son el mismo número escrito distinto. Tienen
  que deduplicarse. Es el test directo de la decisión que se tomó en F03.
- **T37** (`2027-01-15`): fecha futura, antigüedad negativa. Mirá qué hace el
  puntaje con eso.
- **T42 y T43**: fila duplicada exacta salvo un espacio al final del nombre.
- **T21** (localidad vacía): tiene que distinguirse de "fuera de zona". No es lo
  mismo no saber dónde vive que saber que vive lejos.
- **Archivo 3**: si lo lee como una sola columna gigante y no avisa, es un fallo
  silencioso de manual.

## Criterio de aceptación

1. Los tres archivos se corrieron.
2. `salidas/HALLAZGOS_ADVERSARIO.md` existe, con gravedad asignada a cada
   hallazgo.
3. **Cero cambios** en `workflows/` y en `verificadores/`. Verificalo con
   `git diff` antes de cerrar y pegá el resultado.
4. Los hallazgos están resumidos en `ESTADO.md` con el conteo por gravedad.

## Prohibido

- Arreglar cualquier cosa.
- Modificar los archivos adversarios para que pasen.
- Decidir vos qué hallazgo "no cuenta". Se anotan todos; qué se arregla lo
  decide Pedro después.

## Terminado cuando

Está el documento de hallazgos, `git diff` sobre `workflows/` y `verificadores/`
sale vacío, y `ESTADO.md` tiene el resumen. **La sesión siguiente es F09**, que
va a usar esta lista para decidir qué entra en la suite de regresión.
