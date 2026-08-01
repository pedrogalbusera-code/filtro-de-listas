# Ficha de entrada — leads_adversario_2.csv

Generada por el workflow ANTES de confiar en la corrida. Todos los
numeros salen del archivo de origen, no de la salida.

| Campo | Valor |
|-------|-------|
| Estado | **ACEPTADO** |
| Archivo | C:\Users\pedro\OneDrive\Desktop\anaze\cosas\call center\data\leads_adversario_2.csv |
| Tamaño | 798 bytes |
| Formato | CSV / texto plano |
| Separador detectado | coma |
| Encoding | UTF-8 con BOM |
| Encabezado en la linea | 4 |
| Lineas salteadas arriba del encabezado | 3 |
| Filas de datos leidas | 7 |
| Filas vacias ignoradas | 1 |
| Filas con los 6 campos canonicos vacios | 0 |

## Lineas salteadas (basura arriba del encabezado)

- linea 1: LISTADO DE CONTACTOS - PLANILLA COMERCIAL
- linea 2: Exportado el 26/07/2026 - Uso interno
- linea 3: (vacia)

## Columnas encontradas

- Nombre y Apellido
- Documento
- Celular
- Zona
- Origen del lead
- Fecha de alta
- Observaciones

## Mapeo aplicado

| Columna del archivo | Canonica | Como se resolvio |
|---------------------|----------|------------------|
| Nombre y Apellido | nombre | mapeo del cliente |
| Documento | cuil | mapeo del cliente |
| Celular | telefono | mapeo del cliente |
| Zona | localidad | mapeo del cliente |
| Origen del lead | origen | mapeo del cliente |
| Fecha de alta | fecha_carga | mapeo del cliente |

## Columnas extra (se conservan en la auditoria, no puntuan)

- Observaciones

## Filas incompletas (los campos que faltan quedan vacios)

- linea 10: 4 de 7 campos

## Valores distintos de `origen`

Se listan como vienen; NO se normalizan (eso es otra fase). Si estas
etiquetas no coinciden con las que puntua F06, el puntaje de origen da 0.

| Valor | Filas |
|-------|-------|
| (vacio) | 1 |
| Base propia | 1 |
| Evento | 1 |
| Meta | 1 |
| Referido | 2 |
| Web | 1 |

