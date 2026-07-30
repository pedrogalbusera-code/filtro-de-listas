"""Registro de pendientes conocidos — hallazgos adversarios del 2026-07-28.

Cada entrada declara el comportamiento correcto esperado y el comportamiento
actual medido. El verificador (v09_pendientes.py) compara contra actual_medido:
si el pipeline empieza a comportarse distinto, la suite se pone roja.

Formato Python para poder importarlo directamente desde el verificador.

Los valores de actual_medido se obtuvieron corriendo leads_adversario_1.csv
por el pipeline F08 con fecha de corte 2026-07-28 el dia 2026-07-30.
"""

PENDIENTES = [
    {
        "id": "T01",
        "categoria": "telefono",
        "entrada": "+54 11 4161-7956",
        "esperado_correcto": "fijo (formato internacional sin el 9)",
        "actual_medido": {
            "telefono_tipo": "invalido",
            "telefono_norm": "",
        },
        "importa": "Falso invalido: un fijo en formato internacional cae invalido porque tiene 12 digitos y no matchea ningun patron.",
    },
    {
        "id": "T02",
        "categoria": "telefono",
        "entrada": "+54 9 11 4161 7956",
        "esperado_correcto": "celular (el 9 separado por espacios)",
        "actual_medido": {
            "telefono_tipo": "invalido",
            "telefono_norm": "",
        },
        "importa": "El hallazgo mas grave: un espacio entre +54 y 9 pierde un celular valido. startsWith('+549') falla por el espacio.",
    },
    {
        "id": "T03",
        "categoria": "telefono",
        "entrada": "549 11 4161 7956",
        "esperado_correcto": "celular (internacional sin el +)",
        "actual_medido": {
            "telefono_tipo": "invalido",
            "telefono_norm": "",
        },
        "importa": "Falso invalido: 13 digitos sin + al inicio no matchea ningun patron.",
    },
    {
        "id": "T04",
        "categoria": "telefono",
        "entrada": "011 15 4161-7956",
        "esperado_correcto": "celular (formato viejo con 15)",
        "actual_medido": {
            "telefono_tipo": "invalido",
            "telefono_norm": "",
        },
        "importa": "Formato muy comun en Argentina. 13 digitos empezando con 0, no matchea el patron de fijo (11 dig).",
    },
    {
        "id": "T05",
        "categoria": "telefono",
        "entrada": "15-4161-7956",
        "esperado_correcto": "invalido (15 sin codigo de area, no se puede resolver)",
        "actual_medido": {
            "telefono_tipo": "ambiguo",
            "telefono_norm": "+541541617956",
        },
        "importa": "Peor que un falso invalido: acepta como ambiguo un numero que no se puede resolver. El contacto suma 18 puntos y puede ser llamado a un numero equivocado.",
    },
    {
        "id": "T10",
        "categoria": "telefono",
        "entrada": "1141617956 / 1165385561",
        "esperado_correcto": "dos telefonos validos (separados por /)",
        "actual_medido": {
            "telefono_tipo": "invalido",
            "telefono_norm": "",
        },
        "importa": "Se pierden dos numeros buenos. La barra y los digitos extras dan >10 digitos.",
    },
    {
        "id": "T19",
        "categoria": "localidad",
        "entrada": "Morón (Buenos Aires)",
        "esperado_correcto": "en zona (es Moron, la aclaracion entre parentesis no deberia afectar)",
        "actual_medido": {
            "en_zona": "FALSE",
            "motivo_descarte": "fuera de zona de cobertura",
        },
        "importa": "Una aclaracion entre parentesis descarta un contacto valido. La comparacion de localidad es demasiado literal.",
    },
    {
        "id": "T21",
        "categoria": "localidad",
        "entrada": "",
        "esperado_correcto": "indeterminado, distinguido de 'fuera de zona'",
        "actual_medido": {
            "en_zona": "FALSE",
            "motivo_descarte": "fuera de zona de cobertura",
        },
        "importa": "'No se donde vive' y 'se que vive lejos' quedan indistinguibles. El contacto se descarta sin haber preguntado.",
    },
    {
        "id": "T31",
        "categoria": "dedup",
        "entrada": "mismo CUIL que T01 (20-31445902-5), otro telefono (1168442753)",
        "esperado_correcto": "dedup por CUIL correcto, pero el telefono valido del perdedor deberia poder recuperarse",
        "actual_medido": {
            "es_duplicado": "TRUE",
            "duplicado_de": "26",
            "motivo_duplicado": "cuil",
            "telefono_norm": "+541168442753",
        },
        "importa": "El perdedor tenia un telefono utilizable que se pierde. El diseno actual no transfiere datos del perdedor al ganador.",
    },
]
