#!/usr/bin/env python3
"""v13_basura.py — Verificador de F13 (números y nombres basura).

Ejecuta n8n de verdad (importar + --id), mismo estandar que v05/v06/v07/v11/v12.
Tres bloques:

  1. Canonico con basura ENCENDIDA (default del repo): los dos golden de F09
     byte a byte, y el reporte identico al de una corrida con los patrones
     vacios. Ese A/B es la prueba de CERO FALSOS POSITIVOS sobre datos reales:
     si un patron se comiera una fila real, las dos corridas dividirian.
  2. leads_basura_1.csv POR EL NODO REAL: checks de celda contra la tabla.
     Cada patron cae con su motivo exacto, y cada CONTROL real queda intacto.
  3. Reporte: la fila de telefono de relleno cuenta bien sobre el archivo de
     basura, y la subtabla de segmento aparece con la segmentacion encendida
     (la deuda que F12 dejo registrada).

Los esperados son LITERALES escritos a mano desde las reglas de la fase.
Prohibido calcularlos con la logica del nodo: comparar la salida contra la
misma logica que la produjo es el hallazgo de F05.
"""
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(BASE, "herramientas", "gen_workflow.py")
DATA = os.path.join(BASE, "data")
SAL = os.path.join(BASE, "salidas")
CONFIG = os.path.join(BASE, "config")
GOLDEN_COM = os.path.join(SAL, "golden_2026-07-28.csv")
GOLDEN_AUD = os.path.join(SAL, "golden_2026-07-28_auditoria.csv")
CANONICO = os.path.join(DATA, "leads_prueba_SINTETICO_1.csv")
WF_ID = "f13basura___tmp"
FECHA_CORTE = "2026-07-28"

MOT_TEL = "teléfono de relleno"
MOT_NOM = "nombre de relleno"
MOT_SEG = "segmento no buscado"

# ---------------------------------------------------------------------------
# EL SPEC, ESCRITO A MANO. Cada fila de data/leads_basura_1.csv, su CUIL (que
# es la clave con la que se la ubica, porque dos filas tienen el nombre de
# relleno como nombre), y que tiene que pasarle.
#
#   descarta_tel : lleva "teléfono de relleno" y queda descartado
#   marca_nombre : lleva "nombre de relleno" y NO se descarta (sigue llamable)
#   prioridad    : el valor exacto esperado
#
# Todas las filas del archivo son limpias salvo por lo que se esta probando
# (telefono valido, en zona, CUIL valido, fecha fresca, origen referido), asi
# que el UNICO descarte posible es el de basura.
# ---------------------------------------------------------------------------
CASOS = [
    # (cuil, que es, descarta_tel, marca_nombre, prioridad, por que)
    ("20-40100001-2", "B01 teléfono todo unos (10 dígitos iguales)",
     True,  False, "descartado", "los 7 últimos dígitos son iguales"),
    ("27-40100002-5", "B02 teléfono secuencia 1234567890",
     True,  False, "descartado", "está en la lista explícita de secuencias"),
    ("20-40100003-9", "B03 nombre 'test' con teléfono BUENO",
     False, True,  "alta",       "nombre de relleno es marca, no descarte"),
    ("27-40100004-1", "B04 nombre 'N/A' con teléfono BUENO",
     False, True,  "alta",       "normalizado cae en la lista de relleno"),
    ("20-40100005-5", "B05 CONTROL: 1155551111, repite dígitos pero es real",
     False, False, "alta",       "la cola de 7 no es toda igual"),
    ("27-40100006-8", "B06 CONTROL: 'Ana Testa', apellido real que contiene 'test'",
     False, False, "alta",       "la comparación es por igualdad, no por substring"),
    ("20-40100007-1", "B07 CONTROL: 1145111111, 6 repetidos al final",
     False, False, "alta",       "el umbral es 7: seis no alcanza"),
]

# Contados a mano sobre la tabla de arriba.
ESPERADO_DESCARTES_TEL = 2
ESPERADO_MARCAS_NOMBRE = 2

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


def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def leer_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return list(r), list(r.fieldnames or [])


def leer_txt(path):
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()


def escribir_config(cfg, nombre):
    path = os.path.join(tempfile.gettempdir(), nombre)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return path


def fila_reporte(reporte, etiqueta):
    """Saca el numero de una fila de tabla del reporte: | <etiqueta> | N |"""
    m = re.search(r"\|\s*" + re.escape(etiqueta) + r"\s*\|\s*(\d+)\s*\|", reporte)
    return int(m.group(1)) if m else None


