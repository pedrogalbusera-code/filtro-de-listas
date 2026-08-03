# F04 — Completitud y cobertura

## Objetivo
Marcar contactos con datos insuficientes para trabajar, y contactos fuera de la
zona de cobertura del cliente.

## Decisión que Pedro tiene que tomar antes de empezar
**Qué localidades cuentan como "en zona".** Las 10 del CSV son: Castelar, Haedo,
Villa Luzuriaga, Morón, Moreno, Hurlingham, Merlo, San Justo, Ituzaingó,
Ramos Mejía. Sin esa lista, esta fase no arranca.

La lista va como **parámetro del workflow**, no hardcodeada en el nodo Code: el
próximo cliente va a tener otra zona.

## Reglas
- **Datos insuficientes:** sin teléfono utilizable (`telefono_tipo=invalido`) el
  contacto no es llamable, punto. Sin nombre, es llamable pero peor.
- **Fuera de cobertura:** localidad que no está en la lista de zona. Se compara
  normalizando (minúsculas, sin tildes, sin espacios de más): "Morón", "moron"
  y "MORON" son la misma localidad.
- Cada marca deja su motivo en texto legible, no un código.

## Criterio de aceptación
1. Todo contacto marcado tiene al menos un motivo escrito en castellano.
2. La lista de zona se cambia desde un solo lugar y el resultado cambia acorde.
3. Localidades escritas con distinta capitalización o sin tilde matchean igual.
4. Un contacto puede acumular varios motivos y los conserva todos.
5. Siguen saliendo 200 items.

## Verificador
`verificadores/v04_cobertura.py` — verifica que ningún marcado quede sin motivo,
que ningún no-marcado tenga motivo, y corre la comparación de localidades con
variantes de tilde y capitalización.

## Corrección posterior — CORRECCION-F04 (2026-08-02)

La fase cerró con match exacto sobre el normalizado, y eso dejaba dos defectos
que cualquier archivo real dispara el primer día. Los dos están corregidos:

1. **El adorno de la localidad.** Antes de comparar se saca **un** paréntesis
   final y **un** sufijo `, <resto>`: `Morón (Buenos Aires)` y
   `Morón, Buenos Aires` son `moron`. Después, match **exacto** sobre el núcleo
   — nunca substring ni prefijo (con prefijo, `castelar` matchearía cualquier
   cosa que empiece con castelar).
2. **"Sin localidad" ≠ "fuera de zona".** La localidad vacía tiene motivo propio
   (`sin localidad`) y **no descarta**: un contacto sin localidad con teléfono
   bueno sigue siendo llamable. Vale **0 puntos** (decisión de Pedro): no cobra
   el bono de zona, pero tampoco sufre el descarte. Es el mismo criterio que
   `desconocida` en F12 y que "sin nombre" acá al lado — marca, no descarte.

**Fuera de alcance:** no desambigua por provincia. Un `San Justo (Santa Fe)`
daría en zona igual que el bonaerense, pero ese agujero ya existía con el
`San Justo` pelado. Necesita que la zona lleve provincia en el `config`.

Verificado por `data/leads_localidad_1.csv` (5 filas) **por el nodo real**, con
esperados escritos a mano y mirando la **prioridad** end-to-end: el punto de la
regla 2 no es el texto del motivo, es que la fila no quede descartada.
