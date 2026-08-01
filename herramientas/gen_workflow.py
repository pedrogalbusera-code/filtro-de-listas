#!/usr/bin/env python3
"""Genera los workflows de n8n del proyecto.

Existe para no editar JSON a mano: el mismo workflow se emite con rutas de
Windows (la maquina de Pedro) y con rutas de Linux (para poder ejecutarlo y
validarlo automaticamente). Las rutas absolutas quedan embebidas; regenerar es
mas barato que buscar y reemplazar dentro del JSON.

Uso:
    # F00 - pasamanos (identico al que estaba versionado)
    python herramientas/gen_workflow.py workflows/01-pasamanos.json "<csv_in>" "<csv_out>"

    # F01 - normalizacion de telefono
    python herramientas/gen_workflow.py workflows/02-telefono.json "<csv_in>" "<csv_out>" --fase 01

El nodo Code de cada fase se agrega a la cadena; una fase = un nodo mas. El
pasamanos de F00 queda siempre como primer nodo Code (guardarrail de tipos).
"""
import argparse
import json
import os

# ---------------------------------------------------------------------------
# Codigo de los nodos Code, uno por responsabilidad.
# ---------------------------------------------------------------------------

JS_F00 = """// F00 - Pasamanos. Cero logica de negocio.
//
// Este nodo no arregla nada: es un guardarrail.
//
// COMPROBADO en n8n 2.31.7 (2026-07-27): el nodo "Extract From File" ya
// entrega los 6 campos como string. Los 45 telefonos con cero inicial y los
// CUILs con guiones sobreviven sin este nodo. O sea: HOY es redundante.
//
// Se deja igual por dos motivos. Primero, deja el punto de entrada listo para
// F01, que necesita un Code node justo aca. Segundo, si una version futura de
// n8n cambia el parseo, el verificador v00 lo detecta y este nodo es donde se
// arregla. Un guardarrail que no cuesta nada se deja puesto.

const COLUMNAS = ['nombre', 'cuil', 'telefono', 'localidad', 'origen', 'fecha_carga'];

return items.map((item) => {
  const fila = {};
  for (const col of COLUMNAS) {
    const v = item.json[col];
    fila[col] = (v === undefined || v === null) ? '' : String(v);
  }
  // F11: la puerta de entrada puede agregar columnas del archivo del cliente
  // (extra_*) y advertencias de lectura (advertencia_entrada). Se dejan pasar
  // hasta la auditoria. Con el CSV canonico estas claves no existen, asi que
  // este bloque no cambia ni un byte de la salida de F00-F08 (golden intacto).
  // Lo interno de la puerta (_ficha, _rechazo) NO pasa: muere aca.
  for (const [k, v] of Object.entries(item.json)) {
    if (k.indexOf('extra_') === 0 || k === 'advertencia_entrada') {
      fila[k] = (v === undefined || v === null) ? '' : String(v);
    }
  }
  return { json: fila };
});
"""

JS_F01 = """// F01 - Normalizacion de telefono.
//
// Deriva dos campos nuevos por contacto: telefono_norm (canonico) y
// telefono_tipo. El campo 'telefono' original NO se toca.
//
// Canonico (siempre con prefijo +54; el 9 aparece SOLO en celular):
//   celular   +549 + 10 digitos nacionales   <- el 9 distingue celular de fijo
//   fijo      +54  + 10 digitos nacionales
//   ambiguo   +54  + 10 digitos nacionales   <- 10 digitos pelados, sin afirmar movil
//   invalido  ''
//
// El 9 de +549 es lo unico que separa un celular de un fijo en AMBA. Si el
// canonico lo descartara, un fijo y un celular con los mismos 8 digitos finales
// colisionarian y F03 los fusionaria mal. Por eso el celular conserva el 9:
//   celular +5491139927555  vs  fijo +541139927555  -> distintos.
//
// El tipo se infiere del FORMATO DE ENTRADA, no del canonico ya recortado.
// Los 10 digitos sin prefijo son ambiguos de verdad (fijo o celular): NO se
// adivina, se marcan 'ambiguo' y en F06 llevan puntaje intermedio.
// Nada se completa: un truncado de 6 digitos es invalido, no se rellena.
//
// Funcion pura: mismo input -> mismo output, sin estado externo.

function normalizarTelefono(raw) {
  const s = (raw === undefined || raw === null) ? '' : String(raw).trim();

  // Notacion cientifica (dano de Excel) -> invalido. Va antes del filtro de
  // letras porque la E del exponente dispararia esa regla.
  if (/^\\d+\\.\\d+[eE]\\+\\d+$/.test(s)) {
    return { telefono_norm: '', telefono_tipo: 'invalido' };
  }

  // Texto ("sin dato" / "sindato" / "N/D") -> invalido.
  if (/[a-zA-Z]/.test(s)) {
    return { telefono_norm: '', telefono_tipo: 'invalido' };
  }

  // Dos telefonos separados por '/': se toma el primero.
  let input = s;
  if (s.indexOf('/') >= 0) {
    input = s.split('/')[0].trim();
  }

  // Sacar espacios internos antes de clasificar (causa raiz de T01-T04).
  const limpio = input.replace(/\\s+/g, '');
  const digitos = limpio.replace(/\\D/g, '');

  if (digitos.length === 0) {
    return { telefono_norm: '', telefono_tipo: 'invalido' };
  }

  // +549... -> celular (el 9 puede estar pegado o separado por espacios).
  if (limpio.startsWith('+549')) {
    const nac = digitos.slice(3);
    if (nac.length === 10) return { telefono_norm: '+549' + nac, telefono_tipo: 'celular' };
    return { telefono_norm: '', telefono_tipo: 'invalido' };
  }

  // +54 sin 9 -> fijo (formato internacional sin indicador de celular).
  if (limpio.startsWith('+54')) {
    const nac = digitos.slice(2);
    if (nac.length === 10) return { telefono_norm: '+54' + nac, telefono_tipo: 'fijo' };
    return { telefono_norm: '', telefono_tipo: 'invalido' };
  }

  // 549... sin el '+' -> celular (13 digitos).
  if (digitos.startsWith('549') && digitos.length === 13) {
    const nac = digitos.slice(3);
    return { telefono_norm: '+549' + nac, telefono_tipo: 'celular' };
  }

  // 0XX 15 XXXX-XXXX -> celular (formato viejo argentino con 15).
  // Estructura: 0 + area(2-4 dig) + 15 + abonado(8 dig) = 13-15 digitos.
  if (digitos[0] === '0' && digitos.length >= 13 && digitos.length <= 15) {
    for (let areaLen = 2; areaLen <= 4; areaLen++) {
      const area = digitos.slice(1, 1 + areaLen);
      const resto = digitos.slice(1 + areaLen);
      if (resto.startsWith('15') && resto.length === 10) {
        const abonado = resto.slice(2);
        return { telefono_norm: '+549' + area + abonado, telefono_tipo: 'celular' };
      }
    }
  }

  // Fijo: 11 digitos con 0 inicial (011-... o 011... sin guion). Nacional = sin el 0.
  if (digitos.length === 11 && digitos[0] === '0') {
    return { telefono_norm: '+54' + digitos.slice(1), telefono_tipo: 'fijo' };
  }

  // 15-XXXX-XXXX sin codigo de area -> invalido. No se adivina el area.
  if (digitos.startsWith('15') && digitos.length === 10) {
    return { telefono_norm: '', telefono_tipo: 'invalido' };
  }

  // Ambiguo: exactamente 10 digitos sin prefijo. Puede ser fijo o celular.
  if (digitos.length === 10 && !limpio.startsWith('+')) {
    return { telefono_norm: '+54' + digitos, telefono_tipo: 'ambiguo' };
  }

  // Todo lo demas (truncado de 6, largos raros) -> invalido. No se completa.
  return { telefono_norm: '', telefono_tipo: 'invalido' };
}

return items.map((item) => {
  const fila = { ...item.json };
  const r = normalizarTelefono(fila.telefono);
  fila.telefono_norm = r.telefono_norm;
  fila.telefono_tipo = r.telefono_tipo;
  return { json: fila };
});
"""

JS_F02 = """// F02 - Validacion de CUIL (formato + digito verificador modulo 11).
//
// Deriva cuil_norm (11 digitos como string, sin guiones, sin perder ceros) y
// cuil_valido (booleano). El campo 'cuil' original NO se toca.
//
// Modulo 11: pesos 5 4 3 2 7 6 5 4 3 2 sobre los primeros 10 digitos.
//   suma de productos, resto = suma % 11
//   resto 0 -> DV 0
//   resto 1 -> INVALIDO   (ver abajo)
//   si no   -> DV = 11 - resto
//
// POR QUE resto 1 -> INVALIDO (decision de Pedro, correccion 2026-07-27):
// Bajo la regla de AFIP, un CUIL que da resto 1 CON SU PROPIO PREFIJO no puede
// existir: AFIP lo habria reemitido con prefijo 23. Y la reemision no es una
// excepcion al algoritmo, es consistente con el: cambiar el prefijo altera el
// digito que pesa 4 y el resto deja de ser 1. Verificado por fuerza bruta:
// 27272/27272 reemisiones femeninas (23-DNI-4) y 27273/27273 masculinas
// (23-DNI-9) validan con ESTE mismo algoritmo simple. O sea: los CUIL reemitidos
// pasan bien; no hay que modelar sexo ni prefijos. Aceptar resto 1 como DV 9
// solo crearia una colision (DV 9 sale de resto 1 y de resto 2) que debilita el
// verificador. Por eso resto 1 se rechaza.
//
// Prefijos validos: 20 23 24 27 (persona fisica); 30 33 34 (juridica).
// Formato correcto + DV incorrecto = INVALIDO. No hay estado intermedio.
// Funcion pura.

const PREFIJOS = new Set(['20', '23', '24', '27', '30', '33', '34']);
const PESOS = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2];

function validarCuil(raw) {
  const norm = (raw === undefined || raw === null ? '' : String(raw)).replace(/\\D/g, '');
  if (norm.length !== 11) return { cuil_norm: norm, cuil_valido: false, cuil_dudoso: false };
  if (!PREFIJOS.has(norm.slice(0, 2))) return { cuil_norm: norm, cuil_valido: false, cuil_dudoso: false };

  let suma = 0;
  for (let i = 0; i < 10; i++) suma += Number(norm[i]) * PESOS[i];
  const resto = suma % 11;

  // cuil_dudoso: el CUIL da resto 1 con su propio prefijo -> RECHAZADO. AFIP lo
  // habria reemitido con prefijo 23. Se marca para que el rechazo sea auditable.
  if (resto === 1) {
    return { cuil_norm: norm, cuil_valido: false, cuil_dudoso: true };
  }

  const dv = resto === 0 ? 0 : 11 - resto;
  return { cuil_norm: norm, cuil_valido: dv === Number(norm[10]), cuil_dudoso: false };
}

return items.map((item) => {
  const fila = { ...item.json };
  const r = validarCuil(fila.cuil);
  fila.cuil_norm = r.cuil_norm;
  fila.cuil_valido = r.cuil_valido;
  fila.cuil_dudoso = r.cuil_dudoso;
  return { json: fila };
});
"""


