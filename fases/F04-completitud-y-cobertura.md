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
