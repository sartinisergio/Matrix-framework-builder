# Strumenti per gli indici

Due strumenti a parte, **non collegati all'app**: servono per controllare e correggere il JSON di un indice
generato dall'app prima di importarlo. Non richiedono installazioni, salvo Node.js per il primo.

## 1. check_index.js — controllo da terminale

```
node tools/check_index.js indice.json
node tools/check_index.js indice.json --source testo_indice.txt
```

Segnala capitoli mancanti o duplicati, sezioni mancanti nella numerazione, stesso numero con titoli diversi,
`page_start` che tornano indietro o troppo piccoli (pagina del PDF-indice invece di quella del libro), capitoli senza
sezioni e voci `QR…`. I box (`RIQUADRO`, `SALUTE E MEDICINA`…) e le sottosezioni a 3 livelli sono note, non errori.
Con `--source` confronta anche le sezioni `N.X` con quelle del testo del PDF (`pdftotext -layout libro.pdf testo.txt`).
Esce con codice 1 se trova problemi. Non modifica nessun file.

Non sa quanti capitoli ha davvero il libro: un ultimo capitolo perso non emerge da solo. Un capitolo senza sezioni può
essere corretto (es. Alberts, cap. 18, che nel PDF ha solo punti elenco).

## 2. correggi_indice.html — correzione guidata

> **La stessa revisione è ora dentro l'app**: pulsante con la matita sulle schede degli indici, e «Rivedi e correggi»
> nel modale dopo la generazione (con il PDF già caricato, quindi con i suggerimenti). Salva direttamente nell'indice
> dell'app e conserva una copia dell'originale («Ripristina l'originale»). Questa versione a parte fa la stessa cosa
> su file e resta utile per lavorare senza l'app. Il codice dell'app è stato ricavato da questo: se si cambia uno, va
> cambiato anche l'altro.

Si apre con un doppio clic nel browser. Carica il JSON (obbligatorio) e il PDF dell'indice (facoltativo, ma è quello
che dà i suggerimenti). Non modifica l'originale: «Salva JSON corretto» scarica `..._corretto.json`.

**A sinistra i problemi, a destra l'indice modificabile.** Ogni problema ha un pulsante che lo risolve:

| Problema segnalato | Azione |
|---|---|
| Manca la sezione N.X | «Aggiungi»: inserisce la voce al posto giusto, con titolo e pagina letti dal PDF se li trova |
| Pagina inferiore alla precedente | «Usa p. N (dal PDF)» |
| Pagina non compresa nel capitolo | «Usa p. N» se il PDF la conosce, altrimenti «Sposta nel cap. K» |
| Titolo con testo estraneo (© 978…, indice generale) | «Ripulisci» |
| Doppione (stesso titolo e pagina) | «Elimina il doppione» |
| Rimando online `QR…`, testo fisso («Domande», «Problemi»…) | «Elimina» |
| Titolo del PDF con l'aspetto delle sezioni ma assente dall'indice (libri senza numeri) | «Aggiungi» (o «Aggiungi tutti») |

Altri comandi: «+» aggiunge una sezione dopo una riga, «✕» la elimina, «Annulla» torna indietro, «Solo capitoli con
problemi» accorcia la lista. I campi proposti dal PDF sono in giallo: vanno sempre controllati.

### Due modi di usarlo

- **Indice con qualche errore** (il caso normale): apri il JSON e il PDF, risolvi i problemi uno per uno.
  Esempio: `esempio_molecole_con_errori.json` con `manuali/Biologia cellulare/Bonaldo_Molecole_Edises.pdf`
  (5 sezioni mancanti, un rimando QR, una pagina sbagliata).
