# Programmi Downloader

Strumento di supporto al flusso **MyUniversity/Atlante → Matrix Framework Builder**.

Legge il file Excel esportato con l'elenco degli insegnamenti da analizzare, scarica automaticamente i programmi d'esame come PDF e li prepara per l'analisi batch su Matrix Framework Builder.

---

## Flusso di lavoro

```
Atlante/MyUniversity          Scarica Programmi (GUI)              Matrix Framework Builder
 esporta il file .xls   →   anteprima → download → verifica   →      carichi i PDF
```

1. **Esporti** da Atlante/MyUniversity il file Excel con gli insegnamenti da analizzare (colonna `url_ins` con il link al programma)
2. **Apri la GUI** (`Avvia Scarica Programmi.bat`) e fai un'**anteprima** per vedere quanti link sono gestibili
3. **Avvii il download** — i PDF vengono salvati in `programmi_pdf/<nome_file>/`
4. **Verifichi** i PDF scaricati con un click, per scovare eventuali falsi positivi (pagine bloccate da banner cookie, o senza programma pubblicato)
5. **Carichi** i PDF su Matrix Framework Builder per l'analisi

I passaggi in dettaglio sono più sotto. Chi preferisce il terminale può usare la [riga di comando](#uso-da-riga-di-comando) al posto della GUI — fanno esattamente le stesse cose.

---

## Setup (una tantum)

### Python
Se non hai Python installato, scaricalo da [python.org](https://www.python.org/downloads/) e segui l'installazione. Durante l'installazione assicurati di spuntare **"Add Python to PATH"**.

### Dipendenze
Apri il Prompt dei comandi (cerca "cmd" nel menu Start) e lancia:

```
pip install playwright beautifulsoup4 lxml pypdf
playwright install chromium
```

Il secondo comando scarica il browser Chromium (~150 MB) che lo script usa per aprire le pagine. Richiede qualche minuto, va fatto una sola volta.

> Se compare l'errore `'pip' non è riconosciuto`, prova con `python -m pip install playwright beautifulsoup4 lxml pypdf`

---

## Passo 1 — Esporta da Atlante/MyUniversity

Fai la tua ricerca e esporta il file Excel con gli insegnamenti che vuoi analizzare. Salva il file nella cartella `scarica programmi` (la stessa dove si trovano gli script), così la GUI lo trova automaticamente nel menu a tendina.

## Passo 2 — Apri la GUI

Fai doppio clic su **`Avvia Scarica Programmi.bat`**. Non serve aprire il Prompt dei comandi né ricordare parametri.

Nella finestra:
- **File di export**: scegli dal menu a tendina (rileva automaticamente i `.xls`/`.xlsx`/`.csv` nella cartella) o con "Sfoglia…"
- **Filtra per ateneo**: opzionale, utile per testare/limitare a un solo ateneo
- **Limite insegnamenti**: opzionale, per fare una prova su un sottoinsieme prima del download completo
- **Cartella output**: dove salvare i PDF (default `programmi_pdf/`)

## Passo 3 — Anteprima (consigliata prima di un batch grande)

Clicca **"🔍 Anteprima"**: mostra quanti link sono PDF diretti, CINECA, HTML, sistemi gestionali (saltati), senza programma pubblicato, ecc. — **senza scaricare nulla**. Utile per farsi un'idea di quanto lavoro c'è e se il file contiene molti link di tipi che verranno saltati.

## Passo 4 — Avvia il download

Clicca **"▶ Avvia download"**. L'avanzamento appare in tempo reale nella finestra, riga per riga: tipo di link, ateneo, esito (✓ scaricato, ✗ errore, ⏭ saltato). Puoi interrompere in qualsiasi momento con **"⏹ Interrompi"** — tutto quello scaricato fino a quel punto resta salvato, niente va perso.

**Se il download si interrompe o ci sono errori**: rilancia semplicemente lo stesso download con **gli stessi parametri** (stesso file, stesso ateneo/limite, senza spuntare "Ordine casuale"). Lo script salta automaticamente i file già presenti e ritenta solo quelli mancanti o andati in errore.

## Passo 5 — Verifica i PDF scaricati

Clicca **"🔎 Verifica PDF scaricati"**. Controlla ogni PDF già scaricato e segnala:
- pagine con **banner cookie non chiuso** che copre il programma
- pagine con **pochissimo testo** (probabile errore di caricamento)
- pagine **senza programma pubblicato** (il docente non ha ancora compilato il programma — mostrano solo dati generali come CFU/SSD/docente)

Il risultato è un report `verifica_pdf_sospetti.csv` nella cartella dei PDF. Non cancella nulla in automatico: per riscaricare un file segnalato, cancellalo dalla cartella e rilancia il download sullo stesso file di export — verrà ripreso automaticamente, gli altri PDF restano intatti. Per i casi "senza programma" non c'è nulla da fare finché l'ateneo non pubblica il contenuto — non è un errore dello script.

## Passo 6 — Carica su Matrix Framework Builder

I PDF pronti si trovano in `programmi_pdf/<nome_file_export>/`. Caricali su [Matrix Framework Builder](https://matrix-framework-builder.netlify.app/) (o apri `index.html` nella cartella principale, una sopra questa) per l'analisi.

---

## Riferimento — tipi di link gestiti

| Tipo | Esempio | Comportamento |
|---|---|---|
| PDF diretto | URL che termina in `.pdf` | ✅ Scarica direttamente |
| Course Catalogue CINECA | `*.coursecatalogue.cineca.it` | ✅ Clicca "Salva PDF" e scarica |
| Uniroma1 (Sapienza) | `corsidilaurea.uniroma1.it` | ✅ Sceglie il canale (A-K/L-Z) se richiesto, poi stampa PDF |
| Pagina HTML ateneo | `unibo.it`, `polito.it`, `unina.it`… | ✅ Scarica come PDF |
| Sistema gestionale | Esse3, GOMP… | ⏭ Saltato (richiede login) |
| Senza programma pubblicato | `unical.it/storage/cds/...` o pagine CINECA/Sapienza non compilate | ⏭ Saltato (la pagina esiste ma non ha il programma) |
| URL non disponibile | Campo vuoto nell'export | ⏭ Saltato |

**Pagine "errore" mascherate da 200 OK.** Alcuni portali (es. `unisalento.it`) tengono l'ID dell'insegnamento nell'URL, che scade quando cambia l'anno accademico: la pagina risponde comunque con successo ma mostra un messaggio del tipo "Selezionare un insegnamento valido" al posto del programma. Lo script riconosce queste pagine e le segna come errore invece di salvare un PDF inutile. Se un ateneo compare spesso con questo esito, il link nell'export va probabilmente rigenerato per l'anno accademico corrente.

## Riferimento — log_download.csv

Ogni download scrive un log nella cartella dei PDF, con l'esito di ogni riga dell'export:

| Esito | Significato |
|---|---|
| `ok` | PDF scaricato correttamente |
| `errore` | Pagina non raggiungibile, timeout, o link scaduto |
| `senza_programma` | Pagina esistente ma il docente non ha ancora compilato il programma |
| `saltato` | PDF già presente da una sessione precedente |

## Uso da riga di comando

Per chi preferisce il terminale invece della GUI (o vuole automatizzare):

```
python scarica_programmi.py --input nomefile.xls
```

Opzioni principali:

```
--output CARTELLA     cartella di destinazione (default ./programmi_pdf)
--ateneo TESTO        filtra per ateneo
--limit N             limita a N insegnamenti (per test)
--random              ordine casuale (utile con --limit per un campione)
--delay SECONDI        attesa tra un download e l'altro (default 1.5)
--verbose             output dettagliato
--dry-run             mostra solo la distribuzione dei link, senza scaricare (= anteprima della GUI)
--yes                 non chiedere conferma prima di avviare (= quello che fa la GUI)
```

Per verificare i PDF già scaricati da terminale:

```
python verifica_pdf.py --cartella programmi_pdf/nomefile
```

---

## Note

- Lo script gira in background: non si apre nessuna finestra del browser.
- Se interrompi (Ctrl+C da terminale, o "⏹ Interrompi" nella GUI), i PDF già scaricati restano nella cartella. Alla ripresa lo script salta i file già presenti.
- Il log CSV è compatibile con Excel.
- La velocità dipende dalla connessione e dalla reattività dei siti universitari. Con il valore predefinito (1.5 secondi tra un download e l'altro) sono necessari circa 2-3 minuti ogni 100 programmi.
- Per una ripresa pulita dopo un'interruzione, rilancia con gli stessi parametri (stesso ateneo/limite, senza `--random`): l'ordine casuale cambia la numerazione dei file tra un run e l'altro e può confondere il controllo "già presente".

---

## Parte del progetto Zanichelli Core

Questo strumento fa parte dell'ecosistema [Zanichelli Core](https://zanichelli-core-v2.netlify.app/), insieme a:
- [MyUniversity 2.0](https://myuniversity-v2.netlify.app/) — ricerca dell'offerta formativa universitaria italiana
- [Matrix Framework Builder](https://matrix-framework-builder.netlify.app/) — costruzione di framework e indici dai programmi d'esame
- [Matrix Analisi](https://uni-matrix.netlify.app/welcome.html) — analisi approfondita di un singolo programma