JS_F03 = """// F03 - Deduplicacion. NADA se borra: un duplicado es una etiqueta, no un delete.
//
// id_fila estable (posicion original, 1-based). Deriva telefono_match,
// es_duplicado, duplicado_de, motivo_duplicado. F01 (telefono_norm) y F02 no se
// recalculan; solo el telefono_tipo del GANADOR puede adoptar un tipo mas
// especifico de su linea (ver ADOPCION abajo).
//
// CLAVE DE MATCH (decision de Pedro, ver ESTADO): se agrupa por los ULTIMOS 10
// DIGITOS NACIONALES -> telefono_match, ignorando el 9 del celular. En AMBA un
// mismo 11-XXXX-XXXX es una sola linea; el 9 indica el TIPO, no la identidad.
// Asi un celular (+549...) y el mismo numero escrito pelado (ambiguo) colapsan.
// Los invalidos tienen telefono_norm vacio -> telefono_match vacio -> NO agrupan
// entre si (el bug mas caro de la fase seria un grupo falso de 82).
//
// Identidad: misma fila si comparten cuil_norm (no vacio) O telefono_match (no
// vacio). union-find -> UN ganador por componente, sin cadenas A->B->C.
//
// Ganador (regla 3): fecha_carga mas reciente; si empata, mas campos ORIGINALES
// completos; si empata, primero del archivo (id_fila menor). Reproducible.
//
// ADOPCION DE TIPO: el ganador adopta el telefono_tipo mas especifico presente
// en su MISMA linea (mismo telefono_match), precedencia celular > fijo > ambiguo.
// Si el ganador vino 'ambiguo' pero otro de su linea era 'celular', queda
// 'celular'. El telefono original queda intacto: el tipo por-fila de F01 siempre
// se puede recomputar.

const ORIG = ['nombre', 'cuil', 'telefono', 'localidad', 'origen', 'fecha_carga'];
const PREC = { celular: 3, fijo: 2, ambiguo: 1, invalido: 0, '': 0 };

function matchTel(norm) {
  const d = String(norm === undefined || norm === null ? '' : norm).replace(/\\D/g, '');
  return d.length >= 10 ? d.slice(-10) : '';
}

const filas = items.map((item, i) => {
  const json = Object.assign({}, item.json);
  json.telefono_match = matchTel(json.telefono_norm);
  return { json: json, i: i, id_fila: i + 1 };
});

// --- union-find ---
const padre = filas.map((_, i) => i);
function find(x) { while (padre[x] !== x) { padre[x] = padre[padre[x]]; x = padre[x]; } return x; }
function unir(a, b) { const ra = find(a), rb = find(b); if (ra !== rb) padre[ra] = rb; }

function agrupar(campo) {
  const m = new Map();
  filas.forEach((f) => {
    const v = String(f.json[campo] === undefined || f.json[campo] === null ? '' : f.json[campo]).trim();
    if (v === '') return;                 // vacio no agrupa
    if (!m.has(v)) m.set(v, []);
    m.get(v).push(f.i);
  });
  m.forEach((idxs) => { for (let k = 1; k < idxs.length; k++) unir(idxs[0], idxs[k]); });
}
agrupar('cuil_norm');
agrupar('telefono_match');

// --- componentes ---
const comp = new Map();
filas.forEach((f) => { const r = find(f.i); if (!comp.has(r)) comp.set(r, []); comp.get(r).push(f.i); });

function completo(json) {
  return ORIG.reduce((n, c) => n + (String(json[c] === undefined || json[c] === null ? '' : json[c]).trim() !== '' ? 1 : 0), 0);
}

function ganador(idxs) {
  return idxs.reduce((best, i) => {
    const a = filas[i].json, b = filas[best].json;
    const fa = String(a.fecha_carga || ''), fb = String(b.fecha_carga || '');
    if (fa !== fb) return fa > fb ? i : best;          // ISO YYYY-MM-DD: lexicografico = cronologico
    const ca = completo(a), cb = completo(b);
    if (ca !== cb) return ca > cb ? i : best;
    return filas[i].id_fila < filas[best].id_fila ? i : best;
  }, idxs[0]);
}

// --- marcar (sin reordenar: el orden original tiene que sobrevivir) ---
const salida = filas.map((f) => ({
  json: Object.assign({}, f.json, {
    id_fila: f.id_fila, es_duplicado: false, duplicado_de: '', motivo_duplicado: '',
  }),
}));

comp.forEach((idxs) => {
  if (idxs.length < 2) return;
  const g = ganador(idxs);
  const idGanador = filas[g].id_fila;
  const cuilG = String(filas[g].json.cuil_norm || '').trim();
  const matchG = String(filas[g].json.telefono_match || '').trim();

  // ADOPCION de tipo: el mas especifico en la misma linea del ganador.
  if (matchG !== '') {
    let mejor = filas[g].json.telefono_tipo || '';
    idxs.forEach((i) => {
      if (String(filas[i].json.telefono_match || '').trim() !== matchG) return;
      const t = filas[i].json.telefono_tipo || '';
      if ((PREC[t] || 0) > (PREC[mejor] || 0)) mejor = t;
    });
    salida[g].json.telefono_tipo = mejor;
  }

  idxs.forEach((i) => {
    if (i === g) return;
    const motivos = [];
    if (cuilG !== '' && String(filas[i].json.cuil_norm || '').trim() === cuilG) motivos.push('cuil');
    if (matchG !== '' && String(filas[i].json.telefono_match || '').trim() === matchG) motivos.push('telefono');
    salida[i].json.es_duplicado = true;
    salida[i].json.duplicado_de = idGanador;
    salida[i].json.motivo_duplicado = motivos.length ? motivos.join('+') : 'transitivo';
  });
});

return salida;
"""


JS_F04 = """// F04 - Completitud y cobertura.
//
// Marca contactos no llamables por dato y contactos fuera de la zona de
// cobertura. Cada marca deja un MOTIVO en castellano legible (lo lee un
// supervisor de call center, no un dev). Un contacto acumula TODOS sus motivos.
//
// CONFIG es el PARAMETRO del workflow: el unico lugar donde se cambia la zona.
// La zona de hoy es un ESCENARIO DE DEMO, no un cliente real (ver ESTADO). El
// proximo cliente cambia esta lista y NO se toca la logica de abajo.

const CONFIG = {
  // Localidades EN ZONA (cobertura). Se comparan normalizadas: sin tildes,
  // minusculas, sin espacios de mas. 'Moron', 'moron' y 'MORON' son la misma.
  zona: [
    'Castelar', 'Haedo', 'Moron', 'Hurlingham', 'Ituzaingo', 'Ramos Mejia',
    'Villa Luzuriaga', 'San Justo',
  ],
};

function normLoc(s) {
  return String(s === undefined || s === null ? '' : s)
    .normalize('NFD').replace(/[\\u0300-\\u036f]/g, '')   // saca tildes/diacriticos
    .toLowerCase().trim().replace(/\\s+/g, ' ');
}

const zonaSet = new Set(CONFIG.zona.map(normLoc));

return items.map((item) => {
  const json = Object.assign({}, item.json);
  const motivos = [];

  // Datos insuficientes (hecho del archivo).
  if (json.telefono_tipo === 'invalido') motivos.push('sin teléfono utilizable');
  const nombre = String(json.nombre === undefined || json.nombre === null ? '' : json.nombre).trim();
  if (nombre === '') motivos.push('sin nombre');

  // Fuera de cobertura (suposicion nuestra: la zona). Separado a proposito.
  const enZona = zonaSet.has(normLoc(json.localidad));
  if (!enZona) motivos.push('fuera de zona de cobertura');

  json.en_zona = enZona;
  json.marcado = motivos.length > 0;
  json.motivo_descarte = motivos.join('; ');
  return { json: json };
});
"""


JS_F05 = """// F05 - Antiguedad del lead.
//
// Deriva dias_antiguedad, frescura, motivo_frescura, fecha_corte_usada.
//
// CONFIG.fecha_corte: si viene vacio, se usa la fecha del dia (new Date() SOLO
// para fijar el default en CONFIG, NUNCA dentro de la logica de calculo). La
// fecha efectiva se escribe en fecha_corte_usada para que el CSV sea auditable
// sin saber que dia se genero.
//
// Formatos aceptados para fecha_carga:
//   aaaa-mm-dd   (ISO)
//   dd/mm/aaaa   (dia primero, Argentina)
// Se marca 'fecha ambigua' cuando ambos componentes del dd/mm son <= 12 (la
// lectura inversa tambien seria fecha valida). No se adivinan meses en texto ni
// anos de 2 digitos: todo lo demas es 'fecha ilegible'.
//
// Tramos:
//   0 a 15 dias  -> alta
//   16 a 45 dias -> media
//   46 a 90 dias -> baja
//   mas de 90    -> fria
//   no parseable / futuro -> sin dato
//
// Todas las fechas se construyen con Date.UTC para evitar un bug de DST:
// new Date(y, m-1, d) usa hora local, y si el tramo cruza un cambio de horario
// (en otra zona; Argentina no tiene DST desde 2009) Math.floor pierde una hora
// y un contacto salta de tramo. Date.UTC elimina el problema.
//
// dias_antiguedad: el numero real de dias (puede ser negativo para fechas
// futuras). Vacio si la fecha no se puede parsear (nunca -1: un -1 seria "mas
// fresco que 0 dias" para cualquier aritmetica aguas abajo).
//
// Funcion pura.

const CONFIG = {
  fecha_corte: '__FECHA_CORTE__',
};

const _corte_str = CONFIG.fecha_corte || new Date().toISOString().slice(0, 10);

function parseFechaUTC(s) {
  const t = String(s === undefined || s === null ? '' : s).trim();
  if (t === '') return { fecha: null, motivos: ['fecha vacia'] };

  let y, m, d;
  let ambigua = false;

  const iso = /^(\\d{4})-(\\d{2})-(\\d{2})$/.exec(t);
  if (iso) {
    y = Number(iso[1]); m = Number(iso[2]); d = Number(iso[3]);
  } else {
    const dmy = /^(\\d{2})\\/(\\d{2})\\/(\\d{4})$/.exec(t);
    if (dmy) {
      d = Number(dmy[1]); m = Number(dmy[2]); y = Number(dmy[3]);
      if (d <= 12 && m <= 12) ambigua = true;
    } else {
      return { fecha: null, motivos: ['fecha ilegible'] };
    }
  }

  const dt = new Date(Date.UTC(y, m - 1, d));
  if (dt.getUTCFullYear() !== y || dt.getUTCMonth() !== m - 1 || dt.getUTCDate() !== d) {
    return { fecha: null, motivos: ['fecha ilegible'] };
  }

  const motivos = [];
  if (ambigua) motivos.push('fecha ambigua');
  return { fecha: dt, motivos: motivos };
}

const _corteR = parseFechaUTC(_corte_str);
if (!_corteR.fecha) throw new Error('CONFIG.fecha_corte invalida: ' + _corte_str);
const corte = _corteR.fecha;

function tramo(dias) {
  if (dias <= 15) return 'alta';
  if (dias <= 45) return 'media';
  if (dias <= 90) return 'baja';
  return 'fria';
}

return items.map((item) => {
  const json = Object.assign({}, item.json);
  const r = parseFechaUTC(json.fecha_carga);

  json.fecha_corte_usada = _corte_str;

  if (r.fecha === null) {
    json.dias_antiguedad = '';
    json.frescura = 'sin dato';
    json.motivo_frescura = r.motivos.join('; ');
  } else {
    const diff = Math.floor((corte - r.fecha) / 86400000);
    json.dias_antiguedad = diff;

    const motivos = r.motivos.slice();
    if (diff < 0) {
      motivos.push('fecha futura');
      json.frescura = 'sin dato';
    } else {
      json.frescura = tramo(diff);
    }
    json.motivo_frescura = motivos.join('; ');
  }

  return { json: json };
});
"""