- **Indice di soli capitoli** (quello che l'app dà per i libri senza numeri e senza pallini): a sinistra compare
  «Quali sono le sezioni?» con i gruppi di titoli trovati nel PDF (numero, aspetto, esempi). Clicca «Sono le sezioni»
  sul gruppo giusto, poi «Aggiungi tutti i N titoli del PDF» e rivedi.
  Esempio: `esempio_alberts_essenziale_solo_capitoli.json` con `manuali/Biologia cellulare/Alberts_Essenziale_Zanichelli.pdf`.

### Come ragiona

- **Libri con sezioni numerate (N.X):** cerca nel PDF le righe «N.X titolo … pagina». Su Molecole ha ritrovato
  177 sezioni su 177.
- **Libri senza numeri:** impara dall'indice che aspetto hanno i titoli di sezione nel PDF (dimensione, font,
  pallino, MAIUSCOLO) e propone i titoli con quell'aspetto che nell'indice mancano. Se l'aspetto non è uniforme lo
  dice e non propone nulla. I titoli tutti MAIUSCOLI si scrivono con l'iniziale maiuscola, come fa l'app, quindi gli
  acronimi diventano minuscoli («dna»): vanno corretti a mano.

### Limiti

- È un aiuto, non una garanzia: capisce solo PDF con testo (non scansioni) e non aggiunge capitoli mancanti.
- Provato su Molecole, Bonaldo Biologia, Alberts Biologia (indici verificati: risultato identico) e su Alberts
  Essenziale (75 sezioni coerenti, ma senza un indice di riferimento con cui confrontarle).

## 3. segna_indice.html — costruire l'indice direttamente dal PDF, senza AI

> **Ora raggiungibile anche dall'app**: nel modale «Crea JSON indice manuale» (Dashboard → Indici), lo Step 2 ha un
> terzo tab «Costruisci senza AI» che carica questa stessa pagina in un iframe (`tools/segna_indice.html`, percorso
> relativo alla radice del repo). Il pulsante «Usa questo indice nell'app» (visibile solo quando la pagina è
> incorporata così, con `window.parent !== window`) manda il JSON al genitore con `postMessage`
> (`{tipo:'segna-indice:usa', json}`); l'app lo riceve in `usaIndiceSenzaAI()` in `index.html`, tiene i metadati già
> scritti nello Step 1 (non quelli proposti dal nome del file dentro lo strumento, che restano un aiuto solo per chi
> usa la pagina da sola) e salta allo Step 3, la stessa revisione degli indici generati con l'AI. Aperta da sola
> (doppio clic, non incorporata) la pagina si comporta esattamente come descritto sotto, pulsante in più a parte.

Si apre con un doppio clic nel browser (serve la cartella `prototipo_righe/` accanto). Si parte dal solo PDF dell'indice,
senza JSON e senza chiave OpenAI. Il programma ricostruisce le righe dell'indice (`prototipo_righe/estrai_righe.js`:
colonne, titolo e pagina sulla stessa riga) e **propone** per ogni riga «Capitolo», «Sezione» o «Ignora»; la decisione
finale è di chi lo usa. «Scarica il JSON» produce il file da importare nell'app con «Importa indice».

- In alto, i **gruppi di righe simili** (righe «CAPITOLO N», sezioni «N.X», titoli senza numero, sottovoci con pallino,
  rimandi QR…): un menu per gruppo cambia in un colpo solo il comportamento di tutte le righe del gruppo.
- **Avvisi cliccabili**: capitoli o sezioni saltati, sezione sotto il capitolo sbagliato, pagina che torna indietro,
  sezione senza pagina. Il numero mancante di una sezione è calcolato (`N.k`), e si può scrivere a mano.
- **I dati del libro si compilano da soli** (in giallo, da controllare): autore, titolo ed editore dal nome del file
  (`Autore_Titolo_Editore.pdf`, come li nomina «Scarica programmi»), l'ID come lo scrive l'app (`Bonaldo_Molecole`),
  l'editore con la grafia dell'app (`EdiSES`, `Zanichelli-CEA`…), materia e tipo dall'ultimo libro lavorato. Editori e
  materie degli indici già salvati nell'app compaiono come suggerimenti se il browser li rende leggibili da questa
  pagina. Restano da scrivere a mano edizione, anno e volume (facoltativi) e la materia la prima volta.
