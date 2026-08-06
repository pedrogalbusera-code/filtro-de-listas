# Ficha de entrada — leads_fuego_1.csv

Generada por el workflow ANTES de confiar en la corrida. Todos los
numeros salen del archivo de origen, no de la salida.

| Campo | Valor |
|-------|-------|
| Estado | **ACEPTADO** |
| Archivo | C:\Users\pedro\OneDrive\Desktop\anaze\cosas\call center\data\leads_fuego_1.csv |
| Tamaño | 2135 bytes |
| Formato | CSV / texto plano |
| Separador detectado | punto y coma |
| Encoding | Latin-1 (no era UTF-8 valido) |
| Encabezado en la linea | 3 |
| Lineas salteadas arriba del encabezado | 2 |
| Filas de datos leidas | 25 |
| Filas vacias ignoradas | 0 |
| Filas con los 6 campos canonicos vacios | 0 |

## Lineas salteadas (basura arriba del encabezado)

- linea 1: Listado de contactos - Exportado del CRM del cliente
- linea 2: Fecha de exportación: 28/07/2026

## Columnas encontradas

- Nombre y Apellido
- Documento
- Celular
- Zona
- Origen del Contacto
- Fecha de Alta

## Mapeo aplicado

| Columna del archivo | Canonica | Como se resolvio |
|---------------------|----------|------------------|
| Nombre y Apellido | nombre | mapeo del cliente |
| Documento | cuil | mapeo del cliente |
| Celular | telefono | mapeo del cliente |
| Zona | localidad | mapeo del cliente |
| Origen del Contacto | origen | mapeo del cliente |
| Fecha de Alta | fecha_carga | mapeo del cliente |

## Advertencias

- el archivo no es UTF-8; se leyo como Latin-1 (revisar tildes en la salida)

## Valores distintos de `origen`

Se listan como vienen; NO se normalizan (eso es otra fase). Si estas
etiquetas no coinciden con las que puntua F06, el puntaje de origen da 0.

| Valor | Filas |
|-------|-------|
| referido | 25 |

