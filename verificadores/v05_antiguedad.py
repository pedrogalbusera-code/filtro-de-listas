#!/usr/bin/env python3
"""Verificador F05 - Antiguedad del lead.

EJECUTA n8n de verdad — no compara el oraculo contra si mismo.

Corridas:
  A y B: corte 2026-07-28, mismo CSV -> hash de CSV identico (determinismo).
  C: corte 2026-07-29 -> contactos cruzan de tramo (id_fila 103: alta->media).
  D: corte 2026-09-30 -> dos tramos vacios (alta 0, media 0).
  Adversario: leads_adversario_1.csv con corte 2026-07-28 -> trampas T32-T38.

Uso:
    python verificadores/v05_antiguedad.py

Exit code 0 si pasa, 1 si falla.
"""
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
GEN = RAIZ / "herramientas" / "gen_workflow.py"
CSV_IN = RAIZ / "data" / "leads_prueba_SINTETICO_1.csv"
CSV_ADV = RAIZ / "data" / "leads_adversario_1.csv"

TMP_WF = RAIZ / "workflows" / "_tmp_v05.json"
TMP_OUT = RAIZ / "salidas" / "_tmp_v05.csv"
TMP_ADV_OUT = RAIZ / "salidas" / "_tmp_v05_adv.csv"
SALIDA = RAIZ / "salidas" / "salida_f05.csv"

WF_ID_TMP = "f05antiguedad_tmp"

resultados = []


def check(nombre, ok, detalle=""):
    resultados.append((nombre, ok, detalle))
    return ok


# ---------------------------------------------------------------------------
# Oraculo independiente (para comparar fila por fila con n8n)
# ---------------------------------------------------------------------------

def parse_fecha_py(s):
    """Mismo algoritmo que el nodo, en Python."""
    t = "" if s is None else str(s).strip()
    if t == "":
        return None, ["fecha vacia"], False

    m_iso = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", t)
    if m_iso:
        y, mo, d = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
        try:
            return date(y, mo, d), [], False
        except ValueError:
            return None, ["fecha ilegible"], False

    m_dmy = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", t)
    if m_dmy:
        d_val, mo_val, y_val = int(m_dmy.group(1)), int(m_dmy.group(2)), int(m_dmy.group(3))
        ambigua = d_val <= 12 and mo_val <= 12
        try:
            fecha = date(y_val, mo_val, d_val)
        except ValueError:
            return None, ["fecha ilegible"], False
        motivos = ["fecha ambigua"] if ambigua else []
        return fecha, motivos, ambigua

    return None, ["fecha ilegible"], False


def oraculo(fecha_carga_raw, corte):
    """Devuelve (dias_antiguedad, frescura, motivo_frescura)."""
    fc, motivos, _ = parse_fecha_py(fecha_carga_raw)
    if fc is None:
        return "", "sin dato", "; ".join(motivos)
    dias = (corte - fc).days
    motivos_out = list(motivos)
    if dias < 0:
        motivos_out.append("fecha futura")
        return dias, "sin dato", "; ".join(motivos_out)
    if dias <= 15:
        fr = "alta"
    elif dias <= 45:
        fr = "media"
    elif dias <= 90:
        fr = "baja"
    else:
        fr = "fria"
    return dias, fr, "; ".join(motivos_out)


# ---------------------------------------------------------------------------
# Ejecucion de n8n
# ---------------------------------------------------------------------------

def _env():
    env = os.environ.copy()
    env["N8N_RESTRICT_FILE_ACCESS_TO"] = str(RAIZ)
    env["N8N_DIAGNOSTICS_ENABLED"] = "false"
    env["N8N_SECURE_COOKIE"] = "false"
    return env


def generar_y_ejecutar(fecha_corte, csv_in, csv_out):
    """Genera workflow temporal, importa, ejecuta. Devuelve filas del CSV."""
    subprocess.run(
        [sys.executable, str(GEN), str(TMP_WF), str(csv_in), str(csv_out),
         "--fase", "05", "--fecha-corte", fecha_corte],
        check=True, cwd=str(RAIZ), capture_output=True,
    )
    with open(TMP_WF, "r", encoding="utf-8") as fh:
        wf = json.load(fh)
    wf["id"] = WF_ID_TMP
    wf["name"] = "06-antiguedad-tmp"
    with open(TMP_WF, "w", encoding="utf-8") as fh:
        json.dump(wf, fh, indent=2, ensure_ascii=False)

    env = _env()
    subprocess.run(
        ["npx", "n8n", "import:workflow", f"--input={TMP_WF}"],
        check=True, cwd=str(RAIZ), env=env, capture_output=True, shell=True,
    )
    subprocess.run(
        ["npx", "n8n", "execute", f"--id={WF_ID_TMP}"],
        check=True, cwd=str(RAIZ), env=env, capture_output=True, shell=True,
    )
    return leer(csv_out)


