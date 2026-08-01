#!/usr/bin/env python3
"""Genera data/leads_adversario_4.xlsx — el caso de planilla de F11.

Sin openpyxl a proposito: un .xlsx es un zip con XMLs adentro, y para una
planilla de 5 filas la biblioteca estandar alcanza. Asi el repo sigue sin
dependencias externas (misma regla que los verificadores).

La trampa del archivo (criterio 4 de F11): el telefono de la fila T71 esta
guardado como NUMERO, no como texto. Es la trampa clasica de Excel: si el
operador tipea 01141617956, Excel lo convierte a numero y el cero inicial
desaparece. El pipeline tiene que leer el archivo y marcar ESE telefono como
invalido con motivo de artefacto de Excel, sin romper las otras filas.

Los strings van como inlineStr (sin sharedStrings.xml): menos partes, y el
parser de n8n (SheetJS) los lee igual.
"""
import os
import zipfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(BASE, "data", "leads_adversario_4.xlsx")

# (valor, es_numero). Encabezados canonicos: el criterio 4 no ejercita el
# mapeo de columnas, ejercita la lectura de planilla y la celda numerica.
FILAS = [
    [("nombre", False), ("cuil", False), ("telefono", False),
     ("localidad", False), ("origen", False), ("fecha_carga", False)],
    [("T70 Ana Suarez", False), ("20-31445902-5", False), ("011-4161-7956", False),
     ("Castelar", False), ("referido", False), ("2026-07-20", False)],
    # La trampa: telefono como numero. 1141617956 podria ser un fijo que
    # perdio el 0 inicial o un ambiguo legitimo: no se puede saber.
    [("T71 Bruno Diaz", False), ("27-32118745-0", False), (1141617956, True),
     ("Haedo", False), ("evento", False), ("2026-07-21", False)],
    [("T72 Carla Ruiz", False), ("24-34501277-6", False), ("+549 11 3992-7555", False),
     ("Moreno", False), ("web", False), ("2026-07-22", False)],
    [("T73 Dario Vega", False), ("20-36002911-6", False), ("1168442737", False),
     ("Morón", False), ("referido", False), ("2026-07-23", False)],
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
<sheets><sheet name="Hoja1" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""

WORKBOOK_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""


def esc_xml(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def col_letra(i):
    # 0 -> A ... alcanza hasta Z para 6 columnas.
    return chr(ord("A") + i)


def celda(fila_num, col_idx, valor, es_numero):
    ref = f"{col_letra(col_idx)}{fila_num}"
    if es_numero:
        return f'<c r="{ref}"><v>{valor}</v></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t>{esc_xml(valor)}</t></is></c>'


def sheet_xml():
    filas_xml = []
    for i, fila in enumerate(FILAS, start=1):
        celdas = "".join(celda(i, j, v, n) for j, (v, n) in enumerate(fila))
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
