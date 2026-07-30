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


def marcar_oraculo(fila, zona):
    """Devuelve (en_zona, motivos[]). Misma logica que el nodo F04."""
    zona_set = {norm_loc(z) for z in zona}
    motivos = []
    if fila.get("telefono_tipo", "") == "invalido":
        motivos.append("sin teléfono utilizable")
    if str(fila.get("nombre", "")).strip() == "":
        motivos.append("sin nombre")
    en_zona = norm_loc(fila.get("localidad", "")) in zona_set
    if not en_zona:
        motivos.append("fuera de zona de cobertura")
    return en_zona, motivos


def leer(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def es_true(v):
    return str(v).strip().upper() == "TRUE"


def main():
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

    return reportar()


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