def leer(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def hash_archivo(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def cleanup():
    for p in [TMP_WF, TMP_OUT, TMP_ADV_OUT]:
        if p.exists():
            p.unlink()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    try:
        return _main()
    finally:
        cleanup()


def _main():
    # ==================================================================
    # CORRIDA A — corte 2026-07-28 sobre CSV principal
    # ==================================================================
    print("\n  --- Corrida A (corte 2026-07-28) ---")
    filas_a = generar_y_ejecutar("2026-07-28", CSV_IN, SALIDA)

    check("A: salida tiene 200 filas", len(filas_a) == 200, f"tiene {len(filas_a)}")

    cols = filas_a[0].keys() if filas_a else []
    check("A: columna dias_antiguedad", "dias_antiguedad" in cols)
    check("A: columna frescura", "frescura" in cols)
    check("A: columna motivo_frescura", "motivo_frescura" in cols)
    check("A: columna fecha_corte_usada", "fecha_corte_usada" in cols)

    # Oraculo vs n8n
    corte_a = date(2026, 7, 28)
    difs = []
    for i, fo in enumerate(filas_a, 1):
        esp_d, esp_f, esp_m = oraculo(fo["fecha_carga"], corte_a)
        n_d = fo["dias_antiguedad"]
        n_f = fo["frescura"].strip()
        n_m = fo["motivo_frescura"].strip()
        if str(esp_d) != str(n_d):
            difs.append(f"fila {i}: dias n8n={n_d!r} oraculo={esp_d!r}")
        if n_f != esp_f:
            difs.append(f"fila {i}: frescura n8n={n_f!r} oraculo={esp_f!r}")
        if n_m != esp_m:
            difs.append(f"fila {i}: motivo n8n={n_m!r} oraculo={esp_m!r}")
    check(
        "A: n8n coincide con el oraculo en las 200 filas",
        not difs,
        f"{len(difs)} difs; primera: {difs[0] if difs else ''}",
    )

    # Conteos exactos
    conteo_a = {}
    for f in filas_a:
        fr = f["frescura"].strip()
        conteo_a[fr] = conteo_a.get(fr, 0) + 1
    check("A: alta 39", conteo_a.get("alta", 0) == 39, f"hay {conteo_a.get('alta', 0)}")
    check("A: media 42", conteo_a.get("media", 0) == 42, f"hay {conteo_a.get('media', 0)}")
    check("A: baja 65", conteo_a.get("baja", 0) == 65, f"hay {conteo_a.get('baja', 0)}")
    check("A: fria 54", conteo_a.get("fria", 0) == 54, f"hay {conteo_a.get('fria', 0)}")
    check("A: sin dato 0", conteo_a.get("sin dato", 0) == 0, f"hay {conteo_a.get('sin dato', 0)}")

    # 4 tramos poblados
    check(
        "A: los 4 tramos poblados",
        all(conteo_a.get(t, 0) > 0 for t in ["alta", "media", "baja", "fria"]),
    )

    # fecha_corte_usada homogenea
    fcus = set(f["fecha_corte_usada"].strip() for f in filas_a)
    check("A: fecha_corte_usada = 2026-07-28 en las 200", fcus == {"2026-07-28"}, f"{fcus}")

    # motivo_frescura vacio en las 200 (CSV principal no tiene fechas rotas)
    motivos = set(f["motivo_frescura"].strip() for f in filas_a)
    check("A: motivo_frescura vacio en las 200", motivos == {""}, f"{motivos}")

    # id_fila 103 con corte 07-28: 15 dias, alta
    f103_a = next((f for f in filas_a if f.get("id_fila", "").strip() == "103"), None)
    check(
        "A: id_fila 103 existe y es Emilia",
        f103_a is not None and "Emilia" in f103_a.get("nombre", ""),
        f"nombre={f103_a['nombre'] if f103_a else '?'}",
    )
    if f103_a:
        check(
            "A: id_fila 103 tiene 15 dias -> alta",
            f103_a["dias_antiguedad"].strip() == "15" and f103_a["frescura"].strip() == "alta",
            f"dias={f103_a['dias_antiguedad']} frescura={f103_a['frescura']}",
        )

    # Rango de dias
    dias_list = [int(f["dias_antiguedad"]) for f in filas_a if f["dias_antiguedad"].strip() != ""]
    check("A: dias minimo 0", min(dias_list) == 0, f"min={min(dias_list)}")
    check("A: dias maximo 109", max(dias_list) == 109, f"max={max(dias_list)}")

    hash_a = hash_archivo(SALIDA)

    # ==================================================================
    # CORRIDA B — misma fecha, determinismo real
    # ==================================================================
    print("  --- Corrida B (determinismo) ---")
    generar_y_ejecutar("2026-07-28", CSV_IN, SALIDA)
    hash_b = hash_archivo(SALIDA)
    check("B: hash identico a corrida A (determinismo real)", hash_a == hash_b,
          f"A={hash_a[:16]}... B={hash_b[:16]}...")

    # ==================================================================
    # CORRIDA C — corte 2026-07-29
    # ==================================================================
    print("  --- Corrida C (corte 2026-07-29) ---")
    filas_c = generar_y_ejecutar("2026-07-29", CSV_IN, TMP_OUT)

    conteo_c = {}
    for f in filas_c:
        fr = f["frescura"].strip()
        conteo_c[fr] = conteo_c.get(fr, 0) + 1
    check("C: alta 34", conteo_c.get("alta", 0) == 34, f"hay {conteo_c.get('alta', 0)}")
    check("C: media 44", conteo_c.get("media", 0) == 44, f"hay {conteo_c.get('media', 0)}")
    check("C: baja 68", conteo_c.get("baja", 0) == 68, f"hay {conteo_c.get('baja', 0)}")
    check("C: fria 54", conteo_c.get("fria", 0) == 54, f"hay {conteo_c.get('fria', 0)}")

    # id_fila 103 cruza de alta a media
    f103_c = next((f for f in filas_c if f.get("id_fila", "").strip() == "103"), None)
    if check("C: id_fila 103 existe", f103_c is not None):
        check(
            "C: id_fila 103 tiene 16 dias -> media (cruzo el borde)",
            f103_c["dias_antiguedad"].strip() == "16" and f103_c["frescura"].strip() == "media",
            f"dias={f103_c['dias_antiguedad']} frescura={f103_c['frescura']}",
        )

    fcu_c = set(f["fecha_corte_usada"].strip() for f in filas_c)
    check("C: fecha_corte_usada = 2026-07-29", fcu_c == {"2026-07-29"}, f"{fcu_c}")

    # ==================================================================
    # CORRIDA D — corte 2026-09-30
    # ==================================================================
    print("  --- Corrida D (corte 2026-09-30) ---")
    filas_d = generar_y_ejecutar("2026-09-30", CSV_IN, TMP_OUT)

    conteo_d = {}
    for f in filas_d:
        fr = f["frescura"].strip()
        conteo_d[fr] = conteo_d.get(fr, 0) + 1
    check("D: alta 0", conteo_d.get("alta", 0) == 0, f"hay {conteo_d.get('alta', 0)}")
    check("D: media 0", conteo_d.get("media", 0) == 0, f"hay {conteo_d.get('media', 0)}")
    check("D: baja 43", conteo_d.get("baja", 0) == 43, f"hay {conteo_d.get('baja', 0)}")
    check("D: fria 157", conteo_d.get("fria", 0) == 157, f"hay {conteo_d.get('fria', 0)}")

    # ==================================================================
    # CORRIDA ADVERSARIO — leads_adversario_1.csv, corte 2026-07-28
    # ==================================================================
    print("  --- Corrida Adversario (T32-T38) ---")
    filas_adv = generar_y_ejecutar("2026-07-28", CSV_ADV, TMP_ADV_OUT)

    check("ADV: salida tiene 48 filas", len(filas_adv) == 48, f"tiene {len(filas_adv)}")

    # Buscar filas T32-T38 por nombre
    def buscar(prefijo):
        return next((f for f in filas_adv if f.get("nombre", "").startswith(prefijo)), None)

    t32 = buscar("T32")
    t33 = buscar("T33")
    t34 = buscar("T34")
    t35 = buscar("T35")
    t36 = buscar("T36")
    t37 = buscar("T37")
    t38 = buscar("T38")

    check("ADV: T32 existe", t32 is not None)
    if t32:
        check("ADV: T32 dias=109, frescura=fria, motivo=fecha ambigua",
              t32["dias_antiguedad"].strip() == "109"
              and t32["frescura"].strip() == "fria"
              and t32["motivo_frescura"].strip() == "fecha ambigua",
              f"dias={t32['dias_antiguedad']} fr={t32['frescura']} mot={t32['motivo_frescura']}")

    check("ADV: T33 existe", t33 is not None)
    if t33:
        check("ADV: T33 dias=-68, frescura=sin dato, motivo=fecha ambigua; fecha futura",
              t33["dias_antiguedad"].strip() == "-68"
              and t33["frescura"].strip() == "sin dato"
              and t33["motivo_frescura"].strip() == "fecha ambigua; fecha futura",
              f"dias={t33['dias_antiguedad']} fr={t33['frescura']} mot={t33['motivo_frescura']}")

    check("ADV: T34 existe", t34 is not None)
    if t34:
        check("ADV: T34 dias=vacio, frescura=sin dato, motivo=fecha ilegible",
              t34["dias_antiguedad"].strip() == ""
              and t34["frescura"].strip() == "sin dato"
              and t34["motivo_frescura"].strip() == "fecha ilegible",
              f"dias={t34['dias_antiguedad']!r} fr={t34['frescura']} mot={t34['motivo_frescura']}")

    check("ADV: T35 existe", t35 is not None)
    if t35:
        check("ADV: T35 dias=vacio, frescura=sin dato, motivo=fecha vacia",
              t35["dias_antiguedad"].strip() == ""
              and t35["frescura"].strip() == "sin dato"
              and t35["motivo_frescura"].strip() == "fecha vacia",
              f"dias={t35['dias_antiguedad']!r} fr={t35['frescura']} mot={t35['motivo_frescura']}")

    check("ADV: T36 existe", t36 is not None)
    if t36:
        check("ADV: T36 dias=vacio, frescura=sin dato, motivo=fecha ilegible",
              t36["dias_antiguedad"].strip() == ""
              and t36["frescura"].strip() == "sin dato"
              and t36["motivo_frescura"].strip() == "fecha ilegible",
              f"dias={t36['dias_antiguedad']!r} fr={t36['frescura']} mot={t36['motivo_frescura']}")

    check("ADV: T37 existe", t37 is not None)
    if t37:
        check("ADV: T37 dias=-171, frescura=sin dato, motivo=fecha futura",
              t37["dias_antiguedad"].strip() == "-171"
              and t37["frescura"].strip() == "sin dato"
              and t37["motivo_frescura"].strip() == "fecha futura",
              f"dias={t37['dias_antiguedad']} fr={t37['frescura']} mot={t37['motivo_frescura']}")

    check("ADV: T38 existe", t38 is not None)
    if t38:
        check("ADV: T38 dias=2705, frescura=fria, motivo=vacio",
              t38["dias_antiguedad"].strip() == "2705"
              and t38["frescura"].strip() == "fria"
              and t38["motivo_frescura"].strip() == "",
              f"dias={t38['dias_antiguedad']} fr={t38['frescura']} mot={t38['motivo_frescura']!r}")

    # ==================================================================
    # CHECKS DE ORACULO (prefijo '(oraculo)' — Python, no n8n)
    # ==================================================================

    # Fechas malformadas
    corte_o = date(2026, 7, 28)
    d1, f1, m1 = oraculo("", corte_o)
    check("(oraculo) fecha vacia -> sin dato", d1 == "" and f1 == "sin dato" and m1 == "fecha vacia")
    d2, f2, m2 = oraculo("hoy", corte_o)
    check("(oraculo) texto -> sin dato", d2 == "" and f2 == "sin dato" and m2 == "fecha ilegible")
    d3, f3, m3 = oraculo("2026-13-45", corte_o)
    check("(oraculo) mes 13 -> sin dato", d3 == "" and f3 == "sin dato" and m3 == "fecha ilegible")
    d4, f4, m4 = oraculo("10-abr-26", corte_o)
    check("(oraculo) mes texto -> sin dato", d4 == "" and f4 == "sin dato" and m4 == "fecha ilegible")

    # dd/mm/aaaa
    d5, f5, m5 = oraculo("25/12/2026", corte_o)
    check("(oraculo) 25/12 no es ambigua", "fecha ambigua" not in m5, f"motivo={m5!r}")
    d6, f6, m6 = oraculo("10/04/2026", corte_o)
    check("(oraculo) 10/04 SI es ambigua", "fecha ambigua" in m6, f"motivo={m6!r}")

    return reportar()


def reportar():
    ancho = max(len(n) for n, _, _ in resultados)
    print()
    print("  VERIFICADOR F05 - antiguedad del lead")
    print("  " + "-" * (ancho + 12))
    for nombre, ok, detalle in resultados:
        marca = "PASA" if ok else "FALLA"
        linea = f"  {marca:<5} {nombre.ljust(ancho)}"
        if detalle and not ok:
            linea += f"   <- {detalle}"
        elif detalle and ok:
            linea += f"   ({detalle})"
        print(linea)
    fallas = [n for n, ok, _ in resultados if not ok]
    print("  " + "-" * (ancho + 12))
    if fallas:
        print(f"  RESULTADO: FALLA ({len(fallas)} de {len(resultados)} checks)")
        print()
        return 1
    print(f"  RESULTADO: PASA ({len(resultados)} checks)")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
