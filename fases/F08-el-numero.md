# F08 — El número (reporte de impacto)

## Objetivo
El entregable comercial. No la lista: **la cuenta del desperdicio**.

## Qué produce
Un reporte corto (Markdown o HTML de una página) con:

- Contactos que entraron: 200
- Contactos únicos después de deduplicar
- Descartados y por qué motivo, en orden de frecuencia
- Contactos de prioridad alta / media
- **Llamadas evitadas** = descartados
- **Horas de operador ahorradas** = llamadas evitadas x minutos por llamada / 60
- **El supuesto, escrito al lado del número**, no en una nota al pie

## Decisión que Pedro tiene que tomar antes de empezar
Minutos promedio por llamada (intento fallido incluido) y costo horario del
operador. Sin esos dos números el reporte no cierra en plata. Si no los sabe,
se pregunta al cliente en la reunión — y esa pregunta ya es parte del pitch.

## Criterio de aceptación
1. Todo número del reporte se puede recalcular desde el CSV de salida. Cero
   valores escritos a mano.
2. Todo supuesto está visible junto al número que lo usa.
3. El reporte se genera solo al correr el workflow, no se arma a mano.
4. Un gerente que no vio nunca el proyecto lo entiende en menos de un minuto.

## Verificador
`verificadores/v08_reporte.py` — recalcula cada métrica desde el CSV de salida y
la compara contra la que muestra el reporte. Si difieren, falla.

## Nota comercial
El pitch no es el software: es hacer esta cuenta en voz alta con el gerente.
Ofrecer procesar una lista real gratis y medir contactos útiles por hora antes y
después. Cobrar armado inicial + abono mensual por volumen. **Nunca comisión por
venta:** ata el ingreso a la performance del call center, que no se controla
desde acá.
