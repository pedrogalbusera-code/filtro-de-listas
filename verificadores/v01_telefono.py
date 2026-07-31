#!/usr/bin/env python3
"""Verificador F01 - Normalizacion de telefono.

Comprueba que el workflow 02-telefono deriva bien telefono_norm y
telefono_tipo para los 200 contactos, sin tocar el campo 'telefono' original.

La red de seguridad es doble:
  1. Un ORACULO independiente (esperado(), reimplementado en Python) se compara
     fila por fila contra lo que escribio n8n. Si las dos implementaciones
     coinciden en las 200 filas, el nodo Code hace lo que dice el oraculo.
  2. Sobre eso, los conteos duros del CSV de prueba: 118 utilizables / 82
     invalidos, y 42/45/31 por tipo. Si el oraculo estuviera domesticado para
     que pase, estos numbers no cerrarian.

Uso:
    python verificadores/v01_telefono.py
    python verificadores/v01_telefono.py --entrada X.csv --salida Y.csv

Exit code 0 si pasa, 1 si falla.
"""
import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "data" / "leads_prueba_SINTETICO_1.csv"
SALIDA = RAIZ / "salidas" / "salida_f01.csv"

TIPOS_VALIDOS = {"celular", "fijo", "ambiguo", "invalido"}
UTILIZABLES = {"celular", "fijo", "ambiguo"}

# Conteos medidos sobre el CSV de prueba. NO se ajustan para que pase: si el
# codigo da otra cosa, el codigo esta mal (lo dice el prompt de la fase).
ESPERADO_POR_TIPO = {"celular": 42, "fijo": 45, "ambiguo": 31, "invalido": 82}
ESPERADO_UTILIZABLES = 118
ESPERADO_INVALIDOS = 82

resultados = []


def check(nombre, ok, detalle=""):
    resultados.append((nombre, ok, detalle))
    return ok


def esperado(raw):
    """Oraculo independiente: la MISMA regla que el nodo Code, en Python.

    Que sea una segunda implementacion es a proposito: dos implementaciones que
    coinciden en las 200 filas reales es la garantia. Si divergen, salta aca.
    """
    s = "" if raw is None else str(raw).strip()

    # Notacion cientifica (dano de Excel)
    if re.match(r"^\d+\.\d+[eE]\+\d+$", s):
        return ("", "invalido")

    # Texto
    if re.search(r"[a-zA-Z]", s):
        return ("", "invalido")

    # Dos telefonos separados por '/'
    inp = s
    if "/" in s:
        inp = s.split("/")[0].strip()

    # Sacar espacios internos antes de clasificar
    limpio = re.sub(r"\s+", "", inp)
    digitos = re.sub(r"\D", "", limpio)

    if len(digitos) == 0:
        return ("", "invalido")

    # +549... -> celular
    if limpio.startswith("+549"):
        nac = digitos[3:]
        if len(nac) == 10:
            return ("+549" + nac, "celular")
        return ("", "invalido")

    # +54 sin 9 -> fijo
    if limpio.startswith("+54"):
        nac = digitos[2:]
        if len(nac) == 10:
            return ("+54" + nac, "fijo")
        return ("", "invalido")

    # 549... sin + -> celular
    if digitos.startswith("549") and len(digitos) == 13:
        nac = digitos[3:]
        return ("+549" + nac, "celular")

    # 0XX 15 XXXX-XXXX -> celular (formato viejo con 15)
    if digitos and digitos[0] == "0" and 13 <= len(digitos) <= 15:
        for area_len in range(2, 5):
            area = digitos[1:1 + area_len]
            resto = digitos[1 + area_len:]
            if resto.startswith("15") and len(resto) == 10:
                abonado = resto[2:]
                return ("+549" + area + abonado, "celular")

    # Fijo: 11 digitos con 0 inicial
    if len(digitos) == 11 and digitos[0] == "0":
        return ("+54" + digitos[1:], "fijo")

    # 15 sin codigo de area -> invalido
    if digitos.startswith("15") and len(digitos) == 10:
        return ("", "invalido")

    # Ambiguo: 10 digitos sin prefijo
    if len(digitos) == 10 and not limpio.startswith("+"):
        return ("+54" + digitos, "ambiguo")

    return ("", "invalido")


