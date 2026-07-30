#!/usr/bin/env python3
"""Genera los archivos de prueba ADVERSARIOS del Filtro de Listas.

A diferencia de leads_prueba_SINTETICO_1.csv, que fue construido para que el
pipeline lo limpie bien, estos archivos estan construidos para ROMPERLO.

Quien los escribio no vio la implementacion de F04 en adelante. Esa es la
gracia: un set de prueba escrito por el mismo que escribio el codigo solo
contiene los casos que el codigo ya maneja.

Salida:
    leads_adversario_1.csv   mismas 6 columnas, valores sucios (rompe reglas)
    leads_adversario_2.csv   otras columnas + basura arriba (rompe la lectura)
    leads_adversario_3.csv   separador punto y coma (Excel en espanol)

Ningun dato corresponde a una persona real. Los nombres arrancan con T## para
poder rastrear cada trampa en la salida sin agregar columnas al archivo.
"""
import csv
from pathlib import Path

PESOS = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
SALIDA = Path(__file__).resolve().parent


def dv(diez):
    """DV segun la regla que aplica hoy el proyecto (resto 1 -> 9)."""
    r = sum(int(a) * b for a, b in zip(diez, PESOS)) % 11
    return 0 if r == 0 else (9 if r == 1 else 11 - r)


def resto(diez):
    return sum(int(a) * b for a, b in zip(diez, PESOS)) % 11


def cuil(prefijo, dni, forzar_dv=None, formato="guiones"):
    diez = f"{prefijo}{dni}"
    d = forzar_dv if forzar_dv is not None else dv(diez)
    if formato == "guiones":
        return f"{prefijo}-{dni}-{d}"
    if formato == "pelado":
        return f"{prefijo}{dni}{d}"
    if formato == "puntos":
        return f"{prefijo}.{dni}.{d}"
    if formato == "espacios":
        return f"{prefijo} {dni} {d}"
    raise ValueError(formato)


def buscar_dni(prefijo, objetivo_resto, arranque=30000000):
    """Busca un DNI que produzca un resto dado. Para armar casos a medida."""
    for n in range(arranque, arranque + 200000):
        if resto(f"{prefijo}{n}") == objetivo_resto:
            return str(n)
    raise RuntimeError("no encontrado")


# --- Archivo 1: mismas columnas, valores sucios -----------------------------

