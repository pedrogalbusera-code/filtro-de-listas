# Prueba de fuego — el pipeline entero sobre un archivo como lo manda un cliente

Paso 6 de la hoja de ruta. No es un filtro nuevo: es la **prueba de integración** de todo
lo construido (F11 puerta → F01–F08 → F12/F13/F14) sobre un archivo **sucio y realista**,
de punta a punta, hasta los dos CSV de salida + el reporte + la ficha. Los verificadores
por nodo prueban cada pieza; este prueba que **el producto ensamblado** come el archivo de
un cliente y devuelve la lista priorizada y el número.

La afirmación que valida: **"vender a un cliente nuevo = un `config` nuevo, no una sesión de
programación nueva."** El archivo sucio entero se procesa agregando **solo** un mapeo de
columnas y las decisiones comerciales del cliente en `config/`, **sin tocar una línea de
código de nodo.**

## El criterio backbone — equivalencia sucio vs. gemelo limpio (el truco de F11)

Un archivo nuevo no tiene un golden previo. La forma de verificarlo sin inventar esperados
es la de F11: el archivo sucio es la **codificación desprolija de un archivo limpio que
controlamos**.

- `data/leads_fuego_1.csv` — el sucio: separador `;`, 2–3 filas de basura arriba del
  encabezado (título, fecha de export), columnas con **nombres de cliente** (`Nombre y
  Apellido`, `Celular`, `CUIT`, `Localidad`, `Origen`, `Fecha Alta`), acentos en Latin-1 o
  BOM. Es lo que manda un cliente.
- `data/leads_fuego_1_limpio.csv` — el gemelo: **exactamente las mismas filas y los mismos
  valores de celda**, pero en forma canónica: coma, UTF-8 sin BOM, encabezado en la fila 1,
  nombres de columna canónicos, sin basura arriba.

La **única** diferencia entre los dos es la superficie que F11 tiene que neutralizar
(separador, posición del header, nombres de columna, encoding, tipo de archivo). Los valores
sucios de dato (teléfonos en cualquier formato, localidad con paréntesis, nombres basura)
son **idénticos** en los dos.

**Criterio 1:** `leads_fuego_1.csv` → salida **byte a byte idéntica** a la de
`leads_fuego_1_limpio.csv`, en los dos CSV (comercial y auditoría) **y en el reporte**. Las
dos corridas usan la misma baja y las mismas configs; lo único que cambia es el archivo
principal. Si difiere un byte, F11 dejó pasar algo de la superficie del archivo. La ficha
**sí** difiere a propósito (una dice `;` + header corrido, la otra `,` + fila 1): la ficha
se chequea aparte (criterio 4), no entra en la equivalencia.

## El criterio de verdad — celdas firma por el nodo real, esperados a mano

La equivalencia prueba que sucio y limpio **coinciden**, no que el veredicto de cada caso
difícil sea **correcto** (los dos gemelos podrían coincidir en un error). Por eso el archivo
lleva filas firma, cada una prueba una capacidad ganada con sangre, y cada una se verifica
con **esperado literal escrito a mano** sobre la corrida real del sucio (nunca contra un
oráculo que replique el nodo — es el hallazgo de F05):

| Fila | Qué prueba | Esperado (celda) |
|------|------------|------------------|
| G01 | lead limpio de alto valor (referido, celular, en zona, fresco) | **alta** — el control que sobrevive todo |
| G02 | celular `11 15 6161 7956` (`15` sin `0`, CORRECCION-F01b) | `telefono_tipo=celular`, canónico correcto, llamable |
| G03 | `+54 9 11 4161 7956` (el `9` separado, T02) | celular válido, no `invalido` |
| G04 | `15-4161-7956` (formato viejo, T05) | manejo correcto, sin el número inventado |
| G05 | dos teléfonos en una celda | el comportamiento documentado de CORRECCION-F01 |
| G06 | artefacto Excel `1.14162E+09` | `invalido`, motivo **artefacto de Excel** → descarte sin teléfono |
| G07 | teléfono `1111111111` (F13) | descarte, motivo **teléfono de relleno** |
| G08 | nombre `test` + teléfono bueno (F13) | **marca, NO descarte** — prioridad alta/media |
| G09 | duplicado por CUIL (uno más completo/fresco) | uno gana, el otro `duplicado_de` al ganador |
| G10 | duplicado por teléfono escrito distinto (`11 4161-7956` vs `011 4161-7956`) | dedup por teléfono normalizado (aparece recién tras normalizar) |
| G11 | `Morón (Buenos Aires)` (CORRECCION-F04 A) | `en_zona`, sin motivo de zona, llamable |
| G12 | localidad vacía (CORRECCION-F04 B) | motivo **sin localidad**, NO "fuera de zona", **media** no descartado |
| G13 | `Moreno` (fuera real) | **fuera de zona**, descarte |
| G14 | jurídica `30-71234567-1`, cliente vende a individuos (F12) | `tipo_persona=juridica`, descarte de segmento |
| G15 | teléfono/CUIL en la baja (F14) | descarte **opt-out** |

