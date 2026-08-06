#!/usr/bin/env python3
"""Genera los dos gemelos de la PRUEBA DE FUEGO desde una fuente unica.

  data/leads_fuego_1.csv        el SUCIO, como lo manda un cliente:
                                separador ';', 2 filas de basura arriba del
                                encabezado, columnas con nombres de cliente,
                                encoding Latin-1 (Excel en espanol).

  data/leads_fuego_1_limpio.csv el GEMELO limpio, forma canonica:
                                separador ',', UTF-8 sin BOM, encabezado en la
                                fila 1, nombres de columna canonicos.

La UNICA diferencia entre los dos es la superficie que la puerta (F11) tiene que
neutralizar. Los valores de celda son IDENTICOS: por eso la salida del pipeline
tiene que dar byte a byte lo mismo con los dos (criterio 1 de la fase). Como los
dos salen de la MISMA lista de filas, no pueden divergir en un valor por error.

Las filas firma G01-G15 (una capacidad ganada con sangre cada una) estan
documentadas en fases/PRUEBA-DE-FUEGO.md. El resto son filas limpias de relleno
para que parezca una lista de verdad (~25 filas).

Sin dependencias: biblioteca estandar.
"""
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")

# Columnas canonicas, en orden.
CANONICAS = ["nombre", "cuil", "telefono", "localidad", "origen", "fecha_carga"]

# Nombres del cliente para el archivo sucio. 'Documento' y 'Origen del Contacto'
# NO estan en config/sinonimos.json a proposito: obligan a usar mapeo_fuego.json.
CLIENTE = {
    "nombre": "Nombre y Apellido",
    "cuil": "Documento",
    "telefono": "Celular",
    "localidad": "Zona",
    "origen": "Origen del Contacto",
    "fecha_carga": "Fecha de Alta",
}

# Digito verificador de CUIL (modulo 11). Se usa para que las filas callables
# tengan CUIL valido (+15) y el puntaje sea predecible. resto 1 -> se descarta
# el DNI y se prueba el siguiente (misma regla que F02).
PESOS = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]


def cuil(prefijo, dni):
    d = int(dni)
    while True:
        base = f"{prefijo}{d:08d}"
        s = sum(int(base[i]) * PESOS[i] for i in range(10))
        r = s % 11
        if r != 1:
            dv = 0 if r == 0 else 11 - r
            return f"{prefijo}-{d:08d}-{dv}"
        d += 1


F = "2026-07-20"   # fresco (8 dias del corte 2026-07-28 -> frescura alta)
V = "2026-07-05"   # viejo, para el perdedor de la dedup (gana el mas reciente)

# CUIL compartido por el par de duplicados-por-CUIL (G09 y su perdedor).
# DNIs espaciados por 10 para que el bump de resto-1 nunca colisione con el vecino.
CUIL_G09 = cuil("20", 30110090)

