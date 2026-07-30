#!/usr/bin/env python3
"""v06_puntaje.py — Verificador de F06 (Puntaje explicable).

Ejecuta el workflow de n8n y verifica:
  - 200 filas de salida con puntaje, prioridad, motivo
  - Auditabilidad: suma de puntos en motivo == puntaje, fila por fila
  - Consistencia de descarte directo
  - Distribución esperada: alta 48, media 38, descartado 114
  - Oráculo Python independiente vs salida n8n
"""
import csv
import json
import os
import re
import subprocess
import sys
import tempfile

# ---------------------------------------------------------------------------
# Configuración (espejo de CONFIG en JS_F06)
# ---------------------------------------------------------------------------
PESOS_TEL = {"celular": 30, "fijo": 10, "ambiguo": 18}
PESOS_CUIL_V = 15
PESOS_CUIL_I = -10
PESO_ZONA = 20
PESOS_FRESCURA = {"alta": 25, "media": 15, "baja": 5, "fria": 0, "sin dato": 0}
PESOS_ORIGEN = {
    "referido": 15,
    "formulario web": 10,
    "evento": 10,
    "campaña Meta": 5,
    "base propia": 0,
}
UMBRAL_ALTA = 70
UMBRAL_MEDIA = 40

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_IN = os.path.join(BASE, "data", "leads_prueba_SINTETICO_1.csv")
CSV_F05 = os.path.join(BASE, "salidas", "salida_f05.csv")
CSV_OUT = os.path.join(BASE, "salidas", "salida_f06.csv")
WF_PROD = os.path.join(BASE, "workflows", "07-puntaje.json")
GEN = os.path.join(BASE, "herramientas", "gen_workflow.py")
WF_ID_TMP = "f06puntaje_tmp"

ok = 0
fail = 0


def check(nombre, condicion, detalle=""):
    global ok, fail
    if condicion:
        ok += 1
        print(f"  PASA  {nombre}")
    else:
        fail += 1
        print(f"  FALLA {nombre}" + (f": {detalle}" if detalle else ""))


# ---------------------------------------------------------------------------
# Oráculo Python (reimplementación independiente)
# ---------------------------------------------------------------------------
def oraculo_puntaje(row):
    """Calcula (puntaje, prioridad, motivo) para una fila de salida_f05."""
    score = 0
    partes = []
    descarte = False

    def fmt(n):
        return f"+{n}" if n >= 0 else str(n)

    # Teléfono
    tipo = (row.get("telefono_tipo") or "").strip()
    if tipo in PESOS_TEL:
        pts = PESOS_TEL[tipo]
        score += pts
        partes.append(f"{tipo} {fmt(pts)}")
    else:
        partes.append(f"sin teléfono {fmt(0)} → descarte")
        descarte = True

    # CUIL
    cv = (row.get("cuil_valido") or "").strip().upper()
    if cv == "TRUE":
        score += PESOS_CUIL_V
        partes.append(f"cuil válido {fmt(PESOS_CUIL_V)}")
    else:
        score += PESOS_CUIL_I
        partes.append(f"cuil inválido {fmt(PESOS_CUIL_I)}")

    # Zona
    ez = (row.get("en_zona") or "").strip().upper()
    if ez == "TRUE":
        score += PESO_ZONA
        partes.append(f"en zona {fmt(PESO_ZONA)}")
    else:
        partes.append(f"fuera de zona {fmt(0)} → descarte")
        descarte = True

    # Frescura
    fr = (row.get("frescura") or "sin dato").strip()
    fr_pts = PESOS_FRESCURA.get(fr, 0)
    score += fr_pts
    partes.append(f"frescura {fr} {fmt(fr_pts)}")

    # Origen
    orig = (row.get("origen") or "").strip()
    orig_pts = PESOS_ORIGEN.get(orig, 0)
    partes.append(f"{orig or 'origen desconocido'} {fmt(orig_pts)}")
    score += orig_pts

    # Duplicado
    es_dup = (row.get("es_duplicado") or "").strip().upper() == "TRUE"
    if es_dup:
        partes.append(f"duplicado {fmt(0)} → descarte")
        descarte = True

    # Prioridad
    if descarte:
        prioridad = "descartado"
    elif score >= UMBRAL_ALTA:
        prioridad = "alta"
    elif score >= UMBRAL_MEDIA:
        prioridad = "media"
    else:
        prioridad = "descartado"

    return score, prioridad, "; ".join(partes)