JS_F06 = """// F06 - Puntaje explicable.
//
// Asigna puntaje, prioridad y motivo a cada contacto. Cada regla deja su
// contribucion en el motivo; sumar los puntos del motivo da exactamente el
// puntaje. Es la prueba de que el score se puede auditar.
//
// Descartes directos: telefono invalido, fuera de zona, duplicado.
// Fuerzan prioridad = descartado independientemente del puntaje numerico.
//
// CONFIG es el unico lugar donde viven los pesos y umbrales. Cambiar la
// estrategia comercial no requiere tocar la logica de abajo.
// Funcion pura.

const CONFIG = {
  pesos: {
    telefono: { celular: 30, fijo: 10, ambiguo: 18 },
    cuil: { valido: 15, invalido: -10 },
    zona: 20,
    frescura: { alta: 25, media: 15, baja: 5, fria: 0, 'sin dato': 0 },
    origen: {
      referido: 15,
      'formulario web': 10,
      evento: 10,
      'campaña Meta': 5,
      'base propia': 0,
    },
  },
  umbrales: { alta: 70, media: 40 },
};

function fmt(n) {
  return n >= 0 ? '+' + n : String(n);
}

function toBool(v) {
  if (typeof v === 'boolean') return v;
  return String(v === undefined || v === null ? '' : v).trim().toUpperCase() === 'TRUE';
}

return items.map((item) => {
  const json = Object.assign({}, item.json);
  let score = 0;
  const partes = [];
  let descarte = false;

  // 1. Telefono
  const tipo = String(json.telefono_tipo || '').trim();
  if (CONFIG.pesos.telefono.hasOwnProperty(tipo)) {
    const pts = CONFIG.pesos.telefono[tipo];
    score += pts;
    partes.push(tipo + ' ' + fmt(pts));
  } else {
    partes.push('sin teléfono ' + fmt(0) + ' \\u2192 descarte');
    descarte = true;
  }

  // 2. CUIL
  if (toBool(json.cuil_valido)) {
    score += CONFIG.pesos.cuil.valido;
    partes.push('cuil válido ' + fmt(CONFIG.pesos.cuil.valido));
  } else {
    score += CONFIG.pesos.cuil.invalido;
    partes.push('cuil inválido ' + fmt(CONFIG.pesos.cuil.invalido));
  }

  // 3. Zona
  if (toBool(json.en_zona)) {
    score += CONFIG.pesos.zona;
    partes.push('en zona ' + fmt(CONFIG.pesos.zona));
  } else {
    partes.push('fuera de zona ' + fmt(0) + ' \\u2192 descarte');
    descarte = true;
  }

  // 4. Frescura
  const fr = String(json.frescura || 'sin dato').trim();
  const fr_pts = CONFIG.pesos.frescura.hasOwnProperty(fr) ? CONFIG.pesos.frescura[fr] : 0;
  score += fr_pts;
  partes.push('frescura ' + fr + ' ' + fmt(fr_pts));

  // 5. Origen
  const orig = String(json.origen || '').trim();
  const orig_pts = CONFIG.pesos.origen.hasOwnProperty(orig) ? CONFIG.pesos.origen[orig] : 0;
  score += orig_pts;
  partes.push((orig || 'origen desconocido') + ' ' + fmt(orig_pts));

  // 6. Duplicado
  if (toBool(json.es_duplicado)) {
    partes.push('duplicado ' + fmt(0) + ' \\u2192 descarte');
    descarte = true;
  }

  // 7. Segmento no buscado (F12). La clave descarte_segmento SOLO existe si
  // config/segmentacion.json pide descartar un tipo de persona. Con el default
  // del repo (apagado) F12 no la escribe, este bloque no corre y el motivo no
  // cambia ni un caracter: por eso el golden de F09 no se mueve. El descarte
  // por segmento vive aca, con los otros descartes directos, para que toda la
  // decision de prioridad siga estando en un solo nodo.
  if (toBool(json.descarte_segmento)) {
    partes.push(String(json.motivo_segmento || 'segmento no buscado') + ' ' + fmt(0) + ' \\u2192 descarte');
    descarte = true;
  }

  // Prioridad
  let prioridad;
  if (descarte) prioridad = 'descartado';
  else if (score >= CONFIG.umbrales.alta) prioridad = 'alta';
  else if (score >= CONFIG.umbrales.media) prioridad = 'media';
  else prioridad = 'descartado';

  json.puntaje = score;
  json.prioridad = prioridad;
  json.motivo = partes.join('; ');
  return { json: json };
});
"""


JS_F12 = """// F12 - Persona fisica vs. juridica (filtro 8 del catalogo, Nivel 1).
//
// Deriva tipo_persona (fisica | juridica | desconocida) del PREFIJO de
// cuil_norm, que F02 ya calculo. No consulta ninguna fuente externa: sale
// gratis del dato que ya esta en la lista.
//
// CONFIG viene de config/segmentacion.json, embebido al GENERAR el workflow
// (mismo patron que el mapeo de F11: cambiar de cliente es editar un JSON y
// regenerar, nunca editar JavaScript).
//
// EL DEFAULT DEL REPO ESTA APAGADO: {etiquetar:false, descartar:null}. Con esa
// config este nodo devuelve los items TAL CUAL, sin agregar ni una clave. Por
// eso sumarlo al pipeline no mueve el golden de F09 ni un byte. La segmentacion
// es una decision comercial de UN cliente, no del producto.
//
// Cuatro reglas que no se negocian:
//   1. Se clasifica por PREFIJO, aunque el DV sea invalido. Una empresa
//      30-... con un typo en el digito verificador sigue siendo juridica.
//      'desconocida' es solo cuando NO HAY prefijo utilizable (sin CUIL, CUIL
//      corto, prefijo fuera del set). Que el DV falle es otra cosa: para eso
//      esta cuil_valido.
//   2. 'desconocida' NUNCA se descarta. No saber que es no es motivo para
//      tirarlo: seria el error de "sin dato = fuera" que F04 ya tiene medido
//      (T21). Solo se descarta el tipo EXPLICITO que pida la config.
//   3. Descartar = marcar con motivo legible, NUNCA borrar la fila (regla 4
//      del CLAUDE.md, regla 1 del catalogo).
//   4. tipo_persona no suma ni resta puntaje. El unico efecto sobre el score
//      es el descarte directo, y solo cuando la config lo pide. El puntaje de
//      una lista sin segmentar y el de la misma lista etiquetada son iguales.
//
// Funcion pura.

const CONFIG = __SEGMENTACION_JSON__;

const FISICA = new Set(['20', '23', '24', '27']);
const JURIDICA = new Set(['30', '33', '34']);
const ETIQUETA = { fisica: 'persona física', juridica: 'persona jurídica' };

function tipoPersona(cuilNorm) {
  const d = String(cuilNorm === undefined || cuilNorm === null ? '' : cuilNorm).replace(/\\D/g, '');
  if (d.length !== 11) return 'desconocida';
  const pre = d.slice(0, 2);
  if (FISICA.has(pre)) return 'fisica';
  if (JURIDICA.has(pre)) return 'juridica';
  return 'desconocida';
}

const etiquetar = CONFIG.etiquetar === true;
// Solo estos dos valores descartan. Cualquier otra cosa (incluido
// 'desconocida') no descarta a nadie; el generador ademas la rechaza antes.
const descartar = (CONFIG.descartar === 'fisica' || CONFIG.descartar === 'juridica')
  ? CONFIG.descartar : null;

// Config apagada: el nodo es transparente. Ni una clave nueva, ni un byte.
if (!etiquetar && descartar === null) {
  return items;
}

return items.map((item) => {
  const json = Object.assign({}, item.json);
  const tipo = tipoPersona(json.cuil_norm);

  if (etiquetar) json.tipo_persona = tipo;

  if (descartar !== null && tipo === descartar) {
    json.descarte_segmento = true;
    json.motivo_segmento = ETIQUETA[tipo] + ' (segmento no buscado)';
  }
  return { json: json };
});
"""


JS_F07_SORT = """// F07 - Ordenamiento.
// Clave de 4 partes: bloque prioridad (alta > media > descartado), puntaje
// descendente, dias_antiguedad ascendente (vacios al final), id_fila.
// El sort de V8 (Node 18+) es estable; id_fila garantiza determinismo total.

const PRIORIDAD_ORDEN = { alta: 0, media: 1, descartado: 2 };

items.sort((a, b) => {
  const ja = a.json, jb = b.json;

  const pa = PRIORIDAD_ORDEN[ja.prioridad] !== undefined ? PRIORIDAD_ORDEN[ja.prioridad] : 2;
  const pb = PRIORIDAD_ORDEN[jb.prioridad] !== undefined ? PRIORIDAD_ORDEN[jb.prioridad] : 2;
  if (pa !== pb) return pa - pb;

  const sa = Number(ja.puntaje);
  const sb = Number(jb.puntaje);
  if (sa !== sb) return sb - sa;

  const daRaw = ja.dias_antiguedad;
  const dbRaw = jb.dias_antiguedad;
  const da = (daRaw === '' || daRaw === undefined || daRaw === null) ? Infinity : Number(daRaw);
  const db = (dbRaw === '' || dbRaw === undefined || dbRaw === null) ? Infinity : Number(dbRaw);
  if (da !== db) return da - db;

  return Number(ja.id_fila) - Number(jb.id_fila);
});

return items;
"""


