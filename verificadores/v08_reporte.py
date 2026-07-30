#!/usr/bin/env python3
"""v08_reporte.py — Verificador de F08 (El número / reporte de impacto).

Ejecuta el workflow de n8n y verifica:
  - El reporte Markdown se genera automáticamente
  - Cada métrica del reporte coincide con el recálculo desde el CSV
  - Los supuestos están visibles junto al número que los usa
  - Los CSVs de salida siguen siendo correctos (200 filas, distribución)
"""
import csv
import json
import os
import re
import subprocess
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_IN = os.path.join(BASE, "data", "leads_prueba_SINTETICO_1.csv")
GEN = os.path.join(BASE, "herramientas", "gen_workflow.py")
WF_ID_TMP = "f08reporte__tmp"

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


def generar_y_ejecutar(csv_in, csv_out_com, csv_out_aud, reporte_out):
    tmp_wf = os.path.join(tempfile.gettempdir(), "wf_f08_tmp.json")
    subprocess.run(
        [sys.executable, GEN, tmp_wf, csv_in, csv_out_com,
         "--fase", "08", "--fecha-corte", "2026-07-28",
         "--csv-out-audit", csv_out_aud,
         "--reporte-out", reporte_out],
        check=True,
    )
    with open(tmp_wf, "r", encoding="utf-8") as f:
        wf = json.load(f)
    wf["id"] = WF_ID_TMP
    wf["name"] = "tmp-reporte"
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


def leer_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def extraer_numero(texto, patron):
    """Busca un patrón regex en el texto y devuelve el primer grupo como número."""
    m = re.search(patron, texto)
    if m:
        return m.group(1)
    return None


