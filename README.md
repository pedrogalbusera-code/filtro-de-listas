# Filtro de Listas

Workflow de n8n que recibe un CSV de contactos de un call center y devuelve la
misma lista ordenada por prioridad, con un puntaje explicable por fila y un
reporte de impacto que dice cuántos contactos entraron, cuántos quedaron útiles
y cuánto tiempo de llamadas se ahorra.

**Datos sintéticos.** El archivo de prueba (`data/leads_prueba_SINTETICO_1.csv`,
200 filas) fue generado al azar. Ninguna fila corresponde a una persona real.
Una lista real de personas no se puede subir a un repo público: un teléfono con
un CUIL identifican a alguien aunque le cambies el nombre (Ley 25.326).

## Números (CSV de prueba, 200 contactos)

| Métrica | Valor |
|---------|-------|
| Contactos procesados | 200 |
| Contactos únicos (sin duplicados) | 186 |
| **Contactos llamables** (alta + media prioridad) | **86** |
| Descartados | 114 |
| — sin teléfono utilizable | 82 |
| — duplicados | 14 |
| — fuera de zona de cobertura | 39 |
| — puntaje bajo sin descarte directo | 3 |
| Horas de operador ahorradas (supuesto: 4 min/llamada) | 7,6 h |

Un contacto puede tener más de un motivo de descarte.

---

## Lo que se descubrió construyendo esto

### 1. El validador de CUIL que daba verde y estaba mal

El validador de CUIL daba 200 de 200 válidos, todo verde. Al contrastarlo contra
la regla real de AFIP se descubrió que estaba calibrado contra el generador del
archivo de prueba, no contra la realidad.

La regla vieja decía: si el módulo 11 da resto 1, el dígito verificador es 9.
La regla correcta dice: **resto 1 es inválido** — AFIP no emite CUILs que den
resto 1 con su propio prefijo; los reemite con prefijo 23, y la reemisión valida
sola con el mismo algoritmo (verificado por fuerza bruta: 54.545 de 54.545
reemisiones validan).

El costo medido:

| Regla | Typos de un dígito no detectados |
|-------|----------------------------------|
| Vieja (resto 1 → DV 9) | **1,58%** |
| Corregida (resto 1 → inválido) | **0%** |

19 de los 200 CUILs del archivo de prueba pasaron a inválidos. Es esperable:
el archivo se generó con la regla vieja.

Y hubo un segundo error propio: la primera medición del porcentaje de typos dio
0,93% porque estaba tomando como base los 200 CUILs (incluyendo los 19 que ya
eran inválidos bajo la regla nueva). La base correcta son solo los válidos.
También quedó documentado en `ESTADO.md`.

### 2. La suite de regresión que daba verde y estaba mintiendo

La suite daba 9/9 en verde. Al mirarla en serio se descubrió que cinco de los
nueve verificadores no ejecutaban el pipeline: leían CSVs de corridas de días
anteriores. Rompías cualquier regla y seguían en verde.

Se corrigió agregando una pasada de regeneración que ejecuta el pipeline completo
antes de verificar. Después se probó de verdad: se rompió a propósito la
validación de CUIL (cambiar `cuil_valido: false` a `true` para los de resto 1)
y la suite respondió así:

```
  Verif    Estado   Tiempo   Detalle
  -------------------------------------------------------------
  v00      PASA        0s   RESULTADO: PASA (10 checks)
  v01      PASA        0s   RESULTADO: PASA (25 checks)
  v02      FALLA       0s   RESULTADO: FALLA (6 de 22 checks)
  v03      PASA        0s   RESULTADO: PASA (29 checks)
  v04      PASA        0s   RESULTADO: PASA (18 checks)
  v05      PASA      233s   RESULTADO: PASA (51 checks)
  v06      FALLA      35s   v06_puntaje: 21/24 PASA, 3 FALLA
  v07      FALLA      68s   v07_salida: 21/23 PASA, 2 FALLA
  v08      FALLA      42s   v08_reporte: 29/31 PASA, 2 FALLA
  golden   FALLA      37s   comercial difiere / auditoria difiere
  -------------------------------------------------------------
  Suite de regresion: 5/10 PASA, 5 FALLA  (total 763s)
```

La rotura se propaga hacia adelante por dependencia real: v00–v01 pasan
(anteriores a la fase rota), v02 falla (la fase rota), v03–v05 pasan (no
dependen de `cuil_valido`), v06–v08 y golden fallan (dependen del puntaje). Al
revertir, 10/10 PASA.

### 3. Los archivos que rompieron el pipeline

Se pasaron tres archivos adversarios escritos a propósito para romper el
pipeline, sin haber visto la implementación. 13 hallazgos. Los tres más graves:

1. **Separador `;`** (archivo 3): n8n parsea con coma, el output tiene cara de
   correcto (5 filas, 26 columnas, puntaje, prioridad) pero todo está vacío.
   Un cliente recibe esto y no se entera.
2. **`+54 9 11 4161 7956`**: un espacio entre `+54` y `9` pierde un celular
   válido.
3. **`15-4161-7956`**: aceptado como ambiguo con normalización incorrecta. El
   contacto se llamaría a un número equivocado.

