#!/usr/bin/env python3
"""Genera data/lista_baja_1.xlsx — la lista de baja de F14 en formato planilla.

Mismo criterio que gen_xlsx_adversario4.py: sin openpyxl, zipfile + XML de la
biblioteca estandar, para que el repo siga sin dependencias externas.

QUE PRUEBA ESTE ARCHIVO: que una lista de baja en Excel da EXACTAMENTE el mismo
veredicto de opt-out que la misma lista en CSV. Un opt-out de un cliente real
llega en Excel tan seguido como en CSV, y si el formato cambiara el resultado,
el filtro no serviria para el caso mas probable.

Trae las MISMAS 7 filas que data/lista_baja_1.csv, pero:
  - las columnas se llaman distinto ('Celular' y 'CUIT' en vez de
    'Telefono de contacto' y 'CUIL/CUIT'), para que el mapeo por
    config/sinonimos.json tenga que resolverlas de verdad;
  - hay una columna de mas ('Observaciones') que no mapea a nada y tiene que
    ignorarse sin romper nada.

LO QUE NO TRAE, y es a proposito: basura arriba del encabezado. En planilla la
fila 1 ES el encabezado (limitacion heredada de F11, documentada en leerPlanilla
y en fases/F14). Un titulo arriba haria que ese titulo sea el encabezado. En
texto si se saltea y se reporta.
"""
import os
import zipfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(BASE, "data", "lista_baja_1.xlsx")

# (valor, es_numero). Las mismas 7 filas de lista_baja_1.csv, en el mismo
# orden, con los telefonos escritos IGUAL (el formato distinto respecto de la
# lista principal es lo que prueba el cruce por canonico).
FILAS = [
    [("Celular", False), ("CUIT", False), ("Observaciones", False)],
    [("011 4161-7956", False), ("", False), ("pidio la baja por telefono", False)],
    [("+54 9 11 6161 7956", False), ("", False), ("no llamar mas", False)],
    [("", False), ("27-35110489-4", False), ("baja por mail", False)],
    [("s/d", False), ("", False), ("el operador no anoto el numero", False)],
    [("", False), ("20-4412233", False), ("documento incompleto en el registro", False)],
    [("011 4242-4242", False), ("20-31445901-7", False), ("baja con los dos datos", False)],
    [("11 9999-0000", False), ("", False), ("no esta en la lista principal", False)],
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
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def col_letra(i):
    return chr(ord("A") + i)


def celda(fila_num, col_idx, valor, es_numero):
    ref = f"{col_letra(col_idx)}{fila_num}"
    if es_numero:
        return f'<c r="{ref}"><v>{valor}</v></c>'
    if valor == "":
        # Celda vacia: se omite. Asi llega como campo ausente, que es lo que
        # produce Excel de verdad, y el nodo tiene que tratarlo como vacio.
        return ""
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
