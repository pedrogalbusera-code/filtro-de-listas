#!/usr/bin/env python3
"""v_procesar.py — verifica herramientas/procesar.py corriendolo DE VERDAD
(subprocess, como lo haria un usuario). Tres casos:

  1. CANONICO: procesar.py sobre leads_prueba_SINTETICO_1.csv (corte 2026-07-28)
     -> comercial y auditoria byte a byte identicos a los GOLDEN. Si pasa,
     procesar.py es el MISMO pipeline y no una copia que va a divergir.
  2. FUEGO: procesar.py sobre leads_fuego_1.csv con el mapeo/baja/segmentacion
     fuego y la misma fecha que v_fuego -> byte a byte contra la salida que
     produce la corrida de v_fuego (comercial + auditoria + reporte). La
     referencia se genera reusando v_fuego.correr(), no una copia del runner.
  3. RECHAZO: el .txt de prosa -> exit != 0, el motivo aparece en la salida, y
     NO quedo escrita ninguna salida a medias (comercial/auditoria).
"""
import hashlib
import os
import shutil
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "verificadores"))
import v_fuego  # reusa correr() como referencia del caso fuego (mismo runner)

PROC = os.path.join(BASE, "herramientas", "procesar.py")
DATA = os.path.join(BASE, "data")
SAL = os.path.join(BASE, "salidas")
CONFIG = os.path.join(BASE, "config")
GOLDEN_COM = os.path.join(SAL, "golden_2026-07-28.csv")
GOLDEN_AUD = os.path.join(SAL, "golden_2026-07-28_auditoria.csv")
CANONICO = os.path.join(DATA, "leads_prueba_SINTETICO_1.csv")
FUEGO = os.path.join(DATA, "leads_fuego_1.csv")
PROSA = os.path.join(DATA, "leads_adversario_5_prosa.txt")
SCRATCH = os.path.join(SAL, "_vproc")
FECHA = "2026-07-28"

ok = 0
fail = 0


def check(nombre, cond, detalle=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASA  {nombre}")
    else:
        fail += 1
        print(f"  FALLA {nombre}" + (f": {detalle}" if detalle else ""))


def sha(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def correr_procesar(archivo, extra=None):
    """Corre procesar.py como un usuario. Devuelve (CompletedProcess, stem)."""
    stem = os.path.splitext(os.path.basename(archivo))[0]
    cmd = [sys.executable, PROC, archivo, "--fecha-corte", FECHA, "--salida-dir", SCRATCH]
    if extra:
        cmd += extra
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r, stem


def out_paths(stem):
    return (os.path.join(SCRATCH, f"{stem}_comercial.csv"),
            os.path.join(SCRATCH, f"{stem}_auditoria.csv"),
            os.path.join(SCRATCH, f"{stem}_reporte.md"))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("=" * 70)
    print("v_procesar.py — procesar.py corrido de verdad (canonico / fuego / rechazo)")
    print("=" * 70)

    if os.path.exists(SCRATCH):
        shutil.rmtree(SCRATCH)
    os.makedirs(SCRATCH, exist_ok=True)

    # ==================================================================
    print("\n--- Caso 1: canonico -> byte a byte contra el golden ---")
    r, stem = correr_procesar(CANONICO)
    check("(canonico) procesar.py termina con exito", r.returncode == 0,
          (r.stderr or r.stdout or "")[-300:])
    check("(canonico) imprime la fecha de corte (regla 6: nada de fechas escondidas)",
          FECHA in (r.stdout or ""))
    com, aud, rep = out_paths(stem)
    check("(canonico) comercial byte a byte identico al golden",
          sha(com) is not None and sha(com) == sha(GOLDEN_COM),
          "procesar.py no es el mismo pipeline que el canonico")
    check("(canonico) auditoria byte a byte identica al golden",
          sha(aud) is not None and sha(aud) == sha(GOLDEN_AUD),
          "procesar.py no es el mismo pipeline que el canonico")

    # ==================================================================
    print("\n--- Caso 2: fuego -> byte a byte contra la corrida de v_fuego ---")
    # Referencia: la MISMA corrida que hace v_fuego (reusa su correr(), no una copia).
    ref = v_fuego.correr(v_fuego.SUCIO, "procref")
    check("(fuego) la referencia de v_fuego corrio bien", ref["exito"])
    r, stem = correr_procesar(FUEGO, extra=[
        "--mapeo", os.path.join(CONFIG, "mapeo_fuego.json"),
        "--baja", os.path.join(DATA, "lista_baja_fuego.xlsx"),
        "--segmentacion", os.path.join(CONFIG, "segmentacion_fuego.json")])
    check("(fuego) procesar.py termina con exito", r.returncode == 0,
          (r.stderr or r.stdout or "")[-300:])
    com, aud, rep = out_paths(stem)
    check("(fuego) comercial byte a byte igual a la corrida de v_fuego",
          sha(com) is not None and sha(com) == sha(ref["com"]))
    check("(fuego) auditoria byte a byte igual a la corrida de v_fuego",
          sha(aud) is not None and sha(aud) == sha(ref["aud"]))
    check("(fuego) reporte byte a byte igual a la corrida de v_fuego",
          sha(rep) is not None and sha(rep) == sha(ref["rep"]))
    check("(fuego) el resumen final imprime el numero del reporte",
          "El numero" in (r.stdout or "") and "ahorradas" in (r.stdout or ""))

    # ==================================================================
    print("\n--- Caso 3: prosa -> rechazo legible, sin salida a medias ---")
    r, stem = correr_procesar(PROSA)
    com, aud, rep = out_paths(stem)
    check("(rechazo) procesar.py sale con exit != 0", r.returncode != 0,
          f"returncode={r.returncode}")
    salida = (r.stdout or "") + (r.stderr or "")
    check("(rechazo) el motivo del rechazo aparece en la salida (no un stacktrace)",
          "RECHAZ" in salida.upper(),
          (salida.strip().splitlines() or ["(vacio)"])[-1])
    check("(rechazo) NO se escribio comercial a medias", not os.path.exists(com),
          "quedo un comercial de un archivo rechazado")
    check("(rechazo) NO se escribio auditoria a medias", not os.path.exists(aud))

    # Limpieza del scratch (todo lo de este verificador es transitorio).
    if os.path.exists(SCRATCH):
        shutil.rmtree(SCRATCH)

    print("\n" + "=" * 70)
    total = ok + fail
    if fail == 0:
        print(f"RESULTADO: PASA ({total} checks)")
        sys.exit(0)
    print(f"RESULTADO: FALLA ({fail} de {total} checks)")
    sys.exit(1)


if __name__ == "__main__":
    main()
