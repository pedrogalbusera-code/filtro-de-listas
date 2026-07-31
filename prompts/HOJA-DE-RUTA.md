# Hoja de ruta — cómo avanzar sin frenar

Este archivo existe para una cosa: que avanzar sea **copiar un prompt, pegarlo en
Claude Code, y pasar al siguiente** cuando ese cierra en verde. No hay que decidir
nada en el medio salvo donde diga **[decisión tuya]**.

## El modelo

- Una sesión de Code = un prompt de esta lista, en orden.
- Cada prompt ya trae: qué construir, los números que son criterio, qué verificador,
  qué está prohibido y cuándo está terminado.
- Code cierra cuando su verificador da verde. Recién ahí pasás al siguiente.
- Si un prompt dice "frená y mostrame", Code para y te trae el dato. Eso no es un
  error: es el diseño.

## Orden de sesiones

| # | Prompt para pegarle a Code | Estado del prompt | Qué deja listo |
|---|----------------------------|-------------------|----------------|
| 1 | `prompts/CIERRE-F10.md` | ✅ escrito y actualizado | Repo + commit + criterio en limpio. Cierra la demo. |
| 2 | `prompts/CORRECCION-F01.md` | ✅ escrito (nuevo) | Teléfonos: recupera los formatos perdidos, arregla el `15-` peligroso. |
| 3 | `prompts/CORRECCION-F02.md` | ✅ escrito | CUIL: `resto 1 → inválido`. Baja los typos no detectados a 0%. |
| 4 | `prompts/F11.md` | ✅ escrito | **La puerta de entrada.** Acá empieza a comer archivos reales. |
| 5 | Fases nuevas de filtros Nivel 1 | ⏳ las escribo yo cuando llegues al 4 | Física/jurídica, basura, lista negra/opt-out. |
| 6 | Prueba de fuego | ⏳ | Un archivo real con `;` y columnas renombradas, de punta a punta. |

Con el 1 al 4 el producto **funciona sobre el archivo de un cliente real**. El 5 es
"descartar todo lo posible" con los datos de la lista. La Etapa 2 (obra social,
crédito, AFIP) viene después y necesita trámites — ver `CATALOGO-FILTROS.md`.

## Decisiones que ya tomé por vos (para no frenarte)

- **El guion de venta y el catálogo de filtros NO van al repo público.** Tienen el
  modelo de cobro y la estrategia comercial; un cliente que llega por el portfolio
  no tiene por qué leerlos antes de hablar con vos. Van al `.gitignore`, quedan en
  tu máquina. Ya está escrito así en `CIERRE-F10.md` punto 6.
- **El catálogo se guarda en la raíz del repo** como `CATALOGO-FILTROS.md` (pero
  gitignoreado, por lo de arriba).
- **El repo de GitHub lo creo yo** cuando llegues a cerrar F10 (sesión 1), no antes:
  hasta que F10 no esté lista para commitear, un repo vacío no suma. Ojo: GitHub usa
  login de GitHub, no de Google — cuando lo cree te aviso si necesito que estés
  logueado en el navegador.

## Qué hace cada uno

- **Vos:** pegás el prompt, mirás que Code cierre en verde, pasás al siguiente.
- **Code:** escribe el código y corre los verificadores.
- **Yo (Claude):** escribo los prompts, reviso los entregables corriendo las
  verificaciones (no leyéndolas), tomo las decisiones de producto que pueda tomar sin
  vos, y creo el repo cuando toque.

## Si algo se pone rojo

No ajustes el verificador para que pase. Traeme el output (la tabla de la suite, el
diff del golden, lo que sea) y lo resolvemos. Un check que se afloja para pasar es la
forma más cara de mentirse — ya nos pasó con la suite de F09.
