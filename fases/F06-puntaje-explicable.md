# F06 — Puntaje explicable

## Objetivo
Un número por contacto, construido como suma de reglas, donde cada regla deja
su línea de motivo. Es la fase central del producto.

## Decisión que Pedro tiene que tomar antes de empezar
Los pesos. Propuesta de arranque, para discutir y ajustar:

| Regla                          | Puntos |
|--------------------------------|--------|
| Teléfono celular               | +30    |
| Teléfono fijo                  | +10    |
| Teléfono ambiguo (10 díg sin prefijo) | +18 |
| Teléfono inválido              | descarta |
| CUIL válido                    | +15    |
| CUIL inválido                  | -10    |
| En zona de cobertura           | +20    |
| Fuera de zona                  | descarta |
| Frescura alta / media / baja / fría | +25 / +15 / +5 / 0 |
| Origen: referido               | +15    |
| Origen: formulario web / evento| +10    |
| Origen: campaña Meta           | +5     |
| Origen: base propia            | 0      |
| Es duplicado (perdedor)        | descarta |

Umbrales: **alta** >= 70, **media** 40 a 69, **descartado** < 40 o cualquier
regla de descarte directo.

Los pesos y umbrales viven en **un solo objeto de configuración** arriba del
nodo Code. Cambiar la estrategia comercial no puede requerir tocar la lógica.

## Criterio de aceptación
1. Los 200 items tienen `puntaje`, `prioridad` y `motivo`.
2. **Auditabilidad:** para cualquier fila, sumar los puntos listados en `motivo`
   da exactamente `puntaje`. Esto lo comprueba el verificador, fila por fila.
3. Un descarte directo siempre dice cuál regla lo descartó.
4. Cambiar un peso en la configuración cambia el resultado sin tocar otra línea.
5. Las tres prioridades tienen contactos con el CSV de prueba (si "alta" queda
   vacía, los umbrales están mal calibrados y hay que ajustarlos ahí mismo).

## Verificador
`verificadores/v06_puntaje.py` — reconstruye el puntaje de las 200 filas desde
sus motivos y falla si alguna no cierra. Este es el verificador más importante
del proyecto: es la prueba de que el puntaje se le puede vender a alguien.
