#!/usr/bin/env python3
"""v07_salida.py — Verificador de F07 (Salida ordenada).

Ejecuta el workflow de n8n y verifica:
  - 200 filas en ambos archivos (comercial y auditoría)
  - Distribución invariante: alta 48, media 38, descartado 114
  - Orden: clave de 4 partes verificada fila por fila
  - Oráculo Python independiente (sort) vs salida n8n
  - Alineación entre archivos comercial y auditoría
  - Determinismo: dos corridas producen archivos byte a byte idénticos
  - Encoding: UTF-8 con BOM, tildes intactas, saltos \n
  - Caso armado a mano: empate triple con dias_antiguedad vacío
"""
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_IN = os.path.join(BASE, "data", "leads_prueba_SINTETICO_1.csv")
GEN = os.path.join(BASE, "herramientas", "gen_workflow.py")
WF_ID_TMP = "f07salida__tmp"

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
# Oráculo Python: ordena igual que JS_F07_SORT
# ---------------------------------------------------------------------------
PRIORIDAD_ORDEN = {"alta": 0, "media": 1, "descartado": 2}


def sort_key(row):
    pri = PRIORIDAD_ORDEN.get(row.get("prioridad", ""), 2)
    puntaje = -int(row.get("puntaje", 0))
    da_raw = row.get("dias_antiguedad", "")
    da = float("inf") if da_raw == "" else float(da_raw)
    id_fila = int(row.get("id_fila", 0))
    return (pri, puntaje, da, id_fila)


# ---------------------------------------------------------------------------
# Generación y ejecución del workflow
# ---------------------------------------------------------------------------
def generar_y_ejecutar(csv_in, csv_out_com, csv_out_aud):
    tmp_wf = os.path.join(tempfile.gettempdir(), "wf_f07_tmp.json")
    subprocess.run(
        [sys.executable, GEN, tmp_wf, csv_in, csv_out_com,
         "--fase", "07", "--fecha-corte", "2026-07-28",
         "--csv-out-audit", csv_out_aud],
        check=True,
    )
    with open(tmp_wf, "r", encoding="utf-8") as f:
        wf = json.load(f)
    wf["id"] = WF_ID_TMP
    wf["name"] = "tmp-salida"
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