Code completa el archivo con unas filas limpias de relleno para que parezca una lista de
verdad (~25–30 filas). Los esperados se transcriben a mano de esta tabla.

## El número — coherencia del reporte (el entregable que se vende)

La corrida produce el reporte de F08 sobre el sucio. **Criterio 3:**

- Las **cuatro** categorías de descarte aparecen con conteo ≥ 1 — un archivo realista las
  dispara todas: **calidad de dato** (G06 sin tel, G07 basura, G09/G10 duplicado), **zona**
  (G13), **segmento** (G14), **opt-out** (G15). Que las cuatro estén pobladas es lo que hace
  a este archivo una prueba de fuego y no otro adversario chico.
- Los conteos de las subtablas **suman** al total de descartados (la aritmética cierra).
- El **ahorro en horas** está calculado con el supuesto documentado (`minutos_por_llamada:
  4`). Es "el número" del pitch.

## La baja y la limitación conocida

La baja (opt-out) va en `.xlsx` para ejercitar ese path de punta a punta:
`data/lista_baja_fuego.xlsx`, con el header en la fila 1 (sin basura arriba). El archivo
**principal** va en `;`-CSV con basura arriba **a propósito**: ese combo lo maneja
`leerTabla()`, no `leerPlanilla()`. Así la prueba de fuego corre por el path que sí saltea
basura y **no** toca la limitación registrada de `leerPlanilla()` — coherente con la
decisión de no abrir `CORRECCION-F11b` todavía.

## El config del cliente — la prueba de que escala

Todo el archivo se resuelve con un bundle de `config/` nuevo, sin código:
`config/mapeo_fuego.json` (los nombres de columna del cliente → canónicos, vía el mismo
mecanismo que `mapeo_adversario2.json` de F11) y la segmentación del cliente
(`etiquetar:true, descartar:"juridica"`, porque este cliente vende a individuos). **Criterio
5:** la fase no agrega ni un nodo nuevo; es data + config. La ficha lo confirma (abajo).

## La ficha de entrada — lo que le mostrás al cliente

**Criterio 4:** la ficha del sucio reporta el separador detectado (`;`), la fila real del
encabezado (después de la basura), y **el mapeo** de cada columna de cliente a la canónica.
Es el artefacto que prueba que el archivo se leyó bien antes de tocar un dato.

## Verificador

`verificadores/v_fuego.py` — **corre n8n de verdad**, mismo estándar. Bloques: (1)
equivalencia sucio vs limpio en com+aud+reporte, byte a byte; (2) celdas firma G01–G15 por
esperado literal; (3) coherencia del reporte (4 categorías ≥1, suma cierra, ahorro con 4
min); (4) ficha del sucio (separador, header, mapeo). Actualizá `correr_todo.py` si querés
que la prueba de fuego entre a la regresión, o dejala como verificador propio — decisión de
Pedro, anotala.

## Terminado cuando

`python verificadores/v_fuego.py` verde en los cuatro bloques, `python
verificadores/correr_todo.py` sigue verde y el golden del canónico **no se movió** (la
prueba de fuego corre sobre sus propios archivos, no sobre el canónico), y existen
`data/leads_fuego_1.csv`, `data/leads_fuego_1_limpio.csv`, `data/lista_baja_fuego.xlsx` y
`config/mapeo_fuego.json`.

En `ESTADO.md`: el número del reporte de la prueba de fuego (entraron / quedan / ahorro), y
la confirmación de que se resolvió **solo con config**, sin código de nodo nuevo.

## Fuera de alcance

- **Basura arriba en el `.xlsx`** (limitación de `leerPlanilla()`): el principal va en CSV a
  propósito. No se toca acá.
- **Un archivo de 200+ filas.** La equivalencia + las celdas firma no lo necesitan; ~30
  filas cubren los caminos. Si un cliente real trae un archivo grande, esa es la prueba con
  archivo real (paso aparte), no esta.
- **Nivel 2** (AFIP, obra social, crédito, No Llame oficial): trámites.
