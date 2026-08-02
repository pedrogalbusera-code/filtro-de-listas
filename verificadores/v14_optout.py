#!/usr/bin/env python3
"""v14_optout.py — Verificador de F14 (lista negra / opt-out del cliente).

Ejecuta n8n de verdad (importar + --id), mismo estandar que v11/v12/v13.
Tres bloques:

  1. Default SIN lista de baja: los dos golden de F09 byte a byte, sin columna
     ni motivo de opt-out, y el reporte identico al de la fase anterior (A/B
     contra la fase 12). El gate de F14 es la PRESENCIA de la lista: sin lista
     el pipeline no se puede haber movido.
  2. Con lista_baja_1.csv sobre leads_optout_1.csv POR EL NODO REAL: celda por
     celda O01-O07, las dos trampas de vacio, el motivo una sola vez, y el
     conteo por via de cruce.
  3. El reporte: la linea de opt-out con su conteo, en su propia categoria, y
     con la aclaracion de que NO se consulta el registro oficial "No Llame".

Los esperados son LITERALES escritos a mano desde las tablas de
fases/F14-lista-negra-optout.md y desde el canonico documentado en F01
(+54 / +549 + 10 digitos nacionales). Prohibido calcularlos con la logica del
nodo: comparar la salida contra la misma logica que la produjo es el hallazgo
de F05.
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
LISTA_BAJA = os.path.join(DATA, "lista_baja_1.csv")
PRINCIPAL = os.path.join(DATA, "leads_optout_1.csv")
WF_ID = "f14optout___tmp"
FECHA_CORTE = "2026-07-28"

# Escrito a mano desde config/opt_out.json (y verificado contra el archivo).
MOTIVO = "en lista de no llamar del cliente (opt-out)"
MOT_SIN_TEL = "sin teléfono"

# ---------------------------------------------------------------------------
# EL SPEC, ESCRITO A MANO.
#
# Los canonicos salen de la regla documentada en F01 (+54 / +549 + los 10
# digitos nacionales), no de correr el normalizador:
#
#   O01  '11 4161-7956'      -> +541141617956   | L1 '011 4161-7956'      -> +541141617956   MATCH
#   O02  '011 15 6161-7956'  -> +5491161617956  | L2 '+54 9 11 6161 7956' -> +5491161617956  MATCH
#   O07  '11 4242-4242'      -> +541142424242   | L6 '011 4242-4242'      -> +541142424242   MATCH
#
# Las tres parejas estan escritas en formatos DISTINTOS a proposito: si el
# cruce comparara el string crudo, ninguna matchearia y los tres se llamarian
# igual. Ese es el falso negativo caro que paga esta fase.
# ---------------------------------------------------------------------------
CASOS = [
    # (tag, opt_out, via esperada, prioridad, que prueba)
    ("O01", True,  "telefono", "descartado",
     "fijo escrito sin el 0; en la baja viene con 0 -> mismo canonico"),
    ("O02", True,  "telefono", "descartado",
     "celular viejo con 15; en la baja viene como +54 9 -> mismo canonico"),
    ("O03", True,  "cuil",     "descartado",
     "el telefono NO esta en la baja, cruza por CUIL (prueba el OR)"),
    ("O04", False, "",         "alta",
     "CONTROL: ni el telefono ni el CUIL estan en la baja"),
    ("O05", False, "",         "descartado",
     "TRAMPA: telefono 's/d' igual que en la baja, pero canonico vacio NUNCA matchea vacio"),
    ("O06", False, "",         "media",
     "TRAMPA: CUIL de 9 digitos igual que en la baja, pero <11 digitos no cruza"),
    ("O07", True,  "ambos",    "descartado",
     "esta por telefono Y por CUIL: el motivo tiene que aparecer UNA sola vez"),
]

# Contados a mano sobre la tabla de arriba.
ESPERADO_VIA = {"telefono": 2, "cuil": 1, "ambos": 1}
ESPERADO_OPTOUT = 4

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


def fila_reporte(reporte, etiqueta):
    m = re.search(r"\|\s*" + re.escape(etiqueta) + r"\s*\|\s*(\d+)\s*\|", reporte)
    return int(m.group(1)) if m else None


def correr_caso(archivo_in, etiqueta, fase="14", lista_baja=""):
    """Genera el workflow, lo importa y lo ejecuta en n8n de verdad."""
    stem = os.path.splitext(os.path.basename(archivo_in))[0]
    com = os.path.join(SAL, f"_v14_{etiqueta}_{stem}_com.csv")
    aud = os.path.join(SAL, f"_v14_{etiqueta}_{stem}_aud.csv")
    rep = os.path.join(SAL, f"_v14_{etiqueta}_{stem}_rep.md")
    ficha = os.path.join(SAL, f"ficha_entrada_{stem}.md")
    for f in (com, aud, rep):
        if os.path.exists(f):
            os.remove(f)

    tmp_wf = os.path.join(tempfile.gettempdir(), "wf_v14_tmp.json")
    cmd = [sys.executable, GEN, tmp_wf, archivo_in, com,
           "--fase", fase, "--fecha-corte", FECHA_CORTE,
           "--csv-out-audit", aud, "--reporte-out", rep, "--ficha-out", ficha]
    if lista_baja:
        cmd += ["--lista-baja", lista_baja]
    subprocess.run(cmd, check=True, capture_output=True)

    with open(tmp_wf, "r", encoding="utf-8") as f:
        wf = json.load(f)
    wf["id"] = WF_ID
    wf["name"] = "tmp-v14"
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
    return {"com": com, "aud": aud, "rep": rep, "exito": exito,
            "salida": (r.stdout or "") + (r.stderr or "")}


def fila(rows, tag):
    return next((x for x in rows if x.get("nombre", "").startswith(tag + " ")), None)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("=" * 70)
    print("v14_optout.py — Verificador F14 (lista negra / opt-out del cliente)")
    print("=" * 70)

    # ==================================================================
    print("\n--- La config: el motivo tiene que seguir siendo contable ---")
    with open(os.path.join(CONFIG, "opt_out.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    check("config/opt_out.json trae el motivo esperado", cfg.get("motivo") == MOTIVO,
          f"vino {cfg.get('motivo')!r}")
    check("el default del repo NO trae lista de baja (el gate es su presencia)",
          cfg.get("lista") is None, f"vino {cfg.get('lista')!r}")

    tmp_wf = os.path.join(tempfile.gettempdir(), "wf_v14_cfg.json")

    def generar_con(cfg_mod):
        p = os.path.join(tempfile.gettempdir(), "opt_out_v14_cfgcheck.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(cfg_mod, fh, ensure_ascii=False)
        return subprocess.run(
            [sys.executable, GEN, tmp_wf, CANONICO, os.path.join(SAL, "_v14_x.csv"),
             "--fase", "14", "--opt-out", p],
            capture_output=True, text=True, encoding="utf-8", errors="replace")

    r = generar_con({"motivo": "no lo llames", "lista": None})
    check("un motivo sin la marca 'opt-out' se rechaza al generar "
          "(el reporte cuenta por esa marca y dejaria de contar en silencio)",
          r.returncode != 0, "el generador lo acepto")
    r = generar_con({"motivo": "", "lista": None})
    check("un motivo vacio se rechaza al generar", r.returncode != 0)
    r = generar_con({"motivo": "pidio la baja (opt-out) 2026", "lista": None})
    check("un motivo propio del cliente que conserva la marca es valido",
          r.returncode == 0, (r.stderr or "")[-160:])
    if os.path.exists(tmp_wf):
        os.remove(tmp_wf)

    # ==================================================================
    print("\n--- Bloque 1: SIN lista de baja — el pipeline no se puede haber movido ---")
    caso = correr_caso(CANONICO, "sinbaja")
    check("(sin baja) la corrida termina bien", caso["exito"])
    check("(sin baja) comercial byte a byte idéntico al golden de F09",
          os.path.exists(caso["com"]) and file_hash(caso["com"]) == file_hash(GOLDEN_COM),
          "el golden se movió con el filtro apagado: el bug es de F14")
    check("(sin baja) auditoría byte a byte idéntica al golden de F09",
          os.path.exists(caso["aud"]) and file_hash(caso["aud"]) == file_hash(GOLDEN_AUD),
          "el golden se movió con el filtro apagado: el bug es de F14")
    rows, cols = leer_csv(caso["aud"])
    check("(sin baja) la columna optout_via NO existe", "optout_via" not in cols,
          f"columnas del final: {cols[-3:]}")
    check("(sin baja) ninguna de las 200 filas menciona opt-out en el motivo",
          len(rows) == 200 and not any("opt-out" in r["motivo"] for r in rows))

    rep_sin = leer_txt(caso["rep"])
    check("(sin baja) el reporte NO trae la sección de opt-out (cuenta 0)",
          "opt-out" not in rep_sin and "No Llame" not in rep_sin)

    # A/B contra la fase anterior (12): si F14 hubiera movido el reporte del
    # golden, los dos textos dividirian.
    caso12 = correr_caso(CANONICO, "f12", fase="12")
    check("(sin baja) la corrida de la fase 12 termina bien", caso12["exito"])
    check("(sin baja) el reporte es idéntico al de la fase 12 (F14 no lo movió)",
          rep_sin != "" and rep_sin == leer_txt(caso12["rep"]))

    # ==================================================================
    print("\n--- Bloque 2: con la lista de baja, por el NODO REAL ---")
    caso = correr_caso(PRINCIPAL, "baja", lista_baja=LISTA_BAJA)
    check("(baja) la corrida termina bien", caso["exito"])
    rows, cols = leer_csv(caso["aud"]) if os.path.exists(caso["aud"]) else ([], [])
    check("(baja) 7 filas de salida: opt-out MARCA, no borra", len(rows) == 7,
          f"hay {len(rows)}")
    check("(baja) la columna optout_via aparece cuando hay lista", "optout_via" in cols)

    for tag, es_optout, via, prioridad, que_prueba in CASOS:
        r = fila(rows, tag)
        if r is None:
            check(f"(baja) {tag}: la fila está en la salida", False, "no aparece")
            continue
        tiene = MOTIVO in r["motivo"]
        if es_optout:
            check(f"(baja) {tag} → opt-out ({que_prueba})", tiene,
                  f"motivo: {r['motivo']!r}")
            check(f"(baja) {tag} → optout_via == {via}", r.get("optout_via") == via,
                  f"esperado [{via}] obtenido [{r.get('optout_via')!r}]")
            check(f"(baja) {tag} → el motivo aparece UNA sola vez",
                  r["motivo"].count(MOTIVO) == 1,
                  f"aparece {r['motivo'].count(MOTIVO)} veces: {r['motivo']!r}")
        else:
            check(f"(baja) {tag} → NO opt-out ({que_prueba})", not tiene,
                  f"motivo: {r['motivo']!r}")
            check(f"(baja) {tag} → sin optout_via", (r.get("optout_via") or "") == "",
                  f"obtenido [{r.get('optout_via')!r}]")
        check(f"(baja) {tag} → prioridad {prioridad}", r["prioridad"] == prioridad,
              f"esperado [{prioridad}] obtenido [{r['prioridad']}]")

    # O05 se verifica por DOS cosas, no por una: quedo descartado Y su motivo
    # es el de sin telefono, no el de opt-out. Un check que solo mirara
    # "descartado" pasaria con el bug de vacio-matchea-vacio puesto.
    o05 = fila(rows, "O05")
    check("(baja) O05 quedó descartado por SIN TELÉFONO, no por opt-out",
          o05 is not None and MOT_SIN_TEL in o05["motivo"] and MOTIVO not in o05["motivo"],
          f"motivo: {o05['motivo']!r}" if o05 else "no está")
    check("(baja) O05 tiene el teléfono canónico vacío (es la trampa que se prueba)",
          o05 is not None and o05["telefono_norm"] == "",
          f"telefono_norm: {o05['telefono_norm']!r}" if o05 else "")
    o06 = fila(rows, "O06")
    check("(baja) O06 tiene el CUIL de 9 dígitos y NO cruzó",
          o06 is not None and o06["cuil_norm"] == "204412233"
          and MOTIVO not in o06["motivo"],
          f"cuil_norm: {o06['cuil_norm']!r}" if o06 else "")

    vias = {}
    for r in rows:
        v = (r.get("optout_via") or "").strip()
        if v:
            vias[v] = vias.get(v, 0) + 1
    for via, esp in ESPERADO_VIA.items():
        check(f"(baja) {esp} fila(s) cruzaron por {via}", vias.get(via, 0) == esp,
              f"hay {vias.get(via, 0)}")
    n_opt = sum(1 for r in rows if MOTIVO in r["motivo"])
    check(f"(baja) {ESPERADO_OPTOUT} descartes por opt-out en total",
          n_opt == ESPERADO_OPTOUT, f"hay {n_opt}")
    check("(baja) las filas de opt-out siguen enteras (nombre, teléfono, motivo)",
          all(r["nombre"].strip() and r["motivo"].strip()
              for r in rows if MOTIVO in r["motivo"]))
    check("(baja) el puntaje sigue siendo auditable: la suma del motivo da el puntaje",
          all(sum(int(n) for n in re.findall(r"([+-]\d+)", r["motivo"])) == int(r["puntaje"])
              for r in rows))
    # L7 de la lista de baja es un telefono que no esta en la principal: se
    # ignora sin romper. Que la corrida haya terminado bien ya lo prueba.
    check("(baja) un teléfono de la baja que no está en la principal se ignora sin error",
          caso["exito"] and len(rows) == 7)

    # ==================================================================
    print("\n--- Bloque 3: el reporte ---")
    rep = leer_txt(caso["rep"])
    check("(reporte) aparece la sección de opt-out",
          "Por pedido de baja del titular (opt-out)" in rep)
    check(f"(reporte) cuenta exactamente {ESPERADO_OPTOUT}",
          fila_reporte(rep, "En la lista de no llamar que aporta el cliente") == ESPERADO_OPTOUT,
          f"dice {fila_reporte(rep, 'En la lista de no llamar que aporta el cliente')}")
    check("(reporte) el opt-out va en su propia categoría, después de zona y segmento",
          rep.index("Por pedido de baja del titular") > rep.index("Por zona de cobertura"))
    check("(reporte) NO se mezcla con la calidad de dato",
          rep.index("Por calidad de dato") < rep.index("Por pedido de baja del titular"))
    check("(reporte) aclara que se cruza SOLO la lista del cliente y que NO se "
          "consulta el registro oficial 'No Llame'",
          "No Llame" in rep and "26.951" in rep
          and ("no** se consulta" in rep.lower() or "**no** se consulta" in rep.lower()),
          repr([l for l in rep.split("\n") if "No Llame" in l][:1]))
    check("(reporte) los descartados del reporte son los 5 del CSV (4 opt-out + 1 sin teléfono)",
          fila_reporte(rep, "Contactos descartados") == 5
          and sum(1 for r in rows if r["prioridad"] == "descartado") == 5,
          f"reporte dice {fila_reporte(rep, 'Contactos descartados')}")

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