# (nombre, cuil, telefono, localidad, origen, fecha_carga)
# El orden importa: es identico en los dos archivos.
FILAS = [
    ("G01 Lead Alto Valor",        cuil("20", 30110010), "+54 9 11 3011 2233", "Castelar",              "referido", F),
    ("G02 Celular 15 Sin 0",       cuil("27", 30110020), "11 15 6161 7956",    "Haedo",                 "referido", F),
    ("G03 Celular 9 Separado",     cuil("20", 30110030), "+54 9 11 4161 7956", "Morón",            "referido", F),
    ("G04 Quince Sin Area",        cuil("20", 30110040), "15-4161-7956",       "Castelar",              "referido", F),
    ("G05 Dos Telefonos",          cuil("20", 30110050), "1146669999 / 1155667788", "Hurlingham",       "referido", F),
    ("G06 Artefacto Excel",        cuil("20", 30110060), "1.14162E+09",        "Ituzaingó",        "referido", F),
    ("G07 Telefono Relleno",       cuil("20", 30110070), "1111111111",         "Ramos Mejía",      "referido", F),
    ("test",                       cuil("20", 30110080), "+54 9 11 4777 8888", "San Justo",             "referido", F),
    ("G09 Ganador Fresco",         CUIL_G09,             "+54 9 11 4888 9999", "Villa Luzuriaga",       "referido", F),
    ("G09b Perdedor Viejo",        CUIL_G09,             "011 4999-0000",      "Castelar",              "referido", V),
    ("G10 Ganador Fresco",         cuil("20", 30110100), "11 3392-7555",       "Haedo",                 "referido", F),
    ("G10b Perdedor Viejo",        cuil("20", 30110110), "011 3392-7555",      "Morón",            "referido", V),
    ("G11 Localidad Con Parentesis", cuil("20", 30110120), "+54 9 11 5011 1222", "Morón (Buenos Aires)", "referido", F),
    ("G12 Sin Localidad",          cuil("20", 30110130), "011 4444-5555",      "",                      "referido", F),
    ("G13 Fuera De Zona",          cuil("20", 30110140), "+54 9 11 5111 2223", "Moreno",                "referido", F),
    ("G14 Persona Juridica",       "30-71234567-1",      "+54 9 11 5222 3334", "Castelar",              "referido", F),
    ("G15 Opt Out",                cuil("20", 30110150), "11 4242-4242",       "Castelar",              "referido", F),
    ("Relleno Uno",                cuil("20", 30220010), "+54 9 11 6000 0001", "Castelar",              "referido", F),
    ("Relleno Dos",                cuil("27", 30220020), "+54 9 11 6000 0002", "Haedo",                 "referido", F),
    ("Relleno Tres",               cuil("20", 30220030), "+54 9 11 6000 0003", "Morón",            "referido", F),
    ("Relleno Cuatro",             cuil("20", 30220040), "+54 9 11 6000 0004", "Hurlingham",            "referido", F),
    ("Relleno Cinco",              cuil("20", 30220050), "+54 9 11 6000 0005", "Ituzaingó",        "referido", F),
    ("Relleno Seis",               cuil("20", 30220060), "+54 9 11 6000 0006", "Ramos Mejía",      "referido", F),
    ("Relleno Siete",              cuil("20", 30220070), "+54 9 11 6000 0007", "San Justo",             "referido", F),
    ("Relleno Ocho",               cuil("20", 30220080), "+54 9 11 6000 0008", "Villa Luzuriaga",       "referido", F),
]

# Basura arriba del encabezado (solo en el sucio). Una sola columna: no vota en
# la deteccion de separador (regla del 80% de F11) y se saltea y reporta.
BASURA_ARRIBA = [
    "Listado de contactos - Exportado del CRM del cliente",
    "Fecha de exportación: 28/07/2026",
]


def _fila_valores(f):
    return list(f)  # ya viene en orden canonico


def escribir_sucio(path):
    """';' + Latin-1 + basura arriba + nombres de cliente. Ningun valor tiene
    ';' ni ',' ni comillas, asi que no hace falta escapar nada."""
    lineas = []
    lineas.extend(BASURA_ARRIBA)
    lineas.append(";".join(CLIENTE[c] for c in CANONICAS))
    for f in FILAS:
        lineas.append(";".join(_fila_valores(f)))
    texto = "\r\n".join(lineas) + "\r\n"
    with open(path, "wb") as fh:
        fh.write(texto.encode("latin-1"))


def escribir_limpio(path):
    """',' + UTF-8 sin BOM + encabezado en la fila 1 + nombres canonicos."""
    lineas = []
    lineas.append(",".join(CANONICAS))
    for f in FILAS:
        lineas.append(",".join(_fila_valores(f)))
    texto = "\n".join(lineas) + "\n"
    with open(path, "wb") as fh:
        fh.write(texto.encode("utf-8"))


def main():
    # Chequeo de invariante: ningun valor lleva separador o comilla (si no, los
    # dos archivos necesitarian escapes distintos y dejarian de ser gemelos).
    for f in FILAS:
        for v in _fila_valores(f):
            assert ";" not in v and "," not in v and '"' not in v and "\n" not in v, \
                f"valor con separador/comilla rompe la equivalencia: {v!r}"
    # Los CUIL tienen que ser unicos salvo el par de duplicados-por-CUIL (G09/G09b):
    # un CUIL repetido de mas crearia una dedup que rompe el conteo del reporte.
    cuils = [f[1] for f in FILAS]
    repetidos = sorted({c for c in cuils if cuils.count(c) > 1})
    assert repetidos == [CUIL_G09], f"CUIL duplicado inesperado: {repetidos} (solo se permite {CUIL_G09})"
    sucio = os.path.join(DATA, "leads_fuego_1.csv")
    limpio = os.path.join(DATA, "leads_fuego_1_limpio.csv")
    escribir_sucio(sucio)
    escribir_limpio(limpio)
    print("escrito:", sucio, f"({len(FILAS)} filas + {len(BASURA_ARRIBA)} de basura + header)")
    print("escrito:", limpio, f"({len(FILAS)} filas + header)")


if __name__ == "__main__":
    main()
