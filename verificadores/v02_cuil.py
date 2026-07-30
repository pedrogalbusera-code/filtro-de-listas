#!/usr/bin/env python3
"""Verificador F02 - Validacion de CUIL.

Comprueba que el workflow 03-cuil deriva bien cuil_norm (11 digitos string) y
cuil_valido (bool) para los 200 contactos, con modulo 11 real.

Regla (correccion 2026-07-27): resto 1 -> INVALIDO. Un CUIL que da resto 1 con
su propio prefijo no existe bajo AFIP (lo habria reemitido con prefijo 23), y las
reemisiones 23-DNI-9/4 validan solas con este mismo algoritmo simple.

Red de seguridad:
  1. Un ORACULO independiente (validar_cuil, reimplementado en Python) se compara
     fila por fila contra lo que escribio n8n. Si coinciden en las 200 filas, el
     nodo Code implementa el mismo modulo 11.
  2. Clasificacion esperada EXACTA: 181 validos y 19 invalidos por resto 1. El CSV
     se genero con la regla vieja (resto 1 -> DV 9), asi que esos 19 caen
     invalidos: es la prueba de que el archivo estaba mal generado, no un bug.
  3. Rechazo real: se mutan los CUILs validos y se comprueba que se rechazan.
     - Test fuerte: cambiar el DIGITO VERIFICADOR por cualquier otro valor da
       invalido siempre. Prueba que el DV se controla de verdad.
     - Test del medio: cambiar un digito DEL MEDIO invalida SIEMPRE (100%). Al
       rechazar resto 1 desaparecio la colision de DV (antes resto 1 y 2 daban
       ambos 9), asi que ya no hay mutaciones del medio que sobrevivan.

Uso:
    python verificadores/v02_cuil.py
    python verificadores/v02_cuil.py --entrada X.csv --salida Y.csv

Exit code 0 si pasa, 1 si falla.
"""
import argparse
import csv
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "data" / "leads_prueba_SINTETICO_1.csv"
SALIDA = RAIZ / "salidas" / "salida_f02.csv"

PREFIJOS = {"20", "23", "24", "27", "30", "33", "34"}
PESOS = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]

resultados = []


def check(nombre, ok, detalle=""):
    resultados.append((nombre, ok, detalle))
    return ok


def validar_cuil(raw):
    """Oraculo independiente: mismo modulo 11 que el nodo Code, en Python.

    Devuelve (norm, valido, dudoso). resto 1 -> INVALIDO (un CUIL con resto 1
    con su propio prefijo no existe: AFIP lo habria reemitido con prefijo 23).
    dudoso = fue rechazado por resto 1 (marca auditable del rechazo).
    """
    norm = re.sub(r"\D", "", "" if raw is None else str(raw))
    if len(norm) != 11:
        return norm, False, False
    if norm[:2] not in PREFIJOS:
        return norm, False, False
    suma = sum(int(norm[i]) * PESOS[i] for i in range(10))
    resto = suma % 11
    if resto == 1:
        return norm, False, True
    dv = 0 if resto == 0 else 11 - resto
    return norm, dv == int(norm[10]), False