F1 = [
    # nombre, cuil, telefono, localidad, origen, fecha_carga
    ("T01 Ana Ruiz",        cuil(20, "31445902"), "+54 11 4161-7956",   "Castelar",  "referido",       "2026-07-01"),
    ("T02 Bruno Paz",       cuil(27, "32118745"), "+54 9 11 4161 7956", "Haedo",     "formulario web", "2026-07-02"),
    ("T03 Celia Mota",      cuil(20, "33920014"), "549 11 4161 7956",   "Morón",     "evento",         "2026-07-03"),
    ("T04 Dario Sena",      cuil(24, "34501277"), "011 15 4161-7956",   "Hurlingham","campaña Meta",   "2026-07-04"),
    ("T05 Elsa Vidal",      cuil(27, "35110488"), "15-4161-7956",       "Ituzaingó", "base propia",    "2026-07-05"),
    ("T06 Fabio Luna",      cuil(20, "36002911"), "4161-7956",          "Ramos Mejía","referido",      "2026-07-06"),
    ("T07 Gina Roldán",     cuil(23, "37451200"), "(011) 4161-7956",    "San Justo", "evento",         "2026-07-07"),
    ("T08 Hugo Ferro",      cuil(20, "38112003"), "1141617956.0",       "Villa Luzuriaga","referido",  "2026-07-08"),
    ("T09 Ivan Costa",      cuil(24, "39220145"), "1.14162E+09",        "Castelar",  "campaña Meta",   "2026-07-09"),
    ("T10 Jana Ortiz",      cuil(27, "40330288"), "1141617956 / 1165385561","Haedo", "formulario web", "2026-07-10"),
    ("T11 Kevin Diaz",      cuil(20, "41007733"), "  1155551111  ",     "Morón",     "referido",       "2026-07-11"),
    ("T12 Lara Sosa",       cuil(27, "41880422"), "+549 11 5555-1111",  "Morón",     "evento",         "2026-07-12"),
    ("T13 Mateo Rey",       cuil(24, "42115509"), "011-45551111",       "Hurlingham","base propia",    "2026-07-13"),
    ("T14 Nadia Bravo",     cuil(23, "42998100"), "1145551111",         "Hurlingham","referido",       "2026-07-14"),
    ("T15 Omar Vega",       cuil(20, "43220017"), "1168442737",         "MORÓN",     "referido",       "2026-07-15"),
    ("T16 Pia Nuñez",       cuil(27, "43771902"), "1168442738",         "moron",     "evento",         "2026-07-16"),
    ("T17 Raul Gomez",      cuil(20, "44001255"), "1168442739",         " Haedo ",   "campaña Meta",   "2026-07-17"),
    ("T18 Sara Molina",     cuil(24, "44552388"), "1168442740",         "Ramos Mejia","referido",      "2026-07-18"),
    ("T19 Tomas Cruz",      cuil(20, "45110944"), "1168442741",         "Morón (Buenos Aires)","evento","2026-07-19"),
    ("T20 Uma Prieto",      cuil(27, "45880233"), "1168442742",         "Ciudad de Buenos Aires","referido","2026-07-20"),
    ("T21 Vito Alonso",     cuil(23, "46220188"), "1168442743",         "",          "base propia",    "2026-07-21"),
    ("T22 Wanda Rios",      cuil(20, "46991044"), "1168442744",         "Merlo",     "referido",       "2026-07-22"),
    ("T23 Xul Peralta",     "",                   "1168442745",         "Castelar",  "evento",         "2026-07-23"),
    ("T24 Yago Medina",     "20-4412233",         "1168442746",         "Haedo",     "referido",       "2026-07-24"),
    ("T25 Zoe Arce",        cuil(99, "44122335"), "1168442747",         "Morón",     "campaña Meta",   "2026-07-25"),
    ("T26 Abel Ponce",      cuil(20, "31445902", formato="pelado"),   "1168442748","Castelar","referido","2026-07-26"),
    ("T27 Bea Quiroga",     cuil(27, "32118745", formato="puntos"),   "1168442749","Haedo",   "evento",  "2026-07-27"),
    ("T28 Ciro Duarte",     cuil(24, "34501277", formato="espacios"), "1168442750","Morón",   "referido","2026-07-28"),
    ("T29 Dana Miranda",    cuil(20, "47220011", forzar_dv=0),        "1168442751","Castelar","evento",  "2026-07-28"),
    ("T30 Erik Salas",      cuil(30, "71234567"),                     "1168442752","Haedo",   "base propia","2026-06-30"),
    ("T31 Flor Cabrera",    cuil(20, "31445902"), "1168442753",       "Castelar",  "referido",       "2026-05-01"),
    ("T32 Gael Ibarra",     cuil(20, "48110022"), "1168442754",       "Morón",     "evento",         "10/04/2026"),
    ("T33 Hana Correa",     cuil(27, "48771033"), "1168442755",       "Haedo",     "referido",       "04/10/2026"),
    ("T34 Iker Ramos",      cuil(24, "49220144"), "1168442756",       "Castelar",  "campaña Meta",   "10-abr-26"),
    ("T35 Julia Naveiro",   cuil(20, "49881255"), "1168442757",       "Hurlingham","referido",       ""),
    ("T36 Kai Ledesma",     cuil(27, "50110366"), "1168442758",       "Ituzaingó", "evento",         "2026-13-45"),
    ("T37 Lena Ocampo",     cuil(20, "50772477"), "1168442759",       "Morón",     "referido",       "2027-01-15"),
    ("T38 Mara Zabala",     cuil(24, "51220588"), "1168442760",       "Haedo",     "base propia",    "2019-03-02"),
    ("",                    cuil(20, "51881699"), "1168442761",       "Castelar",  "referido",       "2026-07-20"),
    ("T40 PEREZ, JUAN",     cuil(27, "52110700"), "1168442762",       "Morón",     "evento",         "2026-07-21"),
    ("T41   Nora   Vera  ", cuil(20, "52772811"), "1168442763",       "Haedo",     "referido",       "2026-07-22"),
    ("T42 Ada Lovelace",    cuil(24, "53220922"), "1168442764",       "Castelar",  "campaña Meta",   "2026-07-23"),
    ("T42 Ada Lovelace ",   cuil(24, "53220922"), "1168442764",       "Castelar",  "campaña Meta",   "2026-07-23"),
    ("T44 Beto Silva",      cuil(20, "53881033"), "sin  dato",        "Merlo",     "referido",       "2026-07-24"),
    ("T45 Cora Iglesias",   cuil(27, "54110144"), "N/D",              "Moreno",    "evento",         "2026-07-25"),
    ("T46 Dante Ruiz",      cuil(20, "54772255"), "0",                "Castelar",  "referido",       "2026-07-26"),
]