JS_F07_COMERCIAL = """// F07 - Genera CSV comercial con BOM UTF-8.
// 9 columnas: 6 originales + puntaje, prioridad, motivo.
// Genera el CSV a mano para controlar BOM y line endings (\\n, no CRLF).

const COLS = ['nombre', 'cuil', 'telefono', 'localidad', 'origen', 'fecha_carga',
              'puntaje', 'prioridad', 'motivo'];

function esc(v) {
  if (typeof v === 'boolean') return v ? 'TRUE' : 'FALSE';
  const s = String(v === undefined || v === null ? '' : v);
  if (s.indexOf(',') >= 0 || s.indexOf('"') >= 0 || s.indexOf('\\n') >= 0 || s.indexOf('\\r') >= 0) {
    return '"' + s.replace(/"/g, '""') + '"';
  }
  return s;
}

const header = COLS.map(esc).join(',');
const filas = items.map(item => COLS.map(col => esc(item.json[col])).join(','));
const csv = '\\uFEFF' + header + '\\n' + filas.join('\\n') + '\\n';
const buf = Buffer.from(csv, 'utf-8');

return [{
  json: {},
  binary: {
    data: {
      data: buf.toString('base64'),
      mimeType: 'text/csv',
      fileName: 'comercial.csv',
    }
  }
}];
"""


JS_F07_AUDIT = """// F07 - Genera CSV de auditoria con BOM UTF-8.
// Las 26 columnas del pipeline en orden natural.

const COLS = [
  'nombre', 'cuil', 'telefono', 'localidad', 'origen', 'fecha_carga',
  'telefono_norm', 'telefono_tipo',
  'cuil_norm', 'cuil_valido', 'cuil_dudoso',
  'telefono_match', 'id_fila', 'es_duplicado', 'duplicado_de', 'motivo_duplicado',
  'en_zona', 'marcado', 'motivo_descarte',
  'fecha_corte_usada', 'dias_antiguedad', 'frescura', 'motivo_frescura',
  'puntaje', 'prioridad', 'motivo',
];

function esc(v) {
  if (typeof v === 'boolean') return v ? 'TRUE' : 'FALSE';
  const s = String(v === undefined || v === null ? '' : v);
  if (s.indexOf(',') >= 0 || s.indexOf('"') >= 0 || s.indexOf('\\n') >= 0 || s.indexOf('\\r') >= 0) {
    return '"' + s.replace(/"/g, '""') + '"';
  }
  return s;
}

const header = COLS.map(esc).join(',');
const filas = items.map(item => COLS.map(col => esc(item.json[col])).join(','));
const csv = '\\uFEFF' + header + '\\n' + filas.join('\\n') + '\\n';
const buf = Buffer.from(csv, 'utf-8');

return [{
  json: {},
  binary: {
    data: {
      data: buf.toString('base64'),
      mimeType: 'text/csv',
      fileName: 'auditoria.csv',
    }
  }
}];
"""


JS_F08_REPORTE = """// F08 - Reporte de impacto.
// Calcula metricas de la lista procesada y genera un informe en Markdown.
// CONFIG tiene los supuestos; cambiar aca, no abajo.
//
// costo_hora_operador = 0 -> el reporte dice "a definir con el cliente".
// Si no los sabe, se pregunta al cliente en la reunion: esa pregunta ya es
// parte del pitch.

const CONFIG = {
  minutos_por_llamada: 4,
  costo_hora_operador: 0,
};

const total = items.length;
let alta = 0, media = 0, descartado = 0;
let sin_tel = 0, fuera_zona = 0, dup = 0, por_score = 0;

for (const item of items) {
  const pri = String(item.json.prioridad || '');
  const motivo = String(item.json.motivo || '');

  if (pri === 'alta') alta++;
  else if (pri === 'media') media++;
  else descartado++;

  if (pri === 'descartado') {
    if (motivo.indexOf('sin tel\\u00e9fono') >= 0 && motivo.indexOf('\\u2192 descarte') >= 0) sin_tel++;
    if (motivo.indexOf('fuera de zona') >= 0 && motivo.indexOf('\\u2192 descarte') >= 0) fuera_zona++;
    if (motivo.indexOf('duplicado') >= 0 && motivo.indexOf('\\u2192 descarte') >= 0) dup++;
    if (motivo.indexOf('\\u2192 descarte') < 0) por_score++;
  }
}

const unicos = total - dup;
const llamables = alta + media;
const horas = (descartado * CONFIG.minutos_por_llamada / 60).toFixed(1);
const fecha_corte = String(items[0].json.fecha_corte_usada || '');

let md = '';
md += '# Reporte de impacto \\u2014 Limpieza de lista de contactos\\n\\n';

md += '| | |\\n';
md += '|---|---|\\n';
md += '| Fecha de corte | ' + fecha_corte + ' |\\n';
md += '| Contactos procesados | ' + total + ' |\\n\\n';

md += '## Resumen\\n\\n';
md += '| M\\u00e9trica | Cantidad |\\n';
md += '|---------|----------|\\n';
md += '| Contactos en el archivo | ' + total + ' |\\n';
md += '| Contactos \\u00fanicos (sin duplicados) | ' + unicos + ' |\\n';
md += '| **Contactos llamables** (alta + media) | **' + llamables + '** |\\n';
md += '| Contactos descartados | ' + descartado + ' |\\n\\n';

md += '## Contactos llamables\\n\\n';
md += '| Prioridad | Cantidad | % del total |\\n';
md += '|-----------|----------|-------------|\\n';
md += '| Alta | ' + alta + ' | ' + (alta * 100 / total).toFixed(1) + '% |\\n';
md += '| Media | ' + media + ' | ' + (media * 100 / total).toFixed(1) + '% |\\n\\n';

md += '## Motivos de descarte\\n\\n';
md += '### Por calidad de dato (hechos del archivo)\\n\\n';
md += '| Motivo | Contactos |\\n';
md += '|--------|-----------|\\n';
md += '| Sin tel\\u00e9fono utilizable | ' + sin_tel + ' |\\n';
md += '| Duplicado | ' + dup + ' |\\n';
if (por_score > 0) {
  md += '| Puntaje bajo (< 40) sin descarte directo | ' + por_score + ' |\\n';
}
md += '\\n';

md += '### Por zona de cobertura (supuesto nuestro, no del archivo)\\n\\n';
md += '| Motivo | Contactos |\\n';
md += '|--------|-----------|\\n';
md += '| Fuera de zona de cobertura | ' + fuera_zona + ' |\\n\\n';

md += '*Un contacto puede tener m\\u00e1s de un motivo. La suma de motivos supera el total de descartados.*\\n\\n';

md += '## Ahorro estimado\\n\\n';
md += '| Concepto | Valor |\\n';
md += '|----------|-------|\\n';
const horas_bajo = (descartado * 2 / 60).toFixed(1);
const horas_alto = (descartado * 5 / 60).toFixed(1);

md += '| Llamadas evitadas | ' + descartado + ' |\\n';
md += '| Tiempo por llamada *(supuesto)* | ' + CONFIG.minutos_por_llamada + ' min |\\n';
md += '| **Horas de operador ahorradas** | **' + horas + ' h** |\\n';
md += '| Sensibilidad (2 a 5 min/llamada) | ' + horas_bajo + ' h a ' + horas_alto + ' h |\\n';

if (CONFIG.costo_hora_operador > 0) {
  const ahorro = Math.round(descartado * CONFIG.minutos_por_llamada / 60 * CONFIG.costo_hora_operador);
  md += '| Costo hora operador *(supuesto)* | $' + CONFIG.costo_hora_operador + ' |\\n';
  md += '| **Ahorro estimado** | **$' + ahorro + '** |\\n';
} else {
  md += '| Costo hora operador | *a definir con el cliente* |\\n';
}

md += '\\n';
md += '*Los supuestos se calibran con cada cliente. Pregunte: \\u201c\\u00bfCu\\u00e1nto tarda una llamada promedio, incluyendo los intentos que no conectan?\\u201d*\\n';

const buf = Buffer.from(md, 'utf-8');

return [{
  json: {},
  binary: {
    data: {
      data: buf.toString('base64'),
      mimeType: 'text/markdown',
      fileName: 'reporte.md',
    }
  }
}];
"""


