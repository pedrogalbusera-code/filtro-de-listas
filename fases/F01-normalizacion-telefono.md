# F01 — Normalización de teléfono

## Objetivo
Derivar dos campos nuevos por contacto: `telefono_norm` (canónico) y
`telefono_tipo` (`celular` | `fijo` | `ambiguo` | `invalido`). El campo original
no se toca.

## Lo que hay en el CSV de prueba (medido)

| Entrada             | Filas | Interpretación            |
|---------------------|-------|---------------------------|
| `011-41617956`      | 45    | fijo AMBA                 |
| `+549 11 3992-7555` | 42    | celular (el 9 lo marca)   |
| `1168442737`        | 31    | 10 dígitos sin prefijo, **ambiguo** |
| `116056`            | 41    | truncado -> inválido      |
| `sin dato`/`sindato`| 41    | texto -> inválido         |

**Utilizables: 118. No utilizables: 82.** El 41% de la lista no se puede llamar
y hoy nadie lo sabe hasta que un operador lo intenta. Ese dato solo ya justifica
la reunión.

## La trampa central de esta fase
El `9` de `+549` es lo único que distingue celular de fijo en AMBA. Si el
canónico lo descarta y guarda solo `11XXXXXXXX`, un fijo y un celular con los
mismos 8 dígitos finales colisionan y la deduplicación de F03 los fusiona mal.

**Decisión: el canónico conserva el 9.** `+5491139927555` para celular,
`+541141617956` para fijo. El tipo se infiere del formato de entrada, no del
canónico ya recortado.

Los 31 de 10 dígitos son ambiguos de verdad: pueden ser cualquiera de los dos.
Se marcan `ambiguo` y se les da un puntaje intermedio en F06. **No se adivina.**

## Criterio de aceptación
1. Los 200 items tienen `telefono_norm` y `telefono_tipo`. Ninguno indefinido.
2. La misma línea escrita en dos formatos distintos produce **exactamente el
   mismo** `telefono_norm`.
3. Un fijo y un celular con los mismos 8 dígitos finales producen canónicos
   **distintos**.
4. Los 41 `sin dato`/`sindato` -> `invalido`, con `telefono_norm` vacío (no la
   cadena "undefined", no "+549").
5. Los 41 truncados de 6 dígitos -> `invalido`. No se completan ni se adivinan.
6. El conteo final da 118 utilizables y 82 inválidos. Si da otra cosa, hay una
   rama mal escrita.
7. La función es pura: mismo input, mismo output, sin estado.

## Verificador
`verificadores/v01_telefono.py` — tabla de casos entrada/salida esperada (los
cinco formatos, el caso de colisión fijo/celular y al menos un borde por rama),
más el conteo 118/82 sobre los 200 items reales.

## Formatos agregados después del cierre

La fase cerró con los 5 formatos del CSV de prueba. Dos correcciones posteriores
ampliaron el normalizador **sin mover el golden** (los formatos nuevos no están
en el archivo canónico):

- **`CORRECCION-F01`** — internacional con y sin `+`, el `9` separado por
  espacios, el formato viejo con `15`, artefactos de Excel (`.0`, notación
  científica) y celdas con dos teléfonos. Y el arreglo que más importaba:
  `15-4161-7956` **sin código de área** pasó de `ambiguo` con un número
  inventado a `invalido`.
- **`CORRECCION-F01b`** — el `0` de salida del formato con `15` es **opcional**:
  `11 15 6161 7956` es el mismo celular que `011 15 6161-7956` y que
  `+54 9 11 6161-7956`. Los tres dan `+5491161617956`. Sigue exigiendo el
  marcador `15` después del área: no acepta 12 dígitos cualesquiera. Es seguro
  porque ningún fijo AMBA tiene 12 dígitos.

## Fuera de alcance
Deduplicar. Acá solo se normaliza; comparar es F03.
