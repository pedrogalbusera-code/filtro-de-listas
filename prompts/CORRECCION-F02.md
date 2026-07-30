Estás trabajando en este repo. Antes de tocar nada, leé `CLAUDE.md`, `ESTADO.md`
y `fases/F02-validacion-cuil.md` completos.

# CORRECCIÓN F02 — Regla del CUIL y un dato mal documentado

Esta no es una fase nueva. Es una corrección sobre F02, que ya está cerrada.
Corrandola en su propia sesión, sin mezclarla con ninguna fase.

## Antes de escribir una sola línea

Comprobá el entorno y **pedí instalar lo que falte AHORA**: Node 20+,
Python 3.10+, git, y n8n con `npx n8n` (nunca global). Comprobá que
`N8N_RESTRICT_FILE_ACCESS_TO` apunte a esta carpeta. Detalle en
`prompts/SETUP.md`.

---

## Parte 1 — Borrar una consecuencia que está mal escrita

En `ESTADO.md`, en "Limitaciones conocidas → F02", está anotado que un CUIL
femenino reemitido (`23-DNI-4`) sería marcado **inválido** por el validador
actual.

**Eso es falso. Borralo.**

La reemisión no es una excepción al algoritmo: es consistente con él. Cambiar el
prefijo de `27` a `23` altera el dígito que pesa 4. La diferencia es
`(7 - 3) x 4 = 16`, y `16 mod 11 = 5`. Si con `27` el resto era 1, con `23` pasa
a ser 7, y `11 - 7 = 4`: sale el DV 4 exacto. De `20` a `23` la diferencia es
12, `12 mod 11 = 1`, el resto pasa de 1 a 2, y `11 - 2 = 9`: sale el DV 9.

Verificado por fuerza bruta sobre 300.000 DNI: **27.272 de 27.272** reemisiones
femeninas validan como `23-DNI-4` y **27.273 de 27.273** masculinas validan como
`23-DNI-9`. Cero excepciones.

O sea: **los CUIL reemitidos pasan bien con el algoritmo simple.** No hay falsos
inválidos por ese motivo.

## Parte 2 — Aplicar la regla correcta

Decisión de Pedro, ya tomada: **resto 1 pasa a inválido.**

El fundamento: bajo la regla de AFIP, un CUIL que da resto 1 **con su propio
prefijo** no puede existir, porque AFIP lo habría reemitido como 23. Aceptarlo
con DV 9 crea una colisión —el DV 9 sale tanto de resto 1 como de resto 2— y esa
colisión debilita el dígito verificador.

Cambio a hacer en el nodo Code `Validar CUIL`: donde hoy dice
`resto 1 -> DV 9`, pasa a `resto 1 -> inválido`. **Es una línea.** No hace falta
modelar sexo ni cambiar prefijos: eso ya está cubierto por el algoritmo.

## Parte 3 — Las consecuencias, que hay que aceptar y anotar

1. **19 de los 200 CUIL del CSV sintético pasan de válidos a inválidos.** Es
   esperable y no es un bug: ese archivo fue generado con la regla vieja. Es la
   prueba de que el archivo estaba mal generado.
2. **Hay que reescribir los esperados de `v02_cuil.py`.** El criterio "cero
   falsos inválidos / 200 válidos" ya no aplica: pasa a **181 válidos y 19
   inválidos por resto 1**. Escribí el nuevo esperado explícito, no lo dejes
   como "la mayoría válidos".
3. **`cuil_dudoso` se queda**, pero cambia de significado: ahora marca los que
   fueron rechazados por resto 1, no los aceptados con reserva. Actualizá el
   comentario del campo para que diga eso.
4. Los typos de un dígito no detectados bajan de **1,58% a 0,93%**. Podés
   comprobarlo con `python herramientas/medir_typos.py <csv>`, que ya está en el
   repo y corre las cuatro combinaciones.

## Criterio de aceptación

1. La consecuencia falsa quedó borrada de `ESTADO.md`, y en su lugar está
   explicada la aritmética de la reemisión.
2. El nodo Code rechaza resto 1 y el workflow se regeneró, reimportó y reejecutó.
3. `v02_cuil.py` pasa con los esperados nuevos: 181 válidos, 19 inválidos por
   resto 1, y sigue rechazando el 100% de los CUIL mutados.
4. `herramientas/medir_typos.py` confirma el 0,93%.
5. La bitácora de `ESTADO.md` registra el cambio y por qué.

## Prohibido

- Dejar el esperado del verificador como un rango o un "al menos". Va el número
  exacto: 181 y 19.
- Tocar F03 o cualquier fase posterior en esta sesión. Si el cambio de
  `cuil_valido` hace fallar un verificador de otra fase, **anotalo y frená**:
  eso se resuelve en su propia sesión.

## Terminado cuando

`v02_cuil.py` da verde con los números nuevos y `ESTADO.md` quedó corregido.