JS_F11_PUERTA = """// F11 - Puerta de entrada (modo __MODO__).
//
// Todo F00-F10 supone que el archivo es NUESTRO CSV: coma, UTF-8, seis
// columnas conocidas, encabezado en la fila 1. Este nodo se ocupa del archivo
// de un CLIENTE: o lo entiende, o lo rechaza con un error que se entiende.
// Lo unico prohibido es procesarlo mal en silencio (hallazgo 13: el CSV con
// ';' salio con cara de correcto y las 5 filas vacias).
//
// REGLA DE ORO: ante la duda, frenar fuerte. No se adivina un separador, no
// se mapea una columna por parecido, no se rellena un dato.
//
// El rechazo NO se lanza aca: se marca en _rechazo y lo lanza el nodo Reja,
// DESPUES de que la rama de la ficha escribio su archivo. Un rechazo sin
// ficha no explica nada.
//
// SINONIMOS y MAPEO vienen de config/sinonimos.json y config/mapeo_*.json,
// embebidos al GENERAR el workflow. Cambiar de cliente = otro JSON en config/
// y regenerar; nunca editar JavaScript.

const ARCHIVO = __ARCHIVO_JSON__;
const MODO = '__MODO__';
const SINONIMOS = __SINONIMOS_JSON__;
const MAPEO = __MAPEO_JSON__;

const CANONICAS = ['nombre', 'cuil', 'telefono', 'localidad', 'origen', 'fecha_carga'];

function normNombre(s) {
  return String(s === undefined || s === null ? '' : s)
    .normalize('NFD').replace(/[\\u0300-\\u036f]/g, '')
    .toLowerCase().trim().replace(/\\s+/g, ' ');
}

// Cantidad de campos de una linea, fuera de comillas. Para DETECTAR el
// separador; el parseo real es parsearCSV, abajo.
function contarCampos(linea, sep) {
  let n = 1, enComillas = false;
  for (let i = 0; i < linea.length; i++) {
    const ch = linea[i];
    if (ch === '"') enComillas = !enComillas;
    else if (ch === sep && !enComillas) n++;
  }
  return n;
}

// Parser CSV RFC4180: campos entrecomillados con separadores, comillas
// escapadas ("") y saltos de linea adentro. Devuelve registros (arrays).
function parsearCSV(texto, sep) {
  const registros = [];
  let campo = '', registro = [], enComillas = false;
  for (let i = 0; i < texto.length; i++) {
    const ch = texto[i];
    if (enComillas) {
      if (ch === '"') {
        if (texto[i + 1] === '"') { campo += '"'; i++; }
        else enComillas = false;
      } else campo += ch;
    } else if (ch === '"' && campo === '') {
      enComillas = true;
    } else if (ch === sep) {
      registro.push(campo); campo = '';
    } else if (ch === '\\n' || ch === '\\r') {
      if (ch === '\\r' && texto[i + 1] === '\\n') i++;
      registro.push(campo); campo = '';
      registros.push(registro); registro = [];
    } else {
      campo += ch;
    }
  }
  if (campo !== '' || registro.length) { registro.push(campo); registros.push(registro); }
  return registros;
}

const meta = {
  archivo: ARCHIVO,
  tam: null,
  formato: MODO === 'texto' ? 'CSV / texto plano' : 'planilla (xlsx)',
  separador: MODO === 'texto' ? '' : 'n/a (planilla)',
  encoding: MODO === 'texto' ? '' : 'n/a (planilla)',
  encabezadoLinea: null,
  salteadas: [],
  columnas: [],
  mapeo: [],
  extras: [],
  faltantes: [],
  filasLeidas: 0,
  filasVaciasIgnoradas: 0,
  filasTodoVacio: 0,
  filasIncompletas: [],
  advertencias: [],
  origenes: null,
  estado: 'ACEPTADO',
  motivoRechazo: '',
};

function armarFicha(m) {
  const L = [];
  L.push('# Ficha de entrada \\u2014 ' + m.archivo.split(/[\\\\/]/).pop());
  L.push('');
  L.push('Generada por el workflow ANTES de confiar en la corrida. Todos los');
  L.push('numeros salen del archivo de origen, no de la salida.');
  L.push('');
  L.push('| Campo | Valor |');
  L.push('|-------|-------|');
  L.push('| Estado | **' + m.estado + '** |');
  if (m.motivoRechazo) L.push('| Motivo del rechazo | ' + m.motivoRechazo.replace(/\\|/g, '\\\\|') + ' |');
  L.push('| Archivo | ' + m.archivo + ' |');
  L.push('| Tama\\u00f1o | ' + (m.tam === null ? 'n/d' : m.tam + ' bytes') + ' |');
  L.push('| Formato | ' + m.formato + ' |');
  L.push('| Separador detectado | ' + (m.separador || 'n/d') + ' |');
  L.push('| Encoding | ' + (m.encoding || 'n/d') + ' |');
  L.push('| Encabezado en la linea | ' + (m.encabezadoLinea === null ? 'n/d' : m.encabezadoLinea) + ' |');
  L.push('| Lineas salteadas arriba del encabezado | ' + m.salteadas.length + ' |');
  L.push('| Filas de datos leidas | ' + m.filasLeidas + ' |');
  L.push('| Filas vacias ignoradas | ' + m.filasVaciasIgnoradas + ' |');
  L.push('| Filas con los 6 campos canonicos vacios | ' + m.filasTodoVacio + ' |');
  L.push('');
  if (m.salteadas.length) {
    L.push('## Lineas salteadas (basura arriba del encabezado)');
    L.push('');
    m.salteadas.forEach((s) => L.push('- linea ' + s.linea + ': ' + (s.contenido || '(vacia)')));
    L.push('');
  }
  L.push('## Columnas encontradas');
  L.push('');
  m.columnas.forEach((c) => L.push('- ' + (c === '' ? '(sin nombre)' : c)));
  L.push('');
  if (m.mapeo.length) {
    L.push('## Mapeo aplicado');
    L.push('');
    L.push('| Columna del archivo | Canonica | Como se resolvio |');
    L.push('|---------------------|----------|------------------|');
    m.mapeo.forEach((mm) => L.push('| ' + mm.orig + ' | ' + mm.canonica + ' | ' + mm.fuente + ' |'));
    L.push('');
  }
  if (m.faltantes.length) {
    L.push('## Columnas canonicas SIN RESOLVER');
    L.push('');
    m.faltantes.forEach((c) => L.push('- ' + c));
    L.push('');
  }
  if (m.extras.length) {
    L.push('## Columnas extra (se conservan en la auditoria, no puntuan)');
    L.push('');
    m.extras.forEach((c) => L.push('- ' + c));
    L.push('');
  }
  if (m.filasIncompletas.length) {
    L.push('## Filas incompletas (los campos que faltan quedan vacios)');
    L.push('');
    m.filasIncompletas.forEach((f) => L.push('- ' + f));
    L.push('');
  }
  if (m.advertencias.length) {
    L.push('## Advertencias');
    L.push('');
    m.advertencias.forEach((a) => L.push('- ' + a));
    L.push('');
  }
  if (m.origenes) {
    L.push('## Valores distintos de `origen`');
    L.push('');
    L.push('Se listan como vienen; NO se normalizan (eso es otra fase). Si estas');
    L.push('etiquetas no coinciden con las que puntua F06, el puntaje de origen da 0.');
    L.push('');
    L.push('| Valor | Filas |');
    L.push('|-------|-------|');
    Object.keys(m.origenes).sort().forEach((k) => {
      L.push('| ' + (k === '' ? '(vacio)' : k) + ' | ' + m.origenes[k] + ' |');
    });
    L.push('');
  }
  return L.join('\\n') + '\\n';
}

function frenar(detectado, esperado) {
  const e = new Error(
    'F11 RECHAZO \\u2014 archivo: ' + ARCHIVO +
    ' \\u2014 detectado: ' + detectado +
    ' \\u2014 esperado: ' + esperado
  );
  e._esRechazo = true;
  throw e;
}

try {
  let encabezados = null;   // nombres originales de columna
  let filasDatos = null;    // array de objetos { encabezado: valor }

  if (MODO === 'texto') {
    // En n8n 2.x el Code node corre en un task runner: el binario NO viaja
    // como base64 dentro de items[].binary (ahi queda una referencia), se
    // pide con helpers.getBinaryDataBuffer. El fallback a items[].binary
    // existe para poder probar esta logica fuera de n8n (Node pelado).
    let buf = null;
    if (typeof helpers !== 'undefined' && helpers && helpers.getBinaryDataBuffer) {
      buf = await helpers.getBinaryDataBuffer(0, 'data');
    } else if (items[0].binary && items[0].binary.data && items[0].binary.data.data) {
      buf = Buffer.from(items[0].binary.data.data, 'base64');
    }
    if (!buf || !buf.length) throw new Error('F11: no llego el archivo binario al nodo Puerta');
    meta.tam = buf.length;

    const conBOM = buf.length >= 3 && buf[0] === 0xEF && buf[1] === 0xBB && buf[2] === 0xBF;
    const cuerpo = conBOM ? buf.slice(3) : buf;
    let texto = cuerpo.toString('utf8');
    if (texto.indexOf('\\uFFFD') >= 0) {
      // No era UTF-8 valido. Latin-1 mapea todos los bytes: no pierde nada.
      texto = cuerpo.toString('latin1');
      meta.encoding = 'Latin-1 (no era UTF-8 valido)';
      meta.advertencias.push('el archivo no es UTF-8; se leyo como Latin-1 (revisar tildes en la salida)');
    } else {
      meta.encoding = conBOM ? 'UTF-8 con BOM' : 'UTF-8 sin BOM';
    }

    // --- Deteccion de separador ---
    // Regla de la fase: gana el que produce la MISMA cantidad de campos (>=2)
    // en al menos el 80% de las primeras 10 lineas no vacias. Refinamientos
    // (documentados en ESTADO.md):
    //   - una linea con 1 solo campo no vota (no contiene el separador: es
    //     titulo/basura, no evidencia en contra) -> el 80% se exige sobre las
    //     lineas con >=2 campos;
    //   - pero la moda tiene que aparecer en >=50% del TOTAL de las lineas
    //     muestreadas, para que un ';' perdido dentro de una celda no gane
    //     con una sola linea;
    //   - dos separadores igual de consistentes = ambiguo = rechazo.
    const lineas = texto.split(/\\r\\n|\\r|\\n/);
    const muestra = lineas.filter((l) => l.trim() !== '').slice(0, 10);
    if (muestra.length === 0) frenar('archivo vacio (0 lineas con contenido)', 'un archivo con encabezado y datos');

    const SEPS = [[',', 'coma'], [';', 'punto y coma'], ['\\t', 'tabulador']];
    const aptos = [];
    for (const par of SEPS) {
      const sep = par[0], nombreSep = par[1];
      const counts = muestra.map((l) => contarCampos(l, sep));
      const multi = counts.filter((c) => c >= 2);
      if (!multi.length) continue;
      const frec = new Map();
      multi.forEach((c) => frec.set(c, (frec.get(c) || 0) + 1));
      let moda = 0, fmax = 0;
      frec.forEach((f, c) => { if (f > fmax) { fmax = f; moda = c; } });
      const soporteMulti = fmax / multi.length;
      const soporteTotal = counts.filter((c) => c === moda).length / counts.length;
      if (soporteMulti >= 0.8 && soporteTotal >= 0.5) {
        aptos.push({ sep: sep, nombreSep: nombreSep, moda: moda, soporteTotal: soporteTotal });
      }
    }
    if (aptos.length === 0) {
      frenar(
        'ningun separador (coma, punto y coma, tabulador) produce una cantidad estable de columnas (>=2) sobre las primeras ' + muestra.length + ' lineas no vacias',
        'una tabla con separador consistente; esto no parece una tabla'
      );
    }
    aptos.sort((a, b) => b.soporteTotal - a.soporteTotal);
    if (aptos.length > 1 && aptos[0].soporteTotal === aptos[1].soporteTotal) {
      frenar(
        'dos separadores igual de consistentes: ' + aptos[0].nombreSep + ' y ' + aptos[1].nombreSep,
        'un unico separador dominante; no se adivina'
      );
    }
    const sep = aptos[0].sep;
    meta.separador = aptos[0].nombreSep;

    // --- Parseo completo + encabezado ---
    const registros = parsearCSV(texto, sep);
    const esVacio = (r) => r.every((c) => String(c).trim() === '');

    const frecCols = new Map();
    registros.forEach((r) => {
      if (esVacio(r) || r.length < 2) return;
      frecCols.set(r.length, (frecCols.get(r.length) || 0) + 1);
    });
    let modaCols = 0, fcmax = 0;
    frecCols.forEach((f, c) => { if (f > fcmax) { fcmax = f; modaCols = c; } });
    if (modaCols < 2) {
      frenar('una sola columna en un archivo de ' + registros.length + ' lineas', 'al menos 2 columnas');
    }

    // El encabezado es la primera linea cuya cantidad de campos coincide con
    // la de la mayoria. Lo de arriba se saltea y se REPORTA, no muere mudo.
    const headerIdx = registros.findIndex((r) => !esVacio(r) && r.length === modaCols);
    meta.encabezadoLinea = headerIdx + 1;
    for (let i = 0; i < headerIdx; i++) {
      const r = registros[i];
      meta.salteadas.push({
        linea: i + 1,
        contenido: esVacio(r) ? '' : r.join(sep === '\\t' ? ' ' : sep).slice(0, 80),
      });
    }
    encabezados = registros[headerIdx].map((c) => String(c).trim());

    filasDatos = [];
    for (let i = headerIdx + 1; i < registros.length; i++) {
      const r = registros[i];
      if (esVacio(r)) { meta.filasVaciasIgnoradas++; continue; }
      let campos = r.slice();
      if (campos.length > encabezados.length) {
        const sobra = campos.slice(encabezados.length);
        if (sobra.every((c) => String(c).trim() === '')) {
          campos = campos.slice(0, encabezados.length);
          meta.advertencias.push('linea ' + (i + 1) + ': campos vacios de mas al final, recortados');
        } else {
          frenar(
            'la linea ' + (i + 1) + ' tiene ' + campos.length + ' campos con contenido y el encabezado tiene ' + encabezados.length,
            'filas con a lo sumo tantos campos como el encabezado'
          );
        }
      }
      if (campos.length < encabezados.length) {
        meta.filasIncompletas.push(
          'linea ' + (i + 1) + ': ' + campos.length + ' de ' + encabezados.length + ' campos'
        );
        while (campos.length < encabezados.length) campos.push('');
      }
      const obj = {};
      encabezados.forEach((h, j) => { obj[h] = campos[j]; });
      filasDatos.push(obj);
    }
  } else {
    // Planilla: los items ya vienen de extractFromFile (operation xlsx), que
    // es la unica pieza que sabe leer el formato. Aca no hay separador ni
    // encabezado que buscar: la primera fila de la hoja es el encabezado.
    meta.encabezadoLinea = 1;
    encabezados = [];
    const visto = new Set();
    for (const it of items) {
      for (const k of Object.keys(it.json)) {
        if (!visto.has(k)) { visto.add(k); encabezados.push(k); }
      }
    }
    encabezados = encabezados.map((h) => String(h).trim());
    filasDatos = items.map((it) => it.json);
  }

  meta.columnas = encabezados.slice();

  // --- Encabezados repetidos: mapeo ambiguo, se frena ---
  const nrm = encabezados.map(normNombre);
  for (let i = 0; i < nrm.length; i++) {
    if (nrm[i] !== '' && nrm.indexOf(nrm[i]) !== i) {
      frenar("columna repetida en el encabezado: '" + encabezados[i] + "'", 'nombres de columna unicos');
    }
  }

  // --- Mapeo: primero el del cliente, despues sinonimos. Nunca por parecido ---
  const MAPEO_NORM = {};
  if (MAPEO) {
    for (const k of Object.keys(MAPEO)) {
      if (k.indexOf('_') === 0) continue;
      MAPEO_NORM[normNombre(k)] = MAPEO[k];
    }
  }
  const SIN_NORM = {};
  for (const canon of Object.keys(SINONIMOS)) {
    if (canon.indexOf('_') === 0) continue;
    SINONIMOS[canon].forEach((s) => { SIN_NORM[normNombre(s)] = canon; });
  }

  const resolucion = {};   // canonica -> { orig, fuente }
  const usadas = new Set();
  for (const h of encabezados) {
    const destino = MAPEO_NORM[normNombre(h)];
    if (!destino) continue;
    if (resolucion[destino]) {
      frenar(
        "dos columnas ('" + resolucion[destino].orig + "' y '" + h + "') mapean a '" + destino + "'",
        'una columna por canonica'
      );
    }
    resolucion[destino] = { orig: h, fuente: 'mapeo del cliente' };
    usadas.add(h);
  }
  for (const canon of CANONICAS) {
    if (resolucion[canon]) continue;
    const cand = encabezados.filter((h) => !usadas.has(h) && SIN_NORM[normNombre(h)] === canon);
    if (cand.length > 1) {
      frenar(
        "dos columnas ('" + cand.join("', '") + "') coinciden por sinonimos con '" + canon + "'",
        'una columna por canonica; resolver con config/mapeo_<cliente>.json'
      );
    }
    if (cand.length === 1) {
      resolucion[canon] = {
        orig: cand[0],
        fuente: normNombre(cand[0]) === canon ? 'nombre canonico' : 'sinonimos',
      };
      usadas.add(cand[0]);
    }
  }

  meta.faltantes = CANONICAS.filter((c) => !resolucion[c]);
  if (meta.faltantes.length) {
    frenar(
      "columnas canonicas sin resolver: [" + meta.faltantes.join(', ') + "]. Columnas del archivo: [" + encabezados.join(', ') + "]",
      'resolverlas por config/mapeo_<cliente>.json o config/sinonimos.json; no se adivina por parecido ni por posicion'
    );
  }
  meta.mapeo = CANONICAS.map((c) => ({ canonica: c, orig: resolucion[c].orig, fuente: resolucion[c].fuente }));
  meta.extras = encabezados.filter((h) => !usadas.has(h) && normNombre(h) !== '');

  // --- Construir filas canonicas ---
  const filasOut = [];
  for (let i = 0; i < filasDatos.length; i++) {
    const fila = filasDatos[i];
    const out = {};
    const adv = [];
    for (const canon of CANONICAS) {
      let v = fila[resolucion[canon].orig];
      if (typeof v === 'number') {
        // Celda numerica de planilla. Para el telefono es la trampa clasica
        // de Excel: si habia un 0 inicial (011-...), ya se perdio y no hay
        // forma de saberlo. Un telefono asi no es confiable: se serializa
        // con el artefacto visible (.0) para que F01 lo marque invalido,
        // y el motivo queda en advertencia_entrada y en la ficha.
        if (canon === 'telefono') {
          adv.push('telefono llego como numero de planilla (posible perdida del 0 inicial): artefacto de Excel');
          v = v.toFixed(1);
        } else {
          adv.push(canon + ' llego como numero de planilla');
          v = String(v);
        }
      }
      out[canon] = (v === undefined || v === null) ? '' : String(v);
    }
    for (const h of meta.extras) {
      const v = fila[h];
      out['extra_' + h] = (v === undefined || v === null) ? '' : String(v);
    }
    if (CANONICAS.every((c) => out[c].trim() === '')) meta.filasTodoVacio++;
    if (adv.length) {
      out.advertencia_entrada = adv.join('; ');
      meta.advertencias.push('fila ' + (i + 1) + ' de datos: ' + adv.join('; '));
    }
    filasOut.push(out);
  }
  meta.filasLeidas = filasOut.length;

  // --- Reja anti-silencio: los checks que habrian atrapado el hallazgo 13 ---
  if (filasOut.length === 0) {
    frenar('cero filas de datos despues del encabezado', 'al menos una fila de datos');
  }
  if (meta.filasTodoVacio / filasOut.length > 0.5) {
    frenar(
      meta.filasTodoVacio + ' de ' + filasOut.length + ' filas con los 6 campos canonicos vacios',
      'una lista con datos; esto no es una lista mala, es un parseo mal hecho'
    );
  }

  const origenes = {};
  filasOut.forEach((o) => {
    const k = String(o.origen || '').trim();
    origenes[k] = (origenes[k] || 0) + 1;
  });
  meta.origenes = origenes;

  const salida = filasOut.map((o) => ({ json: o }));
  salida[0].json._ficha = armarFicha(meta);
  return salida;

} catch (e) {
  if (!e._esRechazo) throw e;
  meta.estado = 'RECHAZADO';
  meta.motivoRechazo = e.message;
  return [{ json: { _rechazo: e.message, _ficha: armarFicha(meta) } }];
}
"""


