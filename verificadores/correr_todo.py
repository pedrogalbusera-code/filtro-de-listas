#!/usr/bin/env python3
"""correr_todo.py — Suite de regresion (F09).

Un solo comando: python verificadores/correr_todo.py
Corre v00-v08 + comparacion contra golden file.
Exit 0 si todo pasa, exit 1 si algo falla.

Uso:
    python verificadores/correr_todo.py           # suite completa
    python verificadores/correr_todo.py --golden   # regenerar golden (separado)
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VERIFICADORES = [
    ("v00", "v00_pasamanos.py"),
    ("v01", "v01_telefono.py"),
    ("v02", "v02_cuil.py"),
    ("v03", "v03_dedup.py"),
    ("v04", "v04_cobertura.py"),
    ("v05", "v05_antiguedad.py"),
    ("v06", "v06_puntaje.py"),
    ("v07", "v07_salida.py"),
    ("v08", "v08_reporte.py"),
]

GOLDEN_COM = os.path.join(BASE, "salidas", "golden_2026-07-28.csv")
GOLDEN_AUD = os.path.join(BASE, "salidas", "golden_2026-07-28_auditoria.csv")
GEN = os.path.join(BASE, "herramientas", "gen_workflow.py")
CSV_IN = os.path.join(BASE, "data", "leads_prueba_SINTETICO_1.csv")
FECHA_CORTE = "2026-07-28"

# Fases que se regeneran ANTES del loop de verificadores.
#
# F00-F04: v00-v04 leen salida_fXX.csv sin ejecutar n8n. Sin esta pasada,
#   verificaban contra CSVs de corridas anteriores (dias viejos).
# F05 NO se incluye: v05 ejecuta n8n y escribe directamente a salida_f05.csv.
# F06: v06 ejecuta n8n pero escribe a un temporal (_tmp); el estandar
#   salida_f06.csv no se refresca.
# F07-F08: v07/v08 hacen sus propias corridas con nombres distintos
#   (_com_v1, _v_com, etc.) y no refrescan los salida_f07/f08 estandar.
#
# Formato: (fase, csv_comercial, csv_auditoria_o_None, reporte_o_None)
FASES_REGENERAR = [
    ("00", "salida_f00.csv", None, None),
    ("01", "salida_f01.csv", None, None),
    ("02", "salida_f02.csv", None, None),
    ("03", "salida_f03.csv", None, None),
    ("04", "salida_f04.csv", None, None),
    ("06", "salida_f06.csv", None, None),
    ("07", "salida_f07_comercial.csv", "salida_f07_auditoria.csv", None),
    ("08", "salida_f08_comercial.csv", "salida_f08_auditoria.csv", "reporte_f08.md"),
]


def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def extraer_resumen(stdout):
    """Saca la linea de resumen del verificador (entre === y ===)."""
    lineas = [l.strip() for l in stdout.strip().split("\n") if l.strip()]
    for l in reversed(lineas):
        if "PASA" in l or "FALLA" in l:
            return l
    return lineas[-1] if lineas else "(sin salida)"


def _ejecutar_n8n(wf_path, wf_id, env):
    """Importa y ejecuta un workflow en n8n por CLI."""
    with open(wf_path, "r", encoding="utf-8") as f:
        wf = json.load(f)
    wf["id"] = wf_id
    wf["name"] = f"tmp-{wf_id}"
    with open(wf_path, "w", encoding="utf-8") as f:
        json.dump(wf, f, indent=2, ensure_ascii=False)

    subprocess.run(
        f'npx n8n import:workflow --input="{wf_path}"',
        shell=True, check=True, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    result = subprocess.run(
        f"npx n8n execute --id={wf_id}",
        shell=True, check=True, env=env,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if not result.stdout or "Execution was successful" not in result.stdout:
        raise RuntimeError(f"n8n execution failed for {wf_id}")


def regenerar_csvs():
    """Regenera F00-F04, F06, F07, F08 ejecutando n8n antes del loop."""
    print("\n--- Regenerando CSVs (F00-F04, F06-F08) ---")

    tmp_wf = os.path.join(tempfile.gettempdir(), "wf_regen_tmp.json")
    wf_id = "f09regen_____tmp"
    env = os.environ.copy()
    env["N8N_RESTRICT_FILE_ACCESS_TO"] = BASE

    try:
        for fase, nombre_com, nombre_aud, nombre_rep in FASES_REGENERAR:
            csv_out = os.path.join(BASE, "salidas", nombre_com)
            label = nombre_com
            if nombre_aud:
                label += f" + {nombre_aud}"
            print(f"  F{fase} -> {label} ... ", end="", flush=True)
            t0 = time.time()

            cmd = [sys.executable, GEN, tmp_wf, CSV_IN, csv_out,
                   "--fase", fase, "--fecha-corte", FECHA_CORTE]
            if nombre_aud:
                cmd += ["--csv-out-audit", os.path.join(BASE, "salidas", nombre_aud)]
            if nombre_rep:
                cmd += ["--reporte-out", os.path.join(BASE, "salidas", nombre_rep)]
            subprocess.run(cmd, check=True, capture_output=True)
            _ejecutar_n8n(tmp_wf, wf_id, env)

            dt = time.time() - t0
            print(f"OK ({dt:.0f}s)")

    except Exception as e:
        print(f"FALLA")
        print(f"  ERROR: {str(e)[:200]}")
        return False

    finally:
        if os.path.exists(tmp_wf):
            os.remove(tmp_wf)

    return True


def correr_golden():
    """Ejecuta el pipeline completo y compara contra los dos golden files."""
    for g in [GOLDEN_COM, GOLDEN_AUD]:
        if not os.path.exists(g):
            return "FALLA", f"archivo golden no existe: {os.path.basename(g)}", 0

    tmp_com = os.path.join(BASE, "salidas", "_golden_tmp_com.csv")
    tmp_aud = os.path.join(BASE, "salidas", "_golden_tmp_aud.csv")
    tmp_rep = os.path.join(BASE, "salidas", "_golden_tmp_rep.md")
    tmp_wf = os.path.join(tempfile.gettempdir(), "wf_golden_tmp.json")
    wf_id = "f09golden___tmp"

    t0 = time.time()
    try:
        subprocess.run(
            [sys.executable, GEN, tmp_wf, CSV_IN, tmp_com,
             "--fase", "08", "--fecha-corte", FECHA_CORTE,
             "--csv-out-audit", tmp_aud,
             "--reporte-out", tmp_rep],
            check=True, capture_output=True,
        )

        env = os.environ.copy()
        env["N8N_RESTRICT_FILE_ACCESS_TO"] = BASE
        _ejecutar_n8n(tmp_wf, wf_id, env)

        dt = time.time() - t0

        h_com_golden = file_hash(GOLDEN_COM)
        h_com_actual = file_hash(tmp_com)
        h_aud_golden = file_hash(GOLDEN_AUD)
        h_aud_actual = file_hash(tmp_aud)

        if h_com_golden == h_com_actual and h_aud_golden == h_aud_actual:
            return "PASA", f"SHA-256 coincide com={h_com_golden[:12]}... aud={h_aud_golden[:12]}...", dt
        else:
            partes = []
            if h_com_golden != h_com_actual:
                partes.append(f"comercial difiere: golden={h_com_golden[:12]}... actual={h_com_actual[:12]}...")
            if h_aud_golden != h_aud_actual:
                partes.append(f"auditoria difiere: golden={h_aud_golden[:12]}... actual={h_aud_actual[:12]}...")
            return "FALLA", "; ".join(partes), dt

    except Exception as e:
        return "FALLA", str(e)[:120], time.time() - t0

    finally:
        for f in [tmp_com, tmp_aud, tmp_rep, tmp_wf]:
            if os.path.exists(f):
                os.remove(f)


def regenerar_golden():
    """Comando separado: regenera los dos golden files desde gen_workflow.py."""
    print("Regenerando golden files...")
    print(f"  fecha_corte = {FECHA_CORTE}")
    print(f"  csv_in      = {CSV_IN}")

    tmp_wf = os.path.join(tempfile.gettempdir(), "wf_golden_regen.json")
    wf_id = "f09goldenreg_tmp"

    try:
        subprocess.run(
            [sys.executable, GEN, tmp_wf, CSV_IN, GOLDEN_COM,
             "--fase", "08", "--fecha-corte", FECHA_CORTE,
             "--csv-out-audit", GOLDEN_AUD,
             "--reporte-out", os.path.join(BASE, "salidas", "_golden_tmp_rep.md")],
            check=True, capture_output=True,
        )

        env = os.environ.copy()
        env["N8N_RESTRICT_FILE_ACCESS_TO"] = BASE
        _ejecutar_n8n(tmp_wf, wf_id, env)

        h_com = file_hash(GOLDEN_COM)
        h_aud = file_hash(GOLDEN_AUD)
        print(f"\n  Golden comercial:  {GOLDEN_COM}")
        print(f"  SHA-256: {h_com}")
        print(f"  Golden auditoria: {GOLDEN_AUD}")
        print(f"  SHA-256: {h_aud}")
        print("\nGolden regenerado. Verificar con: python verificadores/correr_todo.py")

    finally:
        for f in [tmp_wf, os.path.join(BASE, "salidas", "_golden_tmp_rep.md")]:
            if os.path.exists(f):
                os.remove(f)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="Suite de regresion F09")
    ap.add_argument("--golden", action="store_true",
                    help="Regenerar los golden files (no corre la suite)")
    args = ap.parse_args()

    if args.golden:
        regenerar_golden()
        return

    print("=" * 65)
    print("  Suite de regresion - F09")
    print("=" * 65)

    t_total = time.time()

    if not regenerar_csvs():
        print("\n  ABORTANDO: la regeneracion fallo.")
        print("  No tiene sentido verificar contra archivos a medio escribir.")
        sys.exit(1)

    print(f"\n  Regeneracion OK ({time.time() - t_total:.0f}s)")

    resultados = []

    for tag, archivo in VERIFICADORES:
        path = os.path.join(BASE, "verificadores", archivo)
        print(f"\n>>> {tag}: {archivo}")
        t0 = time.time()

        r = subprocess.run(
            [sys.executable, path],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        dt = time.time() - t0
        resumen = extraer_resumen(r.stdout)

        if r.returncode == 0:
            resultados.append((tag, "PASA", resumen, dt))
            print(f"    {resumen}  ({dt:.0f}s)")
        else:
            resultados.append((tag, "FALLA", resumen, dt))
            print(f"    FALLA: {resumen}  ({dt:.0f}s)")
            ultimas = r.stdout.strip().split("\n")[-8:] if r.stdout else []
            for l in ultimas:
                print(f"    | {l}")
            if r.stderr:
                for l in r.stderr.strip().split("\n")[-4:]:
                    print(f"    ! {l}")

    print(f"\n>>> golden: comparacion contra {os.path.basename(GOLDEN_COM)} + {os.path.basename(GOLDEN_AUD)}")
    estado_g, detalle_g, dt_g = correr_golden()
    resultados.append(("golden", estado_g, detalle_g, dt_g))
    print(f"    {estado_g}: {detalle_g}  ({dt_g:.0f}s)")

    dt_total = time.time() - t_total

    print("\n" + "=" * 65)
    print(f"  {'Verif':<8} {'Estado':<7} {'Tiempo':>7}   {'Detalle'}")
    print("  " + "-" * 61)
    fallos = 0
    for tag, estado, detalle, dt in resultados:
        marca = "PASA" if estado == "PASA" else "FALLA"
        print(f"  {tag:<8} {marca:<7} {dt:>5.0f}s   {detalle}")
        if estado == "FALLA":
            fallos += 1

    total = len(resultados)
    print("  " + "-" * 61)
    if fallos == 0:
        print(f"  Suite de regresion: {total}/{total} PASA  (total {dt_total:.0f}s)")
    else:
        print(f"  Suite de regresion: {total - fallos}/{total} PASA, {fallos} FALLA  (total {dt_total:.0f}s)")
    print("=" * 65)

    sys.exit(0 if fallos == 0 else 1)


if __name__ == "__main__":
    main()
