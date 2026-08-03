#!/usr/bin/env python3
"""Verificador F04 - Completitud y cobertura.

Comprueba que el workflow 05-cobertura marca contactos no llamables por dato y
fuera de zona, con motivo en castellano, sin borrar filas.

Red de seguridad:
  1. ORACULO independiente (misma logica de marcado, en Python) comparado fila
     por fila contra n8n: en_zona, marcado y motivo_descarte.
  2. Conteos duros del CSV: 39 fuera de zona, 82 sin telefono utilizable, 106
     marcados (union), 15 con dos motivos.
  3. La zona es PARAMETRO: se corre el oraculo con dos listas distintas y el
     resultado cambia (criterio 3).
  4. La comparacion de localidades normaliza tildes/capitalizacion (criterio 4).

Uso:
    python verificadores/v04_cobertura.py
    python verificadores/v04_cobertura.py --salida Y.csv

Exit code 0 si pasa, 1 si falla.
"""
import argparse
import csv
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "salidas" / "salida_f04.csv"

# La zona configurada (debe coincidir con CONFIG.zona del nodo F04).
ZONA = ["Castelar", "Haedo", "Moron", "Hurlingham", "Ituzaingo", "Ramos Mejia",
        "Villa Luzuriaga", "San Justo"]

# Conteos medidos sobre el CSV de prueba. No se ajustan para que pase.
ESP_FUERA = 39
ESP_SIN_TEL = 82
ESP_SIN_NOMBRE = 0
ESP_MARCADO = 106
ESP_DOS_MOTIVOS = 15

resultados = []


def check(nombre, ok, detalle=""):
    resultados.append((nombre, ok, detalle))
    return ok