def leer(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def es_texto_sindato(raw):
    return "sindato" in str(raw).strip().lower().replace(" ", "") or \
        bool(re.search(r"[a-zA-Z]", str(raw)))


def es_truncado_6(raw):
    d = re.sub(r"\D", "", str(raw))
    return len(d) == 6 and not re.search(r"[a-zA-Z]", str(raw))


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

    check(
        "la salida tiene 200 filas",
        len(filas_out) == 200,
        f"tiene {len(filas_out)}",
    )
    check(
        "entran las mismas filas que salen",
        len(filas_in) == len(filas_out),
        f"entrada {len(filas_in)} / salida {len(filas_out)}",
    )

    # Las dos columnas nuevas existen y las 6 originales sobreviven.
    cols = filas_out[0].keys() if filas_out else []
    check("existe la columna telefono_norm", "telefono_norm" in cols)
    check("existe la columna telefono_tipo", "telefono_tipo" in cols)
    originales = ["nombre", "cuil", "telefono", "localidad", "origen", "fecha_carga"]
    check(
        "sobreviven las 6 columnas originales",
        all(c in cols for c in originales),
        f"columnas: {list(cols)}",
    )

    # 'telefono' original intacto, fila por fila (no se toca el campo de entrada).
    tel_intacto = all(
        fi["telefono"] == fo["telefono"] for fi, fo in zip(filas_in, filas_out)
    )
    check("el campo 'telefono' original no se toco", tel_intacto)

    # Toda fila tiene los dos campos, y tipo dentro del dominio de 4 valores.
    faltantes = [
        i for i, f in enumerate(filas_out, 1)
        if f.get("telefono_norm") is None or f.get("telefono_tipo") is None
    ]
    check(
        "las 200 filas tienen telefono_norm y telefono_tipo (ninguno indefinido)",
        not faltantes,
        f"faltan en filas {faltantes[:5]}",
    )
    tipos_fuera = sorted({f["telefono_tipo"] for f in filas_out} - TIPOS_VALIDOS)
    check(
        "telefono_tipo siempre en {celular, fijo, ambiguo, invalido}",
        not tipos_fuera,
        f"tipos raros: {tipos_fuera}",
    )

    # Nunca aparece 'undefined' ni '+549' pelado como norm (criterio 4).
    basura = [
        f["telefono_norm"] for f in filas_out
        if f["telefono_norm"] in ("undefined", "+549", "+54")
    ]
    check("ningun telefono_norm es 'undefined' ni un prefijo pelado", not basura,
          f"{len(basura)} casos")

    # --- Oraculo independiente, fila por fila ---
    difs = []
    for i, fo in enumerate(filas_out, 1):
        norm_e, tipo_e = esperado(fo["telefono"])
        if fo["telefono_norm"] != norm_e or fo["telefono_tipo"] != tipo_e:
            difs.append(
                f"fila {i} tel={fo['telefono']!r}: "
                f"n8n=({fo['telefono_norm']!r},{fo['telefono_tipo']}) "
                f"oraculo=({norm_e!r},{tipo_e})"
            )
    check(
        "n8n coincide con el oraculo en las 200 filas",
        not difs,
        f"{len(difs)} diferencias; primera: {difs[0] if difs else ''}",
    )

    # --- Conteos duros del CSV de prueba ---
    por_tipo = Counter(f["telefono_tipo"] for f in filas_out)
    for tipo, esp in ESPERADO_POR_TIPO.items():
        check(
            f"hay {esp} de tipo {tipo}",
            por_tipo.get(tipo, 0) == esp,
            f"hay {por_tipo.get(tipo, 0)}",
        )
    utilizables = sum(1 for f in filas_out if f["telefono_tipo"] in UTILIZABLES)
    invalidos = sum(1 for f in filas_out if f["telefono_tipo"] == "invalido")
    check(
        f"{ESPERADO_UTILIZABLES} telefonos utilizables",
        utilizables == ESPERADO_UTILIZABLES,
        f"hay {utilizables}",
    )
    check(
        f"{ESPERADO_INVALIDOS} telefonos invalidos",
        invalidos == ESPERADO_INVALIDOS,
        f"hay {invalidos}",
    )

    # --- Los invalidos tienen norm EXACTAMENTE vacio (criterios 4 y 5) ---
    sindato_mal = [
        f["telefono"] for f in filas_out
        if es_texto_sindato(f["telefono"]) and f["telefono_norm"] != ""
    ]
    check(
        "los 'sin dato'/'sindato' quedan norm vacio ''",
        not sindato_mal,
        f"{len(sindato_mal)} con norm no vacio",
    )
    trunc_mal = [
        f["telefono"] for f in filas_out
        if es_truncado_6(f["telefono"]) and (f["telefono_norm"] != "" or f["telefono_tipo"] != "invalido")
    ]
    check(
        "los truncados de 6 digitos quedan invalido y norm vacio (no se completan)",
        not trunc_mal,
        f"{len(trunc_mal)} truncados mal resueltos",
    )
    # Que existan de verdad las dos ramas (no vacias por accidente).
    n_sindato = sum(1 for f in filas_out if es_texto_sindato(f["telefono"]))
    n_trunc = sum(1 for f in filas_out if es_truncado_6(f["telefono"]))
    check("hay 41 'sin dato' en la muestra", n_sindato == 41, f"hay {n_sindato}")
    check("hay 41 truncados de 6 en la muestra", n_trunc == 41, f"hay {n_trunc}")

    # --- La trampa central: fijo y celular con los mismos 8 finales -> distintos ---
    # (criterio 3, probado explicitamente sobre el esquema canonico)
    cel_norm, cel_tipo = esperado("+549 11 3992-7555")   # celular, tail 39927555
    fijo_norm, fijo_tipo = esperado("011-39927555")       # fijo,    tail 39927555
    mismo_tail = cel_norm[-8:] == fijo_norm[-8:] == "39927555"
    check(
        "colision fijo/celular con mismos 8 finales -> canonicos DISTINTOS",
        mismo_tail and cel_norm != fijo_norm and cel_tipo == "celular" and fijo_tipo == "fijo",
        f"cel={cel_norm} fijo={fijo_norm}",
    )
    check(
        "el celular conserva el 9 (+549...)",
        cel_norm.startswith("+549"),
        f"cel={cel_norm}",
    )

    # --- Misma linea en dos formatos -> el mismo canonico (criterio 2) ---
    a = esperado("+549 11 3992-7555")
    b = esperado("+5491139927555")
    check(
        "el mismo numero en dos formatos da el mismo telefono_norm",
        a == b == ("+5491139927555", "celular"),
        f"a={a} b={b}",
    )

    # --- Pureza: mismo input, mismo output (criterio 7) ---
    check(
        "la normalizacion es determinista (mismo input -> mismo output)",
        all(esperado(f["telefono"]) == esperado(f["telefono"]) for f in filas_out),
    )

    # --- CORRECCION-F01: formatos nuevos, verificados por celda ---
    CASOS_F01 = [
        ("T01", "+54 11 4161-7956",           "fijo",     "+541141617956"),
        ("T02", "+54 9 11 4161 7956",          "celular",  "+5491141617956"),
        ("T03", "549 11 4161 7956",            "celular",  "+5491141617956"),
        ("T04", "011 15 4161-7956",            "celular",  "+5491141617956"),
        ("T05", "15-4161-7956",                "invalido", ""),
        ("T06", "4161-7956",                   "invalido", ""),
        ("T07", "(011) 4161-7956",             "fijo",     "+541141617956"),
        ("T08", "1141617956.0",                "invalido", ""),
        ("T09", "1.14162E+09",                 "invalido", ""),
        ("T10", "1141617956 / 1165385561",     "ambiguo",  "+541141617956"),
    ]
    for tag, entrada, tipo_e, norm_e in CASOS_F01:
        norm_r, tipo_r = esperado(entrada)
        check(
            f"{tag} {entrada!r} -> {tipo_e}",
            tipo_r == tipo_e and norm_r == norm_e,
            f"oraculo=({norm_r!r},{tipo_r})",
        )

    # Casos que ya funcionaban y no se tocan.
    NO_TOCAR = [
        ("T11", "  1155551111  ",              "ambiguo",  "+541155551111"),
        ("T12", "+549 11 5555-1111",           "celular",  "+5491155551111"),
        ("T13", "011-45551111",                "fijo",     "+541145551111"),
        ("T14", "1145551111",                  "ambiguo",  "+541145551111"),
        ("T44", "sin  dato",                   "invalido", ""),
        ("T45", "N/D",                         "invalido", ""),
        ("T46", "0",                           "invalido", ""),
    ]
    for tag, entrada, tipo_e, norm_e in NO_TOCAR:
        norm_r, tipo_r = esperado(entrada)
        check(
            f"{tag} {entrada!r} -> {tipo_e} (no tocar)",
            tipo_r == tipo_e and norm_r == norm_e,
            f"oraculo=({norm_r!r},{tipo_r})",
        )

    return reportar()


def reportar():
    ancho = max(len(n) for n, _, _ in resultados)
    print()
    print("  VERIFICADOR F01 - normalizacion de telefono")
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
