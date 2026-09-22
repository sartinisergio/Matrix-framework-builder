// PROTOTIPO — non collegato all'app.
// Ricostruisce le voci di un indice a partire dai frammenti di testo di pdf.js
// USANDO LE COORDINATE (x, y, larghezza) invece di unirli con uno spazio.
//
// Passi: frammenti → righe visive → colonne → intestazioni ripetute → voci
// (numero, titolo, pagina) → testo "una voce per riga".
//
// Nessuna dipendenza: funziona nel browser (window.EstraiRighe) e in Node (require).
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.EstraiRighe = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // ── 1. Frammenti ────────────────────────────────────────────────────────
  function frammenti(items) {
    var out = [], visti = {};
    items.forEach(function (it) {
      if (!it.str || !it.str.trim()) return;
      // Testo stampato due volte nello stesso punto (falso grassetto, ombra: es. Strachan, "INDICE GENERALE
      // INDICE GENERALE"): un frammento identico nella stessa posizione non aggiunge nulla, si tiene una volta.
      var chiave = it.str + '|' + Math.round(it.transform[4] / 2) + '|' + Math.round(it.transform[5] / 2);
      if (visti[chiave]) return;
      visti[chiave] = true;
      out.push({
        s: it.str,
        fn: it.fontName || '',
        x: it.transform[4],
        y: it.transform[5],
        w: it.width,
        h: Math.abs(it.height) || Math.abs(it.transform[3]) || 10
      });
    });
    return out;
  }

  // Testo come lo produce oggi l'app: tutto su una riga, unito da spazi.
  function testoPiatto(items) {
    return items.map(function (i) { return i.str; }).join(' ');
  }

  var RE_SOLO_PAGINA = /^\s*(\d{1,4}|[ivxlcdm]{1,7}|[A-Za-z]{1,2}-\d{1,3})\s*$/i;

  // ── 2. Colonne ──────────────────────────────────────────────────────────
  // Cerca la fascia verticale vuota più larga nella parte centrale della pagina.
  // Restituisce la x del centro della fascia, oppure null se la pagina è a colonna unica.
  // tol = quanti frammenti possono attraversare la fascia senza che smetta di essere "vuota" (titoli o
  // voci lunghe che sconfinano). Con pochi (2) è la lettura prudente; con più, si trovano colonne strette.
  function trovaGutter(fr, W, tol) {
    tol = tol || 2;
    if (fr.length < 20) return null;
    var cov = new Uint16Array(Math.ceil(W) + 2);
    fr.forEach(function (f) {
      if (f.w > 0.6 * W) return;                 // titoli a tutta larghezza: non contano
      // I numeri di pagina, allineati a destra, possono cadere dentro la fascia tra le colonne
      // (Alberts: colonna sinistra fino a 260, i suoi numeri a 276-288, colonna destra da 298):
      // non contano, altrimenti la fascia si sposta e i numeri finiscono nella colonna sbagliata.
      if (RE_SOLO_PAGINA.test(f.s)) return;
      var a = Math.max(0, Math.floor(f.x)), b = Math.min(cov.length - 1, Math.ceil(f.x + f.w));
      for (var x = a; x <= b; x++) cov[x]++;
    });
    var lo = Math.floor(W * 0.30), hi = Math.ceil(W * 0.70);
    // "vuoto" = attraversato al massimo da 2 frammenti: un titolo o un'intestazione a cavallo
    // delle colonne non deve impedire di trovare la fascia.
    var best = null, run = 0, start = 0;
    for (var x = lo; x <= hi; x++) {
      if (cov[x] <= tol) { if (run === 0) start = x; run++; }
      if (cov[x] > tol || x === hi) {
        if (run >= 9 && (!best || run > best.len)) best = { from: start, len: run };
        run = 0;
      }
    }
    if (!best) return null;
    // Il confine sta vicino al lato DESTRO della fascia (poco prima dell'inizio della colonna
    // destra): i numeri di pagina che restano nella fascia appartengono alla colonna sinistra.
    var g = best.from + best.len - Math.min(6, best.len / 2);
    var sx = 0, dx = 0;
    fr.forEach(function (f) { if (f.x + f.w / 2 < g) sx++; else dx++; });
    if (sx < fr.length * 0.15 || dx < fr.length * 0.15) return null;
    return { g: g, from: best.from };
  }

  // ── 3. Righe visive ─────────────────────────────────────────────────────
  // Spazio tra due frammenti vicini: nessuno / spazio / tabulazione (celle separate).
  function uniscis(fr) {
    fr.sort(function (a, b) { return a.x - b.x; });
    var t = '';
    for (var i = 0; i < fr.length; i++) {
      var f = fr[i];
      if (i > 0) {
        var p = fr[i - 1], gap = f.x - (p.x + p.w), h = Math.max(p.h, f.h);
        var spazioGia = /\s$/.test(t) || /^\s/.test(f.s);
        if (gap > 0.9 * h) t = t.replace(/[ ]+$/, '') + '\t';
        else if (gap > 0.12 * h && !spazioGia) t += ' ';
      }
      t += f.s;
    }
    return t.replace(/[ ]{2,}/g, ' ').replace(/[ ]*\t[ ]*/g, '\t').trim();
  }

  function raggruppaRighe(fr, col) {
    var ord = fr.slice().sort(function (a, b) { return (b.y - a.y) || (a.x - b.x); });
    var righe = [];
    ord.forEach(function (f) {
      var r = null;
      for (var i = righe.length - 1; i >= 0 && i >= righe.length - 3; i--) {
        if (Math.abs(righe[i].y - f.y) <= 0.4 * Math.max(righe[i].h, f.h)) { r = righe[i]; break; }
      }
      if (!r) { r = { y: f.y, h: f.h, frags: [], col: col }; righe.push(r); }
      r.frags.push(f);
      if (f.h > r.h) r.h = f.h;
    });
    righe.forEach(function (r) {
      r.text = uniscis(r.frags);                       // (ordina i frammenti per x)
      // tipo di carattere della riga: quello del frammento più largo (il titolo) e quello del primo (numero/lettera)
      r.fontN = r.frags[0].fn;
      r.font = r.frags.slice().sort(function (a, b) { return b.w - a.w; })[0].fn;
      r.x0 = Math.min.apply(null, r.frags.map(function (f) { return f.x; }));
      r.x1 = Math.max.apply(null, r.frags.map(function (f) { return f.x + f.w; }));
    });
    return righe;
  }

  // Righe di UNA pagina nell'ordine di lettura: per ogni fascia (delimitata dalle righe a
  // tutta larghezza) prima la colonna sinistra, poi la destra.
  // conBlocchi = true: oltre alle righe a tutta larghezza, anche le fasce bianche orizzontali separano
  // blocchi da leggere uno alla volta (vedi fasceBianche). Quale lettura sia giusta lo decide elabora().
  function righePagina(items, W, conBlocchi, tol) {
    var fr = frammenti(items);
    var gt = trovaGutter(fr, W, tol), g = gt ? gt.g : null;
    if (g === null) {
      return { righe: raggruppaRighe(fr, 'U'), colonne: 1, gutter: null };
    }
    var L = [], R = [], F = [];
    fr.forEach(function (f) {
      if (f.x < g - 2 && f.x + f.w > g + 2) F.push(f);
      // Dentro la fascia tra le colonne i numeri di pagina ("48") chiudono la voce di sinistra, mentre
      // un numero di sezione ("23.6") apre quella di destra: si distinguono dal contenuto.
      else if (f.x + f.w / 2 < g && !(f.x >= gt.from && !RE_SOLO_PAGINA.test(f.s))) L.push(f);
      else R.push(f);
    });
    var rl = raggruppaRighe(L, 'L'), rr = raggruppaRighe(R, 'R'), rf = raggruppaRighe(F, 'F');
    // Confini tra un blocco e il successivo: le righe a tutta larghezza e le fasce bianche orizzontali
    // che attraversano l'intera pagina. Ogni blocco si legge da solo: prima sinistra, poi destra.
    var bord = rf.map(function (f) { return { y: f.y, f: f }; });
    if (conBlocchi) fasceBianche(rl.concat(rr, rf)).forEach(function (y) { bord.push({ y: y, f: null }); });
    bord.sort(function (a, b) { return b.y - a.y; });
    function fascia(r) {
      var n = 0;
      bord.forEach(function (x) { if (x.y > r.y + 1) n++; });
      return n;
    }
    var out = [];
    for (var b = 0; b <= bord.length; b++) {
      var inL = rl.filter(function (r) { return fascia(r) === b; }).sort(function (a, c) { return c.y - a.y; });
      var inR = rr.filter(function (r) { return fascia(r) === b; }).sort(function (a, c) { return c.y - a.y; });
      out = out.concat(inL, inR);
      if (b < bord.length && bord[b].f) out.push(bord[b].f);
    }
    return { righe: out, colonne: 2, gutter: g };
  }

  // Fasce orizzontali bianche che attraversano TUTTA la pagina, molto più alte dell'interlinea (es. tra la
  // fine di un capitolo e l'inizio del successivo, quando questo comincia in basso in entrambe le colonne):
  // senza, si leggerebbe tutta la colonna sinistra e poi tutta la destra, e il capitolo che segue finirebbe
  // prima della fine di quello precedente. Restituisce le y di mezzo di ciascuna fascia.
  function fasceBianche(linee) {
    if (linee.length < 8) return [];
    var iv = linee.map(function (r) { return [r.y - 0.3 * r.h, r.y + 0.85 * r.h]; }).sort(function (a, b) { return a[0] - b[0]; });
    var diff = [];
    var ys = linee.map(function (r) { return r.y; }).sort(function (a, b) { return b - a; });
    for (var i = 1; i < ys.length; i++) { var d = ys[i - 1] - ys[i]; if (d > 5 && d < 40) diff.push(d); }
    if (diff.length < 5) return [];
    diff.sort(function (a, b) { return a - b; });
    var pitch = diff[Math.floor(diff.length / 2)];
    var soglia = Math.max(20, 1.9 * pitch);
    var out = [], hi = iv[0][1];
    for (var j = 1; j < iv.length; j++) {
      if (iv[j][0] - hi >= soglia) out.push((iv[j][0] + hi) / 2);
      if (iv[j][1] > hi) hi = iv[j][1];
    }
    return out;
  }

  // ── 4. Intestazioni e piè di pagina ─────────────────────────────────────
  // Una riga in cima o in fondo a una colonna che ricompare (a meno di numeri di pagina)
  // su più pagine è un'intestazione corrente: non è una voce dell'indice.
  function chiaveIntestazione(t) {
    return t.toLowerCase().split(/[\s\t]+/).filter(function (w) {
      return w && !/^([ivxlcdm]+|\d+)$/i.test(w);
    }).join(' ').replace(/[^a-zàèéìòù© ]/g, '').trim();
  }

  function marcaIntestazioni(pagine) {
    var conta = {};
    var estremi = pagine.map(function (pg) {
      var perCol = {}, out = [];
      pg.righe.forEach(function (r) { (perCol[r.col] = perCol[r.col] || []).push(r); });
      Object.keys(perCol).forEach(function (c) {
        var rs = perCol[c];
        [rs[0], rs[rs.length - 1]].forEach(function (r) { if (out.indexOf(r) === -1) out.push(r); });
      });
      out.forEach(function (r) {
        r.chiave = chiaveIntestazione(r.text);
        if (r.chiave) conta[r.chiave] = (conta[r.chiave] || 0) + 1;
      });
      return out;
    });
    var soglia = Math.max(3, Math.ceil(pagine.length * 0.25));
    estremi.forEach(function (out) {
      out.forEach(function (r) {
        // chiave vuota = solo numeri: è un numero di pagina solo se lo è davvero ("XI", "48"),
        // non un numero di sezione ("23.6")
        if ((r.chiave === '' && /^\s*(\d{1,4}|[ivxlcdm]{1,7})\s*$/i.test(r.text)) || conta[r.chiave] >= soglia) r.intestazione = true;
      });
    });
  }

  // ── 5. Voci ─────────────────────────────────────────────────────────────
  // NB: in JavaScript \b non funziona dopo una lettera accentata ("UNITÀ"): si usa un lookahead.
  var RE_MARCATORE_MAIUSC = /^(CAPITOLO|CAP\.|CHAPTER|PARTE|UNIT[ÀA]|SEZIONE)(?![A-Za-zÀ-ÿ])[ \t]*(?:([0-9]{1,2}|[IVX]{1,5})(?![A-Za-zÀ-ÿ0-9]))?[ \t]*[-–—:.]?[ \t]*/;
  var RE_MARCATORE_NUM = /^(Capitolo|Cap\.|Chapter|Parte|Unit[àa]|Sezione)[ \t]+([0-9]{1,2}|[IVX]{1,5})(?![A-Za-zÀ-ÿ0-9])[ \t]*[-–—:.]?[ \t]*/;
  var RE_NUMERO = /^(\d{1,2}(?:\.\d{1,2}){0,3}|[ivx]{1,4}\.\d{1,2})\.?(?:[ \t]+|(?=[A-ZÀ-Ý])|$)/;
  var RE_ROMANO_PUNTO = /^([IVX]{1,5})\.[ \t]+(?=[A-ZÀ-Ý])/;
  var RE_PALLINO =/^([■•▪●◦□▫‣·])[ \t]*/;
  var RE_QR = /^QR\s?(?:code)?\s?\d{1,2}-\d/i;
  var RE_PAGINA = /^(.*?)(?:[\s.…·_]*[.…·]{3,}[\s.…·_]*|[\s.…·_]*\t[\s.…·_]*)(\d{1,4}|[ivxlcdm]{1,7}|[A-Za-z]{1,2}-\d{1,3})\s*$/i;

  function separaPagina(t) {
    var m = t.match(RE_PAGINA);
    if (!m) return { testo: t.replace(/[.…·_\s]+$/, ''), pagina: null };
    return { testo: m[1].replace(/\t/g, ' ').trim(), pagina: m[2] };
  }

  function analizzaRiga(r) {
    // "C A P I T O L O 1" (lettere spaziate per lo stile grafico) → "CAPITOLO 1"
    // (con lo stile spaziato anche il numero a due cifre lo è: "C A P I T O L O 1 0" → "CAPITOLO 10")
    var t = r.text.replace(/^C A P I T O L O (\d) (\d)(?!\d)/, 'C A P I T O L O $1$2')
      .replace(/(?<![A-Za-zÀ-ÿ])(?:[A-ZÀ-Þ] ){3,}[A-ZÀ-Þ](?![A-Za-zÀ-ÿ])/g, function (m) { return m.replace(/ /g, ''); });
    var o = { inizio: false, tipo: null, numero: null, pallino: null };
    var m;
    if (RE_QR.test(t)) { o.inizio = true; o.tipo = 'qr'; }
    else if ((m = t.match(RE_MARCATORE_NUM)) || (m = t.match(RE_MARCATORE_MAIUSC))) {
      o.inizio = true; o.tipo = 'capitolo';
      o.numero = (m[1].toUpperCase() + (m[2] ? ' ' + m[2] : ''));
      t = t.slice(m[0].length);
    } else if ((m = t.match(RE_ROMANO_PUNTO))) {           // "II. Sensazione" (parte, numero romano)
      o.inizio = true; o.tipo = 'capitolo'; o.numero = 'PARTE ' + m[1]; t = t.slice(m[0].length);
    } else if ((m = t.match(RE_PALLINO))) {
      o.inizio = true; o.tipo = 'pallino'; o.pallino = m[1]; t = t.slice(m[0].length);
    } else if ((m = t.match(RE_NUMERO))) {
      o.inizio = true; o.tipo = 'numerata'; o.numero = m[1]; t = t.slice(m[0].length);
    }
    var sp = separaPagina(t);
    o.testo = sp.testo.replace(/\t/g, ' ').replace(/\s{2,}/g, ' ').trim();
    o.pagina = sp.pagina;
    return o;
  }

  // Parole del documento (minuscole) per decidere sui trattini a fine riga.
  function vocabolario(pagine) {
    var v = {};
    pagine.forEach(function (pg) {
      pg.righe.forEach(function (r) {
        (r.text.match(/[A-Za-zÀ-ÿ]+(?:-[A-Za-zÀ-ÿ]+)*-?/g) || []).forEach(function (w) {
          if (/-$/.test(w)) return;              // frammento di riga spezzata: non è una parola
          v[w.toLowerCase()] = true;
        });
      });
    });
    return v;
  }

  // Attacca la riga seguente. Se la precedente finisce con un trattino tra due lettere può essere
  // una sillabazione ("relazio-|ne") o un trattino vero ("chimica-|fisica"): si guarda se il
  // documento contiene altrove la forma unita o quella col trattino; se nessuna, si toglie il
  // trattino (è il caso più frequente) e si segnala il dubbio.
  function attacca(prec, nuovo, vocab) {
    var maiusc = /[A-ZÀ-Þ]{2}-$/.test(prec) && /^[A-ZÀ-Þ]/.test(nuovo);   // "ORGANIZZA-" + "ZIONE"
    if (/[A-Za-zÀ-ÿ]-$/.test(prec) && (/^[a-zà-ÿ]/.test(nuovo) || maiusc)) {
      var pw = (prec.match(/([A-Za-zÀ-ÿ]+)-$/) || [])[1] || '';
      var nw = (nuovo.match(/^[A-Za-zÀ-ÿ]+/) || [''])[0];
      var unita = (pw + nw).toLowerCase(), col = (pw + '-' + nw).toLowerCase();
      if (vocab[col] && !vocab[unita]) return { t: prec + nuovo, sill: false, dubbia: false };
      // "chimica-|fisica": se entrambe le metà sono parole intere che il documento usa altrove,
      // è un composto col trattino vero; "relazio-|ne" o "mam-|miferi" non lo sono.
      if (pw.length >= 4 && nw.length >= 4 && vocab[pw.toLowerCase()] && vocab[nw.toLowerCase()] && !vocab[unita]) {
        return { t: prec + nuovo, sill: false, dubbia: true };
      }
      return { t: prec.slice(0, -1) + nuovo, sill: true, dubbia: !vocab[unita] };
    }
    return { t: (prec + ' ' + nuovo).trim(), sill: false, dubbia: false };
  }

  // Una riga senza numero né pallino, dopo una voce ancora senza pagina, è la sua continuazione
  // solo se "sembra" la stessa cosa: stessa dimensione del carattere, non rientrata meno della
  // riga precedente, e non da maiuscolo a minuscolo (titolo del capitolo → prima sezione).
  function puoContinuare(cur, r, a) {
    if (cur.titolo === '') return true;           // marcatore ("CAPITOLO 3") ancora senza titolo
    if (cur.hRef !== null && Math.abs(r.h - cur.hRef) > 1) return false;
    if (r.x0 < cur.xUlt - 3) return false;
    // un rimando QR senza pagina continua a capo solo se la riga dopo è rientrata;
    // se parte allo stesso rientro è la voce successiva
    if (cur.tipo === 'qr' && r.x0 < cur.x0 + 3) return false;
    var tutto = cur.titolo === cur.titolo.toUpperCase() && /[A-ZÀ-Þ]{3}/.test(cur.titolo);
    if (tutto && /[a-zà-ÿ]/.test(a.testo)) return false;
    return true;
  }

  function costruisciVoci(pagine) {
    marcaIntestazioni(pagine);
    var vocab = vocabolario(pagine);
    var voci = [], cur = null;
    pagine.forEach(function (pg, pi) {
      pg.righe.forEach(function (r) {
        if (r.intestazione) return;
        var a = analizzaRiga(r);
        if (!a.testo && a.pagina === null && !a.inizio) return;
        if (a.inizio || cur === null || cur.pagina !== null || !puoContinuare(cur, r, a)) {
          cur = {
            tipo: a.inizio ? a.tipo : 'testo',
            numero: a.numero, pallino: a.pallino,
            titolo: a.testo, pagina: a.pagina,
            pdfPagina: pi + 1, x0: r.x0, col: r.col, righe: 1, sillabazioni: 0, sillabazioniDubbie: [],
            hRef: a.testo ? r.h : null, xUlt: r.x0, h: r.h, font: r.font, fontN: r.fontN
          };
          voci.push(cur);
        } else {                                  // continuazione di un titolo su più righe
          var j = attacca(cur.titolo, a.testo, vocab);
          cur.titolo = j.t; if (j.sill) cur.sillabazioni++;
          if (j.dubbia) cur.sillabazioniDubbie.push(j.t.slice(0, 60));
          if (cur.hRef === null && a.testo) cur.hRef = r.h;
          cur.xUlt = r.x0;
          cur.pagina = a.pagina; cur.righe++;
        }
      });
    });
    // Titoli di capitolo in caratteri grandi: il numero di pagina può restare attaccato al titolo
    // ("La chimica che rende possibile la vita 14"). Solo per i capitoli, e lo segnalo.
    voci.forEach(function (v) {
      if (v.tipo === 'capitolo' && v.pagina === null) {
        var m = v.titolo.match(/^(.*[A-Za-zÀ-ÿ’'\)\?]) (\d{1,4})$/);
        if (m) { v.titolo = m[1]; v.pagina = m[2]; v.paginaDedotta = true; }
      }
    });
    return spezzaFlussi(voci);
  }

  // Indici "a paragrafo" (Belsky, Verrocchio, Occhini…): più voci di seguito nella stessa riga,
  // ciascuna con la pagina dopo una virgola o uno spazio ("Il contesto, 5; L'influenza, 5" oppure
  // "Modelli 12 Il modello cognitivo 18"). Le coordinate non aiutano: si spezza il testo dove
  // compare un numero che può essere una pagina. Un numero è una pagina solo se non torna
  // indietro rispetto alla pagina precedente e non salta troppo avanti: "Le 3 C delle terapie"
  // (3 dopo pagina 18) non viene spezzato.
  var SALTO_MAX = 90;
  function spezzaFlusso(testo, ultimaPagina) {
    var re = /(?:^|[\s,;])(\d{1,4})(?=$|\s*[;,.]|\s+[A-ZÀ-Ý“«‘"(‘“])/g;
    var m, pezzi = [], da = 0, ultima = ultimaPagina;
    while ((m = re.exec(testo)) !== null) {
      var n = parseInt(m[1], 10), fine = m.index + m[0].length;
      var prima = testo.slice(da, m.index + (m[0].length - m[1].length)).replace(/^[\s,;.]+|[\s,;.]+$/g, '');
      if (!prima || prima.length < 3) continue;                 // il numero non ha un titolo davanti
      if (n < ultima || n - ultima > SALTO_MAX) continue;        // non può essere la pagina
      pezzi.push({ titolo: prima, pagina: String(n) });
      ultima = n; da = fine; re.lastIndex = fine;
    }
    var resto = testo.slice(da).replace(/^[\s,;.]+|[\s,;.]+$/g, '');
    return { pezzi: pezzi, resto: resto, ultima: ultima };
  }

  function nuova(v, titolo, pagina, tipo) {
    return { tipo: tipo || 'flusso', numero: null, pallino: null, titolo: titolo, pagina: pagina,
             pdfPagina: v.pdfPagina, x0: v.x0, col: v.col, h: v.h, font: v.font, fontN: v.fontN, righe: v.righe, sillabazioni: 0, sillabazioniDubbie: [] };
  }

  function spezzaFlussi(voci) {
    var out = [], ultima = 0;
    voci.forEach(function (v) {
      if (v.tipo === 'qr') { out.push(v); return; }
      // Se la pagina finale era già stata staccata dalla riga, la si rimette in coda: dentro il
      // titolo possono esserci altre voci ("… psicopatologia? 11 Il modello psicoanalitico | 12").
      var pagNum = v.pagina !== null && /^\d+$/.test(v.pagina);
      var testo = pagNum ? v.titolo + ' ' + v.pagina : v.titolo;
      var s = testo.length >= 12 ? spezzaFlusso(testo, ultima) : { pezzi: [], resto: '' };
      var utile = pagNum ? s.pezzi.length >= 2 : s.pezzi.length >= 1;
      if (!utile) {
        // Elenchi in cui le pagine ripartono ("0.1 Disturbo mentale 4", "SCHEDE…"): il numero in
        // coda a una voce numerata o con pallino è la sua pagina anche se torna indietro.
        if (v.pagina === null && (v.tipo === 'numerata' || v.tipo === 'pallino' || v.tipo === 'capitolo')) {
          var m = v.titolo.match(/^(.*[A-Za-zÀ-ÿ’'\)\?]) (\d{1,4})$/);
          if (m && m[1].length >= 3) { v.titolo = m[1]; v.pagina = m[2]; v.paginaDedotta = true; }
        }
        if (v.pagina !== null && /^\d+$/.test(v.pagina)) ultima = parseInt(v.pagina, 10);
        out.push(v); return;
      }
      s.pezzi.forEach(function (p, i) {
        var n = i === 0 ? v : nuova(v);
        n.titolo = p.titolo; n.pagina = p.pagina; out.push(n);
      });
      if (!pagNum && s.resto.length >= 3) out.push(nuova(v, s.resto, null));
      ultima = s.ultima;
    });
    return out;
  }

  // ── 6. Testo di uscita: una voce per riga ───────────────────────────────
  function formattaVoci(voci) {
    return voci.map(function (v) {
      var n = v.tipo === 'qr' ? 'QR' : v.tipo === 'pallino' ? '•' : (v.numero || '-');
      return n + ' | ' + v.titolo + ' | ' + (v.pagina === null ? '' : v.pagina);
    }).join('\n');
  }

  // Punto d'ingresso: riceve, per ogni pagina, {items, larghezza}.
  // Costo di un ordine di lettura: quante volte, lungo le righe, la pagina o il numero di capitolo/sezione
  // TORNANO INDIETRO. In un indice letto nell'ordine giusto non succede (o quasi). È un controllo che vale per
  // qualsiasi formato, e permette di scegliere tra letture diverse della stessa pagina senza conoscerne il formato.
  function costoOrdine(righe) {
    var costo = 0, pagPrec = null, numPrec = null;
    righe.forEach(function (r) {
      var t = r.text, sp = t.match(RE_PAGINA);
      if (sp && /^\d{1,4}$/.test(sp[2])) {
        var p = parseInt(sp[2], 10);
        if (pagPrec !== null && p < pagPrec) costo++;
        pagPrec = p;
      }
      var m = t.match(/^(\d{1,2})\.(\d{1,2})(?=[\s\t]|$)/), n = null;
      if (m) n = [+m[1], +m[2]];
      else if ((m = t.match(/^(?:CAPITOLO\s+)?(\d{1,2})(?=[ \t]+[A-ZÀ-Ý]|$)/i))) n = [+m[1], 0];
      if (n) {
        if (numPrec && (n[0] < numPrec[0] || (n[0] === numPrec[0] && n[1] < numPrec[1]))) costo++;
        numPrec = n;
      }
    });
    return costo;
  }

  function elabora(pagineGrezze) {
    // Letture possibili di una stessa pagina: [a blocchi?, tolleranza nel cercare le colonne]. Si parte dalla
    // più prudente; una lettura diversa la sostituisce solo se riduce davvero le inversioni (le più
    // "sensibili" solo se le riducono di almeno 2, o le azzerano), così una pagina già a posto non cambia.
    var LETTURE = [[false, 2], [true, 2], [false, 8], [true, 8], [false, 16], [true, 16]];
    var pagine = pagineGrezze.map(function (p) {
      var best = righePagina(p.items, p.larghezza, false, 2);
      var base = costoOrdine(best.righe), bc = base;
      var nome = best.colonne < 2 ? 'unica' : 'colonne';
      for (var i = 1; i < LETTURE.length; i++) {
        var c = righePagina(p.items, p.larghezza, LETTURE[i][0], LETTURE[i][1]);
        if (c.colonne < 2) continue;
        var cc = costoOrdine(c.righe);
        if (cc < bc && (LETTURE[i][1] === 2 || bc - cc >= 2 || cc === 0)) {
          best = c; bc = cc; nome = (LETTURE[i][0] ? 'blocchi' : 'colonne') + (LETTURE[i][1] > 2 ? '+' : '');
        }
      }
      best.strategia = nome; best.costo = bc; best.costoBase = base;
      return best;
    });
    var voci = costruisciVoci(pagine);
    return { pagine: pagine, voci: voci, testo: formattaVoci(voci) };
  }

  return {
    elabora: elabora, testoPiatto: testoPiatto, righePagina: righePagina,
    costruisciVoci: costruisciVoci, formattaVoci: formattaVoci
  };
});
