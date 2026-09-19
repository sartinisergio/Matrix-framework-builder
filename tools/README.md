# Strumenti

## check_index.js

Controlla la qualità di un JSON indice generato dall'app (Node.js, nessuna dipendenza).

```
node tools/check_index.js Bonaldo_Biologia.json
node tools/check_index.js Bonaldo_Biologia.json --source testo_indice.txt
```

Segnala capitoli mancanti o duplicati, sezioni mancanti nella numerazione, stesso
numero con titoli diversi, `page_start` che tornano indietro o troppo piccoli (pagina
del PDF-indice invece di quella del libro), capitoli senza sezioni e voci `QR…`.
I box (`RIQUADRO`, `SALUTE E MEDICINA`…) e le sottosezioni a 3 livelli sono note, non errori.

Con `--source` confronta anche le sezioni `N.X` del JSON con quelle presenti nel testo
del PDF. Per ottenere il testo: `pdftotext -layout libro.pdf testo_indice.txt`.

Il controllo non sa quanti capitoli ha davvero il libro: un ultimo capitolo perso non
emerge da solo. Confronta sempre l'ultimo capitolo con l'indice del PDF.

Un capitolo senza sezioni può essere corretto (es. Alberts, cap. 18: nel PDF ha solo
punti elenco). Esce con codice 1 se trova problemi.
