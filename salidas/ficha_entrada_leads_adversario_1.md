# Ficha de entrada — leads_adversario_1.csv

Generada por el workflow ANTES de confiar en la corrida. Todos los
numeros salen del archivo de origen, no de la salida.

| Campo | Valor |
|-------|-------|
| Estado | **ACEPTADO** |
| Archivo | C:\Users\pedro\OneDrive\Desktop\anaze\cosas\call center\data\leads_adversario_1.csv |
| Tamaño | 3462 bytes |
| Formato | CSV / texto plano |
| Separador detectado | coma |
| Encoding | UTF-8 sin BOM |
| Encabezado en la linea | 1 |
| Lineas salteadas arriba del encabezado | 0 |
| Filas de datos leidas | 48 |
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

## Valores distintos de `origen`

Se listan como vienen; NO se normalizan (eso es otra fase). Si estas
etiquetas no coinciden con las que puntua F06, el puntaje de origen da 0.

| Valor | Filas |
|-------|-------|
| base propia | 5 |
| campaña Meta | 7 |
| evento | 13 |
| formulario web | 2 |
| referido | 21 |