def main():
    global ok, fail

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 60)
    print("v08_reporte.py — Verificador F08 (El número)")
    print("=" * 60)

    # --- Paso 1: ejecutar n8n ---
    print("\n--- Ejecutando workflow en n8n ---")
    com = os.path.join(BASE, "salidas", "salida_f08_v_com.csv")
    aud = os.path.join(BASE, "salidas", "salida_f08_v_aud.csv")
    rep = os.path.join(BASE, "salidas", "reporte_f08_v.md")

    try:
        generar_y_ejecutar(CSV_IN, com, aud, rep)
    except Exception as e:
        print(f"  ERROR ejecutando n8n: {e}")
        sys.exit(1)

    # --- Paso 2: archivos generados ---
    print("\n--- Archivos generados ---")
    check("comercial existe", os.path.exists(com))
    check("auditoría existe", os.path.exists(aud))
    check("reporte existe", os.path.exists(rep))

    rows_com = leer_csv(com)
    rows_aud = leer_csv(aud)

    with open(rep, encoding="utf-8") as f:
        reporte = f.read()

    # --- Paso 3: CSVs siguen correctos ---
    print("\n--- CSVs intactos ---")
    check("(com) 200 filas", len(rows_com) == 200,
          f"esperado 200, obtenido {len(rows_com)}")
    check("(aud) 200 filas", len(rows_aud) == 200,
          f"esperado 200, obtenido {len(rows_aud)}")

    from collections import Counter
    dist = Counter(r["prioridad"] for r in rows_com)
    check("(com) alta=48", dist.get("alta", 0) == 48, f"obtenido {dist.get('alta', 0)}")
    check("(com) media=38", dist.get("media", 0) == 38, f"obtenido {dist.get('media', 0)}")
    check("(com) descartado=114", dist.get("descartado", 0) == 114,
          f"obtenido {dist.get('descartado', 0)}")

    # --- Paso 4: recalcular métricas desde CSV ---
    print("\n--- Recálculo desde CSV ---")
    total = len(rows_aud)
    n_alta = sum(1 for r in rows_aud if r["prioridad"] == "alta")
    n_media = sum(1 for r in rows_aud if r["prioridad"] == "media")
    n_descartado = sum(1 for r in rows_aud if r["prioridad"] == "descartado")
    llamables = n_alta + n_media

    n_dup = 0
    n_sin_tel = 0
    n_fuera_zona = 0
    n_por_score = 0

    for r in rows_aud:
        if r["prioridad"] != "descartado":
            continue
        motivo = r["motivo"]
        tiene_descarte = "→ descarte" in motivo
        if "sin teléfono" in motivo and tiene_descarte:
            n_sin_tel += 1
        if "fuera de zona" in motivo and tiene_descarte:
            n_fuera_zona += 1
        if "duplicado" in motivo and tiene_descarte:
            n_dup += 1
        if not tiene_descarte:
            n_por_score += 1

    unicos = total - n_dup
    horas = round(n_descartado * 4 / 60, 1)

    print(f"  (info) total={total} alta={n_alta} media={n_media} desc={n_descartado}")
    print(f"  (info) sin_tel={n_sin_tel} dup={n_dup} fuera={n_fuera_zona} score={n_por_score}")
    print(f"  (info) unicos={unicos} llamables={llamables} horas={horas}")

    # --- Paso 5: parsear reporte y comparar ---
    print("\n--- Comparar reporte vs recálculo ---")

    def buscar_en_tabla(patron, texto):
        m = re.search(patron, texto)
        return m.group(1).strip() if m else None

    rep_total = buscar_en_tabla(r"Contactos en el archivo\s*\|\s*(\d+)", reporte)
    check("total en reporte", rep_total == str(total),
          f"reporte={rep_total} csv={total}")

    rep_unicos = buscar_en_tabla(r"sin duplicados\)\s*\|\s*(\d+)", reporte)
    check("únicos en reporte", rep_unicos == str(unicos),
          f"reporte={rep_unicos} csv={unicos}")

    rep_llamables = buscar_en_tabla(r"Contactos llamables.*?\|\s*\**(\d+)\**", reporte)
    check("llamables en reporte", rep_llamables == str(llamables),
          f"reporte={rep_llamables} csv={llamables}")

    rep_descartados = buscar_en_tabla(r"Contactos descartados\s*\|\s*(\d+)", reporte)
    check("descartados en reporte", rep_descartados == str(n_descartado),
          f"reporte={rep_descartados} csv={n_descartado}")

    rep_alta = buscar_en_tabla(r"\| Alta\s*\|\s*(\d+)", reporte)
    check("alta en reporte", rep_alta == str(n_alta),
          f"reporte={rep_alta} csv={n_alta}")

    rep_media = buscar_en_tabla(r"\| Media\s*\|\s*(\d+)", reporte)
    check("media en reporte", rep_media == str(n_media),
          f"reporte={rep_media} csv={n_media}")

    rep_sin_tel = buscar_en_tabla(r"Sin tel.*utilizable\s*\|\s*(\d+)", reporte)
    check("sin_tel en reporte", rep_sin_tel == str(n_sin_tel),
          f"reporte={rep_sin_tel} csv={n_sin_tel}")

    rep_dup = buscar_en_tabla(r"Duplicado\s*\|\s*(\d+)", reporte)
    check("duplicados en reporte", rep_dup == str(n_dup),
          f"reporte={rep_dup} csv={n_dup}")

    rep_fuera = buscar_en_tabla(r"Fuera de zona.*\|\s*(\d+)", reporte)
    check("fuera_zona en reporte", rep_fuera == str(n_fuera_zona),
          f"reporte={rep_fuera} csv={n_fuera_zona}")

    rep_evitadas = buscar_en_tabla(r"Llamadas evitadas\s*\|\s*(\d+)", reporte)
    check("llamadas evitadas en reporte", rep_evitadas == str(n_descartado),
          f"reporte={rep_evitadas} csv={n_descartado}")

    rep_horas = buscar_en_tabla(r"Horas de operador ahorradas.*?\|\s*\**(\d+\.?\d*)\s*h", reporte)
    check("horas en reporte", rep_horas == str(horas),
          f"reporte={rep_horas} csv={horas}")

    # --- Paso 6: supuestos visibles ---
    print("\n--- Supuestos visibles ---")
    check("minutos por llamada visible",
          "4 min" in reporte and "supuesto" in reporte.split("4 min")[0].split("\n")[-1],
          "4 min no está junto a *(supuesto)*")

    check("costo operador = a definir",
          "a definir con el cliente" in reporte)

    # --- Paso 7: fecha de corte en reporte ---
    check("fecha de corte en reporte", "2026-07-28" in reporte)

    # --- Paso 8: por_score si > 0 ---
    if n_por_score > 0:
        rep_score = buscar_en_tabla(r"Puntaje bajo.*?\|\s*(\d+)", reporte)
        check("por_score en reporte", rep_score == str(n_por_score),
              f"reporte={rep_score} csv={n_por_score}")
    else:
        check("por_score no aparece (es 0)",
              "Puntaje bajo" not in reporte)

    # --- Paso 9: porcentajes correctos ---
    print("\n--- Porcentajes ---")
    pct_alta = round(n_alta * 100 / total, 1)
    pct_media = round(n_media * 100 / total, 1)
    rep_pct_alta = buscar_en_tabla(r"\| Alta\s*\|\s*\d+\s*\|\s*(\d+\.?\d*)%", reporte)
    rep_pct_media = buscar_en_tabla(r"\| Media\s*\|\s*\d+\s*\|\s*(\d+\.?\d*)%", reporte)
    check("% alta correcto", rep_pct_alta == str(pct_alta),
          f"reporte={rep_pct_alta} csv={pct_alta}")
    check("% media correcto", rep_pct_media == str(pct_media),
          f"reporte={rep_pct_media} csv={pct_media}")

    # --- Paso 10: legibilidad básica ---
    print("\n--- Legibilidad ---")
    check("título presente", "Reporte de impacto" in reporte)
    check("sección Resumen", "## Resumen" in reporte)
    check("sección Contactos llamables", "## Contactos llamables" in reporte)
    check("sección Motivos de descarte", "## Motivos de descarte" in reporte)
    check("sección Ahorro estimado", "## Ahorro estimado" in reporte)
    check("separación calidad vs zona",
          "calidad de dato" in reporte and "zona de cobertura" in reporte)

    # --- Limpieza ---
    for f in [com, aud, rep]:
        if os.path.exists(f):
            os.remove(f)

    # --- Resumen ---
    total_checks = ok + fail
    print("\n" + "=" * 60)
    if fail == 0:
        print(f"v08_reporte: {ok}/{total_checks} PASA")
    else:
        print(f"v08_reporte: {ok}/{total_checks} PASA, {fail} FALLA")
    print("=" * 60)

    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
