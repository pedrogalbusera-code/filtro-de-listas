#!/usr/bin/env python3
"""procesar.py — procesa la lista de un cliente de punta a punta con UN comando.

    python herramientas/procesar.py <archivo> [--mapeo config/X.json] [--baja archivo]
           [--segmentacion config/Y.json] [--fecha-corte AAAA-MM-DD] [--salida-dir salidas/]

Reusa EXACTAMENTE el mecanismo de v_fuego.correr(): arma el workflow con
gen_workflow.py (los mismos nodos, la misma logica) y lo corre en n8n por CLI
(import + execute). NO reimplementa el pipeline. Si esto divergiera del canonico
seria un bug de EMPAQUETADO, no del motor: por eso v_procesar.py lo cruza contra
el golden byte a byte.

La puerta de entrada (F11) rechaza los archivos que no entiende: eso es un
RESULTADO (exit != 0 con el motivo legible), no un crash. Nunca procesa basura
en silencio (regla 4 de CLAUDE.md, aplicada al archivo).
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(BASE, "herramientas", "gen_workflow.py")
# Id propio: no pisa el canonico (f08reporte00001) ni los de los verificadores.
WF_ID = "procesar____cli"


def _leer(path):
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()


def _row_num(reporte, clave):
    """Primer numero (con decimal opcional) de la fila del reporte que contiene `clave`."""
    for linea in reporte.splitlines():
        if clave in linea:
            m = re.search(r"(\d+(?:[.,]\d+)?)", linea.split(clave, 1)[1])
            if m:
                return m.group(1)
    return "?"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(
        description="Procesa una lista de cliente en un comando (F11 puerta -> pipeline -> reporte).")
    ap.add_argument("archivo", help="CSV/TXT (con cualquier separador/basura arriba) o .xlsx del cliente")
    ap.add_argument("--mapeo", default="", help="config/mapeo_<cliente>.json (columnas del cliente -> canonicas)")
    ap.add_argument("--baja", default="", help="lista de baja / opt-out del cliente (CSV o .xlsx)")
    ap.add_argument("--segmentacion", default="", help="config de segmentacion (persona fisica/juridica)")
    ap.add_argument("--fecha-corte", default="", help="AAAA-MM-DD; default = hoy. Se imprime SIEMPRE.")
    ap.add_argument("--salida-dir", default=os.path.join(BASE, "salidas"),
                    help="carpeta de salida (default: salidas/). Tiene que estar dentro del repo.")
    ap.add_argument("--fase", default="14",
                    help="fase del pipeline (default 14: puerta + persona + basura + opt-out).")
    args = ap.parse_args()

    archivo = os.path.abspath(args.archivo)
    if not os.path.exists(archivo):
        print(f"ERROR: no existe el archivo {archivo}", file=sys.stderr)
        sys.exit(2)

    fecha = args.fecha_corte or datetime.date.today().isoformat()
    salida_dir = os.path.abspath(args.salida_dir)
    os.makedirs(salida_dir, exist_ok=True)

    stem = os.path.splitext(os.path.basename(archivo))[0]
    com = os.path.join(salida_dir, f"{stem}_comercial.csv")
    aud = os.path.join(salida_dir, f"{stem}_auditoria.csv")
    rep = os.path.join(salida_dir, f"{stem}_reporte.md")
    ficha = os.path.join(salida_dir, f"ficha_entrada_{stem}.md")
    # Limpiar salidas viejas de ESTE archivo: un rechazo no puede dejar en pie una
    # corrida anterior que se lea como si fuera la de ahora.
    for f in (com, aud, rep):
        if os.path.exists(f):
            os.remove(f)

    print(f"Procesando: {archivo}")
    print(f"Fecha de corte: {fecha}")
    if args.mapeo:
        print(f"Mapeo: {os.path.abspath(args.mapeo)}")
    if args.segmentacion:
        print(f"Segmentacion: {os.path.abspath(args.segmentacion)}")
    if args.baja:
        print(f"Lista de baja: {os.path.abspath(args.baja)}")

    # --- Armar el workflow (mismo gen_workflow.py que el canonico y los verificadores) ---
    tmp_wf = os.path.join(tempfile.gettempdir(), "wf_procesar_cli.json")
    cmd = [sys.executable, GEN, tmp_wf, archivo, com,
           "--fase", args.fase, "--fecha-corte", fecha,
           "--csv-out-audit", aud, "--reporte-out", rep, "--ficha-out", ficha]
    if args.mapeo:
        cmd += ["--mapeo", os.path.abspath(args.mapeo)]
    if args.segmentacion:
        cmd += ["--segmentacion", os.path.abspath(args.segmentacion)]
    if args.baja:
        cmd += ["--lista-baja", os.path.abspath(args.baja)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    except subprocess.CalledProcessError as e:
        # gen_workflow frena por config invalida (motivo escrito), no un stacktrace.
        msg = (e.stderr or e.stdout or "").strip()
        print("\nNo se pudo armar el workflow:", file=sys.stderr)
        print("  " + (msg.splitlines()[-1] if msg else "error desconocido"), file=sys.stderr)
        sys.exit(1)

    with open(tmp_wf, "r", encoding="utf-8") as f:
        wf = json.load(f)
    wf["id"] = WF_ID
    wf["name"] = "procesar-cli"
    with open(tmp_wf, "w", encoding="utf-8") as f:
        json.dump(wf, f, indent=2, ensure_ascii=False)

    # --- Correr en n8n de verdad (import + execute) ---
    env = os.environ.copy()
    env["N8N_RESTRICT_FILE_ACCESS_TO"] = BASE
    subprocess.run(
        f'npx n8n import:workflow --input="{tmp_wf}"',
        shell=True, check=True, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    r = subprocess.run(
        f"npx n8n execute --id={WF_ID}",
        shell=True, env=env,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if os.path.exists(tmp_wf):
        os.remove(tmp_wf)

    salida = (r.stdout or "") + "\n" + (r.stderr or "")
    exito = r.returncode == 0 and "Execution was successful" in (r.stdout or "")

    if not exito:
        # La puerta rechaza lo que no entiende: motivo legible, exit != 0. No stacktrace.
        m = re.search(r"F1[14] RECHAZO[^\n]*", salida)
        print("", file=sys.stderr)
        if m:
            print("ARCHIVO RECHAZADO por la puerta de entrada:", file=sys.stderr)
            print("  " + m.group(0).strip(), file=sys.stderr)
            print("  (la ficha de entrada quedo en %s)" % ficha, file=sys.stderr)
        else:
            print("La corrida no termino bien. Ultimas lineas:", file=sys.stderr)
            for l in salida.strip().splitlines()[-8:]:
                print("  " + l, file=sys.stderr)
        sys.exit(1)

    # --- Resumen final: lo que se lee en voz alta en una reunion ---
    rep_txt = _leer(rep)
    entran = _row_num(rep_txt, "Contactos en el archivo")
    llamables = _row_num(rep_txt, "Contactos llamables")
    descartados = _row_num(rep_txt, "Contactos descartados")
    horas = _row_num(rep_txt, "Horas de operador ahorradas")

    print("\nListo. Se generaron:")
    print(f"  comercial: {com}")
    print(f"  auditoria: {aud}")
    print(f"  reporte:   {rep}")
    print(f"  ficha:     {ficha}")
    print(f"\nEl numero (corte {fecha}): entran {entran} · llamables {llamables} "
          f"· descartados {descartados} · {horas} h de operador ahorradas")


if __name__ == "__main__":
    main()
