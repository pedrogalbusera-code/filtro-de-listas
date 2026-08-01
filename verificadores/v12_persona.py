#!/usr/bin/env python3
"""v12_persona.py — Verificador de F12 (persona fisica vs. juridica).

Ejecuta n8n de verdad (importar + --id), mismo estandar que v05/v06/v07/v11.
Tres bloques:

  1. Config DEFAULT (segmentacion APAGADA) sobre el CSV canonico: los dos
     golden de F09 byte a byte. Es el check que manda — sumar un filtro nuevo
     no puede mover el pipeline base.
  2. Config {etiquetar:true, descartar:"juridica"} POR EL NODO REAL sobre dos
     archivos: leads_segmento_1.csv (cubre los 7 prefijos y los tres bordes) y
     leads_adversario_1.csv (el archivo de la corrida adversaria). Checks de
     celda de tipo_persona fila por fila, mas el descarte y su motivo.
  3. Proyeccion: {etiquetar:true, descartar:null} sobre el canonico. Sacando la
     columna tipo_persona, la auditoria vuelve a ser el golden celda por celda
     y el comercial no se movio ni un byte: etiquetar no toca el scoring.

Los esperados de tipo_persona son LITERALES transcriptos a mano desde el spec
de fases/F12-persona-fisica-juridica.md. Prohibido calcularlos con la logica
del nodo o con cualquier funcion del pipeline: comparar la salida contra la
misma logica que la produjo es el hallazgo de F05 (un oraculo contra si mismo).
"""
import csv
import hashlib
import json
import os
import subprocess
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(BASE, "herramientas", "gen_workflow.py")
DATA = os.path.join(BASE, "data")
SAL = os.path.join(BASE, "salidas")
GOLDEN_COM = os.path.join(SAL, "golden_2026-07-28.csv")
GOLDEN_AUD = os.path.join(SAL, "golden_2026-07-28_auditoria.csv")
CANONICO = os.path.join(DATA, "leads_prueba_SINTETICO_1.csv")
WF_ID = "f12persona__tmp"
FECHA_CORTE = "2026-07-28"

MOTIVO_JURIDICA = "persona jurídica (segmento no buscado)"

# ---------------------------------------------------------------------------
# EL SPEC, ESCRITO A MANO. Cada valor sale de leer el CUIL del archivo de
# entrada y aplicar la tabla de la fase, no de correr el nodo.
#
#   prefijo 20 / 23 / 24 / 27  -> fisica
#   prefijo 30 / 33 / 34       -> juridica
#   sin CUIL de 11 digitos     -> desconocida
#   prefijo fuera del set      -> desconocida
#   DV invalido                -> NO importa: se clasifica por prefijo
# ---------------------------------------------------------------------------

# data/leads_segmento_1.csv — armado para cubrir los 7 prefijos y los bordes
# que el archivo adversario no tiene (33, 34 y un 30 con DV roto).
SEGMENTO = [
    # (prefijo de nombre, cuil del archivo, tipo_persona esperado, por que)
    ("S01", "20-31445901-7", "fisica",      "prefijo 20"),
    ("S02", "23-37451201-3", "fisica",      "prefijo 23"),
    ("S03", "24-34501278-4", "fisica",      "prefijo 24"),
    ("S04", "27-35110489-4", "fisica",      "prefijo 27"),
    ("S05", "30-70999888-5", "juridica",    "prefijo 30"),
    ("S06", "33-69876543-2", "juridica",    "prefijo 33"),
    ("S07", "34-60123456-6", "juridica",    "prefijo 34"),
    ("S08", "",              "desconocida", "sin CUIL"),
    ("S09", "99-44122335-4", "desconocida", "prefijo 99, fuera del set"),
    ("S10", "30-71234570-9", "juridica",    "prefijo 30 con DV invalido: manda el prefijo"),
    ("S11", "20-4412233",    "desconocida", "CUIL de 9 digitos: no hay prefijo utilizable"),
]

# Con descartar="juridica", la prioridad exacta de cada fila del archivo de
# segmento. Todas las filas son limpias a proposito (telefono fijo valido,
# localidad en zona, fecha fresca, origen referido): el UNICO descarte posible
# es el del segmento. Las de CUIL no utilizable pierden 10 puntos y caen a
# media, pero NO se descartan.
SEGMENTO_PRIORIDAD = {
    "S01": "alta", "S02": "alta", "S03": "alta", "S04": "alta",
    "S05": "descartado", "S06": "descartado", "S07": "descartado",
    "S08": "media", "S09": "media",
    "S10": "descartado",
    "S11": "media",
}

