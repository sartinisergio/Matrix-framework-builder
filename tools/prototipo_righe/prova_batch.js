// PROTOTIPO — non collegato all'app. Prova l'estrazione per righe su uno o più PDF.
//
//   node prova_batch.js libro.pdf [altro.pdf ...] [--out cartella]
//
// Richiede pdfjs-dist 3.11.174 (la stessa versione dell'app), fuori dal repository:
//   npm install pdfjs-dist@3.11.174        (in una cartella qualsiasi)
//   NODE_PATH=<cartella>/node_modules node prova_batch.js ...
const fs = require('fs');
const path = require('path');
const pdfjs = require('pdfjs-dist/legacy/build/pdf.js');
const E = require('./estrai_righe.js');

async function leggi(file) {
  const pdf = await pdfjs.getDocument({ data: new Uint8Array(fs.readFileSync(file)), verbosity: 0 }).promise;
  const pagine = [];
  for (let p = 1; p <= pdf.numPages; p++) {
    const page = await pdf.getPage(p);
    const tc = await page.getTextContent();
    pagine.push({ items: tc.items, larghezza: page.getViewport({ scale: 1 }).width });
  }
  return pagine;
}

function statistiche(pagine, r) {
  const v = r.voci, tipi = {};
  v.forEach(x => { tipi[x.tipo] = (tipi[x.tipo] || 0) + 1; });
  const utili = v.filter(x => x.tipo !== 'qr');
  return {
    pagine: pagine.length,
    pagineDueColonne: r.pagine.filter(p => p.colonne === 2).length,
    voci: v.length, tipi,
    conPagina: utili.filter(x => x.pagina !== null).length,
    senzaPagina: utili.filter(x => x.pagina === null).length,
    sillabazioni: v.reduce((s, x) => s + x.sillabazioni, 0)
  };
}

module.exports = { leggi, statistiche };

if (require.main === module) {
  const args = process.argv.slice(2);
  let out = null;
  const oi = args.indexOf('--out');
  if (oi !== -1) { out = args[oi + 1]; args.splice(oi, 2); fs.mkdirSync(out, { recursive: true }); }
  (async () => {
    for (const f of args) {
      const pagine = await leggi(f);
      const r = E.elabora(pagine);
      const s = statistiche(pagine, r);
      console.log(path.basename(f) + '  ' + JSON.stringify(s));
      if (out) {
        const base = path.join(out, path.basename(f, '.pdf'));
        fs.writeFileSync(base + '.righe.txt', r.testo, 'utf8');
        fs.writeFileSync(base + '.piatto.txt', pagine.map(p => E.testoPiatto(p.items)).join('\n'), 'utf8');
        fs.writeFileSync(base + '.voci.json', JSON.stringify(r.voci, null, 1), 'utf8');
      }
    }
  })();
}
