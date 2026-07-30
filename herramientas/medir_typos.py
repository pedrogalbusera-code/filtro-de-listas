#!/usr/bin/env python3
"""Mide que porcentaje de typos de UN digito quedan sin detectar, segun la
regla que se use para el digito verificador.

Se ejecuta sobre los CUILs del CSV. No decide nada: solo mide.

    python medir_typos.py <ruta del csv> [--columna cuil]
"""
import argparse, csv, re

PESOS = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]


def resto(d):
    return sum(int(a) * b for a, b in zip(d[:10], PESOS)) % 11


def dv_simplificado(r):
    """La regla que aplica hoy el validador: resto 1 -> DV 9."""
    if r == 0:
        return 0
    if r == 1:
        return 9
    return 11 - r


def dv_estricto(r):
    """Resto 1 -> el CUIL no existe con ese prefijo. Devuelve None = rechazo.

    OJO: esto NO es la regla completa de AFIP. Es una simplificacion mas dura
    que la otra: no modela la reemision con prefijo 23 y DV 9/4 segun sexo.
    Sirve como cota, no como verdad.
    """
    if r == 0:
        return 0
    if r == 1:
        return None
    return 11 - r


def medir(cuils, dv, posiciones):
    """Mide typos NO detectados.

    OJO con la base: solo se mutan CUIL que son VALIDOS bajo la regla que se
    esta midiendo. Un typo parte de un dato bueno. Mutar un CUIL que ya era
    invalido y que por casualidad caiga en valido no es un typo no detectado:
    es basura que se volvio valida, que es otro fenomeno. Medir sobre los 200
    sin filtrar fue el error que dio el falso 0,93%.
    """
    base = [c for c in cuils
            if dv(resto(c)) is not None and str(dv(resto(c))) == c[10]]
    sobreviven = total = 0
    for d in base:
        for i in posiciones:
            for nuevo in "0123456789":
                if nuevo == d[i]:
                    continue
                total += 1
                m = d[:i] + nuevo + d[i + 1:]
                esperado = dv(resto(m))
                if esperado is not None and str(esperado) == m[10]:
                    sobreviven += 1
    return sobreviven, total, len(base)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--columna", default="cuil")
    args = ap.parse_args()

    with open(args.csv, newline="", encoding="utf-8-sig") as fh:
        cuils = [re.sub(r"\D", "", f[args.columna]) for f in csv.DictReader(fh)]
    cuils = [c for c in cuils if len(c) == 11]

    print(f"\n  CUILs analizados: {len(cuils)}\n")
    print(f"  {'regla':<14} {'posiciones':<24} {'base':<9} {'no detectados':>18}")
    print("  " + "-" * 72)
    for nombre_pos, posiciones in (
        ("0-9 (todas)", range(0, 10)),
        ("2-9 (sin prefijo)", range(2, 10)),
    ):
        for nombre_dv, dv in (("simplificada", dv_simplificado), ("estricta", dv_estricto)):
            s, t, b = medir(cuils, dv, posiciones)
            print(f"  {nombre_dv:<14} {nombre_pos:<24} base={b:<4} {s:>5}/{t:<6} {100*s/t:>6.2f}%")
    print()


if __name__ == "__main__":
    main()
