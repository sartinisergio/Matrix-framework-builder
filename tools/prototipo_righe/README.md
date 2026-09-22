# Prototipo: estrazione dell'indice per righe

**Non è collegato all'app** (`index.html` non è stato modificato). Serve a verificare se ricostruire le righe
dell'indice dalle coordinate del testo (x, y, larghezza) dà un input migliore di quello di oggi, dove pdf.js
unisce tutto con uno spazio.

## Cosa fa

`estrai_righe.js` riceve i frammenti di testo di pdf.js e produce **una voce per riga**: `numero | titolo | pagina`.

1. raggruppa i frammenti in righe visive (stessa y);
2. trova le due colonne (fascia vuota al centro) e le legge una dopo l'altra;
3. scarta intestazioni e piè di pagina che si ripetono;
4. riconosce capitoli (`CAPITOLO 3`, `UNITÀ 1`, anche a lettere spaziate), sezioni numerate, sottovoci con pallino e rimandi `QR…`;
5. aggancia il numero di pagina (a destra, dopo i puntini) al titolo e unisce i titoli spezzati su più righe
   (sillabazione: toglie il trattino, salvo che il documento contenga altrove la forma con trattino).

6. **Indici "a paragrafo"** (Belsky, Verrocchio, Atkinson…): più voci di seguito nella stessa riga, con la pagina dopo
   una virgola o uno spazio. Le coordinate non bastano, quindi si spezza il testo dove compare un numero che può
   essere una pagina: cioè non torna indietro rispetto alla pagina precedente e non salta oltre 90 pagine
   («Le 3 C delle terapie» non viene spezzato).

7. **Sceglie tra più letture della stessa pagina, con un controllo valido per qualsiasi formato.** Non si può
   sapere in anticipo come è impaginato un indice, ma si sa che, letto nell'ordine giusto, le pagine e i numeri di
   capitolo/sezione **non tornano indietro**. Per ogni pagina si provano più letture (colonne una dopo l'altra, blocchi
   separati da fasce bianche orizzontali, ricerca delle colonne più o meno sensibile) e si tiene quella con meno
   «inversioni»; se nessuna migliora, resta la più prudente. Sui 28 PDF le inversioni totali scendono da 54 a 40 e non
   peggiora nessun libro (Cooper 16 → 8, Hansell 4 → 2, Alberts Essenziale 2 → 0, Ceccarelli 2 → 0). Le inversioni
   restanti sono in parte errori veri (Cooper, pagine 2 e 3: colonne non separate) e in parte struttura vera del libro
   (Kring, Occhini: elenchi di riquadri che ripartono da pagine più basse).
   `segna_indice.html` mostra le pagine del PDF dove succede («Pagine del PDF da controllare»): un errore dichiarato
   invece di uno silenzioso.

## Come provarlo

- **Nel browser:** apri `prova.html` con un doppio clic e scegli un PDF di indice. Mostra affiancati il testo di oggi
  e quello ricostruito, con le statistiche. Non serve installare nulla (pdf.js arriva dalla rete come nell'app).
- **Da terminale, su più PDF** (serve Node.js e `pdfjs-dist@3.11.174`, installato fuori dal repository):

  ```
  npm install pdfjs-dist@3.11.174          # in una cartella qualsiasi
  set NODE_PATH=<cartella>\node_modules
  node prova_batch.js libro.pdf --out cartella_output
  node confronta_indice.js libro.pdf indice.json               # confronto con un indice già fatto
  node confronta_indice.js libro.pdf backup.json "Titolo"      # ... preso dal backup dell'app
  ```

Il confronto conta le sezioni dell'indice di riferimento ritrovate nelle voci estratte e con la stessa pagina.
Se l'indice di riferimento ha errori suoi, le differenze non sono errori del prototipo: sono i punti da guardare nel PDF.

## Limiti noti

- Solo PDF con testo selezionabile (nessun OCR).
- Le regole sono tarate su 28 PDF di biologia e psicologia (`manuali/`). Altri layout (tre colonne, indici a tabella)
  possono richiedere aggiustamenti.
- Molti indici non hanno numeri di pagina (Hooley, Gerrig, Girotto, Bruno, Legrenzi…): le voci escono senza pagina, ed è corretto.
- Nei paragrafi con regola «pagina non decrescente», una pagina che torna indietro (elenchi che ripartono da 1)
  viene accettata solo in coda a una voce numerata o con pallino.
- **Non è stato provato con l'AI.** Le misure confrontano le voci estratte con indici già generati dall'app, che
  possono avere errori loro. Manca il confronto finale: stesso libro, indice generato con il vecchio e con il nuovo testo.
- Sillabazione ambigua ("chimica-fisica" / "relazio-ne"): se il documento non aiuta, il trattino viene tolto e
  il caso è segnalato come "incerto".
- Un rimando `QR…` o una voce senza pagina può ancora inglobare la riga successiva quando i due hanno lo stesso
  rientro e la stessa dimensione del carattere.
