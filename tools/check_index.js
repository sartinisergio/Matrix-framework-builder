#!/usr/bin/env node
// Controllo di qualità di un JSON indice generato da Matrix Framework Builder.
//
// Uso:
//   node tools/check_index.js indice.json
//   node tools/check_index.js indice.json --source testo_indice.txt
//
// Controlla: capitoli mancanti/duplicati, sezioni mancanti nella numerazione,
// stesso numero con titoli diversi, page_start non crescenti o sospettosamente
// piccoli (pagina del PDF-indice invece di quella del libro), capitoli senza
// sezioni. Con --source confronta anche le sezioni "N.X" con quelle presenti
// nel testo del PDF (es. estratto con: pdftotext -layout libro.pdf testo.txt).
//
// Esce con codice 1 se trova problemi. Non modifica nessun file.

const fs = require('fs');

const args = process.argv.slice(2);
const file = args.find(a => !a.startsWith('--'));
const srcIdx = args.indexOf('--source');
const sourceFile = srcIdx !== -1 ? args[srcIdx + 1] : null;
if (!file) {
  console.log('Uso: node tools/check_index.js indice.json [--source testo.txt]');
  process.exit(2);
}

const data = JSON.parse(fs.readFileSync(file, 'utf8'));
const chs = data.index_chapters ||
  (function find(o) {
    if (Array.isArray(o) && o.length && o[0] && 'number' in o[0] && 'title' in o[0]) return o;
    if (o && typeof o === 'object') for (const k of Object.keys(o)) { const r = find(o[k]); if (r) return r; }
    return null;
  })(data);
if (!chs) { console.log('Nessun elenco di capitoli trovato'); process.exit(2); }

const problems = []; // da correggere
const notes = [];    // informativi (box, sottovoci): non sono errori

const nums = chs.map(c => Number(c.number));
const seenCh = {};
nums.forEach((n, i) => {
  if (seenCh[n] !== undefined) problems.push(`Capitolo ${n} duplicato: "${chs[seenCh[n]].title}" / "${chs[i].title}"`);
  seenCh[n] = i;
});
const minN = Math.min(...nums), maxN = Math.max(...nums);
for (let n = minN; n <= maxN; n++) if (!(n in seenCh)) problems.push(`Capitolo ${n} MANCANTE`);
if (minN !== 1) problems.push(`Il primo capitolo è ${minN}, non 1`);

const BOX = /^(?:RI)?QUADRO\b|^SALUTE E MEDICINA\b|^NUCLEI FONDANTI\b|^CONCETTI CHIAVE\b|^RISORSE DIGITALI\b/i;
let totSec = 0, prevPage = 0;
const allNumbered = new Set();

chs.forEach(c => {
  const p = c.page_start;
  if (p == null) problems.push(`Cap ${c.number}: page_start assente`);
  else {
    if (p < prevPage) problems.push(`Cap ${c.number}: page_start ${p} inferiore al capitolo precedente (${prevPage})`);
    prevPage = p;
  }
  const secs = c.sections || [];
  totSec += secs.length;
  if (!secs.length) problems.push(`Cap ${c.number} "${c.title}": nessuna sezione (può essere corretto se il libro non ne ha)`);

  const byX = {};
  let lastP = p || 0;
  secs.forEach(s => {
    const num = String(s.number).trim();
    const m = /^(\d+)\.(\d+)$/.exec(num);
    if (!m) {
      if (/^QR/i.test(num)) problems.push(`Cap ${c.number}: voce "${num}" è un rimando online, non una sezione ("${s.title}")`);
      else if (BOX.test(num)) notes.push(`Cap ${c.number}: box "${num}"`);
      else if (/^\d+\.\d+\.\d+/.test(num)) notes.push(`Cap ${c.number}: sottosezione a 3 livelli "${num}"`);
      else problems.push(`Cap ${c.number}: numero malformato "${num}" ("${s.title}")`);
      return;
    }
    if (Number(m[1]) !== Number(c.number)) problems.push(`Cap ${c.number}: sezione ${num} con prefisso sbagliato ("${s.title}")`);
    const x = Number(m[2]);
    if (byX[x]) problems.push(`COLLISIONE ${num}: "${byX[x].title}" / "${s.title}"`);
    byX[x] = s;
    allNumbered.add(num);
    if (s.page_start == null) problems.push(`Sez ${num}: page_start assente`);
    else {
      if (s.page_start < lastP) problems.push(`Sez ${num}: page_start ${s.page_start} inferiore alla precedente (${lastP})`);
      lastP = Math.max(lastP, s.page_start);
    }
  });
  const xs = Object.keys(byX).map(Number);
  if (xs.length) {
    const miss = [];
    for (let x = 1; x <= Math.max(...xs); x++) if (!byX[x]) miss.push(`${c.number}.${x}`);
    if (miss.length) problems.push(`Cap ${c.number}: sezioni mancanti nella numerazione: ${miss.join(', ')}`);
  }
});

const pages = chs.map(c => c.page_start).filter(x => x != null);
if (pages.length && Math.max(...pages) <= 30) {
  problems.push(`page_start massimo dei capitoli = ${Math.max(...pages)}: probabile pagina del PDF-indice invece di quella del libro`);
}

// Confronto con il testo sorgente (facoltativo)
if (sourceFile) {
  const txt = fs.readFileSync(sourceFile, 'utf8');
  const re = /(?:^|\s{2,})(\d{1,2}\.\d{1,2})\s+[A-ZÈÉ"“]/gm;
  const inSrc = new Set();
  let m;
  while ((m = re.exec(txt))) {
    const [a, b] = m[1].split('.').map(Number);
    if (a >= minN && a <= maxN && b >= 1 && b <= 30) inSrc.add(m[1]);
  }
  const byNum = (x, y) => { const [a1, b1] = x.split('.').map(Number), [a2, b2] = y.split('.').map(Number); return a1 - a2 || b1 - b2; };
  const missing = [...inSrc].filter(x => !allNumbered.has(x)).sort(byNum);
  const extra = [...allNumbered].filter(x => !inSrc.has(x)).sort(byNum);
  if (missing.length) problems.push(`Nel testo sorgente ma NON nel JSON: ${missing.join(', ')}`);
  if (extra.length) notes.push(`Nel JSON ma non trovate nel testo (potrebbero essere andate a capo, o inventate): ${extra.join(', ')}`);
  if (!inSrc.size) notes.push('Nel testo sorgente non ho trovato sezioni "N.X": il libro potrebbe non avere sezioni numerate');
}

console.log(`${data.title || file}`);
console.log(`Capitoli: ${chs.length} (${minN}–${maxN}) | Sezioni: ${totSec} | page_start capitoli: ${Math.min(...pages)}–${Math.max(...pages)}`);
console.log(`\n== PROBLEMI (${problems.length}) ==`);
problems.forEach(p => console.log('- ' + p));
if (notes.length) {
  console.log(`\n== NOTE (${notes.length}) ==`);
  notes.slice(0, 15).forEach(n => console.log('- ' + n));
  if (notes.length > 15) console.log(`- … e altre ${notes.length - 15}`);
}
console.log('\n== SEZIONI PER CAPITOLO ==');
console.log(chs.map(c => `${c.number}:${(c.sections || []).length}`).join('  '));
process.exit(problems.length ? 1 : 0);