JS_F11_REJA = """// F11 - Reja. Si la puerta marco rechazo, aca se corta la corrida con una
// excepcion de n8n (exit code de error, SIN archivo de salida). Esta separado
// de la puerta para que la rama de la ficha alcance a escribirse ANTES de
// frenar: un rechazo sin ficha no explica nada.
if (items.length && items[0].json._rechazo) {
  throw new Error(items[0].json._rechazo);
}
return items;
"""


JS_F11_FICHA = """// F11 - Ficha de entrada. Toma el markdown que armo la puerta y lo convierte
// en archivo. Se escribe SIEMPRE: tambien (sobre todo) cuando la corrida se
// rechaza, porque la ficha es lo que se lee antes de apretar correr.
const md = String((items[0] && items[0].json && items[0].json._ficha) || '');
if (md === '') throw new Error('F11: la puerta no dejo la ficha de entrada');
const buf = Buffer.from(md, 'utf-8');
return [{
  json: {},
  binary: {
    data: {
      data: buf.toString('base64'),
      mimeType: 'text/markdown',
      fileName: 'ficha.md',
    }
  }
}];
"""


JS_F11_AUDIT = """// F11 - CSV de auditoria con columnas extra del cliente.
// Identico a la auditoria de F07 (mismas 26 columnas, mismo orden, mismo
// escape) MAS las columnas opcionales, al final y ordenadas:
//   - las que la puerta conservo del archivo del cliente (extra_*)
//   - advertencia_entrada (F11)
//   - tipo_persona (F12, solo si la segmentacion esta etiquetando)
// Ninguna de las tres existe con el CSV canonico y la config por defecto, asi
// que la salida es byte a byte la de F07 (golden intacto).

const COLS = [
  'nombre', 'cuil', 'telefono', 'localidad', 'origen', 'fecha_carga',
  'telefono_norm', 'telefono_tipo',
  'cuil_norm', 'cuil_valido', 'cuil_dudoso',
  'telefono_match', 'id_fila', 'es_duplicado', 'duplicado_de', 'motivo_duplicado',
  'en_zona', 'marcado', 'motivo_descarte',
  'fecha_corte_usada', 'dias_antiguedad', 'frescura', 'motivo_frescura',
  'puntaje', 'prioridad', 'motivo',
];

const OPCIONALES = new Set(['advertencia_entrada', 'tipo_persona']);

const extras = new Set();
for (const item of items) {
  for (const k of Object.keys(item.json)) {
    if (k.indexOf('extra_') === 0 || OPCIONALES.has(k)) extras.add(k);
  }
}
const cols = COLS.concat(Array.from(extras).sort());

function esc(v) {
  if (typeof v === 'boolean') return v ? 'TRUE' : 'FALSE';
  const s = String(v === undefined || v === null ? '' : v);
  if (s.indexOf(',') >= 0 || s.indexOf('"') >= 0 || s.indexOf('\\n') >= 0 || s.indexOf('\\r') >= 0) {
    return '"' + s.replace(/"/g, '""') + '"';
  }
  return s;
}

const header = cols.map(esc).join(',');
const filas = items.map(item => cols.map(col => esc(item.json[col])).join(','));
const csv = '\\uFEFF' + header + '\\n' + filas.join('\\n') + '\\n';
const buf = Buffer.from(csv, 'utf-8');

return [{
  json: {},
  binary: {
    data: {
      data: buf.toString('base64'),
      mimeType: 'text/csv',
      fileName: 'auditoria.csv',
    }
  }
}];
"""


# ---------------------------------------------------------------------------
# Nodos fijos de la cadena (iguales en todas las fases).
# ---------------------------------------------------------------------------

