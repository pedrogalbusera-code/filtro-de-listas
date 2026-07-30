# Proyecto: Limpieza y priorización de listas de contactos (Etapa 1)

## Qué es esto

Un workflow de n8n que recibe un CSV de contactos y devuelve la misma lista
ordenada y anotada con tres columnas nuevas: `puntaje`, `prioridad`
(alta / media / descartado) y `motivo`.

El entregable comercial **no es la lista limpia**: es el número. Cuántos
contactos entraron, cuántos quedaron útiles, cuánto tiempo de llamadas se
ahorra y con qué supuesto. Eso es lo que se muestra en una reunión.

## Decisiones de arquitectura (cerradas)

- **La lógica vive en nodos Code (JavaScript) dentro de n8n.** No en scripts
  Python externos. El objetivo es aprender n8n construyendo.
- **n8n corre local y gratis** (`npx n8n` o Docker). Nada de plan cloud hasta
  que haya un cliente pagando.
- **Los verificadores sí son Python**, corren fuera de n8n sobre el CSV de
  salida y sobre el JSON exportado del workflow. Son la red de seguridad.
- Un nodo Code por responsabilidad. Si un nodo hace dos cosas, se parte.

## Reglas de trabajo

1. **Una fase por sesión.** El criterio de aceptación se escribe ANTES de
   tocar código. Está en `fases/FXX-*.md`.
2. **Si algo se puede verificar automáticamente, se construye el verificador.**
   Va en `verificadores/`. Una fase no cierra sin su verificador en verde.
3. **Si una sesión termina sin algo ejecutable, la sesión salió mal.**
4. **Ninguna fila se pierde en silencio.** Filas de salida == filas de entrada,
   siempre. Un descarte es una etiqueta, no una eliminación.
5. **El puntaje tiene que ser auditable.** Cada punto sumado o restado deja su
   línea de motivo. Un puntaje que nadie puede explicar no se vende.
6. **Nada de fechas hardcodeadas.** La fecha de corte es un parámetro.
7. No se agregan etapas nuevas (ARCA, WhatsApp) hasta que F00-F10 corra de
   punta a punta con el CSV de prueba.
8. No se arma interfaz web antes de que la lógica esté resuelta.

## Estructura

```
CLAUDE.md            este archivo
ESTADO.md            qué fase está cerrada y qué sigue
fases/               una fase = un archivo = una sesión
data/                CSV de entrada (sintético, sin datos reales)
workflows/           export JSON del workflow de n8n, versionado
salidas/             CSV procesados que produce el workflow
verificadores/       checks en Python, uno por fase
```

## Datos de prueba

`data/leads_prueba_SINTETICO_1.csv` — 200 filas, generado al azar, **no
corresponde a personas reales**. Los CUILs tienen dígito verificador válido
solo para poder probar la validación de formato.

Hechos medidos sobre ese archivo (base de los criterios de aceptación):

| Qué                                             | Cuánto |
|-------------------------------------------------|--------|
| Filas                                           | 200    |
| Filas completamente idénticas                   | 11     |
| Duplicados por CUIL (filas extra, 14 grupos)    | 14     |
| Teléfonos utilizables                           | 118    |
| Teléfonos no utilizables                        | 82     |
| — texto `sin dato` / `sindato`                  | 41     |
| — truncados a 6 dígitos                         | 41     |
| Formato `011-41617956` (11 díg)                 | 45     |
| Formato `+549 11 3992-7555` (13 díg)            | 42     |
| Formato `1168442737` (10 díg)                   | 31     |
| Duplicados por teléfono normalizado (filas extra)| 8     |
| Duplicados por teléfono comparando string crudo | 6      |
| Rango de fecha_carga (sin vacías)               | 2026-04-10 a 2026-07-28 |
| Localidades distintas                           | 10     |

Los **2 duplicados** que aparecen al normalizar y no antes (8 contra 6) son la
prueba de que la normalización sirve. Si un cambio los pierde, el cambio está mal.
## Límites legales (no se negocian)

- **Nada de scraping de sitios con captcha.** El padrón de la Superintendencia
  de Servicios de Salud tiene captcha para impedir exactamente esto. El camino
  oficial es el web service de ARCA con certificado digital.
- **Datos personales de terceros (Ley 25.326).** Cuando se procesen listas que
  no son propias, tiene que estar por escrito que los datos son del cliente y
  que acá solo se procesan por encargo. Datos de salud son categoría sensible.
- **Antes de aceptar procesar leads, preguntar de dónde salieron.** Si la
  respuesta es confusa, el responsable del procesamiento es quien los procesa.

## Cómo hablarle a Pedro

Castellano rioplatense, directo, sin jerga de consultor. Ya sabe programar: no
hace falta explicarle qué es una variable, sí el modelo mental de n8n (nodos,
`$json`, cómo se mueven los items). Si algo no va a funcionar, decírselo con el
motivo, sin endulzar.
