# Matrix Framework Builder

Progetto Zanichelli per la costruzione di framework di valutazione disciplinare a partire dai programmi d'esame universitari italiani.

Il progetto è composto da **tre strumenti indipendenti**, usati in sequenza:

```
Atlante            Accorpa Insegnamenti      Scarica Programmi         Matrix Framework Builder
(offerta   →   decidi se/cosa vale   →   scarica i programmi   →   costruisci il framework
formativa)      la pena costruire         della materia scelta        e l'indice
```

## 1. Accorpa Insegnamenti — `accorpa_insegnamenti.html`

Punto di partenza. Le stesse materie compaiono su Atlante con nomi leggermente diversi da ateneo ad ateneo ("Chimica Generale", "Chimica Generale e Inorganica"...). Questo strumento le raggruppa in famiglie, per vedere la rilevanza nazionale reale di una materia **prima** di decidere se vale la pena costruirci un framework. Esporta un CSV con il risultato del raggruppamento.

Si apre direttamente nel browser (file HTML singolo, nessuna installazione).

## 2. Scarica Programmi — `scarica programmi/`

Una volta deciso su quale materia lavorare, si esporta da Atlante l'elenco degli insegnamenti con i link ai programmi. Questo strumento legge quell'export e scarica automaticamente i programmi come PDF, pronti per il passo successivo.

È uno strumento locale (Python + interfaccia grafica) con la sua documentazione dedicata:
- [`scarica programmi/Guida.html`](scarica%20programmi/Guida.html) — guida rapida illustrata, passo per passo
- [`scarica programmi/README.md`](scarica%20programmi/README.md) — riferimento tecnico completo (setup, opzioni da riga di comando)

## 3. Matrix Framework Builder — `index.html`

Il cuore del progetto. Carica i PDF scaricati al passo precedente, li analizza tramite AI (OpenAI API, chiamata direttamente dal browser) e costruisce il framework di valutazione disciplinare — sia il framework stesso che l'indice del volume — in un JSON compatibile con Atlante e con MATRIX Analisi Programmi.

Si apre direttamente nel browser (file HTML singolo) oppure è disponibile online su [matrix-framework-builder.netlify.app](https://matrix-framework-builder.netlify.app/). Richiede una chiave API OpenAI, impostata dall'utente nell'app.

---

## Cosa non è in questo repository

Il repository è pubblico, quindi contiene solo il codice dei tre strumenti. Restano esclusivamente locali (mai su GitHub): i manuali di riferimento, i report ed export generati dall'uso quotidiano, i programmi scaricati, e la documentazione interna di contesto del progetto — vedi `.gitignore`.

## Parte dell'ecosistema Zanichelli Core

Insieme a:
- [MyUniversity 2.0](https://myuniversity-v2.netlify.app/) — ricerca dell'offerta formativa universitaria italiana
- [Matrix Analisi](https://uni-matrix.netlify.app/welcome.html) — analisi approfondita di un singolo programma