def _nodos_lectura(path_in):
    return [
        {
            "parameters": {},
            "id": "n0-trigger",
            "name": "Ejecutar manualmente",
            "type": "n8n-nodes-base.manualTrigger",
            "typeVersion": 1,
            "position": [0, 0],
        },
        {
            "parameters": {"fileSelector": path_in, "options": {}},
            "id": "n1-leer",
            "name": "Leer CSV de disco",
            "type": "n8n-nodes-base.readWriteFile",
            "typeVersion": 1,
            "position": [200, 0],
        },
        {
            "parameters": {
                "operation": "csv",
                "options": {"headerRow": True, "delimiter": ","},
            },
            "id": "n2-extraer",
            "name": "CSV a items",
            "type": "n8n-nodes-base.extractFromFile",
            "typeVersion": 1,
            "position": [400, 0],
        },
    ]


def _nodos_escritura(path_out, x_armar, x_escribir, convert_type_version=1.1):
    out_name = os.path.basename(path_out)
    return [
        {
            "parameters": {
                "operation": "csv",
                "options": {"fileName": out_name, "headerRow": True},
            },
            "id": "n8-armar",
            "name": "Items a CSV",
            "type": "n8n-nodes-base.convertToFile",
            "typeVersion": convert_type_version,
            "position": [x_armar, 0],
        },
        {
            "parameters": {"operation": "write", "fileName": path_out, "options": {}},
            "id": "n9-escribir",
            "name": "Escribir CSV a disco",
            "type": "n8n-nodes-base.readWriteFile",
            "typeVersion": 1,
            "position": [x_escribir, 0],
        },
    ]


def _params(js, fecha_corte, seg_json):
    """Reemplaza los parametros que se embeben al generar el workflow."""
    return js.replace("__FECHA_CORTE__", fecha_corte).replace("__SEGMENTACION_JSON__", seg_json)


def _nodo_code(node_id, name, js, x, code_type_version=2):
    return {
        "parameters": {"jsCode": js},
        "id": node_id,
        "name": name,
        "type": "n8n-nodes-base.code",
        "typeVersion": code_type_version,
        "position": [x, 0],
    }


# Cada fase agrega su nodo Code a esta cadena. F00 siempre esta (guardarrail).
FASES = {
    "00": {
        "id": "f00pasamanos001",
        "name": "01-pasamanos",
        "codes": [("n3-pasamanos", "Pasamanos (todo string)", JS_F00)],
    },
    "01": {
        "id": "f01telefono0001",
        "name": "02-telefono",
        "codes": [
            ("n3-pasamanos", "Pasamanos (todo string)", JS_F00),
            ("n4-telefono", "Normalizar telefono", JS_F01),
        ],
    },
    "02": {
        "id": "f02cuil00000001",
        "name": "03-cuil",
        "codes": [
            ("n3-pasamanos", "Pasamanos (todo string)", JS_F00),
            ("n4-telefono", "Normalizar telefono", JS_F01),
            ("n5-cuil", "Validar CUIL", JS_F02),
        ],
    },
    "03": {
        "id": "f03dedup0000001",
        "name": "04-dedup",
        "codes": [
            ("n3-pasamanos", "Pasamanos (todo string)", JS_F00),
            ("n4-telefono", "Normalizar telefono", JS_F01),
            ("n5-cuil", "Validar CUIL", JS_F02),
            ("n6-dedup", "Marcar duplicados", JS_F03),
        ],
    },
    "04": {
        "id": "f04cobertura0001",
        "name": "05-cobertura",
        "codes": [
            ("n3-pasamanos", "Pasamanos (todo string)", JS_F00),
            ("n4-telefono", "Normalizar telefono", JS_F01),
            ("n5-cuil", "Validar CUIL", JS_F02),
            ("n6-dedup", "Marcar duplicados", JS_F03),
            ("n7-cobertura", "Completitud y cobertura", JS_F04),
        ],
    },
    "05": {
        "id": "f05antiguedad001",
        "name": "06-antiguedad",
        "codes": [
            ("n3-pasamanos", "Pasamanos (todo string)", JS_F00),
            ("n4-telefono", "Normalizar telefono", JS_F01),
            ("n5-cuil", "Validar CUIL", JS_F02),
            ("n6-dedup", "Marcar duplicados", JS_F03),
            ("n7-cobertura", "Completitud y cobertura", JS_F04),
            ("n8-antiguedad", "Antiguedad del lead", JS_F05),
        ],
    },
    "06": {
        "id": "f06puntaje00001",
        "name": "07-puntaje",
        "codes": [
            ("n3-pasamanos", "Pasamanos (todo string)", JS_F00),
            ("n4-telefono", "Normalizar telefono", JS_F01),
            ("n5-cuil", "Validar CUIL", JS_F02),
            ("n6-dedup", "Marcar duplicados", JS_F03),
            ("n7-cobertura", "Completitud y cobertura", JS_F04),
            ("n8-antiguedad", "Antiguedad del lead", JS_F05),
            ("n9-puntaje", "Puntaje explicable", JS_F06),
        ],
    },
    "07": {
        "id": "f07salida000001",
        "name": "08-salida",
        "codes": [
            ("n3-pasamanos", "Pasamanos (todo string)", JS_F00),
            ("n4-telefono", "Normalizar telefono", JS_F01),
            ("n5-cuil", "Validar CUIL", JS_F02),
            ("n6-dedup", "Marcar duplicados", JS_F03),
            ("n7-cobertura", "Completitud y cobertura", JS_F04),
            ("n8-antiguedad", "Antiguedad del lead", JS_F05),
            ("n9-puntaje", "Puntaje explicable", JS_F06),
            ("nA-ordenar", "Ordenar por prioridad y puntaje", JS_F07_SORT),
        ],
        "salida_dual": {
            "comercial": ("nB-comercial", "CSV comercial", JS_F07_COMERCIAL),
            "auditoria": ("nC-auditoria", "CSV auditoría", JS_F07_AUDIT),
        },
    },
    "08": {
        "id": "f08reporte00001",
        "name": "09-reporte",
        "codes": [
            ("n3-pasamanos", "Pasamanos (todo string)", JS_F00),
            ("n4-telefono", "Normalizar telefono", JS_F01),
            ("n5-cuil", "Validar CUIL", JS_F02),
            ("n6-dedup", "Marcar duplicados", JS_F03),
            ("n7-cobertura", "Completitud y cobertura", JS_F04),
            ("n8-antiguedad", "Antiguedad del lead", JS_F05),
            ("n9-puntaje", "Puntaje explicable", JS_F06),
            ("nA-ordenar", "Ordenar por prioridad y puntaje", JS_F07_SORT),
        ],
        "salida_dual": {
            "comercial": ("nB-comercial", "CSV comercial", JS_F07_COMERCIAL),
            "auditoria": ("nC-auditoria", "CSV auditoría", JS_F07_AUDIT),
            "reporte": ("nG-reporte", "Reporte de impacto", JS_F08_REPORTE),
        },
    },
    # F11 - puerta de entrada. Mismo pipeline completo que F08, pero la
    # cabeza cambia: en vez de extractFromFile con coma fija, la puerta
    # detecta separador/encabezado, mapea columnas por config y frena fuerte
    # ante un archivo que no se entiende. La auditoria es la variante F11
    # (conserva columnas extra del cliente; byte-identica a F07 sin extras).
    "11": {
        "id": "f11puerta000001",
        "name": "10-puerta",
        "puerta": True,
        "codes": [
            ("n3-pasamanos", "Pasamanos (todo string)", JS_F00),
            ("n4-telefono", "Normalizar telefono", JS_F01),
            ("n5-cuil", "Validar CUIL", JS_F02),
            ("n6-dedup", "Marcar duplicados", JS_F03),
            ("n7-cobertura", "Completitud y cobertura", JS_F04),
            ("n8-antiguedad", "Antiguedad del lead", JS_F05),
            ("n9-puntaje", "Puntaje explicable", JS_F06),
            ("nA-ordenar", "Ordenar por prioridad y puntaje", JS_F07_SORT),
        ],
        "salida_dual": {
            "comercial": ("nB-comercial", "CSV comercial", JS_F07_COMERCIAL),
            "auditoria": ("nC-auditoria", "CSV auditoría (F11)", JS_F11_AUDIT),
            "reporte": ("nG-reporte", "Reporte de impacto", JS_F08_REPORTE),
        },
    },
    # F12 - persona fisica vs juridica. Es F11 mas un nodo: la segmentacion se
    # decide DESPUES de tener el CUIL normalizado (F02) y ANTES del puntaje
    # (F06), que es donde vive el descarte directo. F11 queda intacta a
    # proposito: v11_puerta.py sigue verificando exactamente lo que cerro.
    "12": {
        "id": "f12persona00001",
        "name": "11-persona",
        "puerta": True,
        "codes": [
            ("n3-pasamanos", "Pasamanos (todo string)", JS_F00),
            ("n4-telefono", "Normalizar telefono", JS_F01),
            ("n5-cuil", "Validar CUIL", JS_F02),
            ("n6-dedup", "Marcar duplicados", JS_F03),
            ("n7-cobertura", "Completitud y cobertura", JS_F04),
            ("n8-antiguedad", "Antiguedad del lead", JS_F05),
            ("n8b-persona", "Persona física o jurídica", JS_F12),
            ("n9-puntaje", "Puntaje explicable", JS_F06),
            ("nA-ordenar", "Ordenar por prioridad y puntaje", JS_F07_SORT),
        ],
        "salida_dual": {
            "comercial": ("nB-comercial", "CSV comercial", JS_F07_COMERCIAL),
            "auditoria": ("nC-auditoria", "CSV auditoría (F11)", JS_F11_AUDIT),
            "reporte": ("nG-reporte", "Reporte de impacto", JS_F08_REPORTE),
        },
    },
}


def _segmentacion_json(spec, segmentacion_path):
    """Lee y valida config/segmentacion.json; devuelve el literal JS a embeber.

    Solo se lee si la fase tiene el nodo de F12. La validacion es fuerte a
    proposito: un valor raro en la config tiene que frenar al generar, no
    convertirse en un descarte silencioso (o en ningun descarte) recien en n8n.
    """
    if not any("__SEGMENTACION_JSON__" in js for _, _, js in spec["codes"]):
        return ""

    if not segmentacion_path:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        segmentacion_path = os.path.join(base, "config", "segmentacion.json")
    with open(segmentacion_path, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)

    etiquetar = cfg.get("etiquetar", False)
    descartar = cfg.get("descartar", None)
    if not isinstance(etiquetar, bool):
        raise SystemExit(
            f"segmentacion {segmentacion_path}: 'etiquetar' tiene que ser true o false, "
            f"vino {etiquetar!r}")
    if descartar not in (None, "fisica", "juridica"):
        extra = ""
        if descartar == "desconocida":
            extra = (" — 'desconocida' NUNCA se descarta: no saber que es un contacto "
                     "no es motivo para tirarlo")
        raise SystemExit(
            f"segmentacion {segmentacion_path}: 'descartar' tiene que ser null, "
            f"'fisica' o 'juridica', vino {descartar!r}{extra}")

    return json.dumps({"etiquetar": etiquetar, "descartar": descartar}, ensure_ascii=False)


