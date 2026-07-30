#!/usr/bin/env python3
"""Verificador F03 - Deduplicacion.

Comprueba que el workflow 04-dedup marca duplicados por CUIL y por telefono
normalizado, elige un unico ganador por grupo y NO borra ninguna fila.

Red de seguridad:
  1. ORACULO independiente (mismo union-find + misma regla de ganador, en
     Python) comparado fila por fila contra n8n: id_fila, es_duplicado,
     duplicado_de y motivo_duplicado. Si coinciden en las 200, el nodo hace lo
     que dice el oraculo.
  2. Conteos duros del CSV, calculados directo de las columnas: 14 por CUIL, 8
     por telefono_norm (no vacio), 6 por telefono crudo entre utilizables, 11
     filas identicas, y la union (14). El 8-vs-6 es la prueba de que F01 sirve.
  3. Las dos trampas caras, explicitas: agrupar por crudo (daria 6/48) y
     agrupar los invalidos con telefono_norm vacio (daria un grupo gigante).
  4. Invariantes de estructura: duplicado_de apunta a un id que existe y que NO
     es duplicado (sin cadenas), un solo ganador por grupo, 200 filas.
  5. La regla de ganador (fecha -> completitud -> posicion) NO la ejercita la
     muestra (los 14 pares empatan y se deciden por posicion), asi que se
     unit-testea con casos sinteticos.

Uso:
    python verificadores/v03_dedup.py
    python verificadores/v03_dedup.py --salida Y.csv

Exit code 0 si pasa, 1 si falla.
"""
import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "salidas" / "salida_f03.csv"

ORIG = ["nombre", "cuil", "telefono", "localidad", "origen", "fecha_carga"]
PREC = {"celular": 3, "fijo": 2, "ambiguo": 1, "invalido": 0, "": 0}

# Conteos medidos sobre el CSV de prueba. No se ajustan para que pase.
ESP_CUIL = 14
ESP_TEL_NORM = 8
ESP_TEL_CRUDO = 6      # entre utilizables (telefono_norm no vacio)
ESP_IDENTICAS = 11
ESP_UNION = 14         # los 8 pares por telefono estan contenidos en los 14 por CUIL

resultados = []


def check(nombre, ok, detalle=""):
    resultados.append((nombre, ok, detalle))
    return ok


# ---------------------------------------------------------------------------
# ORACULO: misma logica que el nodo Code, en Python.
# ---------------------------------------------------------------------------

def completo(fila):
    return sum(1 for c in ORIG if str(fila.get(c, "")).strip() != "")


def match_tel(norm):
    d = re.sub(r"\D", "", str(norm or ""))
    return d[-10:] if len(d) >= 10 else ""


