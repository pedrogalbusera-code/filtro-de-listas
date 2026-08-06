# Ficha de entrada — leads_fuego_1.csv

Generada por el workflow ANTES de confiar en la corrida. Todos los
numeros salen del archivo de origen, no de la salida.

| Campo | Valor |
|-------|-------|
| Estado | **RECHAZADO** |
| Motivo del rechazo | F11 RECHAZO — archivo: C:\Users\pedro\OneDrive\Desktop\anaze\cosas\call center\data\leads_fuego_1.csv — detectado: columnas canonicas sin resolver: [cuil, origen]. Columnas del archivo: [Nombre y Apellido, Documento, Celular, Zona, Origen del Contacto, Fecha de Alta] — esperado: resolverlas por config/mapeo_<cliente>.json o config/sinonimos.json; no se adivina por parecido ni por posicion |
| Archivo | C:\Users\pedro\OneDrive\Desktop\anaze\cosas\call center\data\leads_fuego_1.csv |
| Tamaño | 2135 bytes |
| Formato | CSV / texto plano |
| Separador detectado | punto y coma |
| Encoding | Latin-1 (no era UTF-8 valido) |
| Encabezado en la linea | 3 |
| Lineas salteadas arriba del encabezado | 2 |
| Filas de datos leidas | 0 |
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

## Columnas canonicas SIN RESOLVER

- cuil
- origen

## Advertencias

- el archivo no es UTF-8; se leyo como Latin-1 (revisar tildes en la salida)