# ---------------------------------------------------------------------------
# Verificaciones
# ---------------------------------------------------------------------------
def main():
    global ok, fail

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 60)
    print("v07_salida.py — Verificador F07 (Salida ordenada)")
    print("=" * 60)

    # --- Paso 1: ejecutar n8n (corrida 1) ---
    print("\n--- Ejecutando workflow en n8n (corrida 1) ---")
    com1 = os.path.join(BASE, "salidas", "salida_f07_com_v1.csv")
    aud1 = os.path.join(BASE, "salidas", "salida_f07_aud_v1.csv")

    try:
        generar_y_ejecutar(CSV_IN, com1, aud1)
    except Exception as e:
        print(f"  ERROR ejecutando n8n: {e}")
        sys.exit(1)

    rows_com = leer_csv(com1)
    rows_aud = leer_csv(aud1)

    # --- Paso 2: conteo y distribución ---
    print("\n--- Conteo y distribución ---")
    check("(com) 200 filas", len(rows_com) == 200,
          f"esperado 200, obtenido {len(rows_com)}")
    check("(aud) 200 filas", len(rows_aud) == 200,
          f"esperado 200, obtenido {len(rows_aud)}")

    check("(com) 9 columnas", len(rows_com[0]) == 9,
          f"obtenido {len(rows_com[0])}: {list(rows_com[0].keys())}")
    check("(aud) 26 columnas", len(rows_aud[0]) == 26,
          f"obtenido {len(rows_aud[0])}: {list(rows_aud[0].keys())}")

    from collections import Counter
    dist_com = Counter(r["prioridad"] for r in rows_com)
    dist_aud = Counter(r["prioridad"] for r in rows_aud)
    check("(com) alta=48", dist_com.get("alta", 0) == 48,
          f"obtenido {dist_com.get('alta', 0)}")
    check("(com) media=38", dist_com.get("media", 0) == 38,
          f"obtenido {dist_com.get('media', 0)}")
    check("(com) descartado=114", dist_com.get("descartado", 0) == 114,
          f"obtenido {dist_com.get('descartado', 0)}")
    check("(aud) distribución = comercial", dist_aud == dist_com,
          f"aud={dict(dist_aud)}")

    # --- Paso 3: columnas del archivo comercial ---
    print("\n--- Columnas comercial ---")
    COLS_COM_ESPERADAS = ['nombre', 'cuil', 'telefono', 'localidad', 'origen',
                          'fecha_carga', 'puntaje', 'prioridad', 'motivo']
    check("(com) columnas correctas",
          list(rows_com[0].keys()) == COLS_COM_ESPERADAS,
          f"obtenido {list(rows_com[0].keys())}")

    # --- Paso 4: orden verificado fila por fila ---
    print("\n--- Orden (clave de 4 partes) ---")
    orden_ok = True
    orden_det = []
    for i in range(len(rows_aud) - 1):
        ka = sort_key(rows_aud[i])
        kb = sort_key(rows_aud[i + 1])
        if ka > kb:
            orden_ok = False
            orden_det.append(
                f"fila {i+1}→{i+2}: {ka} > {kb} "
                f"(id_fila {rows_aud[i]['id_fila']}→{rows_aud[i+1]['id_fila']})")
    check("(aud) orden correcto fila por fila", orden_ok,
          "; ".join(orden_det[:3]))

    # Verificar que orden estricto funciona (no hay filas desordenadas)
    orden_com_ok = True
    for i in range(len(rows_com) - 1):
        ka = sort_key(rows_com[i])
        kb = sort_key(rows_com[i + 1])
        if ka > kb:
            orden_com_ok = False
    check("(com) orden correcto fila por fila", orden_com_ok)

    # --- Paso 5: oráculo (sort independiente) ---
    print("\n--- Oráculo Python (sort independiente) ---")
    oracle_sorted = sorted(rows_aud, key=sort_key)
    oracle_match = all(
        rows_aud[i]["id_fila"] == oracle_sorted[i]["id_fila"]
        for i in range(len(rows_aud))
    )
    if not oracle_match:
        diffs = [i for i in range(len(rows_aud))
                 if rows_aud[i]["id_fila"] != oracle_sorted[i]["id_fila"]]
        check("(oráculo) orden coincide con sort Python", False,
              f"difieren en posiciones {diffs[:5]}")
    else:
        check("(oráculo) orden coincide con sort Python", True)

    # --- Paso 6: alineación entre comercial y auditoría ---
    print("\n--- Alineación comercial ↔ auditoría ---")
    COLS_COMPARTIDAS = ['nombre', 'cuil', 'telefono', 'localidad', 'origen',
                        'fecha_carga', 'puntaje', 'prioridad', 'motivo']
    alin_ok = True
    alin_det = []
    for i in range(min(len(rows_com), len(rows_aud))):
        for col in COLS_COMPARTIDAS:
            vc = rows_com[i].get(col, "")
            va = rows_aud[i].get(col, "")
            if vc != va:
                alin_ok = False
                alin_det.append(f"fila {i+1}, col '{col}': com={vc!r} vs aud={va!r}")
    check("(alineación) 9 columnas coinciden fila a fila", alin_ok,
          "; ".join(alin_det[:3]))

    # --- Paso 7: determinismo (corrida 2) ---
    print("\n--- Determinismo (corrida 2) ---")
    com2 = os.path.join(BASE, "salidas", "salida_f07_com_v2.csv")
    aud2 = os.path.join(BASE, "salidas", "salida_f07_aud_v2.csv")

    try:
        generar_y_ejecutar(CSV_IN, com2, aud2)
    except Exception as e:
        print(f"  ERROR en corrida 2: {e}")
        check("(det) corrida 2 ejecutó", False, str(e))
    else:
        def file_hash(path):
            with open(path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()

        h_com1 = file_hash(com1)
        h_com2 = file_hash(com2)
        h_aud1 = file_hash(aud1)
        h_aud2 = file_hash(aud2)

        check("(det) comercial byte-identical", h_com1 == h_com2,
              f"sha256 v1={h_com1[:16]}… v2={h_com2[:16]}…")
        check("(det) auditoría byte-identical", h_aud1 == h_aud2,
              f"sha256 v1={h_aud1[:16]}… v2={h_aud2[:16]}…")

    # --- Paso 8: encoding ---
    print("\n--- Encoding ---")
    with open(com1, "rb") as f:
        raw_com = f.read()
    with open(aud1, "rb") as f:
        raw_aud = f.read()

    check("(enc) comercial empieza con BOM",
          raw_com[:3] == b'\xef\xbb\xbf')
    check("(enc) auditoría empieza con BOM",
          raw_aud[:3] == b'\xef\xbb\xbf')

    check("(enc) comercial sin CRLF",
          b'\r\n' not in raw_com,
          f"encontrado CRLF en {raw_com.count(b'\\r\\n')} posiciones")
    check("(enc) auditoría sin CRLF",
          b'\r\n' not in raw_aud)

    # Tildes intactas
    texto_com = raw_com.decode("utf-8-sig")
    check("(enc) tildes en comercial",
          "á" in texto_com or "é" in texto_com or "í" in texto_com,
          "no se encontraron tildes")

    # --- Paso 9: motivo legible ---
    print("\n--- Motivo legible ---")
    for r in rows_com:
        motivo = r["motivo"]
        nums = re.findall(r"([+-]\d+)", motivo)
        suma = sum(int(n) for n in nums)
        puntaje = int(r["puntaje"])
        if suma != puntaje:
            check("(motivo) auditabilidad", False,
                  f"id_fila desconocido: suma={suma} != puntaje={puntaje}")
            break
    else:
        check("(motivo) auditabilidad 200/200", True)

    # --- Paso 10: bloques de prioridad ---
    print("\n--- Bloques de prioridad ---")
    prioridades_en_orden = [r["prioridad"] for r in rows_com]
    bloques = []
    for p in prioridades_en_orden:
        if not bloques or bloques[-1] != p:
            bloques.append(p)
    check("(bloques) orden alta→media→descartado",
          bloques == ["alta", "media", "descartado"],
          f"bloques observados: {bloques}")

    # --- Paso 11: caso armado a mano (empate triple) ---
    print("\n--- Caso armado: empate triple ---")
    empate_rows = [r for r in rows_aud
                   if r["prioridad"] == "alta"
                   and int(r["puntaje"]) == 90
                   and r.get("frescura") == "alta"]
    if len(empate_rows) >= 2:
        for i in range(len(empate_rows) - 1):
            da_a = empate_rows[i]["dias_antiguedad"]
            da_b = empate_rows[i + 1]["dias_antiguedad"]
            fa = float("inf") if da_a == "" else float(da_a)
            fb = float("inf") if da_b == "" else float(da_b)
            if fa > fb:
                check("(empate) dias_antiguedad asc dentro del bloque",
                      False,
                      f"id_fila {empate_rows[i]['id_fila']} (da={da_a}) > "
                      f"id_fila {empate_rows[i+1]['id_fila']} (da={da_b})")
                break
            elif fa == fb:
                if int(empate_rows[i]["id_fila"]) > int(empate_rows[i + 1]["id_fila"]):
                    check("(empate) id_fila asc como desempate final",
                          False,
                          f"id_fila {empate_rows[i]['id_fila']} > "
                          f"{empate_rows[i+1]['id_fila']}")
                    break
        else:
            check("(empate) desempate correcto dentro del bloque", True)
    else:
        check("(empate) grupo encontrado", len(empate_rows) >= 2,
              f"solo {len(empate_rows)} filas con puntaje=90, frescura=alta, alta")

    # --- Limpieza ---
    for f in [com1, aud1, com2, aud2]:
        if os.path.exists(f):
            os.remove(f)

    # --- Resumen ---
    total = ok + fail
    print("\n" + "=" * 60)
    if fail == 0:
        print(f"v07_salida: {ok}/{total} PASA")
    else:
        print(f"v07_salida: {ok}/{total} PASA, {fail} FALLA")
    print("=" * 60)

    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
