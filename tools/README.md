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

## Provato e non adottato: lettura dell'indice come immagini

Si era provato a far leggere le pagine dell'indice a un modello che vede (una pagina per volta) invece di estrarre il
testo. Su Molecole ha dato 169 sezioni su 177 (mancavano 1.3, 11.3, 16.6, 25.2, 25.5), con circa 27.000 token in
ingresso e 36.600 in uscita, mentre il metodo a regole sul testo ne aveva trovate 177 su 177 senza chiamate. Non è
stato adottato e il codice è stato tolto.