def norm_loc(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(s.lower().strip().split())


def nucleo_loc(s):
    """Nucleo de la localidad: sin parentesis final ni sufijo ', provincia'."""
    t = norm_loc(s)
    t = re.sub(r"\s*\([^)]*\)\s*$", "", t)
    t = re.sub(r",.*$", "", t)
    return " ".join(t.split())


def marcar_oraculo(fila, zona):
    """Devuelve (en_zona, motivos[]). Misma logica que el nodo F04.

    OJO: este oraculo REPLICA la logica del nodo, asi que es la 3a forma de
    check falso de prompts/README.md — atrapa que n8n corrompa un valor, no
    que la regla este mal pensada. Por eso los casos de CORRECCION-F04
    (parentesis, sufijo, vacia) NO se verifican con esto: van mas abajo, con
    esperados literales escritos a mano.
    """
    zona_set = {norm_loc(z) for z in zona}
    motivos = []
    if fila.get("telefono_tipo", "") == "invalido":
        motivos.append("sin teléfono utilizable")
    if str(fila.get("nombre", "")).strip() == "":
        motivos.append("sin nombre")
    sin_localidad = norm_loc(fila.get("localidad", "")) == ""
    en_zona = (not sin_localidad) and nucleo_loc(fila.get("localidad", "")) in zona_set
    if sin_localidad:
        motivos.append("sin localidad")
    elif not en_zona:
        motivos.append("fuera de zona de cobertura")
    return en_zona, motivos


def leer(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def es_true(v):
    return str(v).strip().upper() == "TRUE"


def main():
    # La consola de Windows es cp1252 y los motivos traen '→' y tildes.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=str(SALIDA))
    args = ap.parse_args()
    p_out = Path(args.salida)

    if not check("existe el archivo de salida", p_out.exists(), str(p_out)):
        return reportar()

    filas = leer(p_out)
    check("la salida tiene 200 filas (nada se borro)", len(filas) == 200, f"tiene {len(filas)}")

    cols = filas[0].keys() if filas else []
    for c in ["en_zona", "marcado", "motivo_descarte"]:
        check(f"existe la columna {c}", c in cols)

    # --- Oraculo vs n8n, fila por fila ---
    difs = []
    for i, f in enumerate(filas, 1):
        en_zona, motivos = marcar_oraculo(f, ZONA)
        esp = (en_zona, len(motivos) > 0, "; ".join(motivos))
        got = (es_true(f["en_zona"]), es_true(f["marcado"]), f["motivo_descarte"])
        if got != esp:
            difs.append(f"fila {i} loc={f['localidad']}: n8n={got} oraculo={esp}")
    check(
        "n8n coincide con el oraculo en las 200 filas (en_zona, marcado, motivo)",
        not difs,
        f"{len(difs)} difs; primera: {difs[0] if difs else ''}",
    )

    # --- Criterio 1: todo marcado tiene motivo ; Criterio 2: no-marcado no tiene ---
    marcado_sin_motivo = [f["id_fila"] for f in filas if es_true(f["marcado"]) and f["motivo_descarte"].strip() == ""]
    nomarcado_con_motivo = [f["id_fila"] for f in filas if not es_true(f["marcado"]) and f["motivo_descarte"].strip() != ""]
    check("todo contacto marcado tiene al menos un motivo", not marcado_sin_motivo, f"ids: {marcado_sin_motivo[:5]}")
    check("ningun contacto no-marcado tiene motivo", not nomarcado_con_motivo, f"ids: {nomarcado_con_motivo[:5]}")

    # --- Conteos duros ---
    fuera = sum(1 for f in filas if not es_true(f["en_zona"]))
    sin_tel = sum(1 for f in filas if "sin teléfono" in f["motivo_descarte"])
    sin_nombre = sum(1 for f in filas if "sin nombre" in f["motivo_descarte"])
    marcado = sum(1 for f in filas if es_true(f["marcado"]))
    dos_motivos = sum(1 for f in filas if f["motivo_descarte"].count(";") == 1)
    check(f"{ESP_FUERA} contactos fuera de zona", fuera == ESP_FUERA, f"da {fuera}")
    check(f"{ESP_SIN_TEL} contactos sin telefono utilizable", sin_tel == ESP_SIN_TEL, f"da {sin_tel}")
    check(f"{ESP_SIN_NOMBRE} contactos sin nombre", sin_nombre == ESP_SIN_NOMBRE, f"da {sin_nombre}")
    check(f"{ESP_MARCADO} contactos marcados (union)", marcado == ESP_MARCADO, f"da {marcado}")

    # --- Criterio 5: un contacto con varios problemas conserva TODOS los motivos ---
    check(
        f"{ESP_DOS_MOTIVOS} contactos acumulan dos motivos (sin telefono + fuera de zona)",
        dos_motivos == ESP_DOS_MOTIVOS,
        f"da {dos_motivos}",
    )
    combinados = [
        f for f in filas
        if "sin teléfono utilizable" in f["motivo_descarte"] and "fuera de zona de cobertura" in f["motivo_descarte"]
    ]
    check(
        "el contacto con dos problemas conserva ambos motivos en el texto",
        len(combinados) == ESP_DOS_MOTIVOS and all(";" in c["motivo_descarte"] for c in combinados),
        f"{len(combinados)} combinados",
    )

    # --- Criterio 3: la zona es parametro; con dos listas distintas cambia ---
    def contar_fuera(zona):
        return sum(1 for f in filas if not marcar_oraculo(f, zona)[0])
    fuera_zona_real = contar_fuera(ZONA)
    fuera_todas = contar_fuera(ZONA + ["Moreno", "Merlo"])   # zona = las 10 -> 0 fuera
    fuera_vacia = contar_fuera([])                            # zona vacia -> 200 fuera
    check(
        "cambiar la lista de zona cambia el resultado (parametro real)",
        fuera_zona_real == 39 and fuera_todas == 0 and fuera_vacia == 200,
        f"real={fuera_zona_real} todas={fuera_todas} vacia={fuera_vacia}",
    )
    # y n8n usa EXACTAMENTE la zona configurada (su fuera coincide con esa lista)
    check(
        "el fuera-de-zona de n8n coincide con la zona configurada (no otra)",
        fuera == fuera_zona_real,
        f"n8n={fuera} oraculo(zona real)={fuera_zona_real}",
    )

    # --- Criterio 4: tildes y capitalizacion matchean igual (>=3 variantes) ---
    variantes = ["Morón", "moron", "MORON", "  Morón  ", "MoRoN"]
    todas_igual = len({norm_loc(v) for v in variantes}) == 1
    check(
        "3+ variantes de la misma localidad normalizan igual (tilde/mayusculas/espacios)",
        todas_igual and norm_loc("Morón") == "moron",
        f"normalizan a: {sorted({norm_loc(v) for v in variantes})}",
    )
    # y una fila real con 'Morón' (con tilde) cae EN zona
    moron = [f for f in filas if norm_loc(f["localidad"]) == "moron"]
    check(
        "las filas 'Morón' (con tilde en el dato) quedan en_zona=TRUE",
        moron and all(es_true(f["en_zona"]) for f in moron),
        f"{len(moron)} filas Moron, en_zona todas TRUE: {all(es_true(f['en_zona']) for f in moron)}",
    )

    # --- CORRECCION-F04: paréntesis, sufijo y "sin localidad" ---
    # Estos casos NO se verifican con marcar_oraculo(): ese oráculo replica la
    # lógica del nodo y por lo tanto no puede desmentirla. Van con esperados
    # LITERALES escritos a mano, y por el NODO REAL de n8n, mirando además la
    # prioridad end-to-end (F06) — porque el punto de la parte B no es el texto
    # del motivo, es que la fila NO quede descartada.
    corrida = correr_localidad()
    check("(loc) la corrida de n8n termina bien", corrida["exito"], corrida["detalle"])
    filas_loc = corrida["filas"]
    check("(loc) 5 filas de salida", len(filas_loc) == 5, f"hay {len(filas_loc)}")
    por_tag = {f["nombre"].split()[0]: f for f in filas_loc}

    # (tag, localidad del archivo, en_zona, motivo_descarte exacto, prioridad)
    CASOS_LOC = [
        ("L01", "Morón (Buenos Aires)", True,  "",                          "alta"),
        ("L02", "Morón, Buenos Aires",  True,  "",                          "alta"),
        ("L03", "",                     False, "sin localidad",             "media"),
        ("L04", "Moreno",               False, "fuera de zona de cobertura", "descartado"),
        ("L05", "Morón",                True,  "",                          "alta"),
    ]
    for tag, loc, en_zona_e, motivo_e, prioridad_e in CASOS_LOC:
        f = por_tag.get(tag)
        if f is None:
            check(f"(loc) {tag}: la fila está en la salida", False, "no aparece")
            continue
        check(f"(loc) {tag} localidad del archivo es {loc!r}", f["localidad"] == loc,
              f"vino {f['localidad']!r}")
        check(f"(loc) {tag} en_zona == {en_zona_e}", es_true(f["en_zona"]) == en_zona_e,
              f"vino {f['en_zona']!r}")
        check(f"(loc) {tag} motivo_descarte == {motivo_e!r}",
              f["motivo_descarte"] == motivo_e, f"vino {f['motivo_descarte']!r}")
        check(f"(loc) {tag} prioridad == {prioridad_e}", f["prioridad"] == prioridad_e,
              f"vino {f['prioridad']!r}")

    # Los dos que importan, dichos de otra forma para que no se cuelen:
    l03 = por_tag.get("L03")
    check("(loc) L03 (sin localidad) NO dice 'fuera de zona' en ningún lado",
          l03 is not None and "fuera de zona" not in l03["motivo_descarte"]
          and "fuera de zona" not in l03["motivo"],
          f"motivo_descarte={l03['motivo_descarte']!r} motivo={l03['motivo']!r}" if l03 else "")
    check("(loc) L03 NO queda descartada por tener la localidad vacía (sigue llamable)",
          l03 is not None and l03["prioridad"] != "descartado",
          f"prioridad={l03['prioridad']!r}" if l03 else "")
    check("(loc) L03 no cobra el bono de zona: 0 puntos por localidad (decisión de Pedro)",
          l03 is not None and "sin localidad +0" in l03["motivo"],
          f"motivo={l03['motivo']!r}" if l03 else "")
    l04 = por_tag.get("L04")
    check("(loc) L04 (Moreno, realmente fuera) sigue descartada por zona",
          l04 is not None and "fuera de zona +0 → descarte" in l04["motivo"],
          f"motivo={l04['motivo']!r}" if l04 else "")

    # El match es EXACTO sobre el núcleo, no substring ni prefijo.
    check("(loc) el núcleo se compara exacto: 'Castelar Norte' NO es 'Castelar'",
          nucleo_loc("Castelar Norte") == "castelar norte"
          and nucleo_loc("Castelar Norte") not in {norm_loc(z) for z in ZONA})
    check("(loc) 'Morón (Buenos Aires)' y 'Morón, Buenos Aires' dan el mismo núcleo",
          nucleo_loc("Morón (Buenos Aires)") == nucleo_loc("Morón, Buenos Aires") == "moron")

    return reportar()


def correr_localidad():
    """Corre data/leads_localidad_1.csv por el pipeline real de n8n (fase 14).

    Hace falta la corrida real, y hasta el final: la parte B de la corrección
    se juega en la PRIORIDAD (F06), no en el texto del motivo de F04.
    """
    import json
    import os
    import subprocess
    import tempfile

    base = str(RAIZ)
    gen = str(RAIZ / "herramientas" / "gen_workflow.py")
    entrada = str(RAIZ / "data" / "leads_localidad_1.csv")
    com = str(RAIZ / "salidas" / "_v04_loc_com.csv")
    aud = str(RAIZ / "salidas" / "_v04_loc_aud.csv")
    ficha = str(RAIZ / "salidas" / "ficha_entrada_leads_localidad_1.md")
    tmp_wf = os.path.join(tempfile.gettempdir(), "wf_v04_loc.json")

    for f in (com, aud):
        if os.path.exists(f):
            os.remove(f)
    try:
        subprocess.run(
            [sys.executable, gen, tmp_wf, entrada, com, "--fase", "14",
             "--fecha-corte", "2026-07-28", "--csv-out-audit", aud,
             "--ficha-out", ficha],
            check=True, capture_output=True)
        with open(tmp_wf, encoding="utf-8") as fh:
            wf = json.load(fh)
        wf["id"] = "f04loc______tmp"
        wf["name"] = "tmp-v04-loc"
        with open(tmp_wf, "w", encoding="utf-8") as fh:
            json.dump(wf, fh, indent=2, ensure_ascii=False)

        env = os.environ.copy()
        env["N8N_RESTRICT_FILE_ACCESS_TO"] = base
        subprocess.run(f'npx n8n import:workflow --input="{tmp_wf}"', shell=True,
                       check=True, env=env, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        r = subprocess.run(f"npx n8n execute --id={wf['id']}", shell=True, env=env,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        exito = r.returncode == 0 and "Execution was successful" in (r.stdout or "")
        filas = leer(aud) if os.path.exists(aud) else []
        return {"exito": exito, "filas": filas,
                "detalle": ((r.stdout or "") + (r.stderr or ""))[-200:]}
    except Exception as e:
        return {"exito": False, "filas": [], "detalle": str(e)[:200]}
    finally:
        if os.path.exists(tmp_wf):
            os.remove(tmp_wf)


def reportar():
    ancho = max(len(n) for n, _, _ in resultados)
    print()
    print("  VERIFICADOR F04 - completitud y cobertura")
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
