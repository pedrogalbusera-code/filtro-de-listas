#!/usr/bin/env python3
"""v11_puerta.py — Verificador de F11 (puerta de entrada).

Ejecuta n8n de verdad (importar + --id) sobre los seis casos del criterio:

  1. canónico  -> byte a byte idéntico a los DOS golden de F09 (por hash)
  2. adversario 3 (;) -> 5 filas POBLADAS, 3 en zona, 2 fuera
  3. adversario 2 (basura + columnas renombradas) -> 7 filas, T55 completada
  4. adversario 4 (.xlsx) -> teléfono numérico invalido con motivo de Excel
  5. prosa (.txt) -> RECHAZO: exit de error, SIN archivo de salida, CON ficha
  6. adversario 1 -> T01-T10 (formatos de teléfono de CORRECCION-F01) por el
     nodo REAL de n8n, celda por celda contra la tabla del prompt

Los esperados están escritos a mano contra el contenido de los archivos de
data/, no calculados con la misma lógica del nodo. La forma de check falso
que esta fase prohíbe: "el archivo existe y tiene N filas" — ese check lo
pasaba el hallazgo 13. Acá todo parseo se verifica por contenido de celda.
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
WF_ID = "f11puerta___tmp"
FECHA_CORTE = "2026-07-28"

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
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def num_ficha(ficha, etiqueta):
    """Saca un número de la tabla de la ficha: | <etiqueta> | N |"""
    m = re.search(r"\|\s*" + re.escape(etiqueta) + r"\s*\|\s*(\d+)", ficha)
    return int(m.group(1)) if m else None


def correr_caso(archivo_in, mapeo=""):
    """Genera el workflow F11, lo importa y lo ejecuta. Devuelve el dict del
    caso: rutas de salida, exit de n8n, y el texto combinado de la corrida."""
    stem = os.path.splitext(os.path.basename(archivo_in))[0]
    com = os.path.join(SAL, f"_v11_{stem}_com.csv")
    aud = os.path.join(SAL, f"_v11_{stem}_aud.csv")
    ficha = os.path.join(SAL, f"ficha_entrada_{stem}.md")
    for f in (com, aud, ficha):
        if os.path.exists(f):
            os.remove(f)

    tmp_wf = os.path.join(tempfile.gettempdir(), "wf_v11_tmp.json")
    cmd = [sys.executable, GEN, tmp_wf, archivo_in, com,
           "--fase", "11", "--fecha-corte", FECHA_CORTE,
           "--csv-out-audit", aud, "--ficha-out", ficha]
    if mapeo:
        cmd += ["--mapeo", mapeo]
    subprocess.run(cmd, check=True, capture_output=True)

    with open(tmp_wf, "r", encoding="utf-8") as f:
        wf = json.load(f)
    wf["id"] = WF_ID
    wf["name"] = "tmp-v11"
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
    return {
        "com": com, "aud": aud, "ficha": ficha, "exito": exito,
        "salida": (r.stdout or "") + (r.stderr or ""), "wf_json": wf,
    }


def leer_ficha(path):
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("=" * 70)
    print("v11_puerta.py — Verificador F11 (puerta de entrada)")
    print("=" * 70)

    # ------------------------------------------------------------------
    print("\n--- Config versionada (el mapeo NO vive en el nodo) ---")
    sin_path = os.path.join(CONFIG, "sinonimos.json")
    map_path = os.path.join(CONFIG, "mapeo_adversario2.json")
    check("existe config/sinonimos.json", os.path.exists(sin_path))
    check("existe config/mapeo_adversario2.json", os.path.exists(map_path))
    with open(map_path, encoding="utf-8") as f:
        mapeo2 = json.load(f)
    esperado_mapeo = {
        "Nombre y Apellido": "nombre", "Documento": "cuil", "Celular": "telefono",
        "Zona": "localidad", "Origen del lead": "origen", "Fecha de alta": "fecha_carga",
    }
    check("el mapeo del adversario 2 tiene las 6 traducciones del criterio",
          {k: v for k, v in mapeo2.items() if not k.startswith("_")} == esperado_mapeo,
          f"tiene: {mapeo2}")

    # ==================================================================
    print("\n--- Caso 1: CSV canónico — F11 tiene que ser transparente ---")
    caso = correr_caso(os.path.join(DATA, "leads_prueba_SINTETICO_1.csv"))
    check("(canon) la corrida termina bien", caso["exito"])
    check("(canon) comercial byte a byte idéntico al golden",
          os.path.exists(caso["com"]) and file_hash(caso["com"]) == file_hash(GOLDEN_COM),
          "el golden se movió: F11 le cambió el comportamiento a una fase de abajo")
    check("(canon) auditoría byte a byte idéntica al golden",
          os.path.exists(caso["aud"]) and file_hash(caso["aud"]) == file_hash(GOLDEN_AUD))
    ficha = leer_ficha(caso["ficha"])
    check("(canon) la ficha de entrada se generó", ficha != "")
    # Oráculo independiente: contar filas del archivo de origen a mano.
    with open(os.path.join(DATA, "leads_prueba_SINTETICO_1.csv"), encoding="utf-8") as f:
        filas_reales = sum(1 for _ in f) - 1
    check("(canon) ficha: filas leídas == filas reales del archivo",
          num_ficha(ficha, "Filas de datos leidas") == filas_reales,
          f"ficha dice {num_ficha(ficha, 'Filas de datos leidas')}, el archivo tiene {filas_reales}")
    check("(canon) ficha: separador coma, encabezado línea 1, 0 salteadas",
          "| Separador detectado | coma |" in ficha
          and num_ficha(ficha, "Encabezado en la linea") == 1
          and num_ficha(ficha, "Lineas salteadas arriba del encabezado") == 0)
    check("(canon) ficha: estado ACEPTADO", "| Estado | **ACEPTADO** |" in ficha)

    # ==================================================================
    print("\n--- Caso 2: adversario 3 (;) — el que pagaba la fase ---")
    caso = correr_caso(os.path.join(DATA, "leads_adversario_3.csv"))
    check("(adv3) la corrida termina bien", caso["exito"])
    rows = leer_csv(caso["aud"]) if os.path.exists(caso["aud"]) else []
    check("(adv3) 5 filas de salida", len(rows) == 5, f"hay {len(rows)}")
    por_nombre = {r["nombre"]: r for r in rows}

    # Oráculo: el archivo real, leído con OTRO parser (csv de Python, sep=';').
    with open(os.path.join(DATA, "leads_adversario_3.csv"), encoding="utf-8-sig") as f:
        origen = {r["nombre"]: r for r in csv.DictReader(f, delimiter=";")}
    celdas_ok = 0
    celdas_mal = []
    for nombre, r_orig in origen.items():
        r_out = por_nombre.get(nombre)
        if r_out is None:
            celdas_mal.append(f"falta la fila {nombre}")
            continue
        for col in ["cuil", "telefono", "localidad", "origen", "fecha_carga"]:
            if r_out.get(col) == r_orig[col]:
                celdas_ok += 1
            else:
                celdas_mal.append(f"{nombre}.{col}: esperaba [{r_orig[col]}] dio [{r_out.get(col)}]")
    check("(adv3) las 25 celdas coinciden con el archivo leído por el oráculo",
          celdas_ok == 25 and not celdas_mal, "; ".join(celdas_mal[:3]))
    check("(adv3) teléfono y CUIL poblados en las 5 filas (el hallazgo 13 daba vacío)",
          all(r["telefono"].strip() and r["cuil"].strip() for r in rows))
    check("(adv3) telefono_norm poblado en las 5 (la normalización corrió de verdad)",
          all(r["telefono_norm"].startswith("+54") for r in rows),
          str([r["telefono_norm"] for r in rows]))
    en_zona = {r["nombre"]: r["en_zona"] for r in rows}
    check("(adv3) 3 dentro de zona: Castelar, Haedo, Morón",
          en_zona.get("T60 Nina Aguirre") == "TRUE"
          and en_zona.get("T61 Oscar Benitez") == "TRUE"
          and en_zona.get("T62 Pilar Cano") == "TRUE", str(en_zona))
    check("(adv3) 2 fuera de zona: Moreno, Merlo",
          en_zona.get("T63 Quimey Duran") == "FALSE"
          and en_zona.get("T64 Rocio Esteban") == "FALSE", str(en_zona))
    check("(adv3) ninguna fila con los 6 canónicos vacíos",
          all(any(r[c].strip() for c in ["nombre", "cuil", "telefono", "localidad", "origen", "fecha_carga"])
              for r in rows))
    ficha = leer_ficha(caso["ficha"])
    check("(adv3) ficha: separador punto y coma, 5 filas leídas",
          "| Separador detectado | punto y coma |" in ficha
          and num_ficha(ficha, "Filas de datos leidas") == 5)

    # ==================================================================
    print("\n--- Caso 3: adversario 2 — basura arriba, columnas renombradas ---")
    caso = correr_caso(os.path.join(DATA, "leads_adversario_2.csv"), mapeo=map_path)
    check("(adv2) la corrida termina bien (antes crasheaba)", caso["exito"])
    rows = leer_csv(caso["aud"]) if os.path.exists(caso["aud"]) else []
    check("(adv2) 7 filas de datos", len(rows) == 7, f"hay {len(rows)}")
    ficha = leer_ficha(caso["ficha"])
    check("(adv2) ficha: encabezado en la línea 4",
          num_ficha(ficha, "Encabezado en la linea") == 4)
    check("(adv2) ficha: 3 líneas salteadas y reportadas (no mudas)",
          num_ficha(ficha, "Lineas salteadas arriba del encabezado") == 3
          and "LISTADO DE CONTACTOS" in ficha)
    check("(adv2) ficha: 1 fila vacía del medio, ignorada y contada",
          num_ficha(ficha, "Filas vacias ignoradas") == 1)

    por_nombre = {r["nombre"]: r for r in rows}
    t55 = por_nombre.get("T55 Kira Domingo")
    check("(adv2) T55 (4 campos de 7) entra, no se pierde", t55 is not None)
    check("(adv2) T55: los campos que faltan quedan vacíos",
          t55 is not None and t55["origen"] == "" and t55["fecha_carga"] == ""
          and t55.get("extra_Observaciones", "") == "",
          str({k: t55.get(k) for k in ["origen", "fecha_carga", "extra_Observaciones"]} if t55 else {}))
    check("(adv2) T55: los campos que SÍ vinieron quedaron enteros",
          t55 is not None and t55["cuil"] == "20-36002911-6"
          and t55["telefono"] == "1168442804" and t55["localidad"] == "Ituzaingó")
    t50 = por_nombre.get("T50 Gonzalo Paz")
    check("(adv2) columnas renombradas mapeadas: Documento→cuil, Celular→telefono, Zona→localidad",
          t50 is not None and t50["cuil"] == "20-31445902-5"
          and t50["telefono"] == "11 6844-2800" and t50["localidad"] == "Castelar")
    check("(adv2) Observaciones conservada en auditoría con sus comas (quoting RFC4180)",
          t50 is not None and t50.get("extra_Observaciones") == "llamar después de las 18, dijo que sí",
          repr(t50.get("extra_Observaciones")) if t50 else "")
    t57 = por_nombre.get("T57 Mia Ferrari")
    check("(adv2) T57 (DV incorrecto a propósito): cuil_valido FALSE",
          t57 is not None and t57["cuil_valido"] == "FALSE")
    # La lista de orígenes es el insumo de la próxima decisión de negocio.
    origenes_esperados = ["Base propia", "Evento", "Meta", "Referido", "Web", "(vacio)"]
    check("(adv2) ficha: lista los 6 valores distintos de origen",
          all(f"| {o} |" in ficha for o in origenes_esperados),
          f"faltan: {[o for o in origenes_esperados if f'| {o} |' not in ficha]}")

    # El mapeo viene del config, no del template: generado SIN --mapeo, el JS
    # de la puerta tiene MAPEO = null; con --mapeo, tiene la traducción.
    js_con = next(n for n in caso["wf_json"]["nodes"] if n["id"] == "nP-puerta")["parameters"]["jsCode"]
    check("(adv2) el JS de la puerta contiene el mapeo embebido desde config/",
          '"Nombre y Apellido": "nombre"' in js_con)
    tmp_wf2 = os.path.join(tempfile.gettempdir(), "wf_v11_sinmapeo.json")
    subprocess.run([sys.executable, GEN, tmp_wf2,
                    os.path.join(DATA, "leads_adversario_2.csv"),
                    os.path.join(SAL, "_v11_x.csv"), "--fase", "11"],
                   check=True, capture_output=True)
    with open(tmp_wf2, encoding="utf-8") as f:
        js_sin = next(n for n in json.load(f)["nodes"] if n["id"] == "nP-puerta")["parameters"]["jsCode"]
    os.remove(tmp_wf2)
    check("(adv2) sin --mapeo el JS queda con MAPEO = null (no hay nada hardcodeado)",
          "const MAPEO = null;" in js_sin)

    # ==================================================================
    print("\n--- Caso 4: adversario 4 (.xlsx) — la planilla se lee ---")
    caso = correr_caso(os.path.join(DATA, "leads_adversario_4.xlsx"))
    check("(adv4) la corrida termina bien", caso["exito"])
    rows = leer_csv(caso["aud"]) if os.path.exists(caso["aud"]) else []
    check("(adv4) 4 filas de salida", len(rows) == 4, f"hay {len(rows)}")
    por_nombre = {r["nombre"]: r for r in rows}
    t71 = por_nombre.get("T71 Bruno Diaz")
    check("(adv4) T71 (teléfono como número): telefono_tipo invalido",
          t71 is not None and t71["telefono_tipo"] == "invalido",
          t71["telefono_tipo"] if t71 else "no está")
    check("(adv4) T71: telefono_norm vacío (no se inventa un número)",
          t71 is not None and t71["telefono_norm"] == "")
    check("(adv4) T71: motivo específico de artefacto de Excel en advertencia_entrada",
          t71 is not None and "artefacto de Excel" in t71.get("advertencia_entrada", ""),
          repr(t71.get("advertencia_entrada")) if t71 else "")
    check("(adv4) los teléfonos que vinieron como texto siguen bien (fijo/celular/ambiguo)",
          por_nombre.get("T70 Ana Suarez", {}).get("telefono_norm") == "+541141617956"
          and por_nombre.get("T72 Carla Ruiz", {}).get("telefono_norm") == "+5491139927555"
          and por_nombre.get("T73 Dario Vega", {}).get("telefono_tipo") == "ambiguo")
    check("(adv4) las tildes sobreviven a la planilla (Morón)",
          por_nombre.get("T73 Dario Vega", {}).get("localidad") == "Morón")
    ficha = leer_ficha(caso["ficha"])
    check("(adv4) ficha: formato planilla y advertencia del teléfono numérico",
          "planilla (xlsx)" in ficha and "artefacto de Excel" in ficha)

    # ==================================================================
    print("\n--- Caso 5: prosa (.txt) — el rechazo es un rechazo ---")
    caso = correr_caso(os.path.join(DATA, "leads_adversario_5_prosa.txt"))
    check("(prosa) la corrida termina con ERROR (exit code)", not caso["exito"])
    check("(prosa) NO se genera CSV comercial (un rechazo que escribe salida no es rechazo)",
          not os.path.exists(caso["com"]))
    check("(prosa) NO se genera CSV de auditoría", not os.path.exists(caso["aud"]))
    ficha = leer_ficha(caso["ficha"])
    check("(prosa) la ficha SÍ se genera, con estado RECHAZADO",
          "| Estado | **RECHAZADO** |" in ficha)
    # Los dos valores van escritos A MANO: 199 bytes es el tamaño real del
    # archivo y UTF-8 sin BOM su encoding.
    #
    # Por qué existen estos dos checks: al factorizar el lector en F14, la
    # ficha del RECHAZO perdió los dos campos (pasaron a 'n/d') porque el
    # lector cortaba antes de devolver. No lo atrapó ningún verificador —lo
    # atrapó un git diff humano—, que es exactamente el agujero de F05/F09.
    # La ficha del rechazo es la que más se lee: es lo único que queda cuando
    # no hay CSV de salida.
    #
    # Comparan contra el valor EXACTO a propósito: un check de "el campo
    # existe" habría pasado con el bug puesto, porque el 'n/d' estaba ahí.
    check("(prosa) la ficha del rechazo reporta el tamaño exacto (199 bytes)",
          "| Tamaño | 199 bytes |" in ficha,
          str([l for l in ficha.split("\n") if l.startswith("| Tamaño")]))
    check("(prosa) la ficha del rechazo reporta el encoding exacto (UTF-8 sin BOM)",
          "| Encoding | UTF-8 sin BOM |" in ficha,
          str([l for l in ficha.split("\n") if l.startswith("| Encoding")]))
    salida = caso["salida"]
    check("(prosa) el error dice QUÉ archivo",
          "leads_adversario_5_prosa.txt" in salida)
    check("(prosa) el error dice qué se DETECTÓ y qué se ESPERABA",
          "detectado:" in salida and "esperado:" in salida)
    check("(prosa) el mensaje es el de F11, no un crash genérico de parseo",
          "F11 RECHAZO" in salida)

    # ==================================================================
    print("\n--- Caso 6: adversario 1 — T01-T10 por el nodo REAL de n8n ---")
    # Los esperados están transcriptos A MANO de la tabla de
    # prompts/CORRECCION-F01.md. PROHIBIDO calcularlos con el oráculo de
    # v01_telefono.py o con cualquier función del pipeline: la gracia de este
    # caso es comparar el nodo real de n8n contra una verdad escrita por humano
    # (el hallazgo de F05 era un oráculo comparado contra sí mismo). Hasta esta
    # corrida, T01-T10 solo se habían verificado contra el oráculo Python: el
    # nodo real nunca había corrido sobre estos formatos.
    T01_T10 = [
        # (tag, telefono_tipo esperado, telefono_norm esperado)
        ("T01", "fijo",     "+541141617956"),
        ("T02", "celular",  "+5491141617956"),
        ("T03", "celular",  "+5491141617956"),
        ("T04", "celular",  "+5491141617956"),
        ("T05", "invalido", ""),
        ("T06", "invalido", ""),
        ("T07", "fijo",     "+541141617956"),
        ("T08", "invalido", ""),
        ("T09", "invalido", ""),
        ("T10", "ambiguo",  "+541141617956"),
    ]
    caso = correr_caso(os.path.join(DATA, "leads_adversario_1.csv"))
    check("(adv1) la corrida termina bien", caso["exito"])
    rows = leer_csv(caso["aud"]) if os.path.exists(caso["aud"]) else []
    faltan = [tag for tag, _, _ in T01_T10
              if not any(r.get("nombre", "").startswith(tag + " ") for r in rows)]
    check("(adv1) las 10 filas T01-T10 aparecen en el CSV de auditoría",
          not faltan, f"faltan: {faltan}")
    for tag, tipo_e, norm_e in T01_T10:
        r = next((x for x in rows if x.get("nombre", "").startswith(tag + " ")), None)
        if r is None:
            check(f"(adv1) {tag} telefono_tipo == {tipo_e}", False,
                  f"la fila {tag} no está en el CSV de auditoría")
            check(f"(adv1) {tag} telefono_norm == {norm_e!r}", False,
                  f"la fila {tag} no está en el CSV de auditoría")
            continue
        check(f"(adv1) {tag} telefono_tipo == {tipo_e}",
              r.get("telefono_tipo") == tipo_e,
              f"fila {r['nombre']!r}, columna telefono_tipo: "
              f"esperado [{tipo_e}] obtenido [{r.get('telefono_tipo')}]")
        check(f"(adv1) {tag} telefono_norm == {norm_e!r}",
              r.get("telefono_norm") == norm_e,
              f"fila {r['nombre']!r}, columna telefono_norm: "
              f"esperado [{norm_e}] obtenido [{r.get('telefono_norm')!r}]")

    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    total = ok + fail
    if fail == 0:
        print(f"RESULTADO: PASA ({total} checks)")
        sys.exit(0)
    else:
        print(f"RESULTADO: FALLA ({fail} de {total} checks)")
        sys.exit(1)


if __name__ == "__main__":
    main()