- Il lavoro si salva da solo nel browser (per nome e dimensione del file) e si riprende riaprendo lo stesso PDF.
- Il numero di pagina di ogni riga apre la pagina corrispondente del PDF per il controllo.
- **Un titolo di capitolo che inizia come un'intestazione di servizio è riconosciuto lo stesso** (solo nella
  gerarchia dalla tipografia, il caso qui sotto): «Problemi d'urto» (Mencuccini) inizia con «Problemi», la stessa
  parola con cui inizia l'intestazione «Problemi generali» che compare in decine di libri e va scartata. Scartare
  ogni riga che inizia con quella parola perdeva il capitolo (e spostava di uno tutti quelli dopo); non scartarla
  mai rimetteva dentro centinaia di intestazioni vere in tutto il resto della libreria (misurato: 1711 casi su 93
  libri, di cui uno solo un capitolo vero). La soluzione: il filtro resta largo; solo dentro la gerarchia dalla
  tipografia, la riga più vicina a un paragrafo che riparte da 1 — lo stesso segno che riconosce ogni altro
  capitolo — viene recuperata comunque, qualunque parola la apra.
- **Gerarchia dalla tipografia** (per i libri dove i numeri da soli «1.», «2.»… ripartono da 1 in ogni capitolo, come
  Voet, Mencuccini, Dambrosio, Bramanti): se dopo ogni titolo di capitolo i paragrafi numerati ricominciano da 1, i capitoli
  sono i titoli in carattere più grande (o i marcatori «CAPITOLO N»), i paragrafi sono `capitolo.numero` (1.1, 1.2…), le
  sottosezioni rientrate o con lettera sono `capitolo.paragrafo.lettera` (1.1.A) e le intestazioni di servizio (Riepilogo,
  Esercizi, Bibliografia…) sono ignorate. Se il libro non ha questo schema non cambia nulla: su 93 PDF cambiano 7 libri, tutti
  con più sezioni trovate. Le pagine mancanti non sono più avvisi (Atlante non le usa): sono contate a parte.
- **Modalità «Guidato dallo schema»** (riquadro in alto, l'automatico resta quello predefinito): ogni riga ha uno *stile*
  (tipo di carattere, dimensione, rientro, forma del numero). La pagina mostra gli stili di un capitolo di esempio (uno
  centrale, a scelta) e, per ognuno, un menu: Capitolo / Sezione / Sottosezione / Scheda-riquadro / Ignora. La scelta di
  partenza viene dalla proposta automatica, con una soglia inclusiva (uno stile parte come struttura se almeno il 15% delle
  sue righe lo era). Sotto, l'anteprima della struttura del capitolo con la numerazione (1.1, 1.1.A, SCHEDA 1.1). Ogni
  cambio si applica subito a tutto il libro. Con la scelta di partenza dà lo stesso risultato dell'automatico su 56 libri
  su 93; nei restanti cambia soprattutto perché recupera schede e riquadri («BOX 1.1» in Lehninger, le schede su una riga sola
  di Voet, 88 invece di 54), ripulisce i titoli dalle etichette e dalle lettere (che diventano numeri, 1.1.D) e tiene
  gli argomenti che l'automatico scartava (Verrocchio +318). Scarta le intestazioni di servizio (Riepilogo, Esercizi,
  Problemi, Domande, Sintesi, Bibliografia) e tutto ciò che precede il primo capitolo.