def leer(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def a_bool(v):
    return str(v).strip().upper() == "TRUE"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", default=str(ENTRADA))
    ap.add_argument("--salida", default=str(SALIDA))
    args = ap.parse_args()

    p_in, p_out = Path(args.entrada), Path(args.salida)

    if not check("existe el archivo de salida", p_out.exists(), str(p_out)):
        return reportar()

    filas_in = leer(p_in)
    filas_out = leer(p_out)

    check("la salida tiene 200 filas", len(filas_out) == 200, f"tiene {len(filas_out)}")

    cols = filas_out[0].keys() if filas_out else []
    check("existe la columna cuil_norm", "cuil_norm" in cols)
    check("existe la columna cuil_valido", "cuil_valido" in cols)
    check("existe la columna cuil_dudoso", "cuil_dudoso" in cols)
    check(
        "sobreviven las columnas originales y las de F01",
        all(c in cols for c in ["cuil", "telefono_norm", "telefono_tipo"]),
        f"columnas: {list(cols)}",
    )

    # cuil_norm: 11 digitos string, sin perder ceros, coincide con el crudo.
    norm_mal = []
    for i, (fi, fo) in enumerate(zip(filas_in, filas_out), 1):
        esp = re.sub(r"\D", "", fi["cuil"])
        if fo["cuil_norm"] != esp or len(fo["cuil_norm"]) != 11 or not fo["cuil_norm"].isdigit():
            norm_mal.append(f"fila {i}: {fo['cuil_norm']!r} (esperado {esp!r})")
    check(
        "cuil_norm son 11 digitos como string, sin perder ceros",
        not norm_mal,
        f"{len(norm_mal)} mal; primera: {norm_mal[0] if norm_mal else ''}",
    )

    # cuil_valido presente en las 200 (no indefinido).
    falt = [i for i, f in enumerate(filas_out, 1) if f.get("cuil_valido") in (None, "")]
    check("las 200 filas tienen cuil_valido", not falt, f"faltan {falt[:5]}")

    # --- Oraculo vs n8n, fila por fila (valido Y dudoso) ---
    difs = []
    for i, fo in enumerate(filas_out, 1):
        _, esp_v, esp_d = validar_cuil(fo["cuil"])
        if a_bool(fo["cuil_valido"]) != esp_v:
            difs.append(f"fila {i} cuil={fo['cuil']}: valido n8n={fo['cuil_valido']} oraculo={esp_v}")
        if a_bool(fo["cuil_dudoso"]) != esp_d:
            difs.append(f"fila {i} cuil={fo['cuil']}: dudoso n8n={fo['cuil_dudoso']} oraculo={esp_d}")
    check(
        "n8n coincide con el oraculo en las 200 filas (valido y dudoso)",
        not difs,
        f"{len(difs)} difs; primera: {difs[0] if difs else ''}",
    )

    # --- Clasificacion nueva: 181 validos, 19 invalidos por resto 1 ---
    # El CSV se genero con la regla vieja (resto 1 -> DV 9), asi que esos 19
    # ahora caen invalidos. Es esperable: prueba de que el archivo estaba mal
    # generado, no un bug del validador.
    validos = sum(1 for f in filas_out if a_bool(f["cuil_valido"]))
    invalidos = sum(1 for f in filas_out if not a_bool(f["cuil_valido"]))
    check("181 CUILs validos", validos == 181, f"validos {validos}")
    check("19 CUILs invalidos", invalidos == 19, f"invalidos {invalidos}")

    # --- cuil_dudoso: ahora marca los RECHAZADOS por resto 1 ---
    # Son 19 en el CSV, y todos son cuil_valido=FALSE (subconjunto de invalidos).
    dudosos = [f for f in filas_out if a_bool(f["cuil_dudoso"])]
    check(
        "cuil_dudoso marca exactamente los 19 casos 'resto 1' del CSV",
        len(dudosos) == 19,
        f"hay {len(dudosos)}",
    )
    dudoso_valido = [f["cuil_norm"] for f in dudosos if a_bool(f["cuil_valido"])]
    check(
        "todo cuil_dudoso es cuil_valido=FALSE (rechazado por resto 1)",
        not dudoso_valido,
        f"{len(dudoso_valido)} dudosos que quedaron validos",
    )
    # Los 19 invalidos son EXACTAMENTE los dudosos (no hay otros invalidos).
    check(
        "los 19 invalidos son exactamente los rechazados por resto 1",
        invalidos == len(dudosos) == 19,
        f"invalidos {invalidos} / dudosos {len(dudosos)}",
    )
    # Y que 'dudoso' se corresponde 1 a 1 con resto==1 en el oraculo.
    resto1_oraculo = sum(1 for f in filas_out if validar_cuil(f["cuil"])[2])
    check(
        "cuil_dudoso coincide con resto==1 del oraculo",
        len(dudosos) == resto1_oraculo == 19,
        f"n8n {len(dudosos)} / oraculo {resto1_oraculo}",
    )

    # Sanity: que existan los dos prefijos-familia posibles no importa, pero si
    # todos fueran rechazados por prefijo el test anterior ya fallaria. Chequeo
    # extra: los prefijos presentes estan dentro del set permitido.
    pref_fuera = sorted({f["cuil_norm"][:2] for f in filas_out} - PREFIJOS)
    check("todos los prefijos presentes son validos", not pref_fuera, f"fuera: {pref_fuera}")

    # --- Test fuerte de rechazo: flip del digito verificador ---
    # Para cada CUIL valido, cambiar el ultimo digito por cualquiera de los otros
    # 9 tiene que dar invalido. 200 * 9 = 1800 mutantes, todos invalidos.
    total_dv, rechazados_dv = 0, 0
    for f in filas_out:
        n = f["cuil_norm"]
        if not a_bool(f["cuil_valido"]):
            continue
        for d in "0123456789":
            if d == n[10]:
                continue
            total_dv += 1
            mut = n[:10] + d
            _, ok, _ = validar_cuil(mut)
            if not ok:
                rechazados_dv += 1
    check(
        "cambiar el digito verificador da invalido (100%)",
        total_dv > 0 and rechazados_dv == total_dv,
        f"{rechazados_dv}/{total_dv} rechazados",
    )

    # --- Test del medio (lo que pide la fase) ---
    # Cambiar UN digito del medio (posiciones 2..9) de un CUIL valido tiene que
    # invalidarlo SIEMPRE. Con la regla nueva (resto 1 -> invalido) ya no hay
    # colision de DV: resto 1 y resto 2 ya no mapean ambos a 9, asi que cualquier
    # cambio del medio altera el resto y rompe la validez. 100%, sin excepciones.
    total_medio, rompen_medio = 0, 0
    for f in filas_out:
        n = f["cuil_norm"]
        if not a_bool(f["cuil_valido"]):
            continue
        for pos in range(2, 10):
            for d in "0123456789":
                if d == n[pos]:
                    continue
                total_medio += 1
                mut = n[:pos] + d + n[pos + 1:]
                _, ok, _ = validar_cuil(mut)
                if not ok:
                    rompen_medio += 1
    check(
        "cambiar un digito del medio invalida el CUIL (100%, ya sin colision de DV)",
        total_medio > 0 and rompen_medio == total_medio,
        f"{rompen_medio}/{total_medio} = {100*rompen_medio/total_medio:.1f}%",
    )

    # --- Rechazos de formato/prefijo ---
    _, ok_corto, _ = validar_cuil("2712345")          # menos de 11 -> invalido
    _, ok_pref, _ = validar_cuil("99432823887")        # prefijo 99 no valido
    _, ok_letras, _ = validar_cuil("27-ABCDEFG-7")     # letras -> norm corto -> invalido
    check("un CUIL de menos de 11 digitos es invalido", not ok_corto)
    check("un prefijo no permitido (99) es invalido", not ok_pref)
    check("un CUIL con letras es invalido", not ok_letras)

    # --- Pureza / determinismo ---
    check(
        "la validacion es determinista (mismo input -> mismo output)",
        all(validar_cuil(f["cuil"]) == validar_cuil(f["cuil"]) for f in filas_out),
    )

    return reportar()


def reportar():
    ancho = max(len(n) for n, _, _ in resultados)
    print()
    print("  VERIFICADOR F02 - validacion de CUIL")
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
