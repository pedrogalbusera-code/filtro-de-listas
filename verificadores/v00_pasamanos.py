#!/usr/bin/env python3
"""Verificador F00 - Pasamanos.

Comprueba que el workflow 01-pasamanos devuelve el CSV de entrada intacto.
Ninguna fila perdida, ninguna celda alterada, ningun cero inicial comido.

Uso:
    python verificadores/v00_pasamanos.py
    python verificadores/v00_pasamanos.py --entrada X.csv --salida Y.csv

Exit code 0 si pasa, 1 si falla.
"""
import argparse
import csv
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "data" / "leads_prueba_SINTETICO_1.csv"
SALIDA = RAIZ / "salidas" / "salida_f00.csv"

COLUMNAS = ["nombre", "cuil", "telefono", "localidad", "origen", "fecha_carga"]
FILAS_ESPERADAS = 200

resultados = []


def check(nombre, ok, detalle=""):
    resultados.append((nombre, ok, detalle))
    return ok


def leer(path):
    """Lee el CSV como texto puro. Nada de inferencia de tipos."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        lector = csv.reader(fh)
        filas = [f for f in lector if any(c.strip() for c in f)]
    return filas[0], filas[1:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", default=str(ENTRADA))
    ap.add_argument("--salida", default=str(SALIDA))
    args = ap.parse_args()

    p_in, p_out = Path(args.entrada), Path(args.salida)

    if not check("existe el archivo de salida", p_out.exists(), str(p_out)):
        reportar()
        return 1

    try:
        crudo = p_out.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as e:
        check("la salida es UTF-8", False, str(e))
        reportar()
        return 1
    check("la salida es UTF-8", True)

    cab_in, filas_in = leer(p_in)
    cab_out, filas_out = leer(p_out)

    check(
        f"la salida tiene {FILAS_ESPERADAS} filas de datos",
        len(filas_out) == FILAS_ESPERADAS,
        f"tiene {len(filas_out)}",
    )
    check(
        "entran las mismas filas que salen",
        len(filas_in) == len(filas_out),
        f"entrada {len(filas_in)} / salida {len(filas_out)}",
    )
    check(
        "el encabezado es identico y en el mismo orden",
        cab_out == cab_in,
        f"esperado {cab_in} / obtenido {cab_out}",
    )

    # Comparacion celda por celda. Sin ordenar: el orden tambien tiene que
    # sobrevivir, porque F03 va a usar la posicion original como desempate.
    diferencias = []
    for i, (fi, fo) in enumerate(zip(filas_in, filas_out), start=1):
        for j, col in enumerate(cab_in):
            vi = fi[j] if j < len(fi) else ""
            vo = fo[j] if j < len(fo) else ""
            if vi != vo:
                diferencias.append(f"fila {i}, col {col}: {vi!r} -> {vo!r}")
    check(
        "todas las celdas sobreviven identicas",
        not diferencias,
        f"{len(diferencias)} diferencias; primeras 5: " + " | ".join(diferencias[:5])
        if diferencias
        else "",
    )

    # Trampas concretas de esta fase: lo que un parser de CSV rompe solo.
    idx_tel = cab_in.index("telefono")
    idx_cuil = cab_in.index("cuil")

    ceros_in = sum(1 for f in filas_in if f[idx_tel].startswith("0"))
    ceros_out = sum(1 for f in filas_out if f[idx_tel].startswith("0"))
    check(
        "sobreviven los telefonos con cero inicial (011-...)",
        ceros_in == ceros_out and ceros_in > 0,
        f"entrada {ceros_in} / salida {ceros_out}",
    )

    guiones_in = sum(1 for f in filas_in if "-" in f[idx_cuil])
    guiones_out = sum(1 for f in filas_out if "-" in f[idx_cuil])
    check(
        "los CUIL conservan los guiones",
        guiones_in == guiones_out and guiones_in > 0,
        f"entrada {guiones_in} / salida {guiones_out}",
    )

    sindato_in = sum(1 for f in filas_in if not f[idx_tel].strip().replace(" ", "").isdigit()
                     and not any(c.isdigit() for c in f[idx_tel]))
    sindato_out = sum(1 for f in filas_out if not any(c.isdigit() for c in f[idx_tel]))
    check(
        "sobreviven los telefonos con texto ('sin dato')",
        sindato_in == sindato_out and sindato_in > 0,
        f"entrada {sindato_in} / salida {sindato_out}",
    )

    tildes = sum(1 for f in filas_out for c in f if any(x in c for x in "áéíóúñÁÉÍÓÚÑ"))
    check("las tildes y enies no se rompieron", tildes > 0, f"{tildes} celdas con tilde")

    return reportar()


def reportar():
    ancho = max(len(n) for n, _, _ in resultados)
    print()
    print("  VERIFICADOR F00 - pasamanos")
    print("  " + "-" * (ancho + 10))
    for nombre, ok, detalle in resultados:
        marca = "PASA" if ok else "FALLA"
        linea = f"  {marca:<5} {nombre.ljust(ancho)}"
        if detalle and not ok:
            linea += f"   <- {detalle}"
        elif detalle and ok:
            linea += f"   ({detalle})"
        print(linea)
    fallas = [n for n, ok, _ in resultados if not ok]
    print("  " + "-" * (ancho + 10))
    if fallas:
        print(f"  RESULTADO: FALLA ({len(fallas)} de {len(resultados)} checks)")
        print()
        return 1
    print(f"  RESULTADO: PASA ({len(resultados)} checks)")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
