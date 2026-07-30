#!/usr/bin/env python3
"""v09_pendientes.py — Verificador de pendientes conocidos (hallazgos adversarios).

Corre leads_adversario_1.csv por el pipeline F08 (fecha de corte 2026-07-28)
y compara cada caso contra su actual_medido registrado.

Reglas:
  - Sigue fallando igual que lo medido -> OK (pendiente conocido, sin cambio)
  - Empieza a pasar (valor correcto) -> ROJA (cambio no documentado)
  - Falla distinto a lo medido -> ROJA (cambio no documentado)

Sacar un pendiente del registro es una accion manual, nunca automatica.
"""
import csv
import json
import os
import subprocess
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_IN = os.path.join(BASE, "data", "leads_adversario_1.csv")
GEN = os.path.join(BASE, "herramientas", "gen_workflow.py")
WF_ID_TMP = "f09pendient_tmp"
FECHA_CORTE = "2026-07-28"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pendientes_conocidos import PENDIENTES


def generar_y_ejecutar():
    tmp_wf = os.path.join(tempfile.gettempdir(), "wf_pendientes_tmp.json")
    csv_out_com = os.path.join(BASE, "salidas", "_pend_tmp_com.csv")
    csv_out_aud = os.path.join(BASE, "salidas", "_pend_tmp_aud.csv")
    csv_rep = os.path.join(BASE, "salidas", "_pend_tmp_rep.md")

    try:
        subprocess.run(
            [sys.executable, GEN, tmp_wf, CSV_IN, csv_out_com,
             "--fase", "08", "--fecha-corte", FECHA_CORTE,
             "--csv-out-audit", csv_out_aud,
             "--reporte-out", csv_rep],
            check=True, capture_output=True,
        )

        with open(tmp_wf, "r", encoding="utf-8") as f:
            wf = json.load(f)
        wf["id"] = WF_ID_TMP
        wf["name"] = "tmp-pendientes"
        with open(tmp_wf, "w", encoding="utf-8") as f:
            json.dump(wf, f, indent=2, ensure_ascii=False)

        env = os.environ.copy()
        env["N8N_RESTRICT_FILE_ACCESS_TO"] = BASE

        subprocess.run(
            f'npx n8n import:workflow --input="{tmp_wf}"',
            shell=True, check=True, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        result = subprocess.run(
            f"npx n8n execute --id={WF_ID_TMP}",
            shell=True, check=True, env=env,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if not result.stdout or "Execution was successful" not in result.stdout:
            raise RuntimeError("n8n execution failed")

        with open(csv_out_aud, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        return rows

    finally:
        for path in [tmp_wf, csv_out_com, csv_out_aud, csv_rep]:
            if os.path.exists(path):
                os.remove(path)


def find_row(rows, pendiente_id):
    for row in rows:
        if row["nombre"].startswith(pendiente_id + " "):
            return row
    return None


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 65)
    print("  Pendientes conocidos (hallazgos adversarios)")
    print("=" * 65)

    print("\n  Ejecutando pipeline F08 sobre leads_adversario_1.csv...")
    rows = generar_y_ejecutar()
    print(f"  {len(rows)} filas procesadas.\n")

    sin_cambio = 0
    cambio = 0

    for p in PENDIENTES:
        pid = p["id"]
        row = find_row(rows, pid)

        if row is None:
            cambio += 1
            print(f"  CAMBIO  {pid}: fila no encontrada en la salida")
            continue

        medido = p["actual_medido"]
        diffs = []
        for campo, valor_esperado in medido.items():
            valor_actual = row.get(campo, "")
            if valor_actual != valor_esperado:
                diffs.append(f"{campo}: esperaba [{valor_esperado}] pero dio [{valor_actual}]")

        if diffs:
            cambio += 1
            print(f"  CAMBIO  {pid} ({p['categoria']}): {'; '.join(diffs)}")
        else:
            sin_cambio += 1
            print(f"  OK      {pid} ({p['categoria']}): sigue igual — {p['importa'][:60]}")

    total = len(PENDIENTES)
    print("\n" + "-" * 65)
    if cambio == 0:
        print(f"  Pendientes: {total} registrados, {sin_cambio} sin cambio, 0 cambiaron")
        print("  Los bugs conocidos siguen ahi. Ningun comportamiento cambio sin aviso.")
    else:
        print(f"  Pendientes: {total} registrados, {sin_cambio} sin cambio, {cambio} CAMBIARON")
        print("  ATENCION: algun pendiente cambio de comportamiento sin documentarlo.")
    print("-" * 65)

    sys.exit(1 if cambio > 0 else 0)


if __name__ == "__main__":
    main()
