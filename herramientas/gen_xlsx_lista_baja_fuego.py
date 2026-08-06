#!/usr/bin/env python3
"""Genera data/lista_baja_fuego.xlsx — la lista de baja (opt-out) de la PRUEBA
DE FUEGO, en planilla.

Va en .xlsx a proposito: ejercita el path de planilla (extractFromFile +
leerPlanilla) de punta a punta. El principal es el que lleva basura arriba y va
en CSV; la baja NO lleva basura (en planilla la fila 1 ES el encabezado,
limitacion heredada de F11).

Trae el opt-out de G15 escrito en OTRO formato que la lista principal
('011 4242-4242' contra '11 4242-4242'): el cruce corre sobre el canonico, no
sobre el string. Columnas renombradas ('Celular', 'CUIT') + una columna de mas
('Observaciones') para que el mapeo por config/sinonimos.json las resuelva de
verdad. Una fila que no esta en la principal ('11 9999-0000') se ignora sin
romper.

Sin openpyxl: zipfile + XML de la biblioteca estandar (mismo criterio que
gen_xlsx_lista_baja.py), el repo sigue sin dependencias.
"""
import os
import zipfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(BASE, "data", "lista_baja_fuego.xlsx")

# (Celular, CUIT, Observaciones). Fila 1 = encabezado.
FILAS = [
    ("Celular", "CUIT", "Observaciones"),
    ("011 4242-4242", "", "pidio la baja por telefono (es G15)"),
    ("11 9999-0000", "", "no esta en la lista principal: se ignora sin error"),
]

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

WORKBOOK = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="Bajas" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""

WORKBOOK_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""


def esc_xml(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def col_letra(i):
    return chr(ord("A") + i)


def celda(fila_num, col_idx, valor):
    ref = f"{col_letra(col_idx)}{fila_num}"
    if valor == "":
        return ""  # celda ausente = vacia (lo que produce Excel de verdad)
    return f'<c r="{ref}" t="inlineStr"><is><t>{esc_xml(valor)}</t></is></c>'


def sheet_xml():
    filas_xml = []
    for i, fila in enumerate(FILAS, start=1):
        celdas = "".join(celda(i, j, v) for j, v in enumerate(fila))
        filas_xml.append(f'<row r="{i}">{celdas}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(filas_xml)}</sheetData></worksheet>'
    )


def main():
    with zipfile.ZipFile(DESTINO, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("xl/workbook.xml", WORKBOOK)
        z.writestr("xl/_rels/workbook.xml.rels", WORKBOOK_RELS)
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml())
    print("escrito:", DESTINO)


if __name__ == "__main__":
    main()
