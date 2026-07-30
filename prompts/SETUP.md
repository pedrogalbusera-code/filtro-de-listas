Estás arrancando a trabajar en este repo. Antes de construir nada, leé
`CLAUDE.md`, `ESTADO.md` y `prompts/README.md`.

# SETUP — Entorno, una sola vez

Esta sesión no construye nada del producto. Su único trabajo es dejar la máquina
lista y **decir en voz alta qué falta instalar, antes de que empiece la primera
fase**.

## Qué comprobar

Corré cada comprobación y mostrá la versión que devuelve:

| Qué        | Comando            | Mínimo    | Para qué                          |
|------------|--------------------|-----------|-----------------------------------|
| Node.js    | `node -v`          | 20 o más  | n8n corre sobre Node              |
| npm        | `npm -v`           | 10 o más  | para `npx n8n`                    |
| Python     | `python --version` | 3.10+     | los verificadores                 |
| git        | `git --version`    | cualquiera| versionar el workflow y el golden |

## Reglas de instalación

- **No instales nada sin preguntar.** Si falta algo, decí qué falta, proponé el
  comando exacto, y esperá el OK de Pedro.
- **n8n NO se instala global.** Se corre con `npx n8n`. Motivo: la versión queda
  atada al proyecto y no ensucia la máquina. Si `npx n8n` falla, avisá con el
  error completo antes de intentar cualquier otra cosa.
- **Nada de paquetes de pago ni servicios en la nube.** No hay cliente pagando
  todavía. Si una librería resuelve algo, que sea de la biblioteca estándar o
  gratuita y conocida.
- Si los verificadores necesitan alguna librería de Python, decilo ahora. La
  intención es que anden con biblioteca estándar sola; si proponés una
  dependencia, justificá por qué no alcanza con `csv`, `json` y `pathlib`.

## Arrancar n8n

En PowerShell, parado en la carpeta del proyecto:

```powershell
$env:N8N_RESTRICT_FILE_ACCESS_TO = "<ruta absoluta de esta carpeta>"
npx n8n
```

Después, http://localhost:5678

La primera vez `npx` descarga n8n y tarda varios minutos. No lo mates pensando
que se colgó.

**La variable no es opcional.** Desde n8n 2.x los nodos que tocan el disco solo
pueden leer y escribir dentro de `~/.n8n-files`. Sin ella, cualquier fase que
lea el CSV falla con `Access to the file is not allowed`, y parece un bug del
workflow cuando es una restricción de seguridad del propio n8n. La variable dura
lo que dura esa ventana de PowerShell.

Proponéle a Pedro dejar esto en un `arrancar-n8n.ps1` en la raíz del repo, para
no tipearlo cada vez.

## Criterio de aceptación

1. Las cuatro versiones están reportadas y cumplen el mínimo.
2. n8n arranca y la interfaz abre en el navegador.
3. Está claro y por escrito qué hubo que instalar, si hubo algo.
4. `ESTADO.md` tiene una línea de bitácora con las versiones que quedaron.

## Prohibido

- Instalar algo sin el OK de Pedro.
- Instalar n8n global (`npm install -g n8n`).
- Empezar F00 o cualquier fase en esta sesión.

## Terminado cuando

n8n abre en el navegador, las versiones están anotadas en `ESTADO.md`, y quedó
dicho qué falta instalar, si falta algo.