9 de los 13 hallazgos están registrados en la suite
(`verificadores/pendientes_conocidos.py`) con su comportamiento medido. La suite
se pone roja si alguno cambia — incluso si empieza a funcionar bien — porque un
cambio no documentado es un cambio no controlado. Detalle completo en
`salidas/HALLAZGOS_ADVERSARIO.md`.

---

## Qué hace el pipeline

10 nodos Code de n8n encadenados, un nodo por responsabilidad:

1. **Pasamanos** — fuerza todo a string (guardarrail contra inferencia de tipos).
2. **Normalizar teléfono** — clasifica en celular, fijo, ambiguo o inválido.
   Canónico con prefijo `+54`; el `9` aparece solo en celular.
3. **Validar CUIL** — módulo 11 con pesos `5 4 3 2 7 6 5 4 3 2`. Resto 1 se
   rechaza.
4. **Marcar duplicados** — union-find por CUIL y por teléfono normalizado
   (últimos 10 dígitos nacionales). Nada se borra: un duplicado es una etiqueta.
5. **Completitud y cobertura** — marca contactos sin teléfono y fuera de zona.
   La zona es un parámetro (`CONFIG.zona`), cambiable sin tocar lógica.
6. **Antigüedad del lead** — días desde `fecha_carga` hasta una fecha de corte
   parametrizable. Tramos: alta (0–15), media (16–45), baja (46–90), fría (>90).
7. **Puntaje explicable** — cada regla suma o resta puntos y deja su línea en el
   motivo. La suma de los números del motivo da exactamente el puntaje.
8. **Ordenamiento** — bloque prioridad, puntaje desc, antigüedad asc, id_fila.
9. **Salida dual** — CSV comercial (9 columnas) y CSV de auditoría (26 columnas),
   ambos con BOM UTF-8.
10. **Reporte de impacto** — Markdown con las métricas recalculadas desde el CSV.

---

## Cómo se corre

### Requisitos

- Node.js 20+
- Python 3.10+
- git

### Pasos

```powershell
# 1. Arrancar n8n (Windows, PowerShell)
.\arrancar-n8n.ps1

# 2. En otra terminal, importar y ejecutar el workflow
npx n8n import:workflow --input=workflows/etapa1-final.json
npx n8n execute --id=f08reporte00001
```

Las salidas quedan en `salidas/`: `salida_comercial.csv`, `salida_auditoria.csv`
y `reporte.md`.

**Nota:** `arrancar-n8n.ps1` setea `N8N_RESTRICT_FILE_ACCESS_TO` a la carpeta
del proyecto. Sin eso, n8n bloquea el acceso al disco y las fases fallan con
`Access to the file is not allowed`.

**Nota 2:** las rutas de entrada y salida están embebidas en el JSON del
workflow como rutas absolutas. Para correrlo en otra máquina, regenerar con:

```powershell
python herramientas/gen_workflow.py workflows/etapa1-final.json "<csv_in>" "<csv_out>" --fase 08 --fecha-corte 2026-07-28 --csv-out-audit "<csv_audit>" --reporte-out "<reporte>"
```

### Suite de regresión

```powershell
python verificadores/correr_todo.py
```

Tarda ~12 minutos. Regenera todos los CSVs, corre los 9 verificadores y compara
contra golden files por SHA-256. Exit 0 si todo pasa.

---

## Limitaciones conocidas

- **El pipeline solo acepta un CSV con 6 columnas específicas** (`nombre`,
  `cuil`, `telefono`, `localidad`, `origen`, `fecha_carga`), separador coma,
  sin basura arriba del encabezado. Un archivo real de un cliente probablemente
  no cumple esto. Es el trabajo de F11, que no está hecho.

- **La normalización de teléfono reconoce 3 formatos** (`+549...` celular,
  `0XX-...` de 11 dígitos fijo, 10 dígitos pelados ambiguo). Formatos
  internacionales con espacios, el viejo `011 15 ...`, y teléfonos separados
  por `/` caen en inválido.

- **La comparación de localidades es literal.** `Morón (Buenos Aires)` cae
  fuera de zona porque no matchea `Morón`. Localidad vacía es indistinguible
  de "fuera de zona".

- **Los duplicados no transfieren datos del perdedor al ganador.** Si el
  perdedor tiene un teléfono válido distinto, se pierde.

---

## Estructura del repo

```
CLAUDE.md                    instrucciones del proyecto
ESTADO.md                    bitácora completa de cada fase
fases/                       una fase = un archivo = una sesión
data/                        CSV de entrada (sintético)
workflows/
  etapa1-final.json          el workflow completo, importable
salidas/                     CSVs y reportes de salida
  HALLAZGOS_ADVERSARIO.md    detalle de los 13 hallazgos
verificadores/
  correr_todo.py             suite de regresión (10 checks + 9 pendientes)
  pendientes_conocidos.py    9 hallazgos adversarios registrados
herramientas/
  gen_workflow.py            generador de workflows
portfolio-entry.html         entrada de portfolio (HTML)
```

Los documentos comerciales (modelo de cobro, guion de venta) quedan fuera del
repo a propósito.

## Qué viene después (y no antes)

- **Etapa 2 — ARCA.** Consulta al web service oficial para verificar condición
  fiscal. Bloqueada hasta tener monotributo, clave fiscal nivel 3 y certificado
  digital.
- **Etapa 3 — WhatsApp.** Contacto directo con el lead para verificar interés y
  obra social. Bloqueada hasta tener WhatsApp Business API.
