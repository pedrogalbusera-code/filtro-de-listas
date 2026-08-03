"""Registro de pendientes conocidos — hallazgos adversarios del 2026-07-28.

Cada entrada declara el comportamiento correcto esperado y el comportamiento
actual medido. El verificador (v09_pendientes.py) compara contra actual_medido:
si el pipeline empieza a comportarse distinto, la suite se pone roja.

Formato Python para poder importarlo directamente desde el verificador.

Los valores de actual_medido se obtuvieron corriendo leads_adversario_1.csv
por el pipeline F08 con fecha de corte 2026-07-28 el dia 2026-07-30.

Actualizacion 2026-07-31 (CORRECCION-F01): se sacaron T01-T05 y T10 (6 de
telefono, todos corregidos). Se actualizo T31 (dedup) porque la correccion
de T01 cambio el camino de dedup: T01 ahora tiene telefono valido, lo que
hace que T31 se deduplique por transitividad en vez de por CUIL directo.

Actualizacion 2026-08-02 (CORRECCION-F04): se sacaron T19 y T21, los dos de
localidad, porque ahora dan el resultado correcto y estan verificados por
v04_cobertura.py con esperados escritos a mano:

  T19 'Moron (Buenos Aires)' -> en_zona TRUE (el nucleo de la localidad se
      compara sin el parentesis final ni el sufijo ', provincia').
  T21 localidad vacia -> motivo 'sin localidad', NO 'fuera de zona', y NO se
      descarta: sin localidad es marca, no descarte.

Queda UNO: T31. Un pendiente que se arregla se saca de aca; si se quedara,
el registro pasaria a mentir en la direccion contraria (reportar como
pendiente algo que ya funciona).
"""

PENDIENTES = [
    {
        "id": "T31",
        "categoria": "dedup",
        "entrada": "mismo CUIL que T01 (20-31445902-5), otro telefono (1168442753)",
        "esperado_correcto": "dedup por CUIL correcto, pero el telefono valido del perdedor deberia poder recuperarse",
        "actual_medido": {
            "es_duplicado": "TRUE",
            "duplicado_de": "28",
            "motivo_duplicado": "transitivo",
            "telefono_norm": "+541168442753",
        },
        "importa": "El perdedor tenia un telefono utilizable que se pierde. El diseno actual no transfiere datos del perdedor al ganador.",
    },
]