# data/leads_adversario_1.csv — leido a mano, fila por fila. Los tres unicos
# que no son fisica son T23 (CUIL vacio), T24 (9 digitos), T25 (prefijo 99) y
# T30 (prefijo 30, la unica empresa del archivo).
ADVERSARIO = [
    ("T01", "20-31445902-5", "fisica"),
    ("T02", "27-32118745-0", "fisica"),
    ("T04", "24-34501277-6", "fisica"),
    ("T07", "23-37451200-5", "fisica"),
    ("T23", "",              "desconocida"),
    ("T24", "20-4412233",    "desconocida"),
    ("T25", "99-44122335-4", "desconocida"),
    ("T26", "20314459025",   "fisica"),
    ("T27", "27.32118745.0", "fisica"),
    ("T28", "24 34501277 6", "fisica"),
    ("T30", "30-71234567-1", "juridica"),
    ("T48", "23-31000009-4", "fisica"),
]
# Conteo de las 48 filas del archivo, contadas a mano sobre el CSV.
ADVERSARIO_CONTEO = {"fisica": 44, "juridica": 1, "desconocida": 3}

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


def escribir_config(cfg, nombre):
    path = os.path.join(tempfile.gettempdir(), nombre)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return path


def correr_caso(archivo_in, cfg, etiqueta):
    """Genera el workflow de F12 con esa config, lo importa y lo ejecuta."""
    stem = os.path.splitext(os.path.basename(archivo_in))[0]
    com = os.path.join(SAL, f"_v12_{etiqueta}_{stem}_com.csv")
    aud = os.path.join(SAL, f"_v12_{etiqueta}_{stem}_aud.csv")
    ficha = os.path.join(SAL, f"ficha_entrada_{stem}.md")
    for f in (com, aud):
        if os.path.exists(f):
            os.remove(f)

    cfg_path = escribir_config(cfg, f"seg_v12_{etiqueta}.json")
    tmp_wf = os.path.join(tempfile.gettempdir(), "wf_v12_tmp.json")
    subprocess.run(
        [sys.executable, GEN, tmp_wf, archivo_in, com,
         "--fase", "12", "--fecha-corte", FECHA_CORTE,
         "--csv-out-audit", aud, "--ficha-out", ficha,
         "--segmentacion", cfg_path],
        check=True, capture_output=True,
    )

    with open(tmp_wf, "r", encoding="utf-8") as f:
        wf = json.load(f)
    wf["id"] = WF_ID
    wf["name"] = "tmp-v12"
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
    return {"com": com, "aud": aud, "exito": exito, "wf_json": wf}


def fila_por_tag(rows, tag):
    return next((x for x in rows if x.get("nombre", "").startswith(tag + " ")), None)


