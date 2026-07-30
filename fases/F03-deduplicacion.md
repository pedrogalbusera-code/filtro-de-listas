# F03 — Deduplicación

## Objetivo
Marcar duplicados por CUIL y por teléfono normalizado, decidiendo con una regla
explícita cuál copia sobrevive y dejando rastro de la fusión.

## Lo que hay en el CSV de prueba (medido)

| Criterio                                   | Filas extra |
|--------------------------------------------|-------------|
| Filas completamente idénticas               | 11          |
| Duplicados por CUIL (14 grupos de 2)        | 14          |
| Duplicados por teléfono normalizado         | 8           |
| Duplicados por teléfono comparando crudo    | 6           |

Los duplicados por CUIL y por teléfono se solapan en parte: el total de filas
únicas no es una resta directa. El verificador reporta los tres números por
separado y también el conjunto unión.

## Reglas
1. **Duplicado por CUIL** (`cuil_norm` igual). Identidad más fuerte, gana sobre
   el criterio de teléfono.
2. **Duplicado por teléfono normalizado** (`telefono_norm` igual y no vacío).
   Los 82 teléfonos inválidos tienen `telefono_norm` vacío y **no se agrupan
   entre sí**. Si se agrupan, aparece un falso grupo de 82 y el resultado es
   basura — es el bug más caro de esta fase.
3. **Quién sobrevive:** el registro con `fecha_carga` más reciente. Si empatan,
   el que tenga más campos completos. Si vuelven a empatar, el primero del
   archivo (estable, reproducible).
4. Los perdedores quedan con `es_duplicado=true` y `duplicado_de=<id ganador>`.
   **No se borran.** Regla 4 del CLAUDE.md: nada desaparece en silencio.

## Criterio de aceptación
1. Detecta **14 duplicados por CUIL**.
2. Detecta **8 duplicados por teléfono normalizado** — no 6. Los 2 de diferencia
   son los que solo aparecen después de aplicar F01: son la prueba de que la
   normalización sirve.
3. Ningún grupo por teléfono contiene registros con `telefono_norm` vacío.
4. Cada `duplicado_de` referencia un id que existe y que no es a su vez duplicado.
5. Ningún grupo tiene dos ganadores.
6. Siguen saliendo 200 items del workflow.

## Trampa conocida
Si el conteo por teléfono da 6, se están comparando strings crudos y F01 no se
está usando. Si da 82 o más, los inválidos se están agrupando entre sí.
