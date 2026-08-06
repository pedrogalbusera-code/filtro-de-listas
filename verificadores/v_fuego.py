#!/usr/bin/env python3
"""v_fuego.py — La PRUEBA DE FUEGO: el pipeline entero sobre un archivo como lo
manda un cliente, resuelto SOLO con config (un mapeo de columnas + la
segmentacion del cliente), sin una linea de logica de nodo nueva.

Corre n8n de verdad (importar + --id), mismo estandar que v11/v12/v14. Cuatro
bloques, uno por criterio de fases/PRUEBA-DE-FUEGO.md:

  1. EQUIVALENCIA. El archivo sucio (';', basura arriba, columnas del cliente,
     Latin-1) y su gemelo limpio (',', UTF-8, header fila 1, canonicas) dan la
     salida BYTE A BYTE identica en comercial + auditoria + REPORTE. Misma baja
     y mismas configs en las dos corridas; lo unico que cambia es el principal.
     Si difiere un byte, la puerta (F11) dejo pasar algo de la superficie. La
     ficha SI difiere a proposito (se chequea en el bloque 4).

  2. CELDAS FIRMA G01-G15 por el nodo real, ESPERADO LITERAL escrito a mano
     desde la tabla de la fase. Cada fila prueba una capacidad ganada con
     sangre. Prohibido calcular el esperado con la logica del nodo (hallazgo
     de F05): los valores de abajo estan transcriptos a mano.

  3. COHERENCIA DEL REPORTE. Las CUATRO categorias de descarte con conteo >= 1
     (calidad de dato, zona, segmento, opt-out), las subtablas SUMAN al total
     de descartados, y el ahorro con minutos_por_llamada = 4.

  4. FICHA DEL SUCIO. Separador ';' (punto y coma), la fila real del header
     (despues de la basura), y el mapeo de CADA columna del cliente a la
     canonica. Mas la prueba de que el mapeo es LOAD-BEARING: sin el, la corrida
     se frena (es el "config nuevo" que prueba la fase, no un adorno).

La regla que manda la fase: si esto obligo a tocar un nodo Code, la prueba de
fuego encontro un filtro incompleto. No se toco ninguno: es data + config.
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

SUCIO = os.path.join(DATA, "leads_fuego_1.csv")
LIMPIO = os.path.join(DATA, "leads_fuego_1_limpio.csv")
BAJA = os.path.join(DATA, "lista_baja_fuego.xlsx")
MAPEO = os.path.join(CONFIG, "mapeo_fuego.json")
SEGMENTACION = os.path.join(CONFIG, "segmentacion_fuego.json")

WF_ID = "vfuego_____tmp"
FECHA_CORTE = "2026-07-28"

# Motivos, escritos a mano (verificados contra los config del repo).
MOT_SIN_TEL = "sin teléfono"
MOT_RELLENO = "teléfono de relleno"
MOT_DUP = "duplicado"
MOT_ZONA = "fuera de zona"
MOT_SEG = "segmento no buscado"
MOT_OPTOUT = "opt-out"
MARCA_DESCARTE = "→ descarte"   # ' → descarte'

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


def correr(principal, etiqueta, con_mapeo=True):
    """Genera el workflow de fuego, lo importa y lo ejecuta en n8n de verdad.
    Siempre con la misma baja (.xlsx) y la segmentacion del cliente (juridica).
    'con_mapeo' se apaga solo para probar que el mapeo es load-bearing."""
    stem = os.path.splitext(os.path.basename(principal))[0]
    com = os.path.join(SAL, f"_vfuego_{etiqueta}_com.csv")
    aud = os.path.join(SAL, f"_vfuego_{etiqueta}_aud.csv")
    rep = os.path.join(SAL, f"_vfuego_{etiqueta}_rep.md")
    ficha = os.path.join(SAL, f"ficha_entrada_{stem}.md")
    for f in (com, aud, rep):
        if os.path.exists(f):
            os.remove(f)

    tmp_wf = os.path.join(tempfile.gettempdir(), "wf_vfuego_tmp.json")
    cmd = [sys.executable, GEN, tmp_wf, principal, com,
           "--fase", "14", "--fecha-corte", FECHA_CORTE,
           "--csv-out-audit", aud, "--reporte-out", rep, "--ficha-out", ficha,
           "--segmentacion", SEGMENTACION, "--lista-baja", BAJA]
    if con_mapeo:
        cmd += ["--mapeo", MAPEO]
    subprocess.run(cmd, check=True, capture_output=True)

    with open(tmp_wf, "r", encoding="utf-8") as f:
        wf = json.load(f)
    wf["id"] = WF_ID
    wf["name"] = "tmp-vfuego"
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
    return {"com": com, "aud": aud, "rep": rep, "ficha": ficha, "exito": exito,
            "salida": (r.stdout or "") + (r.stderr or "")}


def por_nombre(rows, prefijo):
    """Fila cuyo nombre empieza con 'prefijo ' (con el espacio, para que 'G09 '
    no matchee 'G09b ...')."""
    return next((x for x in rows if x.get("nombre", "").startswith(prefijo + " ")), None)


def por_tel(rows, norm):
    return next((x for x in rows if x.get("telefono_norm") == norm), None)


# ---------------------------------------------------------------------------
# BLOQUE 2 — las celdas firma, ESPERADO LITERAL (fases/PRUEBA-DE-FUEGO.md).
# ---------------------------------------------------------------------------
def celdas_firma(rows):
    def find(pref):
        r = por_nombre(rows, pref)
        if r is None:
            check(f"G firma: {pref} está en la salida", False, "no aparece")
        return r

    # G01 — el control de alto valor que sobrevive todo.
    g01 = find("G01")
    if g01:
        check("G01 lead de alto valor → prioridad alta", g01["prioridad"] == "alta",
              g01["prioridad"])

    # G02 — celular '11 15 6161 7956' (15 sin el 0, CORRECCION-F01b).
    g02 = find("G02")
    if g02:
        check("G02 (15 sin 0) → telefono_tipo celular", g02["telefono_tipo"] == "celular",
              g02["telefono_tipo"])
        check("G02 → canónico +5491161617956", g02["telefono_norm"] == "+5491161617956",
              g02["telefono_norm"])
        check("G02 → llamable (no descartado)", g02["prioridad"] in ("alta", "media"),
              g02["prioridad"])

    # G03 — '+54 9 11 4161 7956' (el 9 separado, T02).
    g03 = find("G03")
    if g03:
        check("G03 (9 separado) → celular válido, no invalido",
              g03["telefono_tipo"] == "celular" and g03["telefono_norm"] == "+5491141617956",
              f"{g03['telefono_tipo']} / {g03['telefono_norm']}")

    # G04 — '15-4161-7956' (viejo sin área, T05): invalido, SIN número inventado.
    g04 = find("G04")
    if g04:
        check("G04 (15 sin área) → invalido, telefono_norm vacío (nada de +541541617956)",
              g04["telefono_tipo"] == "invalido" and g04["telefono_norm"] == "",
              f"{g04['telefono_tipo']} / {g04['telefono_norm']!r}")

    # G05 — dos teléfonos en una celda: toma el PRIMERO (CORRECCION-F01).
    g05 = find("G05")
    if g05:
        check("G05 (dos teléfonos) → toma el primero: +541146669999, ambiguo",
              g05["telefono_norm"] == "+541146669999" and g05["telefono_tipo"] == "ambiguo",
              f"{g05['telefono_tipo']} / {g05['telefono_norm']}")
        check("G05 → llamable", g05["prioridad"] in ("alta", "media"), g05["prioridad"])

    # G06 — artefacto de Excel '1.14162E+09': invalido → descarte sin teléfono.
    # (La notación científica es el 'daño de Excel' que reconoce el normalizador;
    # el efecto observable es invalido + descarte por sin teléfono.)
    g06 = find("G06")
    if g06:
        check("G06 (notación científica de Excel) → invalido, sin teléfono",
              g06["telefono_tipo"] == "invalido" and g06["telefono_norm"] == "",
              f"{g06['telefono_tipo']} / {g06['telefono_norm']!r}")
        check("G06 → descartado por sin teléfono",
              g06["prioridad"] == "descartado"
              and MOT_SIN_TEL in g06["motivo"] and MARCA_DESCARTE in g06["motivo"],
              g06["motivo"])

    # G07 — teléfono '1111111111' (F13): descarte por relleno, NO por sin teléfono.
    g07 = find("G07")
    if g07:
        check("G07 (1111111111) → descartado, motivo teléfono de relleno",
              g07["prioridad"] == "descartado" and MOT_RELLENO in g07["motivo"]
              and MARCA_DESCARTE in g07["motivo"],
              g07["motivo"])
        check("G07 → NO cae por 'sin teléfono' (es ambiguo, no invalido)",
              MOT_SIN_TEL not in g07["motivo"], g07["motivo"])

    # G08 — nombre 'test' + teléfono bueno (F13): MARCA, NO descarte.
    g08 = por_tel(rows, "+5491147778888")
    check("G08 (nombre 'test') está en la salida", g08 is not None)
    if g08:
        check("G08 → nombre de relleno MARCA, NO descarta",
              "nombre de relleno" in g08["motivo"] and g08["prioridad"] != "descartado",
              f"{g08['prioridad']} / {g08['motivo']}")

    # G09 — duplicado por CUIL: uno gana, el otro apunta al ganador.
    g09g = find("G09")
    g09p = por_nombre(rows, "G09b")
    check("G09b (perdedor por CUIL) está en la salida", g09p is not None)
    if g09g and g09p:
        check("G09 ganador NO es duplicado", g09g["es_duplicado"] == "FALSE",
              g09g["es_duplicado"])
        check("G09b perdedor → es_duplicado, descartado, motivo duplicado",
              g09p["es_duplicado"] == "TRUE" and g09p["prioridad"] == "descartado"
              and MOT_DUP in g09p["motivo"] and MARCA_DESCARTE in g09p["motivo"],
              g09p["motivo"])
        check("G09b apunta (duplicado_de) al id_fila del ganador",
              g09p["duplicado_de"] == g09g["id_fila"],
              f"dupde={g09p['duplicado_de']} vs ganador id={g09g['id_fila']}")
        check("G09 dedupó por CUIL (motivo_duplicado)", "cuil" in g09p["motivo_duplicado"],
              g09p["motivo_duplicado"])

    # G10 — duplicado por teléfono escrito distinto: aparece recién tras normalizar.
    g10g = find("G10")
    g10p = por_nombre(rows, "G10b")
    check("G10b (perdedor por teléfono) está en la salida", g10p is not None)
    if g10g and g10p:
        check("G10b perdedor → es_duplicado, descartado, motivo duplicado",
              g10p["es_duplicado"] == "TRUE" and g10p["prioridad"] == "descartado"
              and MOT_DUP in g10p["motivo"] and MARCA_DESCARTE in g10p["motivo"],
              g10p["motivo"])
        check("G10 dedup por teléfono NORMALIZADO ('11 3392-7555' == '011 3392-7555')",
              g10g["telefono_match"] == g10p["telefono_match"] and g10g["telefono_match"] != "",
              f"{g10g['telefono_match']} / {g10p['telefono_match']}")
        check("G10 dedupó por teléfono (motivo_duplicado)", "telefono" in g10p["motivo_duplicado"],
              g10p["motivo_duplicado"])

    # G11 — 'Morón (Buenos Aires)' (CORRECCION-F04 A): en zona, sin motivo de zona.
    g11 = find("G11")
    if g11:
        check("G11 'Morón (Buenos Aires)' → en_zona TRUE",
              g11["en_zona"] == "TRUE", g11["en_zona"])
        check("G11 → sin motivo de zona en motivo_descarte, y llamable",
              "zona" not in g11["motivo_descarte"] and g11["prioridad"] in ("alta", "media"),
              f"{g11['prioridad']} / {g11['motivo_descarte']!r}")

    # G12 — localidad vacía (CORRECCION-F04 B): 'sin localidad', NO 'fuera de zona',
    #       media, NO descartado.
    g12 = find("G12")
    if g12:
        check("G12 (localidad vacía) → motivo 'sin localidad'",
              "sin localidad" in g12["motivo_descarte"], g12["motivo_descarte"])
        check("G12 → NO dice 'fuera de zona'",
              "fuera de zona" not in g12["motivo_descarte"], g12["motivo_descarte"])
        check("G12 → media, NO descartado (un contacto sin localidad sigue siendo llamable)",
              g12["prioridad"] == "media", g12["prioridad"])

    # G13 — 'Moreno' (fuera real): fuera de zona, descarte.
    g13 = find("G13")
    if g13:
        check("G13 'Moreno' → fuera de zona, descartado",
              g13["en_zona"] == "FALSE" and g13["prioridad"] == "descartado"
              and MOT_ZONA in g13["motivo"] and MARCA_DESCARTE in g13["motivo"],
              f"{g13['prioridad']} / {g13['motivo']}")

    # G14 — jurídica '30-71234567-1' (F12), cliente vende a individuos.
    g14 = find("G14")
    if g14:
        check("G14 → tipo_persona juridica", g14.get("tipo_persona") == "juridica",
              g14.get("tipo_persona"))
        check("G14 → descartado por segmento no buscado",
              g14["prioridad"] == "descartado" and MOT_SEG in g14["motivo"]
              and MARCA_DESCARTE in g14["motivo"],
              g14["motivo"])

    # G15 — teléfono en la baja (F14): descarte opt-out, por teléfono.
    g15 = find("G15")
    if g15:
        check("G15 → descartado por opt-out, vía teléfono",
              g15["prioridad"] == "descartado" and g15.get("optout_via") == "telefono"
              and MOT_OPTOUT in g15["motivo"] and MARCA_DESCARTE in g15["motivo"],
              f"{g15['prioridad']} / via={g15.get('optout_via')} / {g15['motivo']}")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("=" * 72)
    print("v_fuego.py — PRUEBA DE FUEGO (pipeline entero sobre un archivo de cliente)")
    print("=" * 72)

    # Los cuatro archivos nuevos existen.
    print("\n--- Los archivos de la prueba de fuego existen ---")
    for p, n in [(SUCIO, "leads_fuego_1.csv"), (LIMPIO, "leads_fuego_1_limpio.csv"),
                 (BAJA, "lista_baja_fuego.xlsx"), (MAPEO, "config/mapeo_fuego.json")]:
        check(f"existe {n}", os.path.exists(p))

    # ==================================================================
    print("\n--- Bloque 1: equivalencia sucio vs. gemelo limpio ---")
    caso_s = correr(SUCIO, "sucio")
    caso_l = correr(LIMPIO, "limpio")
    check("(equiv) la corrida del sucio termina bien", caso_s["exito"], caso_s["salida"][-400:])
    check("(equiv) la corrida del limpio termina bien", caso_l["exito"], caso_l["salida"][-400:])
    for etq, key in [("comercial", "com"), ("auditoría", "aud"), ("reporte", "rep")]:
        both = os.path.exists(caso_s[key]) and os.path.exists(caso_l[key])
        check(f"(equiv) {etq}: sucio → salida BYTE A BYTE idéntica a limpio → salida",
              both and file_hash(caso_s[key]) == file_hash(caso_l[key]),
              "difiere: la puerta dejó pasar algo de la superficie del archivo")
    # La ficha SI difiere a proposito (una dice ';' + header corrido, la otra ','
    # + fila 1). No entra en la equivalencia; se chequea en el bloque 4.
    check("(equiv) la ficha SÍ difiere entre los dos (superficie distinta, chequeada aparte)",
          leer_txt(caso_s["ficha"]) != leer_txt(caso_l["ficha"]))

    rows, cols = leer_csv(caso_s["aud"])
    check("(equiv) 25 filas de salida (ninguna se pierde en silencio)", len(rows) == 25,
          f"hay {len(rows)}")

    # ==================================================================
    print("\n--- Bloque 2: celdas firma G01–G15 (esperado literal, nodo real) ---")
    celdas_firma(rows)

    # ==================================================================
    print("\n--- Bloque 3: coherencia del reporte (el número que se vende) ---")
    rep = leer_txt(caso_s["rep"])
    cats = {
        "calidad de dato": [
            ("Sin teléfono utilizable", 2),
            ("Teléfono de relleno (número inventado)", 1),
            ("Duplicado", 2),
        ],
        "zona": [("Fuera de zona de cobertura", 1)],
        "segmento": [("Tipo de persona que el cliente no busca", 1)],
        "opt-out": [("En la lista de no llamar que aporta el cliente", 1)],
    }
    # Las cuatro secciones aparecen.
    check("(reporte) sección 'Por calidad de dato'", "Por calidad de dato" in rep)
    check("(reporte) sección 'Por zona de cobertura'", "Por zona de cobertura" in rep)
    check("(reporte) sección 'Por segmento no buscado'", "Por segmento no buscado" in rep)
    check("(reporte) sección 'Por pedido de baja del titular (opt-out)'",
          "Por pedido de baja del titular (opt-out)" in rep)

    suma = 0
    todas_pobladas = True
    for cat, filas in cats.items():
        for etiqueta, esperado in filas:
            got = fila_reporte(rep, etiqueta)
            check(f"(reporte) '{etiqueta}' = {esperado}", got == esperado, f"dice {got}")
            if got is None or got < 1:
                todas_pobladas = todas_pobladas and False
            suma += got or 0
    check("(reporte) las CUATRO categorías tienen conteo ≥ 1 "
          "(lo que hace a este archivo una prueba de fuego)", todas_pobladas)

    descartados = fila_reporte(rep, "Contactos descartados")
    n_desc_csv = sum(1 for r in rows if r["prioridad"] == "descartado")
    check("(reporte) los descartados del reporte son los del CSV",
          descartados == n_desc_csv == 8, f"reporte={descartados} csv={n_desc_csv}")
    check("(reporte) las subtablas SUMAN al total de descartados (la aritmética cierra)",
          suma == descartados, f"suma de subtablas={suma}, descartados={descartados}")

    # El ahorro con el supuesto documentado: 8 * 4 / 60 = 0.5 h.
    check("(reporte) tiempo por llamada = 4 min (supuesto documentado)",
          re.search(r"Tiempo por llamada.*\|\s*4 min\s*\|", rep) is not None)
    check("(reporte) ahorro = 0.5 h (8 descartados × 4 min / 60)",
          re.search(r"Horas de operador ahorradas\*\*\s*\|\s*\*\*0\.5 h\*\*", rep) is not None,
          [l for l in rep.split("\n") if "ahorradas" in l][:1])

    # ==================================================================
    print("\n--- Bloque 4: la ficha del sucio (separador, header, mapeo) ---")
    ficha = leer_txt(caso_s["ficha"])
    check("(ficha) separador detectado: punto y coma (';')",
          re.search(r"Separador detectado \|\s*punto y coma", ficha) is not None)
    check("(ficha) el header está en la fila real (línea 3, después de 2 de basura)",
          re.search(r"Encabezado en la linea \|\s*3\b", ficha) is not None
          and re.search(r"Lineas salteadas arriba del encabezado \|\s*2\b", ficha) is not None)
    # El mapeo de CADA columna del cliente a la canonica.
    mapeo_esperado = [
        ("Nombre y Apellido", "nombre"),
        ("Documento", "cuil"),
        ("Celular", "telefono"),
        ("Zona", "localidad"),
        ("Origen del Contacto", "origen"),
        ("Fecha de Alta", "fecha_carga"),
    ]
    for orig, canon in mapeo_esperado:
        check(f"(ficha) mapeo: '{orig}' → {canon}",
              re.search(r"\|\s*" + re.escape(orig) + r"\s*\|\s*" + re.escape(canon) + r"\s*\|",
                        ficha) is not None)

    # El mapeo es LOAD-BEARING: sin --mapeo, 'Documento' y 'Origen del Contacto'
    # no estan en sinonimos.json y la corrida se frena. Es la prueba de que el
    # archivo se resolvio CON config, no que las columnas cayeron por casualidad.
    print("\n--- Bonus: el mapeo del cliente es imprescindible (se resolvió con config) ---")
    caso_sin = correr(SUCIO, "sinmapeo", con_mapeo=False)
    check("(config) sin el mapeo del cliente la corrida SE FRENA "
          "(Documento / Origen del Contacto no están en sinónimos)",
          not caso_sin["exito"], "corrió sin el mapeo: el mapeo no estaría haciendo nada")
    check("(config) el rechazo NO produjo CSV comercial",
          not os.path.exists(caso_sin["com"]))

    # ------------------------------------------------------------------
    print("\n" + "=" * 72)
    total = ok + fail
    if fail == 0:
        print(f"RESULTADO: PASA ({total} checks)")
        sys.exit(0)
    print(f"RESULTADO: FALLA ({fail} de {total} checks)")
    sys.exit(1)


if __name__ == "__main__":
    main()
