# Ficha de entrada — leads_adversario_4.xlsx

Generada por el workflow ANTES de confiar en la corrida. Todos los
numeros salen del archivo de origen, no de la salida.

| Campo | Valor |
|-------|-------|
| Estado | **ACEPTADO** |
| Archivo | C:\Users\pedro\OneDrive\Desktop\anaze\cosas\call center\data\leads_adversario_4.xlsx |
| Tamaño | n/d |
| Formato | planilla (xlsx) |
| Separador detectado | n/a (planilla) |
| Encoding | n/a (planilla) |
| Encabezado en la linea | 1 |
| Lineas salteadas arriba del encabezado | 0 |
| Filas de datos leidas | 4 |
| Filas vacias ignoradas | 0 |
| Filas con los 6 campos canonicos vacios | 0 |

## Columnas encontradas

- nombre
- cuil
- telefono
- localidad
- origen
- fecha_carga

## Mapeo aplicado

| Columna del archivo | Canonica | Como se resolvio |
|---------------------|----------|------------------|
| nombre | nombre | nombre canonico |
| cuil | cuil | nombre canonico |
| telefono | telefono | nombre canonico |
| localidad | localidad | nombre canonico |
| origen | origen | nombre canonico |
| fecha_carga | fecha_carga | nombre canonico |

## Advertencias

- fila 2 de datos: telefono llego como numero de planilla (posible perdida del 0 inicial): artefacto de Excel

## Valores distintos de `origen`

Se listan como vienen; NO se normalizan (eso es otra fase). Si estas
etiquetas no coinciden con las que puntua F06, el puntaje de origen da 0.

| Valor | Filas |
|-------|-------|
| evento | 1 |
| referido | 2 |
| web | 1 |