# Caso a medida: resto 1 (cuil_dudoso) y "reemision femenina" 23-DNI-4.
_dni_resto1 = buscar_dni(20, 1)
F1.append(("T47 Eva Lopez",  cuil(20, _dni_resto1), "1168442765", "Haedo", "referido", "2026-07-27"))
# Reemision femenina real: se calcula con prefijo 27, da resto 1, y AFIP la
# emite como 23-DNI-4. Escrita asi, el validador actual la va a rechazar.
_dni27 = buscar_dni(27, 1, arranque=31000000)
F1.append(("T48 Fina Vera",  f"23-{_dni27}-4",      "1168442766", "Morón", "evento",   "2026-07-27"))


# --- Archivo 2: otras columnas y basura arriba -------------------------------

F2_BASURA = [
    ["LISTADO DE CONTACTOS - PLANILLA COMERCIAL"],
    ["Exportado el 26/07/2026 - Uso interno"],
    [],
]
F2_CABECERA = ["Nombre y Apellido", "Documento", "Celular", "Zona",
               "Origen del lead", "Fecha de alta", "Observaciones"]
F2 = [
    ["T50 Gonzalo Paz",  cuil(20, "31445902"), "11 6844-2800", "Castelar",  "Referido",  "26/07/2026", "llamar después de las 18, dijo que sí"],
    ["T51 Hilda Moran",  cuil(27, "32118745"), "1168442801",   "HAEDO",     "Web",       "25/07/2026", ""],
    ["T52 Ivo Sanchez",  "",              "1168442802",   "moron",     "Meta",      "24/07/2026", "no dejó documento"],
    [],
    ["T54 Jael Ferreyra",cuil(24, "34501277"), "",             "Hurlingham","Evento",    "23/07/2026", "sin teléfono, contactar por mail"],
    ["T55 Kira Domingo", cuil(20, "36002911"), "1168442804",   "Ituzaingó"],
    ["T56 Lucio Bianchi",cuil(20, "38112003"), "1168442805",   "Ramos Mejía","Referido", "22/07/2026", "cliente viejo, ya compró en 2024"],
    ["T57 Mia Ferrari",  cuil(27, "40330288", forzar_dv=1)  # invalido a proposito
     , "1168442806",   "San Justo", "Base propia","21/07/2026","preguntó por precios, urgente"],
]


# --- Archivo 3: separador punto y coma (Excel en espanol) --------------------

F3_CABECERA = ["nombre", "cuil", "telefono", "localidad", "origen", "fecha_carga"]
F3 = [
    ["T60 Nina Aguirre", cuil(20, "31445902"), "1168442900", "Castelar", "referido", "2026-07-20"],
    ["T61 Oscar Benitez",cuil(27, "32118745"), "1168442901", "Haedo",    "evento",   "2026-07-21"],
    ["T62 Pilar Cano",   cuil(24, "34501277"), "1168442902", "Morón",    "referido", "2026-07-22"],
    ["T63 Quimey Duran", cuil(20, "36002911"), "1168442903", "Moreno",   "web",      "2026-07-23"],
    ["T64 Rocio Esteban",cuil(20, "38112003"), "1168442904", "Merlo",    "referido", "2026-07-24"],
]


def escribir():
    p1 = SALIDA / "leads_adversario_1.csv"
    with open(p1, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["nombre", "cuil", "telefono", "localidad", "origen", "fecha_carga"])
        w.writerows(F1)
    print(f"{p1.name}: {len(F1)} filas")

    p2 = SALIDA / "leads_adversario_2.csv"
    with open(p2, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerows(F2_BASURA)
        w.writerow(F2_CABECERA)
        w.writerows(F2)
    print(f"{p2.name}: {len(F2)} filas + 3 de basura + otra cabecera")

    p3 = SALIDA / "leads_adversario_3.csv"
    with open(p3, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(F3_CABECERA)
        w.writerows(F3)
    print(f"{p3.name}: {len(F3)} filas, separador ';'")

    print(f"\nDNI con resto 1 usado en T47: {_dni_resto1}")
    print(f"DNI usado en T48 (calculado con 27, escrito como 23-DNI-4): {_dni27}")


if __name__ == "__main__":
    escribir()