def bloque_tipo(rows, tabla, archivo):
    """Checks de celda de tipo_persona contra la tabla escrita a mano."""
    for fila in tabla:
        tag, cuil_esperado, tipo_esperado = fila[0], fila[1], fila[2]
        r = fila_por_tag(rows, tag)
        if r is None:
            check(f"({archivo}) {tag}: la fila esta en la salida", False,
                  "no aparece ninguna fila cuyo nombre empiece con " + tag)
            continue
        # El CUIL de la tabla es el del archivo de entrada: si no coincide, la
        # tabla quedo desactualizada y los esperados de abajo no valen nada.
        check(f"({archivo}) {tag}: el CUIL del archivo es el de la tabla",
              r.get("cuil") == cuil_esperado,
              f"la tabla dice [{cuil_esperado}] y el archivo trae [{r.get('cuil')}]")
        check(f"({archivo}) {tag} tipo_persona == {tipo_esperado}",
              r.get("tipo_persona") == tipo_esperado,
              f"fila {r['nombre']!r}, columna tipo_persona: "
              f"esperado [{tipo_esperado}] obtenido [{r.get('tipo_persona')!r}]")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("=" * 70)
    print("v12_persona.py — Verificador F12 (persona física vs. jurídica)")
    print("=" * 70)

    # ==================================================================
    print("\n--- La config manda: valores invalidos frenan AL GENERAR ---")
    tmp_wf = os.path.join(tempfile.gettempdir(), "wf_v12_cfg.json")
    for valor, debe_pasar in [("fisica", True), ("juridica", True), (None, True),
                              ("desconocida", False), ("empresa", False)]:
        cfg_path = escribir_config({"etiquetar": True, "descartar": valor},
                                   "seg_v12_cfgcheck.json")
        r = subprocess.run(
            [sys.executable, GEN, tmp_wf, CANONICO, os.path.join(SAL, "_v12_x.csv"),
             "--fase", "12", "--segmentacion", cfg_path],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if debe_pasar:
            check(f"descartar={valor!r} es una config valida", r.returncode == 0,
                  (r.stderr or "")[-160:])
        else:
            check(f"descartar={valor!r} se rechaza al generar (no llega a n8n)",
                  r.returncode != 0, "el generador la acepto")
    # El mensaje del caso peligroso tiene que explicar POR QUE, no solo fallar.
    cfg_path = escribir_config({"etiquetar": True, "descartar": "desconocida"},
                               "seg_v12_cfgcheck.json")
    r = subprocess.run(
        [sys.executable, GEN, tmp_wf, CANONICO, os.path.join(SAL, "_v12_x.csv"),
         "--fase", "12", "--segmentacion", cfg_path],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    check("el rechazo de 'desconocida' explica el motivo",
          "NUNCA se descarta" in (r.stderr or "") + (r.stdout or ""),
          repr((r.stderr or "")[-200:]))
    if os.path.exists(tmp_wf):
        os.remove(tmp_wf)

    # ==================================================================
    print("\n--- Bloque 1: config DEFAULT (apagada) — el pipeline no se mueve ---")
    with open(os.path.join(BASE, "config", "segmentacion.json"), encoding="utf-8") as f:
        default = json.load(f)
    check("el default del repo esta APAGADO (etiquetar=false, descartar=null)",
          default.get("etiquetar") is False and default.get("descartar") is None,
          f"config/segmentacion.json dice etiquetar={default.get('etiquetar')!r} "
          f"descartar={default.get('descartar')!r}")

    caso = correr_caso(CANONICO, {"etiquetar": False, "descartar": None}, "default")
    check("(default) la corrida termina bien", caso["exito"])
    check("(default) comercial byte a byte idéntico al golden de F09",
          os.path.exists(caso["com"]) and file_hash(caso["com"]) == file_hash(GOLDEN_COM),
          "el golden se movió: agregar F12 le cambió el comportamiento al pipeline base")
    check("(default) auditoría byte a byte idéntica al golden de F09",
          os.path.exists(caso["aud"]) and file_hash(caso["aud"]) == file_hash(GOLDEN_AUD),
          "el golden se movió: agregar F12 le cambió el comportamiento al pipeline base")
    rows_def, cols_def = leer_csv(caso["aud"])
    check("(default) la columna tipo_persona NO existe (la config está apagada)",
          "tipo_persona" not in cols_def, f"columnas: {cols_def[-4:]}")
    check("(default) ninguna fila menciona el segmento en el motivo",
          not any(MOTIVO_JURIDICA in r["motivo"] for r in rows_def))

    # ==================================================================
    print("\n--- Bloque 2a: segmento_1 — los 7 prefijos y los tres bordes ---")
    cfg_seg = {"etiquetar": True, "descartar": "juridica"}
    caso = correr_caso(os.path.join(DATA, "leads_segmento_1.csv"), cfg_seg, "juri")
    check("(segmento) la corrida termina bien", caso["exito"])
    rows, cols = leer_csv(caso["aud"]) if os.path.exists(caso["aud"]) else ([], [])
    check("(segmento) 11 filas de salida (nada se borra, ni las descartadas)",
          len(rows) == 11, f"hay {len(rows)}")
    check("(segmento) la columna tipo_persona aparece con etiquetar=true",
          "tipo_persona" in cols, f"columnas: {cols[-4:]}")

    bloque_tipo(rows, SEGMENTO, "segmento")

    for tag, _, tipo_esperado, _ in SEGMENTO:
        r = fila_por_tag(rows, tag)
        if r is None:
            continue
        esperada = SEGMENTO_PRIORIDAD[tag]
        check(f"(segmento) {tag} prioridad == {esperada}",
              r.get("prioridad") == esperada,
              f"fila {r['nombre']!r}: esperado [{esperada}] obtenido [{r.get('prioridad')}]")
        tiene_motivo = MOTIVO_JURIDICA in r.get("motivo", "")
        if tipo_esperado == "juridica":
            check(f"(segmento) {tag} (jurídica) lleva el motivo del segmento",
                  tiene_motivo, f"motivo: {r.get('motivo')!r}")
        else:
            check(f"(segmento) {tag} ({tipo_esperado}) NO lleva el motivo del segmento",
                  not tiene_motivo, f"motivo: {r.get('motivo')!r}")

    desconocidas = [r for r in rows if r.get("tipo_persona") == "desconocida"]
    check("(segmento) hay 3 desconocidas y NINGUNA quedó descartada",
          len(desconocidas) == 3
          and all(r["prioridad"] != "descartado" for r in desconocidas),
          str({r["nombre"]: r["prioridad"] for r in desconocidas}))
    juridicas = [r for r in rows if r.get("tipo_persona") == "juridica"]
    check("(segmento) las 4 jurídicas quedaron descartadas",
          len(juridicas) == 4 and all(r["prioridad"] == "descartado" for r in juridicas),
          str({r["nombre"]: r["prioridad"] for r in juridicas}))
    check("(segmento) S10 (DV inválido) es jurídica Y su CUIL es inválido: "
          "el prefijo clasifica, el DV no",
          (fila_por_tag(rows, "S10") or {}).get("tipo_persona") == "juridica"
          and (fila_por_tag(rows, "S10") or {}).get("cuil_valido") == "FALSE",
          str({k: (fila_por_tag(rows, "S10") or {}).get(k)
               for k in ["tipo_persona", "cuil_valido"]}))
    check("(segmento) el descarte no borró filas: las 4 jurídicas siguen en el CSV "
          "con nombre, teléfono y motivo",
          all(r["nombre"].strip() and r["telefono"].strip() and r["motivo"].strip()
              for r in juridicas))

    # ==================================================================
    print("\n--- Bloque 2b: adversario_1 — el archivo de la corrida adversaria ---")
    caso = correr_caso(os.path.join(DATA, "leads_adversario_1.csv"), cfg_seg, "juri")
    check("(adv1) la corrida termina bien", caso["exito"])
    rows, cols = leer_csv(caso["aud"]) if os.path.exists(caso["aud"]) else ([], [])
    check("(adv1) 48 filas de salida", len(rows) == 48, f"hay {len(rows)}")

    bloque_tipo(rows, ADVERSARIO, "adv1")

    conteo = {"fisica": 0, "juridica": 0, "desconocida": 0}
    raros = []
    for r in rows:
        t = r.get("tipo_persona")
        if t in conteo:
            conteo[t] += 1
        else:
            raros.append((r.get("nombre"), t))
    check("(adv1) tipo_persona siempre en {fisica, juridica, desconocida}",
          not raros, str(raros[:3]))
    for tipo, esp in ADVERSARIO_CONTEO.items():
        check(f"(adv1) hay {esp} de tipo {tipo} (contadas a mano sobre el CSV)",
              conteo[tipo] == esp, f"hay {conteo[tipo]}")

    t30 = fila_por_tag(rows, "T30")
    check("(adv1) T30 (la única empresa del archivo) queda descartada con motivo",
          t30 is not None and t30["prioridad"] == "descartado"
          and MOTIVO_JURIDICA in t30["motivo"],
          str({k: t30.get(k) for k in ["prioridad", "motivo"]} if t30 else {}))
    desc_seg = [r["nombre"] for r in rows if MOTIVO_JURIDICA in r.get("motivo", "")]
    check("(adv1) el motivo del segmento aparece en UNA sola fila, y es T30",
          len(desc_seg) == 1 and desc_seg[0].startswith("T30 "), str(desc_seg))
    check("(adv1) ninguna desconocida lleva el motivo del segmento",
          not any(MOTIVO_JURIDICA in r.get("motivo", "")
                  for r in rows if r.get("tipo_persona") == "desconocida"))

    # ==================================================================
    print("\n--- Bloque 3: etiquetar sin descartar — el scoring no se entera ---")
    caso = correr_caso(CANONICO, {"etiquetar": True, "descartar": None}, "etiq")
    check("(etiq) la corrida termina bien", caso["exito"])
    check("(etiq) el comercial sigue byte a byte idéntico al golden",
          os.path.exists(caso["com"]) and file_hash(caso["com"]) == file_hash(GOLDEN_COM),
          "etiquetar movió el CSV comercial")

    rows_e, cols_e = leer_csv(caso["aud"]) if os.path.exists(caso["aud"]) else ([], [])
    rows_g, cols_g = leer_csv(GOLDEN_AUD)
    check("(etiq) la columna tipo_persona está y es la única de más",
          "tipo_persona" in cols_e and [c for c in cols_e if c != "tipo_persona"] == cols_g,
          f"salida: {cols_e[-3:]} / golden: {cols_g[-3:]}")
    valores = {r.get("tipo_persona") for r in rows_e}
    check("(etiq) las 200 filas tienen tipo_persona con un valor del dominio",
          len(rows_e) == 200 and valores and valores <= {"fisica", "juridica", "desconocida"},
          f"valores: {sorted(v for v in valores if v is not None)}")

    difs = []
    for i, (re_, rg) in enumerate(zip(rows_e, rows_g), 1):
        for c in cols_g:
            if re_.get(c) != rg.get(c):
                difs.append(f"fila {i} col {c}: golden [{rg.get(c)}] salida [{re_.get(c)}]")
    check("(etiq) sacando tipo_persona, las 26 columnas del golden coinciden "
          "celda por celda y en el mismo orden de filas",
          len(rows_e) == len(rows_g) and not difs,
          f"{len(difs)} diferencias; primera: {difs[0] if difs else ''}")
    check("(etiq) ninguna fila quedó descartada por segmento (descartar=null)",
          not any(MOTIVO_JURIDICA in r["motivo"] for r in rows_e))

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