def _js_puerta(path_in, mapeo_path):
    """Arma el JS de la puerta: embebe modo, ruta, sinonimos y mapeo.

    Los JSON viven en config/ y se embeben al GENERAR. Cambiar de cliente =
    editar/crear un JSON y regenerar; nunca editar JavaScript.
    """
    ext = os.path.splitext(path_in)[1].lower()
    modo = "planilla" if ext in (".xlsx", ".xls") else "texto"

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sin_path = os.path.join(base, "config", "sinonimos.json")
    with open(sin_path, "r", encoding="utf-8") as fh:
        sinonimos = json.load(fh)

    mapeo = None
    if mapeo_path:
        with open(mapeo_path, "r", encoding="utf-8") as fh:
            mapeo = json.load(fh)
        canonicas = {"nombre", "cuil", "telefono", "localidad", "origen", "fecha_carga"}
        malas = [v for k, v in mapeo.items()
                 if not k.startswith("_") and v not in canonicas]
        if malas:
            raise SystemExit(f"mapeo {mapeo_path}: destinos no canonicos: {malas}")

    js = (JS_F11_PUERTA
          .replace("__MODO__", modo)
          .replace("__ARCHIVO_JSON__", json.dumps(path_in))
          .replace("__SINONIMOS_JSON__", json.dumps(sinonimos, ensure_ascii=False))
          .replace("__MAPEO_JSON__", json.dumps(mapeo, ensure_ascii=False)))
    return js, modo


def build(path_in, path_out, fase="00", code_type_version=2, convert_type_version=1.1,
          fecha_corte="", path_out_audit="", path_reporte="", mapeo_path="",
          ficha_out="", segmentacion_path=""):
    if fase not in FASES:
        raise SystemExit(f"fase desconocida: {fase!r}. Conocidas: {sorted(FASES)}")
    spec = FASES[fase]
    seg_json = _segmentacion_json(spec, segmentacion_path)

    def link(a, b):
        return {a: {"main": [[{"node": b, "type": "main", "index": 0}]]}}

    if spec.get("puerta"):
        return _build_f11(path_in, path_out, spec, code_type_version, fecha_corte,
                          path_out_audit, path_reporte, mapeo_path, ficha_out, link,
                          seg_json)

    nodos = _nodos_lectura(path_in)
    x = 600
    for node_id, name, js in spec["codes"]:
        js_final = _params(js, fecha_corte, seg_json)
        nodos.append(_nodo_code(node_id, name, js_final, x, code_type_version))
        x += 200

    branch_paths = {"comercial": path_out, "auditoria": path_out_audit, "reporte": path_reporte}

    if "salida_dual" in spec:
        sd = spec["salida_dual"]
        active = [(k, sd[k], branch_paths[k]) for k in sd if branch_paths.get(k)]

    if "salida_dual" in spec and active:
        sort_idx = len(nodos) - 1
        sort_node = nodos[sort_idx]
        y_offsets = [-200, 200, 600]
        branch_nodes = []

        for i, (key, (b_id, b_name, b_js), b_path) in enumerate(active):
            y = y_offsets[i] if i < len(y_offsets) else 200 * (i + 2)
            code_node = _nodo_code(b_id, b_name, b_js, x, code_type_version)
            code_node["position"] = [x, y]
            write_node = {
                "parameters": {"operation": "write", "fileName": b_path, "options": {}},
                "id": f"nW{i}-escribir-{key}",
                "name": f"Escribir {b_name}",
                "type": "n8n-nodes-base.readWriteFile",
                "typeVersion": 1,
                "position": [x + 200, y],
            }
            nodos += [code_node, write_node]
            branch_nodes.append((code_node, write_node))

        connections = {}
        for i in range(sort_idx):
            connections.update(link(nodos[i]["name"], nodos[i + 1]["name"]))

        connections[sort_node["name"]] = {
            "main": [[
                {"node": cn["name"], "type": "main", "index": 0}
                for cn, _ in branch_nodes
            ]]
        }
        for cn, wn in branch_nodes:
            connections.update(link(cn["name"], wn["name"]))
    else:
        nodos += _nodos_escritura(path_out, x, x + 200, convert_type_version)

        connections = {}
        for a, b in zip(nodos, nodos[1:]):
            connections.update(link(a["name"], b["name"]))

    return {
        "id": spec["id"],
        "name": spec["name"],
        "nodes": nodos,
        "connections": connections,
        "active": False,
        "pinData": {},
        "settings": {"executionOrder": "v1"},
    }


def _build_f11(path_in, path_out, spec, code_type_version, fecha_corte,
               path_out_audit, path_reporte, mapeo_path, ficha_out, link,
               seg_json=""):
    """Cablea el workflow de F11.

    trigger -> leer -> [planilla a items (solo xlsx)] -> puerta
    puerta -> ficha -> escribir ficha        (rama 1: se escribe SIEMPRE)
    puerta -> reja -> pasamanos -> ... -> ordenar -> ramas de salida
    La rama de la ficha va PRIMERO en las conexiones: con executionOrder v1
    corre antes que la reja, asi el rechazo nunca deja la corrida sin ficha.

    Las ramas de salida se construyen aca de nuevo (no se toca el camino de
    F07/F08): duplicar 20 lineas es mas barato que arriesgar el golden con
    un refactor.
    """
    js_puerta, modo = _js_puerta(path_in, mapeo_path)

    if not ficha_out:
        stem = os.path.splitext(os.path.basename(path_in))[0]
        out_dir = os.path.dirname(path_out) or "."
        ficha_out = os.path.join(out_dir, f"ficha_entrada_{stem}.md")

    nodos = _nodos_lectura(path_in)[:2]        # trigger + leer, SIN extract csv
    x = 400
    if modo == "planilla":
        nodos.append({
            "parameters": {"operation": "xlsx", "options": {"headerRow": True}},
            "id": "n2-planilla",
            "name": "Planilla a items",
            "type": "n8n-nodes-base.extractFromFile",
            "typeVersion": 1,
            "position": [x, 0],
        })
        x += 200

    puerta = _nodo_code("nP-puerta", "Puerta de entrada", js_puerta, x, code_type_version)
    nodos.append(puerta)
    x += 200

    ficha_code = _nodo_code("nE-ficha", "Ficha de entrada", JS_F11_FICHA, x, code_type_version)
    ficha_code["position"] = [x, -300]
    ficha_write = {
        "parameters": {"operation": "write", "fileName": ficha_out, "options": {}},
        "id": "nE-ficha-escribir",
        "name": "Escribir ficha de entrada",
        "type": "n8n-nodes-base.readWriteFile",
        "typeVersion": 1,
        "position": [x + 200, -300],
    }
    reja = _nodo_code("nR-reja", "Reja anti-silencio", JS_F11_REJA, x, code_type_version)
    nodos += [ficha_code, ficha_write, reja]
    x += 200

    cadena = [reja]
    for node_id, name, js in spec["codes"]:
        js_final = _params(js, fecha_corte, seg_json)
        n = _nodo_code(node_id, name, js_final, x, code_type_version)
        nodos.append(n)
        cadena.append(n)
        x += 200
    sort_node = cadena[-1]

    branch_paths = {"comercial": path_out, "auditoria": path_out_audit, "reporte": path_reporte}
    sd = spec["salida_dual"]
    active = [(k, sd[k], branch_paths[k]) for k in sd if branch_paths.get(k)]
    y_offsets = [-200, 200, 600]
    branch_nodes = []
    for i, (key, (b_id, b_name, b_js), b_path) in enumerate(active):
        y = y_offsets[i] if i < len(y_offsets) else 200 * (i + 2)
        code_node = _nodo_code(b_id, b_name, b_js, x, code_type_version)
        code_node["position"] = [x, y]
        write_node = {
            "parameters": {"operation": "write", "fileName": b_path, "options": {}},
            "id": f"nW{i}-escribir-{key}",
            "name": f"Escribir {b_name}",
            "type": "n8n-nodes-base.readWriteFile",
            "typeVersion": 1,
            "position": [x + 200, y],
        }
        nodos += [code_node, write_node]
        branch_nodes.append((code_node, write_node))

    connections = {}
    connections.update(link(nodos[0]["name"], nodos[1]["name"]))       # trigger -> leer
    if modo == "planilla":
        connections.update(link(nodos[1]["name"], "Planilla a items"))
        connections.update(link("Planilla a items", puerta["name"]))
    else:
        connections.update(link(nodos[1]["name"], puerta["name"]))

    # La ficha PRIMERO (se escribe antes de que la reja pueda frenar).
    connections[puerta["name"]] = {
        "main": [[
            {"node": ficha_code["name"], "type": "main", "index": 0},
            {"node": reja["name"], "type": "main", "index": 0},
        ]]
    }
    connections.update(link(ficha_code["name"], ficha_write["name"]))

    for a, b in zip(cadena, cadena[1:]):
        connections.update(link(a["name"], b["name"]))

    connections[sort_node["name"]] = {
        "main": [[
            {"node": cn["name"], "type": "main", "index": 0}
            for cn, _ in branch_nodes
        ]]
    }
    for cn, wn in branch_nodes:
        connections.update(link(cn["name"], wn["name"]))

    return {
        "id": spec["id"],
        "name": spec["name"],
        "nodes": nodos,
        "connections": connections,
        "active": False,
        "pinData": {},
        "settings": {"executionOrder": "v1"},
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("destino")
    ap.add_argument("csv_in")
    ap.add_argument("csv_out")
    ap.add_argument("--fase", default="00")
    ap.add_argument("--fecha-corte", default="")
    ap.add_argument("--csv-out-audit", default="")
    ap.add_argument("--reporte-out", default="")
    ap.add_argument("--mapeo", default="",
                    help="F11: config/mapeo_<cliente>.json (opcional)")
    ap.add_argument("--ficha-out", default="",
                    help="F11: ruta de la ficha de entrada (default: salidas/ficha_entrada_<archivo>.md)")
    ap.add_argument("--segmentacion", default="",
                    help="F12: config de segmentacion (default: config/segmentacion.json)")
    ap.add_argument("--code-tv", type=float, default=2)
    ap.add_argument("--convert-tv", type=float, default=1.1)
    args = ap.parse_args()

    wf = build(
        args.csv_in,
        args.csv_out,
        fase=args.fase,
        code_type_version=args.code_tv,
        convert_type_version=args.convert_tv,
        fecha_corte=args.fecha_corte,
        path_out_audit=args.csv_out_audit,
        path_reporte=args.reporte_out,
        mapeo_path=args.mapeo,
        ficha_out=args.ficha_out,
        segmentacion_path=args.segmentacion,
    )
    with open(args.destino, "w", encoding="utf-8") as fh:
        json.dump(wf, fh, indent=2, ensure_ascii=False)
    print("escrito:", args.destino)
