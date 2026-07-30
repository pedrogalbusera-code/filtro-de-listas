# F10 — Empaquetado y portfolio

## Objetivo
Cerrar la Etapa 1 como algo mostrable y vendible.

## Qué construir
1. **Export final** del workflow a `workflows/etapa1-final.json`, importable en
   una instalación limpia de n8n.
2. **README** del repo: qué resuelve, cómo se corre, qué números dio.
3. **Entrada de portfolio** en `pedrogalbusera-code.github.io/webs-para-negocios/portfolio/`,
   con la misma estructura que los otros tres proyectos: situación, qué encontré,
   qué construí, con los números.
4. **Guion de venta de una carilla**: la cuenta del desperdicio, la oferta de
   procesar una lista real gratis, y el modelo de cobro (armado + abono, nunca
   comisión).

## Criterio de aceptación
1. Importar el JSON en un n8n limpio y correr el CSV de prueba reproduce el
   golden de F09. Si no reproduce, el workflow depende de algo no versionado.
2. El README lo sigue alguien que nunca vio el proyecto.
3. La entrada de portfolio dice números concretos, no adjetivos.

## Regla que no se rompe
**n8n entra al CV recién ahora**, cuando el workflow existe y corrió de punta a
punta. No antes. Y no se lista ninguna herramienta que no se haya usado: en una
entrevista técnica eso se cae en la primera pregunta.

## Qué viene después (y no antes)
- **Etapa 2 — ARCA.** Bloqueada hasta tener monotributo, clave fiscal nivel 3 y
  certificado digital. Web service oficial `ws_sr_constancia_inscripcion`.
- **Etapa 3 — WhatsApp.** Bloqueada hasta tener WhatsApp Business API,
  idealmente la del cliente, no la propia.

Si aparece la tentación de arrancar por cualquiera de las dos antes de cerrar
F10, el resultado predecible son semanas de trámites sin un solo workflow hecho.
