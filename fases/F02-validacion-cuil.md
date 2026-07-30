# F02 — Validación de CUIL

## Objetivo
Derivar `cuil_norm` (11 dígitos, sin guiones) y `cuil_valido` (booleano),
validando formato **y dígito verificador módulo 11**.

## Regla
- Prefijos válidos: 20, 23, 24, 27 (persona física); 30, 33, 34 (jurídica).
- Dígito verificador: pesos `5 4 3 2 7 6 5 4 3 2` sobre los primeros 10 dígitos,
  suma, resto de 11. Resto 0 -> DV 0. Resto 1 -> caso especial. Si no, 11 - resto.
- Un CUIL con formato correcto y DV incorrecto es **inválido**, no "dudoso".

## Criterio de aceptación
1. Los 200 items tienen `cuil_norm` y `cuil_valido`.
2. **Cero falsos inválidos**: los CUILs del CSV sintético fueron generados con
   DV válido, así que la validación tiene que aprobarlos. Si rechaza alguno,
   el bug está en el algoritmo, no en el dato.
3. La función rechaza correctamente casos alterados a propósito (cambiar un
   dígito del medio tiene que dar inválido).
4. `cuil_norm` conserva los 11 dígitos como string, sin perder ceros a la izquierda.

## Verificador
`verificadores/v02_cuil.py` — corre la validación sobre los 200 CUILs (espera
200 válidos) y sobre una lista de CUILs mutados (espera 100% inválidos).

## Fuera de alcance
Consultar el padrón de ARCA. Eso es Etapa 2 y está bloqueado hasta tener
monotributo y certificado digital. **No empezar por acá.**