- **Confronto tra le due modalità** (riquadro sotto lo schema, **aperto di default**): la riga del riquadro mostra sempre
  capitoli, sezioni e avvisi di automatica e guidata. Sotto, **riga per riga** (non per titolo: `ra[i]`/`rg[i]` vengono
  dalla stessa voce `i`, quindi il confronto è esatto) solo le righe dove le due modalità NON sono d'accordo — dove sono
  d'accordo non compare nulla. Il confronto è sul numero *effettivo* (`r.eff`, quello che finisce nel JSON dopo `ricalcola()`,
  non il numero grezzo proposto), altrimenti nei libri senza numeri (Alberts) ogni riga risulterebbe "diversa" solo perché
  una modalità lo scrive subito e l'altra lo calcola dopo.
  Per ogni riga diversa, un pulsante porta nella modalità **in uso** la versione dell'altra (il numero copiato è quello
  effettivo che si vedeva nel confronto, non quello grezzo, per non farlo ricalcolare in modo diverso nella nuova posizione).
  Un pulsante in blocco («Aggiungi qui tutte le voci che solo l'altra modalità ha») copia in un colpo solo le sole
  *aggiunte* (righe dove qui non c'è nulla e l'altra ha qualcosa): non tocca mai una riga che la modalità in uso ha già
  classificata, quelle restano da decidere una per una. Così si può partire dall'automatica, aggiungere in blocco ciò che
  la guidata trova in più (tipicamente le schede/riquadri), e sistemare a mano solo i pochi casi dove le due discordano
  davvero — invece di scegliere un'unica modalità e perdere quello che l'altra aveva giusto.
  Le due modalità conservano separatamente le correzioni fatte a mano: si può passare dall'una all'altra senza perderle
  (cambiare lo schema nella guidata ricalcola la guidata, comando principale di quella modalità, e in quel caso sì che le
  correzioni fatte lì si perdono). Il JSON che si esporta o si copia viene dalla modalità in uso; i pulsanti «Usa
  l'automatica» / «Usa la guidata» scelgono quale.
  Collaudato sui 93 PDF: nessun errore, il confronto e il pulsante in blocco funzionano ovunque.
- **Aggiungere una riga a mano**: quando un capitolo o una sezione manca dal PDF in entrambe le modalità (es. non è
  stato letto come riga a sé, o manca proprio nel testo estratto), il «+» accanto a ogni riga inserisce una riga vuota
  subito dopo, da compilare a mano (tipo, numero, titolo, pagina); «+ Aggiungi una riga in cima» la mette all'inizio
  di tutto. La riga aggiunta **non appartiene a una sola modalità**: quello che ci si scrive resta identico passando
  da automatica a guidata e viceversa, cambiando lo schema della guidata, e chiudendo e riaprendo lo stesso PDF
  (si salva insieme al resto). Collaudato: inserimento e compilazione in una modalità e verifica nell'altra (nei due
  versi), sopravvivenza a un cambio di schema in guidata, e persistenza dopo ricarica pagina — tutti confermati su
  Voet Fondamenti e Lehninger Principi.
- **«Copia il JSON»** mette il JSON negli appunti, pronto da incollare in Atlante (Utilità → Manuali). Atlante legge dell'indice
  solo numero e titolo dei capitoli e titoli delle sezioni (mai le pagine), quindi le pagine sono facoltative.
- **Indice testuale** (riquadro in fondo ai pulsanti), per i libri dove capitoli e sezioni non si riconoscono bene: una voce
  per riga, nell'ordine di lettura, con il rientro come livello, senza pagine, puntini di guida e rimandi QR. Il testo si
  può correggere direttamente. Il JSON che ne esce ha `index_chapters: []` e il testo in `chapters_summary`, che Atlante
  legge quando manca l'indice a capitoli (`estraiIndiceManuale` in `Atlante/app/js/atlante-shared.js`). Con questo formato
  il vademecum disciplinare di Atlante dà al libro confidenza «bassa», perché non ha capitoli con sezioni.
  Limite di Atlante: 100.000 caratteri per indice (la pagina avvisa se lo superi: togli le sottovoci).

Provato senza correzioni manuali su 9 libri: i capitoli coincidono con gli indici già fatti in 8 casi su 9 e per i libri
numerati (Bonaldo Molecole, Bonaldo Biologia) le sezioni con la stessa pagina sono quasi tutte. Nei libri a paragrafo
(Atkinson, Holt) le proposte sono più rade e vanno riviste con più cura. Non è ancora stato provato su libri diversi da
quelli usati per tarare le regole: vedi `prototipo_righe/README.md`.

## Provato e non adottato: lettura dell'indice come immagini

Si era provato a far leggere le pagine dell'indice a un modello che vede (una pagina per volta) invece di estrarre il
testo. Su Molecole ha dato 169 sezioni su 177 (mancavano 1.3, 11.3, 16.6, 25.2, 25.5), con circa 27.000 token in
ingresso e 36.600 in uscita, mentre il metodo a regole sul testo ne aveva trovate 177 su 177 senza chiamate. Non è
stato adottato e il codice è stato tolto.