# ---------------------------------------------------------------------------
# Generación y ejecución del workflow
# ---------------------------------------------------------------------------
def generar_y_ejecutar(csv_in, csv_out):
    """Genera un workflow temporal, lo importa en n8n y lo ejecuta."""
    tmp_wf = os.path.join(tempfile.gettempdir(), "wf_f06_tmp.json")
    subprocess.run(
        [sys.executable, GEN, tmp_wf, csv_in, csv_out,
         "--fase", "06", "--fecha-corte", "2026-07-28"],
        check=True,
    )
    with open(tmp_wf, "r", encoding="utf-8") as f:
        wf = json.load(f)
    wf["id"] = WF_ID_TMP
    wf["name"] = "tmp-puntaje"
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
        f'npx n8n execute --id={WF_ID_TMP}',
        shell=True, check=True, env=env,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if not result.stdout or "Execution was successful" not in result.stdout:
        raise RuntimeError("n8n execution failed:\n" + (result.stdout or ""))

    os.remove(tmp_wf)
    return csv_out


# ---------------------------------------------------------------------------
# Verificaciones
# ---------------------------------------------------------------------------
def main():
    global ok, fail

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 60)
    print("v06_puntaje.py — Verificador F06 (Puntaje explicable)")
    print("=" * 60)

    # --- Paso 1: ejecutar n8n ---
    print("\n--- Ejecutando workflow en n8n ---")
    csv_out_tmp = os.path.join(BASE, "salidas", "salida_f06_tmp.csv")

    try:
        generar_y_ejecutar(CSV_IN, csv_out_tmp)
        rows = list(csv.DictReader(
            open(csv_out_tmp, encoding="utf-8-sig")))
    except Exception as e:
        print(f"  ERROR ejecutando n8n: {e}")
        sys.exit(1)

    # --- Paso 2: checks sobre la salida de n8n ---
    print("\n--- Checks sobre salida n8n ---")

    check("(n8n) 200 filas de salida", len(rows) == 200,
          f"esperado 200, obtenido {len(rows)}")

    # Columnas nuevas presentes
    for col in ("puntaje", "prioridad", "motivo"):
        check(f"(n8n) columna '{col}' presente", col in rows[0],
              f"columnas: {list(rows[0].keys())}")

    # Distribución
    from collections import Counter
    dist = Counter(r["prioridad"] for r in rows)
    check("(n8n) alta = 48", dist.get("alta", 0) == 48,
          f"obtenido {dist.get('alta', 0)}")
    check("(n8n) media = 38", dist.get("media", 0) == 38,
          f"obtenido {dist.get('media', 0)}")
    check("(n8n) descartado = 114", dist.get("descartado", 0) == 114,
          f"obtenido {dist.get('descartado', 0)}")
    check("(n8n) 3 prioridades pobladas",
          len(dist) == 3 and all(v > 0 for v in dist.values()),
          f"dist = {dict(dist)}")

    # --- Paso 3: auditabilidad ---
    print("\n--- Auditabilidad (motivo → puntaje) ---")
    audit_ok = 0
    audit_fail_rows = []
    for r in rows:
        motivo = r["motivo"]
        nums = re.findall(r"([+-]\d+)", motivo)
        suma = sum(int(n) for n in nums)
        puntaje = int(r["puntaje"])
        if suma == puntaje:
            audit_ok += 1
        else:
            audit_fail_rows.append(
                f"fila {r['id_fila']}: suma={suma} != puntaje={puntaje}")
    check("(n8n) auditabilidad 200/200",
          audit_ok == 200,
          f"{audit_ok}/200 OK; fallos: {audit_fail_rows[:3]}")

    # --- Paso 4: consistencia de descarte ---
    print("\n--- Consistencia descarte directo ---")
    desc_ok = True
    desc_detalles = []
    for r in rows:
        tiene_descarte = "→ descarte" in r["motivo"]
        if tiene_descarte and r["prioridad"] != "descartado":
            desc_ok = False
            desc_detalles.append(
                f"fila {r['id_fila']}: descarte directo → {r['prioridad']}")
    check("(n8n) descarte directo → prioridad descartado", desc_ok,
          "; ".join(desc_detalles[:3]))

    # Descartado por score (sin descarte directo) → puntaje < UMBRAL_MEDIA
    score_desc_ok = True
    score_desc_det = []
    for r in rows:
        if r["prioridad"] == "descartado" and "→ descarte" not in r["motivo"]:
            if int(r["puntaje"]) >= UMBRAL_MEDIA:
                score_desc_ok = False
                score_desc_det.append(
                    f"fila {r['id_fila']}: puntaje={r['puntaje']} >= {UMBRAL_MEDIA}")
    check("(n8n) descartado por score → puntaje < 40", score_desc_ok,
          "; ".join(score_desc_det[:3]))

    # Alta → puntaje >= UMBRAL_ALTA y sin descarte
    alta_ok = True
    alta_det = []
    for r in rows:
        if r["prioridad"] == "alta":
            if int(r["puntaje"]) < UMBRAL_ALTA:
                alta_ok = False
                alta_det.append(f"fila {r['id_fila']}: puntaje={r['puntaje']}")
            if "→ descarte" in r["motivo"]:
                alta_ok = False
                alta_det.append(f"fila {r['id_fila']}: tiene descarte directo")
    check("(n8n) alta → puntaje >= 70, sin descarte", alta_ok,
          "; ".join(alta_det[:3]))

    # Media → puntaje entre 40 y 69, sin descarte
    media_ok = True
    media_det = []
    for r in rows:
        if r["prioridad"] == "media":
            p = int(r["puntaje"])
            if p < UMBRAL_MEDIA or p >= UMBRAL_ALTA:
                media_ok = False
                media_det.append(f"fila {r['id_fila']}: puntaje={p}")
            if "→ descarte" in r["motivo"]:
                media_ok = False
                media_det.append(f"fila {r['id_fila']}: tiene descarte directo")
    check("(n8n) media → puntaje 40-69, sin descarte", media_ok,
          "; ".join(media_det[:3]))

    # --- Paso 5: oráculo vs n8n ---
    print("\n--- Oráculo Python vs n8n ---")

    f05_rows = list(csv.DictReader(
        open(CSV_F05, encoding="utf-8-sig")))
    check("(oráculo) f05 tiene 200 filas", len(f05_rows) == 200,
          f"obtenido {len(f05_rows)}")

    oracle_match = 0
    oracle_fail_rows = []
    for i, r05 in enumerate(f05_rows):
        exp_score, exp_pri, exp_motivo = oraculo_puntaje(r05)
        n8n_row = rows[i]
        n8n_score = int(n8n_row["puntaje"])
        n8n_pri = n8n_row["prioridad"]
        n8n_motivo = n8n_row["motivo"]

        if n8n_score == exp_score and n8n_pri == exp_pri and n8n_motivo == exp_motivo:
            oracle_match += 1
        else:
            diffs = []
            if n8n_score != exp_score:
                diffs.append(f"puntaje: n8n={n8n_score} vs oráculo={exp_score}")
            if n8n_pri != exp_pri:
                diffs.append(f"prioridad: n8n={n8n_pri} vs oráculo={exp_pri}")
            if n8n_motivo != exp_motivo:
                diffs.append(f"motivo difiere")
            oracle_fail_rows.append(
                f"fila {n8n_row['id_fila']}: {'; '.join(diffs)}")

    check("(oráculo) 200/200 filas coinciden con n8n",
          oracle_match == 200,
          f"{oracle_match}/200 OK; fallos: {oracle_fail_rows[:5]}")

    # --- Paso 6: checks puntuales ---
    print("\n--- Checks puntuales ---")

    scores = [int(r["puntaje"]) for r in rows]

    # Puntaje máximo y mínimo observados
    check("(puntual) puntaje máximo = 100",
          max(scores) == 100, f"máx={max(scores)}")
    check("(puntual) puntaje mínimo = 0",
          min(scores) == 0, f"mín={min(scores)}")

    # Un duplicado siempre es descartado
    dup_count = sum(1 for r in rows
                    if "duplicado" in r["motivo"]
                    and "→ descarte" in r["motivo"]
                    and r["prioridad"] == "descartado")
    dup_total = sum(1 for r in rows if "duplicado" in r["motivo"]
                    and "→ descarte" in r["motivo"])
    check("(puntual) duplicados siempre descartados",
          dup_count == dup_total and dup_total > 0,
          f"{dup_count}/{dup_total}")

    # Todos los puntajes son enteros (no NaN, no vacíos)
    all_int = all(r["puntaje"].lstrip("-").isdigit() for r in rows)
    check("(puntual) todos los puntajes son enteros", all_int)

    # Rango de puntajes razonable (sanity)
    check("(puntual) puntaje mínimo >= -10",
          min(scores) >= -10, f"mín={min(scores)}")
    check("(puntual) puntaje máximo <= 105",
          max(scores) <= 105, f"máx={max(scores)}")

    # --- Paso 7: CONFIG auditable ---
    print("\n--- CONFIG auditable ---")
    with open(WF_PROD, "r", encoding="utf-8") as f:
        wf_json = f.read()
    check("(config) pesos.telefono.celular = 30 en workflow",
          '"celular": 30' in wf_json or "'celular': 30" in wf_json
          or "celular: 30" in wf_json)
    check("(config) umbrales.alta = 70 en workflow",
          "alta: 70" in wf_json or '"alta": 70' in wf_json)
    check("(config) umbrales.media = 40 en workflow",
          "media: 40" in wf_json or '"media": 40' in wf_json)

    # --- Limpieza ---
    if os.path.exists(csv_out_tmp):
        os.remove(csv_out_tmp)

    # --- Resumen ---
    total = ok + fail
    print("\n" + "=" * 60)
    if fail == 0:
        print(f"v06_puntaje: {ok}/{total} PASA")
    else:
        print(f"v06_puntaje: {ok}/{total} PASA, {fail} FALLA")
    print("=" * 60)

    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
