# F12 — Persona física vs. jurídica

Filtro 8 del catálogo. El primero de los **filtros nuevos de Nivel 1**: no
consulta ninguna fuente externa, sale del dato que la lista ya trae.

## Objetivo

Etiquetar cada contacto como `fisica` / `juridica` / `desconocida` a partir del
**prefijo del CUIL** que F02 ya normaliza, y permitir **descartar** el tipo que
el cliente no busca — sin tocar puntaje ni orden cuando la segmentación está
apagada.

Si el cliente le vende a individuos, las empresas (CUIT 30/33/34) sobran; si le
vende a empresas, al revés. Es una decisión comercial **de un cliente**, no del
producto: por eso vive en `config/`, apagada por defecto.

## La regla que manda sobre todo lo demás

La segmentación es **config-gated y apagada por defecto**. Con
`config/segmentacion.json` como está en el repo
(`{"etiquetar": false, "descartar": null}`), el nodo devuelve los items **tal
cual**, sin agregar ni una clave, y las dos salidas del CSV canónico quedan
**byte a byte idénticas a los golden de F09**:

- comercial `9a6884603f9128c29a7503cb25b8417ceb233b58bdd89e9053bf4f486a61dcb4`
- auditoría `ae6fcc5f146d6ec59395b3fb09a5bbdfcd764303e762a287dfe6a44623fd9cd2`

Agregar un filtro nuevo **no puede mover el pipeline base**. Si el golden se
mueve con la config por defecto, el bug es de esta fase.

## La tabla es el spec

| Entrada (prefijo de `cuil_norm`) | `tipo_persona` |
|----------------------------------|----------------|
| 20, 23, 24, 27                   | `fisica`       |
| 30, 33, 34                       | `juridica`     |
| sin CUIL / CUIL que no tiene 11 dígitos | `desconocida` |
| prefijo fuera del set (ej. `99-…`) | `desconocida` |
| `30-…` con **DV inválido**       | `juridica` — manda el prefijo, no el DV |

### Las cuatro reglas que no se negocian

1. **Se clasifica por prefijo, aunque el DV sea inválido.** Una empresa `30-…`
   con un typo en el dígito verificador sigue siendo una empresa. `desconocida`
   es solo cuando **no hay prefijo utilizable**; que el DV falle es otra cosa y
   para eso está `cuil_valido`.
2. **`desconocida` NUNCA se descarta.** No saber qué es un contacto no es motivo
   para tirarlo: sería repetir el error de "sin dato = fuera" que F04 ya tiene
   medido (T21). Solo se descarta el tipo **explícito** que pida la config, y
   `descartar: "desconocida"` **frena el generador** con un mensaje que explica
   por qué.
3. **Descartar = marcar con motivo legible, nunca borrar la fila.** Regla 4 del
   `CLAUDE.md`, regla 1 del catálogo. El motivo es
   `persona jurídica (segmento no buscado) +0 → descarte`.
4. **`tipo_persona` no suma ni resta puntaje.** El único efecto sobre el score
   es el descarte directo, y solo cuando la config lo pide. Una lista etiquetada
   y la misma lista sin etiquetar tienen el mismo puntaje fila por fila.

## Diseño

- **`config/segmentacion.json`** (por cliente, versionado). El del repo es el
  default apagado. Se embebe **al generar** el workflow, igual que el mapeo de
  F11: cambiar de cliente es editar un JSON y regenerar, nunca editar JavaScript.
  El generador **valida fuerte**: `etiquetar` tiene que ser booleano y
  `descartar` tiene que ser `null`, `"fisica"` o `"juridica"`. Cualquier otra
  cosa aborta al generar, no se convierte en un descarte silencioso en n8n.
- **Dónde va el nodo:** después de F05 y **antes de F06**. Necesita `cuil_norm`
  (F02) y tiene que llegar antes del puntaje, que es donde viven los descartes
  directos. F12 solo marca `descarte_segmento` + `motivo_segmento`; **la
  decisión de prioridad sigue estando en un solo nodo** (F06), junto a los otros
  tres descartes directos.
- **La fase 11 queda intacta.** F12 es una entrada nueva en `FASES`
  (`workflows/11-persona.json`), no una modificación de F11: `v11_puerta.py`
  sigue verificando exactamente lo que cerró.
- **`tipo_persona` sale solo en el CSV de auditoría**, por el mismo mecanismo de
  columnas opcionales que ya usaban `extra_*` y `advertencia_entrada`. El CSV
  comercial mantiene sus 9 columnas fijas para todas las configs.

## Criterio de aceptación

1. **Config por defecto:** los dos SHA-256 sobre el CSV canónico idénticos al
   golden de F09, y la columna `tipo_persona` **no existe**.
2. **Con `{etiquetar: true, descartar: "juridica"}`:** cada fila da exactamente
   el `tipo_persona` de la tabla, verificado **por celda** contra literales
   escritos a mano; las jurídicas quedan `descartado` con el motivo; las físicas
   y las desconocidas **no** lo llevan; ninguna `desconocida` queda descartada;
   ninguna fila se borra.
3. **Con `{etiquetar: true, descartar: null}`:** sacando la columna
   `tipo_persona`, la auditoría vuelve a ser el golden celda por celda y en el
   mismo orden de filas, y el comercial no se movió ni un byte.

## Verificador

`verificadores/v12_persona.py` — **corre n8n de verdad** por CLI (import +
`--id`), mismo estándar que v05/v06/v07/v11. Los esperados son literales
transcriptos a mano desde la tabla de arriba: **prohibido** calcularlos con la
lógica del nodo, que es el hallazgo de F05 (un oráculo comparado contra sí
mismo).

Dos archivos de entrada para el bloque 2:

- **`data/leads_segmento_1.csv`** (11 filas, nuevo). Cubre los **siete**
  prefijos y los tres bordes que ningún archivo del repo tenía: un `33-…`, un
  `34-…` y un `30-…` con DV roto. Todas las filas son limpias a propósito
  (teléfono válido, en zona, fecha fresca, origen referido) para que el **único**
  descarte posible sea el del segmento.
- **`data/leads_adversario_1.csv`** (48 filas). El archivo real de la corrida
  adversaria: aporta el CUIL vacío (T23), el de 9 dígitos (T24), el prefijo `99`
  (T25) y la única empresa del repo (T30), más los CUILs escritos con puntos,
  espacios y sin separadores (T26–T28).

## Fuera de alcance

- **El reporte de impacto (F08) no cuenta los descartes por segmento.** Con la
  segmentación encendida, esas filas suman al total de descartados pero **no
  aparecen en ninguna de las dos subtablas de motivos** (el reporte busca
  "sin teléfono", "fuera de zona" y "duplicado"). Hoy no molesta —la
  segmentación está apagada y ningún cliente la usa—, pero **hay que agregarle
  su fila al reporte antes de vendérsela a alguien**. Queda registrado, no
  parcheado a las apuradas.
- **Normalizar los valores de `origen`** (sigue siendo de F11/F06).
- **Verificar que el CUIL exista en AFIP.** Eso es Nivel 2, Etapa 2, y sigue
  bloqueado por trámites. F12 lee un prefijo, no consulta un padrón.