def dedup_oraculo(filas):
    """Devuelve lista {id_fila, es_duplicado, duplicado_de, motivo, telefono_tipo}.

    telefono_tipo es el ADOPTADO (el ganador toma el mas especifico de su linea);
    para el resto es el de F01. Match de telefono por ultimos 10 digitos.
    """
    n = len(filas)
    match = [match_tel(f.get("telefono_norm", "")) for f in filas]
    padre = list(range(n))

    def find(x):
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x

    def unir(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            padre[ra] = rb

    def agrupar(valores):
        m = defaultdict(list)
        for i, v in enumerate(valores):
            v = str(v).strip()
            if v == "":
                continue
            m[v].append(i)
        for idxs in m.values():
            for j in idxs[1:]:
                unir(idxs[0], j)

    agrupar([f.get("cuil_norm", "") for f in filas])
    agrupar(match)

    comp = defaultdict(list)
    for i in range(n):
        comp[find(i)].append(i)

    out = [
        {"id_fila": i + 1, "es_duplicado": False, "duplicado_de": "", "motivo": "",
         "telefono_tipo": filas[i].get("telefono_tipo", "")}
        for i in range(n)
    ]

    for idxs in comp.values():
        if len(idxs) < 2:
            continue
        # ganador: fecha mas reciente, luego mas completo, luego id_fila menor
        def clave(i):
            return (str(filas[i].get("fecha_carga", "")), completo(filas[i]), -(i + 1))
        g = max(idxs, key=clave)
        id_g = g + 1
        cuil_g = str(filas[g].get("cuil_norm", "")).strip()
        match_g = match[g]

        # adopcion de tipo: el mas especifico en la misma linea del ganador
        if match_g != "":
            mejor = filas[g].get("telefono_tipo", "")
            for i in idxs:
                if match[i] != match_g:
                    continue
                t = filas[i].get("telefono_tipo", "")
                if PREC.get(t, 0) > PREC.get(mejor, 0):
                    mejor = t
            out[g]["telefono_tipo"] = mejor

        for i in idxs:
            if i == g:
                continue
            motivos = []
            if cuil_g != "" and str(filas[i].get("cuil_norm", "")).strip() == cuil_g:
                motivos.append("cuil")
            if match_g != "" and match[i] == match_g:
                motivos.append("telefono")
            out[i]["es_duplicado"] = True
            out[i]["duplicado_de"] = id_g
            out[i]["motivo"] = "+".join(motivos) if motivos else "transitivo"
    return out


def extra_grupos(pares):
    g = defaultdict(list)
    for i, k in pares:
        g[k].append(i)
    return sum(len(v) - 1 for v in g.values() if len(v) > 1)


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
    for c in ["telefono_match", "id_fila", "es_duplicado", "duplicado_de", "motivo_duplicado"]:
        check(f"existe la columna {c}", c in cols)

    # telefono_match = ultimos 10 digitos de telefono_norm; vacio si norm vacio
    match_mal = []
    for f in filas:
        esp = match_tel(f["telefono_norm"])
        if f["telefono_match"] != esp:
            match_mal.append(f"id {f['id_fila']}: {f['telefono_match']!r} != {esp!r}")
    check(
        "telefono_match son los ultimos 10 digitos nacionales (vacio si invalido)",
        not match_mal,
        f"{len(match_mal)} mal; primero: {match_mal[0] if match_mal else ''}",
    )
    # los invalidos (norm vacio) tienen match vacio y no agrupan
    inval_con_match = [f["id_fila"] for f in filas if f["telefono_norm"].strip() == "" and f["telefono_match"].strip() != ""]
    check("los invalidos (telefono_norm vacio) tienen telefono_match vacio", not inval_con_match, f"ids: {inval_con_match[:5]}")

    # id_fila: 1..200, unico, y == posicion (el orden original sobrevivio)
    ids = [f["id_fila"] for f in filas]
    check(
        "id_fila es 1..200, unico y en orden de archivo",
        ids == [str(i + 1) for i in range(len(filas))],
        f"primeros: {ids[:3]} ... ultimos: {ids[-3:]}",
    )

    # --- Conteos independientes desde las columnas ---
    c_cuil = extra_grupos([(i, f["cuil_norm"]) for i, f in enumerate(filas)])
    c_tel_match = extra_grupos([(i, f["telefono_match"]) for i, f in enumerate(filas) if f["telefono_match"].strip() != ""])
    c_tel_crudo = extra_grupos([(i, f["telefono"]) for i, f in enumerate(filas) if f["telefono_norm"].strip() != ""])
    c_ident = extra_grupos([(i, tuple(f[c] for c in ORIG)) for i, f in enumerate(filas)])
    check(f"{ESP_CUIL} duplicados por CUIL", c_cuil == ESP_CUIL, f"da {c_cuil}")
    check(f"{ESP_TEL_NORM} duplicados por telefono_match (no 6)", c_tel_match == ESP_TEL_NORM, f"da {c_tel_match}")
    check(f"{ESP_TEL_CRUDO} duplicados por telefono crudo entre utilizables", c_tel_crudo == ESP_TEL_CRUDO, f"da {c_tel_crudo}")
    check(
        "los 2 extra (8 vs 6) aparecen solo al normalizar: F01 sirve",
        c_tel_match - c_tel_crudo == 2,
        f"diferencia {c_tel_match - c_tel_crudo}",
    )
    check(f"{ESP_IDENTICAS} filas completamente identicas", c_ident == ESP_IDENTICAS, f"da {c_ident}")

    # --- Union: es_duplicado total ---
    total_dup = sum(1 for f in filas if es_true(f["es_duplicado"]))
    check(f"la union da {ESP_UNION} duplicados (es_duplicado=TRUE)", total_dup == ESP_UNION, f"da {total_dup}")

    # --- Trampa 1: agrupar por crudo daria otra cosa (48 extra con los 'sindato') ---
    c_crudo_todo = extra_grupos([(i, f["telefono"]) for i, f in enumerate(filas)])
    check(
        "agrupar por telefono crudo SOBRE TODO daria 48 (invalidos de texto juntos): no es lo que pasa",
        c_crudo_todo == 48 and total_dup != c_crudo_todo,
        f"crudo-todo={c_crudo_todo}, union={total_dup}",
    )
    # --- Trampa 2: agrupar telefono_match incluyendo vacios daria el grupo gigante ---
    # Los 82 invalidos comparten match vacio: agruparlos daria 81 extra + 8 = 89.
    c_match_con_vacios = extra_grupos([(i, f["telefono_match"]) for i, f in enumerate(filas)])
    check(
        "agrupar por telefono_match incluyendo vacios daria 89 (invalidos juntos): el nodo NO lo hace",
        c_match_con_vacios == 89 and total_dup != c_match_con_vacios,
        f"con-vacios={c_match_con_vacios}, union={total_dup}",
    )
    # Ningun duplicado por telefono tiene telefono_match vacio (criterio 3)
    tel_vacio_agrupado = [
        f["id_fila"] for f in filas
        if es_true(f["es_duplicado"]) and "telefono" in f["motivo_duplicado"] and f["telefono_match"].strip() == ""
    ]
    check(
        "ningun grupo por telefono contiene telefono_match vacio",
        not tel_vacio_agrupado,
        f"ids: {tel_vacio_agrupado[:5]}",
    )
    # motivo 'telefono' aparece exactamente en los 8 phone-dupes -> el nodo USA la clave de match
    con_motivo_tel = sum(1 for f in filas if es_true(f["es_duplicado"]) and "telefono" in f["motivo_duplicado"])
    check(
        "exactamente 8 duplicados tienen 'telefono' en el motivo (el nodo usa telefono_match, no el crudo)",
        con_motivo_tel == ESP_TEL_NORM,
        f"da {con_motivo_tel}",
    )

    # --- ORACULO vs n8n, fila por fila ---
    ora = dedup_oraculo(filas)
    difs = []
    for i, (f, o) in enumerate(zip(filas, ora), 1):
        n8n = (
            f["id_fila"],
            es_true(f["es_duplicado"]),
            str(f["duplicado_de"]).strip(),
            f["motivo_duplicado"].strip(),
            f["telefono_tipo"],
        )
        esp = (
            str(o["id_fila"]),
            o["es_duplicado"],
            str(o["duplicado_de"]) if o["duplicado_de"] != "" else "",
            o["motivo"],
            o["telefono_tipo"],
        )
        if n8n != esp:
            difs.append(f"fila {i}: n8n={n8n} oraculo={esp}")
    check(
        "n8n coincide con el oraculo en las 200 filas (id, es_duplicado, duplicado_de, motivo, tipo)",
        not difs,
        f"{len(difs)} difs; primera: {difs[0] if difs else ''}",
    )

    # --- Criterio 4: duplicado_de referencia un id que existe y NO es duplicado ---
    por_id = {f["id_fila"]: f for f in filas}
    malos_ref = []
    for f in filas:
        if not es_true(f["es_duplicado"]):
            continue
        dd = str(f["duplicado_de"]).strip()
        if dd not in por_id:
            malos_ref.append(f"{f['id_fila']} -> {dd} (no existe)")
        elif es_true(por_id[dd]["es_duplicado"]):
            malos_ref.append(f"{f['id_fila']} -> {dd} (que tambien es duplicado: cadena)")
    check(
        "cada duplicado_de apunta a un id existente y no-duplicado (sin cadenas A->B->C)",
        not malos_ref,
        f"{len(malos_ref)} malos; primero: {malos_ref[0] if malos_ref else ''}",
    )

    # --- Criterio 5: un solo ganador por grupo ---
    # Reconstruyo grupos por ganador referenciado; el ganador no puede ser dup.
    grupos = defaultdict(list)
    for f in filas:
        if es_true(f["es_duplicado"]):
            grupos[str(f["duplicado_de"]).strip()].append(f["id_fila"])
    dos_ganadores = [g for g in grupos if es_true(por_id[g]["es_duplicado"])]
    check(
        "ningun grupo tiene dos ganadores (el ganador nunca es es_duplicado)",
        not dos_ganadores,
        f"ganadores marcados como dup: {dos_ganadores[:5]}",
    )

    # --- Unit tests de la regla de ganador (la muestra no la ejercita) ---
    def uno(fecha, comp_extra, cuil="20111111112", tel="+541100000000", tipo="fijo"):
        base = {"nombre": "x", "cuil": "c", "telefono": "t", "localidad": "l",
                "origen": "o", "fecha_carga": fecha, "cuil_norm": cuil,
                "telefono_norm": tel, "telefono_tipo": tipo}
        if not comp_extra:
            base["localidad"] = ""  # un campo menos completo
        return base

    # gana la fecha mas reciente
    g = dedup_oraculo([uno("2026-01-01", True), uno("2026-05-01", True)])
    check("ganador: gana la fecha_carga mas reciente",
          g[0]["es_duplicado"] and not g[1]["es_duplicado"] and g[0]["duplicado_de"] == 2)
    # fecha empata -> gana el mas completo
    g = dedup_oraculo([uno("2026-01-01", False), uno("2026-01-01", True)])
    check("ganador: con fecha empatada gana el mas completo",
          g[0]["es_duplicado"] and not g[1]["es_duplicado"] and g[0]["duplicado_de"] == 2)
    # fecha y completitud empatan -> gana el primero del archivo
    g = dedup_oraculo([uno("2026-01-01", True), uno("2026-01-01", True)])
    check("ganador: con todo empatado gana el primero del archivo",
          not g[0]["es_duplicado"] and g[1]["es_duplicado"] and g[1]["duplicado_de"] == 1)

    # --- Unit tests de adopcion de tipo (la muestra no la ejercita: 0 casos) ---
    # Mismo numero: uno pelado (ambiguo, +54..) y el mismo con +549 (celular).
    # Colapsan por telefono_match; el ganador adopta 'celular'.
    amb = uno("2026-05-01", True, cuil="", tel="+541139927555", tipo="ambiguo")   # gana por fecha
    cel = uno("2026-01-01", True, cuil="", tel="+5491139927555", tipo="celular")
    g = dedup_oraculo([amb, cel])
    check(
        "adopcion: celular y ambiguo del mismo numero colapsan (match por 10 digitos)",
        g[0]["es_duplicado"] != g[1]["es_duplicado"],
    )
    check(
        "adopcion: el ganador (ambiguo por fecha) adopta 'celular' de su linea",
        g[0]["telefono_tipo"] == "celular" and not g[0]["es_duplicado"],
        f"tipo ganador={g[0]['telefono_tipo']}",
    )
    # precedencia: fijo no pisa a celular
    f1 = uno("2026-05-01", True, cuil="", tel="+541141617956", tipo="fijo")
    c1 = uno("2026-01-01", True, cuil="", tel="+541141617956", tipo="celular")
    g = dedup_oraculo([f1, c1])
    check(
        "adopcion: precedencia celular > fijo (el ganador fijo adopta celular)",
        g[0]["telefono_tipo"] == "celular",
        f"tipo ganador={g[0]['telefono_tipo']}",
    )

    return reportar()


def reportar():
    ancho = max(len(n) for n, _, _ in resultados)
    print()
    print("  VERIFICADOR F03 - deduplicacion")
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