def correr_caso(archivo_in, etiqueta, basura_cfg=None, seg_cfg=None):
    """Genera el workflow (fase 12, la cabeza del pipeline), importa y ejecuta."""
    stem = os.path.splitext(os.path.basename(archivo_in))[0]
    com = os.path.join(SAL, f"_v13_{etiqueta}_{stem}_com.csv")
    aud = os.path.join(SAL, f"_v13_{etiqueta}_{stem}_aud.csv")
    rep = os.path.join(SAL, f"_v13_{etiqueta}_{stem}_rep.md")
    ficha = os.path.join(SAL, f"ficha_entrada_{stem}.md")
    for f in (com, aud, rep):
        if os.path.exists(f):
            os.remove(f)

    cmd = [sys.executable, GEN, os.path.join(tempfile.gettempdir(), "wf_v13_tmp.json"),
           archivo_in, com, "--fase", "12", "--fecha-corte", FECHA_CORTE,
           "--csv-out-audit", aud, "--reporte-out", rep, "--ficha-out", ficha]
    if basura_cfg is not None:
        cmd += ["--basura", escribir_config(basura_cfg, f"basura_v13_{etiqueta}.json")]
    if seg_cfg is not None:
        cmd += ["--segmentacion", escribir_config(seg_cfg, f"seg_v13_{etiqueta}.json")]
    subprocess.run(cmd, check=True, capture_output=True)

    tmp_wf = os.path.join(tempfile.gettempdir(), "wf_v13_tmp.json")
    with open(tmp_wf, "r", encoding="utf-8") as f:
        wf = json.load(f)
    wf["id"] = WF_ID
    wf["name"] = "tmp-v13"
    with open(tmp_wf, "w", encoding="utf-8") as f:
        json.dump(wf, f, indent=2, ensure_ascii=False)

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
    os.remove(tmp_wf)
    exito = r.returncode == 0 and "Execution was successful" in (r.stdout or "")
    return {"com": com, "aud": aud, "rep": rep, "exito": exito}


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("=" * 70)
    print("v13_basura.py — Verificador F13 (números y nombres basura)")
    print("=" * 70)

    # ==================================================================
    print("\n--- La config protege contra el falso positivo: valores golosos frenan ---")
    tmp_wf = os.path.join(tempfile.gettempdir(), "wf_v13_cfg.json")
    base_cfg = {"telefonos": {"min_digitos_iguales_al_final": 7, "secuencias": []},
                "nombres": {"relleno": []}}

    def generar(cfg):
        p = escribir_config(cfg, "basura_v13_cfgcheck.json")
        return subprocess.run(
            [sys.executable, GEN, tmp_wf, CANONICO, os.path.join(SAL, "_v13_x.csv"),
             "--fase", "12", "--basura", p],
            capture_output=True, text=True, encoding="utf-8", errors="replace")

    for minimo, debe_pasar in [(7, True), (4, True), (10, True), (3, False), (1, False), (0, False)]:
        cfg = json.loads(json.dumps(base_cfg))
        cfg["telefonos"]["min_digitos_iguales_al_final"] = minimo
        r = generar(cfg)
        if debe_pasar:
            check(f"umbral de {minimo} dígitos iguales es una config válida",
                  r.returncode == 0, (r.stderr or "")[-160:])
        else:
            check(f"umbral de {minimo} dígitos iguales se rechaza al generar "
                  f"(se comería números reales)", r.returncode != 0,
                  "el generador lo aceptó")

    cfg = json.loads(json.dumps(base_cfg))
    cfg["telefonos"]["secuencias"] = ["12345"]
    r = generar(cfg)
    check("una secuencia que no tiene 10 dígitos se rechaza al generar "
          "(nunca matchearía y nadie se enteraría)", r.returncode != 0,
          "el generador la aceptó")
    if os.path.exists(tmp_wf):
        os.remove(tmp_wf)

    # ==================================================================
    print("\n--- Bloque 1: canónico con basura ENCENDIDA — cero falsos positivos ---")
    with open(os.path.join(CONFIG, "basura.json"), encoding="utf-8") as f:
        cfg_repo = json.load(f)
    check("el default del repo tiene umbral 7 y las dos listas pobladas",
          cfg_repo["telefonos"]["min_digitos_iguales_al_final"] == 7
          and len(cfg_repo["telefonos"]["secuencias"]) >= 3
          and len(cfg_repo["nombres"]["relleno"]) >= 8,
          f"umbral={cfg_repo['telefonos'].get('min_digitos_iguales_al_final')} "
          f"secuencias={len(cfg_repo['telefonos'].get('secuencias', []))} "
          f"nombres={len(cfg_repo['nombres'].get('relleno', []))}")

    caso = correr_caso(CANONICO, "on")
    check("(canon) la corrida termina bien", caso["exito"])
    check("(canon) comercial byte a byte idéntico al golden de F09",
          os.path.exists(caso["com"]) and file_hash(caso["com"]) == file_hash(GOLDEN_COM),
          "el golden se movió: un patrón de basura tiene un FALSO POSITIVO sobre datos reales")
    check("(canon) auditoría byte a byte idéntica al golden de F09",
          os.path.exists(caso["aud"]) and file_hash(caso["aud"]) == file_hash(GOLDEN_AUD),
          "el golden se movió: un patrón de basura tiene un FALSO POSITIVO sobre datos reales")
    rows_on, _ = leer_csv(caso["aud"])
    check("(canon) ninguna de las 200 filas menciona relleno en el motivo",
          len(rows_on) == 200
          and not any(MOT_TEL in r["motivo"] or MOT_NOM in r["motivo"] for r in rows_on),
          str([r["nombre"] for r in rows_on
               if MOT_TEL in r["motivo"] or MOT_NOM in r["motivo"]][:3]))

    rep_on = leer_txt(caso["rep"])
    check("(canon) el reporte NO trae la fila de teléfono de relleno (cuenta 0)",
          "de relleno" not in rep_on)
    check("(canon) el reporte NO trae la subtabla de segmento (cuenta 0)",
          "segmento no buscado" not in rep_on.lower())

    # A/B: la misma corrida con los patrones VACIOS = el pipeline de antes de
    # F13. Si algun patron se comiera una fila real, los reportes dividirian.
    caso_off = correr_caso(CANONICO, "off",
                           basura_cfg={"telefonos": {"min_digitos_iguales_al_final": 7,
                                                     "secuencias": []},
                                       "nombres": {"relleno": []}})
    check("(canon) la corrida con los patrones vacíos termina bien", caso_off["exito"])
    rep_off = leer_txt(caso_off["rep"])
    check("(canon) el reporte del golden es idéntico con basura encendida y apagada",
          rep_on != "" and rep_on == rep_off,
          "F13 movió el reporte de la lista canónica")
    check("(canon) los CSV son idénticos con basura encendida y apagada",
          file_hash(caso["com"]) == file_hash(caso_off["com"])
          and file_hash(caso["aud"]) == file_hash(caso_off["aud"]))

    # ==================================================================
    print("\n--- Bloque 2: leads_basura_1.csv por el NODO REAL ---")
    caso = correr_caso(os.path.join(DATA, "leads_basura_1.csv"), "on")
    check("(basura) la corrida termina bien", caso["exito"])
    rows, _ = leer_csv(caso["aud"]) if os.path.exists(caso["aud"]) else ([], [])
    check("(basura) 7 filas de salida (nada se borra, ni lo descartado)",
          len(rows) == 7, f"hay {len(rows)}")
    por_cuil = {r["cuil"]: r for r in rows}

    for cuil, que_es, desc_tel, marca_nom, prioridad, por_que in CASOS:
        r = por_cuil.get(cuil)
        if r is None:
            check(f"(basura) {que_es}: la fila está en la salida", False,
                  f"no hay ninguna fila con cuil {cuil}")
            continue
        tiene_tel = MOT_TEL in r["motivo"]
        tiene_nom = MOT_NOM in r["motivo"]
        if desc_tel:
            check(f"(basura) {que_es} → descarte por teléfono de relleno ({por_que})",
                  tiene_tel and f"{MOT_TEL} +0 → descarte" in r["motivo"],
                  f"motivo: {r['motivo']!r}")
        else:
            check(f"(basura) {que_es} → NO cae por teléfono ({por_que})",
                  not tiene_tel, f"motivo: {r['motivo']!r}")
        if marca_nom:
            check(f"(basura) {que_es} → marca de nombre de relleno, SIN descarte",
                  tiene_nom and f"{MOT_NOM} +0" in r["motivo"]
                  and "nombre de relleno +0 →" not in r["motivo"],
                  f"motivo: {r['motivo']!r}")
        else:
            check(f"(basura) {que_es} → NO cae por nombre ({por_que})",
                  not tiene_nom, f"motivo: {r['motivo']!r}")
        check(f"(basura) {que_es} → prioridad {prioridad}",
              r["prioridad"] == prioridad,
              f"esperado [{prioridad}] obtenido [{r['prioridad']}]")

    n_tel = sum(1 for r in rows if MOT_TEL in r["motivo"])
    n_nom = sum(1 for r in rows if MOT_NOM in r["motivo"])
    check(f"(basura) exactamente {ESPERADO_DESCARTES_TEL} descartes por teléfono de relleno",
          n_tel == ESPERADO_DESCARTES_TEL, f"hay {n_tel}")
    check(f"(basura) exactamente {ESPERADO_MARCAS_NOMBRE} marcas de nombre de relleno",
          n_nom == ESPERADO_MARCAS_NOMBRE, f"hay {n_nom}")
    llamables = [r for r in rows if r["prioridad"] != "descartado"]
    check("(basura) los 2 nombres de relleno siguen siendo llamables",
          sum(1 for r in llamables if MOT_NOM in r["motivo"]) == ESPERADO_MARCAS_NOMBRE)
    check("(basura) las 2 filas descartadas siguen enteras en el CSV (se marca, no se borra)",
          all(r["nombre"].strip() and r["telefono"].strip() and r["motivo"].strip()
              for r in rows if r["prioridad"] == "descartado"))
    check("(basura) el puntaje sigue siendo auditable: la suma del motivo da el puntaje",
          all(sum(int(n) for n in re.findall(r"([+-]\d+)", r["motivo"])) == int(r["puntaje"])
              for r in rows),
          str([(r["cuil"], r["motivo"], r["puntaje"]) for r in rows
               if sum(int(n) for n in re.findall(r"([+-]\d+)", r["motivo"])) != int(r["puntaje"])][:1]))

    # ==================================================================
    print("\n--- Bloque 3: el reporte deja de esconder los motivos nuevos ---")
    rep = leer_txt(caso["rep"])
    check("(reporte) la fila de teléfono de relleno cuenta exactamente 2",
          fila_reporte(rep, "Teléfono de relleno (número inventado)") == ESPERADO_DESCARTES_TEL,
          f"la fila dice {fila_reporte(rep, 'Teléfono de relleno (número inventado)')}")
    check("(reporte) esa fila está en la tabla de calidad de dato, no en la de zona",
          rep.index("Teléfono de relleno") < rep.index("Por zona de cobertura"))
    check("(reporte) los descartados del reporte son los 2 del CSV",
          fila_reporte(rep, "Contactos descartados") == 2,
          f"el reporte dice {fila_reporte(rep, 'Contactos descartados')}")

    caso_seg = correr_caso(os.path.join(DATA, "leads_segmento_1.csv"), "seg",
                           seg_cfg={"etiquetar": True, "descartar": "juridica"})
    check("(reporte) la corrida con segmentación encendida termina bien", caso_seg["exito"])
    rep_seg = leer_txt(caso_seg["rep"])
    check("(reporte) con segmentación encendida aparece la subtabla de segmento",
          "Por segmento no buscado" in rep_seg, "sigue escondida: la deuda de F12 no se cerró")
    check("(reporte) la subtabla de segmento cuenta exactamente 4 (las 4 jurídicas)",
          fila_reporte(rep_seg, "Tipo de persona que el cliente no busca") == 4,
          f"dice {fila_reporte(rep_seg, 'Tipo de persona que el cliente no busca')}")
    check("(reporte) el segmento va en su propia tabla, separado de la calidad de dato",
          rep_seg.index("Por segmento no buscado") > rep_seg.index("Por zona de cobertura"))
    rows_seg, _ = leer_csv(caso_seg["aud"])
    check("(reporte) los descartados del reporte coinciden con el CSV (4 de 11)",
          fila_reporte(rep_seg, "Contactos descartados") == 4
          and sum(1 for r in rows_seg if r["prioridad"] == "descartado") == 4)

    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    total = ok + fail
    if fail == 0:
        print(f"RESULTADO: PASA ({total} checks)")
        sys.exit(0)
    print(f"RESULTADO: FALLA ({fail} de {total} checks)")
    sys.exit(1)


if __name__ == "__main__":
    main()
