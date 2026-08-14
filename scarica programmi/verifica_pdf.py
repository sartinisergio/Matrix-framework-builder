#!/usr/bin/env python3
"""
verifica_pdf.py
----------------
Scansiona una cartella di PDF già scaricati (output di scarica_programmi.py)
e segnala quelli sospetti: pagine dove un banner cookie o un altro overlay
ha coperto il programma invece di essere chiuso prima della stampa, o pagine
con pochissimo testo (probabile errore di caricamento).

Non cancella nulla: produce solo un elenco/CSV. Per riscaricare i file
segnalati, cancellali manualmente e rilancia scarica_programmi.py sullo
stesso export — i file mancanti verranno scaricati di nuovo.

Uso:
    python verifica_pdf.py --cartella programmi_pdf/psicologia_generale

Dipendenze:
    pip install pypdf
"""

import argparse
import csv
import sys
from pathlib import Path

# Frasi tipiche di banner cookie/consenso in italiano e inglese: se dominano
# il testo estratto, il PDF quasi certamente mostra il banner invece del
# programma.
FRASI_COOKIE = [
    "questo sito utilizza i cookie", "questo sito web utilizza i cookie",
    "accetta tutti i cookie", "accetta i cookies selezionati",
    "gestisci le tue preferenze", "informativa sui cookie",
    "utilizziamo i cookie", "consenso ai cookie", "cookie policy",
    "solo cookie necessari", "rifiuta tutti", "impostazioni dei cookie",
    "this website uses cookies", "accept all cookies", "cookie settings",
    "we use cookies", "manage your preferences",
]

SOGLIA_CARATTERI_MINIMA = 150

# Presenti nei PDF prodotti dai template CINECA/Sapienza (uniroma1). Se un
# PDF ha "informazioni generali" (la tabella con CFU/docente/SSD) ma nessuna
# di queste sezioni di contenuto, il docente non ha ancora compilato il
# programma: il PDF esiste ma non serve all'analisi.
MARCATORE_TEMPLATE_CINECA = "informazioni generali"
FRASI_SEZIONI_PROGRAMMA = [
    "programma dell'insegnamento", "programma dell insegnamento",
    "programma esteso", "programma del corso", "contenuti del corso",
    "obiettivi formativi", "risultati di apprendimento attesi",
    "testi di riferimento", "testi adottati", "bibliografia",
    "prerequisiti", "modalità di svolgimento", "modalità di esame",
    "modalità di verifica",
]


def analizza_pdf(percorso: Path) -> tuple[str, int]:
    """Ritorna (motivo, n_caratteri). motivo è '' se il PDF sembra a posto."""
    try:
        from pypdf import PdfReader
    except ImportError:
        print("Errore: installa pypdf: pip install pypdf")
        sys.exit(1)

    try:
        reader = PdfReader(str(percorso))
        testo = "".join(p.extract_text() or "" for p in reader.pages)
    except Exception as e:
        return f"errore lettura PDF ({e})", 0

    testo_lower = testo.lower()
    n = len(testo.strip())

    if n < SOGLIA_CARATTERI_MINIMA:
        return "pochissimo testo estratto (pagina probabilmente vuota o errore)", n

    if MARCATORE_TEMPLATE_CINECA in testo_lower and not any(f in testo_lower for f in FRASI_SEZIONI_PROGRAMMA):
        return "solo 'Informazioni generali', il docente non ha ancora compilato il programma", n

    frasi_trovate = [f for f in FRASI_COOKIE if f in testo_lower]
    if frasi_trovate:
        # Se il testo "vero" (senza contare le frasi cookie) resta comunque
        # sostanzioso, il banner potrebbe essere solo nel footer e non aver
        # coperto il contenuto: lo segnaliamo comunque, ma con un motivo
        # più prudente, per farlo controllare a vista invece di bocciarlo.
        if n < 600:
            return f"banner cookie rilevato, poco altro testo ({', '.join(frasi_trovate[:2])})", n
        return f"contiene testo di un banner cookie, da controllare ({', '.join(frasi_trovate[:2])})", n

    return "", n


def main():
    parser = argparse.ArgumentParser(
        description="Verifica la qualità dei PDF già scaricati da scarica_programmi.py"
    )
    parser.add_argument("--cartella", required=True, help="Cartella con i PDF da controllare")
    parser.add_argument("--csv", default=None, help="Percorso del report CSV (default: dentro la cartella)")
    args = parser.parse_args()

    cartella = Path(args.cartella)
    if not cartella.is_dir():
        print(f"Errore: cartella non trovata: {cartella}")
        sys.exit(1)

    pdf_files = sorted(cartella.rglob("*.pdf"))
    if not pdf_files:
        print("Nessun PDF trovato nella cartella.")
        return

    print(f"Controllo {len(pdf_files)} PDF in {cartella}...\n")

    sospetti = []
    for pdf in pdf_files:
        motivo, n = analizza_pdf(pdf)
        if motivo:
            sospetti.append((pdf.name, motivo, n))
            print(f"  ⚠️  {pdf.name}")
            print(f"      → {motivo} ({n} caratteri)")

    print(f"\n{'='*60}")
    print(f"  Controllati: {len(pdf_files)}   Sospetti: {len(sospetti)}")
    print(f"{'='*60}")

    if sospetti:
        csv_path = Path(args.csv) if args.csv else cartella / "verifica_pdf_sospetti.csv"
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["file", "motivo", "caratteri_estratti"])
            writer.writerows(sospetti)
        print(f"\nReport: {csv_path}")
        print("Per riscaricarli: cancella questi file dalla cartella e rilancia")
        print("scarica_programmi.py sullo stesso export (i mancanti verranno ripresi).")
    else:
        print("\nNessun problema rilevato.")


if __name__ == "__main__":
    main()
