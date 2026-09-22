// PROTOTIPO — non collegato all'app. Confronta le voci estratte per righe con un indice JSON
// già esistente (quello generato dall'app, e magari corretto a mano).
//
//   node confronta_indice.js libro.pdf indice.json            (indice = file con index_chapters)
//   node confronta_indice.js libro.pdf backup.json "Titolo"   (indice preso dal backup dell'app)
//
// ATTENZIONE: l'indice di riferimento può avere errori suoi. Le differenze vanno lette,
// non contate come errori del prototipo: sono i punti da guardare nel PDF.
const fs = require('fs');
const { leggi } = require('./prova_batch.js');
const E = require('./estrai_righe.js');

const norm = t => String(t || '').toLowerCase().replace(/[^a-zà-ÿ0-9 ]/g, '').replace(/\s+/g, ' ').trim();

function caricaIndice(file, titolo) {
  const j = JSON.parse(fs.readFileSync(file, 'utf8'));
  if (j.index_chapters) return j;
  // "Titolo" oppure "Titolo|Autore" (più libri possono avere lo stesso titolo)
  const [t, aut] = String(titolo).split('|');
  const x = (j.indexes || []).find(i => i.title === t && (!aut || String(i.author).indexOf(aut) !== -1));
  if (!x) throw new Error('indice non trovato nel backup: ' + titolo);
  return typeof x.json === 'string' ? JSON.parse(x.json) : x.json;
}

(async () => {
  const [pdf, idxFile, titolo] = process.argv.slice(2);
  const idx = caricaIndice(idxFile, titolo);
  const r = E.elabora(await leggi(pdf));
  const voci = r.voci.filter(v => v.tipo !== 'qr');
  const perNumero = {};
  voci.filter(v => v.tipo === 'numerata').forEach(v => { (perNumero[v.numero] = perNumero[v.numero] || []).push(v); });
  const perTitolo = {};
  voci.forEach(v => { (perTitolo[norm(v.titolo).slice(0, 40)] = perTitolo[norm(v.titolo).slice(0, 40)] || []).push(v); });

  const sez = [];
  (idx.index_chapters || []).forEach(c => (c.sections || []).forEach(s => sez.push({ cap: c.number, ...s })));
  let trovate = 0, paginaUguale = 0, paginaDiversa = [], nonTrovate = [];
  const usate = new Set();
  sez.forEach(s => {
    let c = null;
    // se ci sono più candidate (es. "Concetti chiave" ripetuto in ogni capitolo) si preferisce
    // quella con la stessa pagina dell'indice
    const scegli = arr => (arr || []).find(v => String(v.pagina) === String(s.page_start)) || (arr || [])[0];
    if (/^\d+\.\d+$/.test(String(s.number || ''))) c = scegli(perNumero[s.number]);
    if (!c) c = scegli(perTitolo[norm(s.title).slice(0, 40)]);
    if (!c && s.number) c = scegli(perTitolo[norm(s.number + ' ' + s.title).slice(0, 40)]);
    if (!c) { nonTrovate.push(s); return; }
    trovate++; usate.add(c);
    if (c.pagina !== null && String(c.pagina) === String(s.page_start)) paginaUguale++;
    else paginaDiversa.push({ s: s.number + ' ' + s.title.slice(0, 50), indice: s.page_start, estratta: c.pagina });
  });
  const extra = voci.filter(v => v.tipo === 'numerata' && !usate.has(v));

  console.log('Indice di riferimento: ' + (idx.title || '?') + ' — ' + (idx.index_chapters || []).length + ' capitoli, ' + sez.length + ' sezioni');
  console.log('Sezioni trovate nelle voci estratte : ' + trovate + '/' + sez.length);
  console.log('   di cui con la stessa pagina      : ' + paginaUguale + '/' + trovate);
  console.log('Sezioni NON trovate                 : ' + nonTrovate.length);
  nonTrovate.slice(0, 30).forEach(s => console.log('   - ' + s.number + ' ' + String(s.title).slice(0, 60) + ' (p.' + s.page_start + ')'));
  console.log('Pagina diversa                      : ' + paginaDiversa.length);
  paginaDiversa.slice(0, 30).forEach(d => console.log('   - ' + d.s + '  indice=' + d.indice + '  estratta=' + d.estratta));
  console.log('Voci numerate estratte ma assenti dall\'indice: ' + extra.length);
  extra.slice(0, 30).forEach(v => console.log('   + ' + v.numero + ' ' + v.titolo.slice(0, 60) + ' (p.' + v.pagina + ')'));
})();
