#!/usr/bin/env python3
"""
scarica_programmi.py
--------------------
Legge un export di MyUniversity, scarica i programmi d'esame come PDF.

Strategie per tipo di URL:
  - CINECA coursecatalogue : clicca "Salva PDF" nativo
  - corsi.unina.it         : clicca "Visualizza" per ogni docente + espande sezioni
  - onlineservices.polimi  : clicca link "schedaincarico" per ogni docente
  - HTML generico          : chiudi cookie + espandi sezioni + stampa
  - PDF diretto            : scarica direttamente
  - Gestionale / vuoto     : saltato

Uso:
    python scarica_programmi.py --input export.xls
    python scarica_programmi.py --input export.xls --ateneo "Milano Politecnico" --verbose
    python scarica_programmi.py --input export.xls --limit 20 --random

Dipendenze:
    pip install playwright beautifulsoup4 lxml
    playwright install chromium
"""

import argparse
import asyncio
import os
import re
import sys
from pathlib import Path

# ── Lettura export ────────────────────────────────────────────────────────────

def leggi_export_xls(percorso: str) -> list[dict]:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("Errore: installa beautifulsoup4: pip install beautifulsoup4 lxml")
        sys.exit(1)

    with open(percorso, "r", encoding="utf-8-sig", errors="replace") as f:
        contenuto = f.read()

    soup = BeautifulSoup(contenuto, "lxml")
    table = soup.find("table")
    if not table:
        print(f"Errore: nessuna tabella trovata in {percorso}")
        sys.exit(1)

    header_row = table.find("thead")
    if header_row:
        headers = [th.get_text(strip=True).lower() for th in header_row.find_all(["th", "td"])]
    else:
        headers = [td.get_text(strip=True).lower() for td in table.find("tr").find_all(["th", "td"])]

    def idx(nome):
        try: return headers.index(nome)
        except ValueError: return -1

    i_ins    = idx("insegnamento")
    i_ateneo = idx("ateneo")
    i_doc    = idx("docente")
    i_url    = idx("url_ins")

    if i_url == -1:
        print(f"Errore: colonna 'url_ins' non trovata. Colonne: {headers}")
        sys.exit(1)

    righe = []
    tbody = table.find("tbody") or table
    for tr in tbody.find_all("tr"):
        celle = tr.find_all("td")
        if not celle: continue

        def testo(i):
            return celle[i].get_text(strip=True) if 0 <= i < len(celle) else ""
        def href(i):
            if 0 <= i < len(celle):
                a = celle[i].find("a")
                return a.get("href", "").strip() if a else celle[i].get_text(strip=True).strip()
            return ""

        docente_raw = testo(i_doc)
        # Gestisce entrambi i separatori: " | " (UNINA e altri) e "<I>" (altri export)
        if " | " in docente_raw:
            docenti = [d.strip() for d in docente_raw.split(" | ") if d.strip()]
        elif "<I>" in docente_raw:
            docenti = [d.strip() for d in docente_raw.split("<I>") if d.strip()]
        else:
            docenti = [docente_raw.strip()] if docente_raw.strip() else []

        # Deduplica docenti (evita di scaricare/nominare due volte lo stesso nome)
        docenti_visti = set()
        docenti_dedup = []
        for d in docenti:
            chiave = d.upper()
            if chiave not in docenti_visti:
                docenti_visti.add(chiave)
                docenti_dedup.append(d)
        docenti = docenti_dedup

        righe.append({
            "insegnamento": testo(i_ins),
            "ateneo":       testo(i_ateneo),
            "docente":      docente_raw,
            "docenti":      docenti,
            "url_ins":      href(i_url),
        })
    return righe


# ── Classificazione URL ───────────────────────────────────────────────────────

SISTEMI_GESTIONALI = [
    "esse3", "u-gov", "ugov", "infostud", "gomp", "aulaweb",
    "portale.unige", "portale.univpm", "portaleservizi",
    "studenti.uniroma", "tuttoservizi", "servizi.unibo", "speedy.unito",
    "personalbook", "unistudium", "beep.metid", "kiro.",
    "portale.unict", "portale.unipa", "fenix.", "idp.", "auth.", "sso.",
    "offf.cineca", "off.cineca", "registerme", "registrar",
    "gestione.", "gestionedidattica", "orari.", "pica.", "prex.",
    "servizionline.", "segreterie."
]

# Domini verificati manualmente: la pagina esiste ma non pubblica mai il
# programma (solo metadati come CFU/SSD/docente) -> non ha senso provare a
# scaricarla, si segnala subito come "senza_programma".
DOMINI_SENZA_PROGRAMMA = [
    "unical.it/storage/cds",
]

def classifica_url(url: str) -> str:
    if not url or not url.strip():
        return "non_disponibile"
    u = url.lower().strip()
    if u.endswith(".pdf") or ".pdf?" in u or "/pdf/" in u:
        return "pdf_diretto"
    if "coursecatalogue.cineca.it" in u:
        return "cineca"
    if "corsi.unina.it" in u and "/insegnamenti/" in u:
        return "unina"
    if "onlineservices.polimi.it/manifesti" in u:
        return "polimi"
    if "corsidilaurea.uniroma1.it" in u:
        return "uniroma1"
    for p in DOMINI_SENZA_PROGRAMMA:
        if p in u:
            return "senza_programma"
    for p in SISTEMI_GESTIONALI:
        if p in u:
            return "gestionale"
    if u.startswith("http://") or u.startswith("https://"):
        return "html"
    return "non_disponibile"


# ── Nome file PDF ─────────────────────────────────────────────────────────────

def nome_file_pdf(row: dict, indice: int, docente: str = "") -> str:
    def pulisci(s):
        s = s.upper()
        s = re.sub(r"[^A-Z0-9 ]", "", s)
        s = re.sub(r"\s+", "_", s.strip())
        return s[:35]
    ins    = pulisci(row.get("insegnamento", ""))
    ateneo = pulisci(row.get("ateneo", ""))
    doc    = pulisci(docente)[:20] if docente else ""
    if doc:
        base = f"{indice:04d}_{ins}_{ateneo}_{doc}"
    else:
        base = f"{indice:04d}_{ins}_{ateneo}" if ins and ateneo else f"{indice:04d}_programma"
    return base + ".pdf"


# ── Utility: chiudi cookie banner ─────────────────────────────────────────────

COOKIE_SELECTORS = [
    "button:has-text('SOLO COOKIE NECESSARI')",
    "a:has-text('SOLO COOKIE NECESSARI')",
    "button:has-text('Accetta solo i necessari')",
    "button:has-text('Accetta necessari')",
    "button:has-text('Solo necessari')",
    "button:has-text('Rifiuta tutti')",
    "button:has-text('Reject all')",
    "button:has-text('Decline')",
    "button:has-text('Necessary only')",
    "button:has-text('Only necessary')",
    "button:has-text('Accetta i cookies selezionati')",
    "#CybotCookiebotDialogBodyButtonDecline",
    ".iubenda-cs-reject-btn",
    ".cookie-accept", "#cookie-close", ".cc-dismiss",
]

async def chiudi_cookie(page):
    for sel in COOKIE_SELECTORS:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=1000):
                await btn.click()
                await asyncio.sleep(0.5)
                break
        except Exception:
            pass


# ── Utility: espandi sezioni collassate ───────────────────────────────────────

EXPAND_SELECTORS = [
    "[data-toggle='collapse']",
    ".accordion-toggle",
    ".accordion-button.collapsed",
    "button[aria-expanded='false']",
    "details:not([open]) > summary",
    ".panel-title a[aria-expanded='false']",
    "a[data-toggle='collapse']",
]

async def espandi_sezioni(page) -> int:
    espansi = 0
    for sel in EXPAND_SELECTORS:
        try:
            els = await page.locator(sel).all()
            for el in els:
                try:
                    if await el.is_visible(timeout=500):
                        await el.click()
                        espansi += 1
                        await asyncio.sleep(0.2)
                except Exception:
                    pass
        except Exception:
            pass
    if espansi:
        await asyncio.sleep(0.5)
    return espansi


# ── Utility: rileva pagine "errore" mascherate da 200 OK ─────────────────────
# Alcuni portali (es. unisalento.it quando l'ID insegnamento è scaduto con il
# cambio di anno accademico) rispondono con una pagina valida (200 OK) ma con
# un messaggio di errore al posto del contenuto. Senza questo controllo lo
# script le segnerebbe "ok" salvando un PDF inutile.
FRASI_PAGINA_NON_VALIDA = [
    "selezionare un insegnamento valido",
    "pagina non trovata",
    "risorsa non trovata",
    "insegnamento non trovato",
    "contenuto non disponibile",
]

async def pagina_ha_contenuto_valido(page) -> bool:
    try:
        testo = (await page.inner_text("body")).strip().lower()
    except Exception:
        return True
    if len(testo) < 40:
        return False
    return not any(frase in testo for frase in FRASI_PAGINA_NON_VALIDA)


# ── Utility: rileva insegnamenti senza programma compilato ───────────────────
# Alcune pagine (tipicamente CINECA/Sapienza) esistono e caricano
# correttamente, ma il docente non ha ancora compilato il programma: la
# pagina mostra solo la tabella "Informazioni generali" (CFU, docente, SSD...)
# senza nessuna delle sezioni di contenuto vero e proprio. Il download
# tecnicamente riesce ma produce un PDF inutile ai fini dell'analisi.
FRASI_SEZIONI_PROGRAMMA = [
    "programma dell'insegnamento", "programma dell insegnamento",
    "programma esteso", "programma del corso", "contenuti del corso",
    "obiettivi formativi", "risultati di apprendimento attesi",
    "testi di riferimento", "testi adottati", "bibliografia",
    "prerequisiti", "modalità di svolgimento", "modalità di esame",
    "modalità di verifica",
]

async def pagina_ha_programma(page) -> bool:
    try:
        testo = (await page.inner_text("body")).strip().lower()
    except Exception:
        return True
    return any(frase in testo for frase in FRASI_SEZIONI_PROGRAMMA)


# ── Utility: nome file univoco (evita sovrascritture silenziose) ─────────────

def nome_univoco(nome_base: str, usati: set) -> str:
    if nome_base not in usati:
        usati.add(nome_base)
        return nome_base
    stem, _, ext = nome_base.rpartition(".")
    stem, ext = (stem, ext) if stem else (nome_base, "pdf")
    n = 2
    while f"{stem}_{n}.{ext}" in usati:
        n += 1
    nuovo = f"{stem}_{n}.{ext}"
    usati.add(nuovo)
    return nuovo


# ── Utility: stampa pagina come PDF ──────────────────────────────────────────

async def stampa_pdf(page, percorso_output: Path) -> bool:
    try:
        await page.pdf(
            path=str(percorso_output),
            format="A4",
            print_background=True,
            margin={"top": "1.5cm", "bottom": "1.5cm",
                    "left": "1.5cm", "right": "1.5cm"}
        )
        return percorso_output.exists() and percorso_output.stat().st_size > 500
    except Exception:
        return False


# ── Strategia CINECA ──────────────────────────────────────────────────────────

async def scarica_cineca(context, url: str, percorso_output: Path,
                         verbose: bool) -> tuple[list[str], str]:
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await chiudi_cookie(page)

        if not await pagina_ha_programma(page):
            if verbose: print(f"\n    ✗ CINECA: nessun programma compilato (solo 'Informazioni generali')")
            return [], "senza_programma"

        async with page.expect_download(timeout=20000) as dl_info:
            salva = page.locator("text=Salva PDF").first
            await salva.wait_for(state="visible", timeout=10000)
            await salva.click()
        download = await dl_info.value
        await download.save_as(str(percorso_output))
        ok = percorso_output.exists()
        return ([str(percorso_output)], "") if ok else ([], "")
    except Exception as e:
        if verbose: print(f"\n    ✗ CINECA: {e}")
        return [], ""
    finally:
        await page.close()


# ── Strategia UNINA ───────────────────────────────────────────────────────────

async def scarica_unina(context, url: str, row: dict, indice: int,
                        cartella: Path, verbose: bool) -> list[str]:
    """
    Apre corsi.unina.it, trova tutti i link a docenti.unina.it,
    per ognuno clicca il pulsante 'Scarica PDF' e intercetta il download.
    """
    page = await context.new_page()
    files = []
    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await chiudi_cookie(page)
        await asyncio.sleep(1)

        # Trova link a docenti.unina.it (pagine programma singolo docente)
        links_docente = []
        seen = set()
        for el in await page.locator("a[href*='docenti.unina.it']").all():
            try:
                href = await el.get_attribute("href") or ""
                if href and href not in seen:
                    links_docente.append(href)
                    seen.add(href)
            except Exception:
                pass

        # Fallback: cerca link "Visualizza"
        if not links_docente:
            for el in await page.locator("a:has-text('Visualizza')").all():
                try:
                    if await el.is_visible() and await el.is_enabled():
                        href = await el.get_attribute("href") or ""
                        if href and href not in seen:
                            links_docente.append(href)
                            seen.add(href)
                except Exception:
                    pass

        if not links_docente:
            if verbose: print(f"\n    ✗ UNINA: nessun link docente trovato")
            return []

        if verbose:
            print(f"\n    → trovati {len(links_docente)} link docente")

        nomi_usati_riga = set()
        for j, href in enumerate(links_docente):
            docente_nome = row["docenti"][j] if j < len(row["docenti"]) else f"doc{j+1}"
            nome = nome_univoco(nome_file_pdf(row, indice, docente_nome), nomi_usati_riga)
            dest = cartella / nome

            if dest.exists() and dest.stat().st_size > 500:
                files.append(str(dest))
                continue

            page_doc = await context.new_page()
            try:
                full_url = href if href.startswith("http") else "https://www.corsi.unina.it" + href
                await page_doc.goto(full_url, wait_until="networkidle", timeout=30000)
                await chiudi_cookie(page_doc)
                await asyncio.sleep(1)

                # Clicca "Scarica PDF" e intercetta il download
                try:
                    async with page_doc.expect_download(timeout=20000) as dl_info:
                        scarica = page_doc.locator("text=Scarica PDF").first
                        await scarica.wait_for(state="visible", timeout=8000)
                        await scarica.click()
                    download = await dl_info.value
                    await download.save_as(str(dest))
                    if dest.exists() and dest.stat().st_size > 500:
                        files.append(str(dest))
                        if verbose: print(f"\n    ✓ UNINA [{docente_nome[:20]}] via 'Scarica PDF'")
                    else:
                        raise Exception("PDF vuoto")
                except Exception:
                    # Fallback: espandi sezioni e stampa
                    if verbose: print(f"\n    → fallback: espansione + stampa")
                    await espandi_sezioni(page_doc)
                    await asyncio.sleep(0.5)
                    if await stampa_pdf(page_doc, dest):
                        files.append(str(dest))
                        if verbose: print(f"\n    ✓ UNINA [{docente_nome[:20]}] via stampa")
                    else:
                        if verbose: print(f"\n    ✗ UNINA [{docente_nome[:20]}]: fallback fallito")

            except Exception as e:
                if verbose: print(f"\n    ✗ UNINA [{docente_nome[:20]}]: {e}")
            finally:
                await page_doc.close()
            await asyncio.sleep(0.8)

    except Exception as e:
        if verbose: print(f"\n    ✗ UNINA pagina indice: {e}")
    finally:
        await page.close()
    return files


# ── Strategia POLIMI ──────────────────────────────────────────────────────────

async def scarica_polimi(context, url: str, row: dict, indice: int,
                         cartella: Path, verbose: bool) -> list[str]:
    """
    Apre il manifesto Polimi, aspetta il caricamento JS,
    trova tutti i link href*='schedaincarico' e stampa PDF per ognuno.
    """
    page = await context.new_page()
    files = []
    try:
        # Polimi non raggiunge networkidle — usa load + attesa esplicita
        await page.goto(url, wait_until="load", timeout=30000)
        await asyncio.sleep(3)  # attesa rendering JS
        await chiudi_cookie(page)
        await asyncio.sleep(0.5)

        # Cerca link a schedaincarico
        links_scheda = []
        seen = set()

        # Prova prima a trovare link già presenti
        for el in await page.locator("a[href*='schedaincarico']").all():
            try:
                href = await el.get_attribute("href") or ""
                if href and href not in seen:
                    links_scheda.append(href)
                    seen.add(href)
            except Exception:
                pass

        # Se non trovati, prova a cliccare "Programma dettagliato" o icone libro
        if not links_scheda:
            for sel in [
                "a:has-text('Programma dettagliato')",
                "a[title*='programma' i]",
                "a[title*='scheda' i]",
                "td a img[src*='book']",
                "td:last-child a",
            ]:
                try:
                    els = await page.locator(sel).all()
                    for el in els:
                        href = await el.get_attribute("href") or ""
                        if not href:
                            # cerca href nel genitore
                            href = await page.evaluate(
                                "el => el.closest('a')?.href || ''",
                                await el.element_handle()
                            )
                        href = href.strip()
                        if href and "schedaincarico" in href and href not in seen:
                            links_scheda.append(href)
                            seen.add(href)
                except Exception:
                    pass

        # Ultimo fallback: estrai tutti gli href dalla pagina che contengono schedaincarico
        if not links_scheda:
            hrefs = await page.evaluate("""
                () => Array.from(document.querySelectorAll('a[href]'))
                    .map(a => a.href)
                    .filter(h => h.includes('schedaincarico'))
            """)
            for href in hrefs:
                if href not in seen:
                    links_scheda.append(href)
                    seen.add(href)

        if not links_scheda:
            if verbose: print(f"\n    ✗ POLIMI: nessun link schedaincarico trovato")
            return []

        if verbose:
            print(f"\n    → trovati {len(links_scheda)} link schedaincarico")

        nomi_usati_riga = set()
        for j, href in enumerate(links_scheda):
            docente_nome = row["docenti"][j] if j < len(row["docenti"]) else f"doc{j+1}"
            nome = nome_univoco(nome_file_pdf(row, indice, docente_nome), nomi_usati_riga)
            dest = cartella / nome

            if dest.exists() and dest.stat().st_size > 500:
                files.append(str(dest))
                continue

            page_sch = await context.new_page()
            try:
                full_url = href if href.startswith("http") else \
                           "https://onlineservices.polimi.it" + href
                await page_sch.goto(full_url, wait_until="load", timeout=30000)
                await asyncio.sleep(2)

                if await stampa_pdf(page_sch, dest):
                    files.append(str(dest))
                    if verbose: print(f"\n    ✓ POLIMI [{docente_nome[:20]}]")
                else:
                    if verbose: print(f"\n    ✗ POLIMI [{docente_nome[:20]}]: stampa fallita")
            except Exception as e:
                if verbose: print(f"\n    ✗ POLIMI [{docente_nome[:20]}]: {e}")
            finally:
                await page_sch.close()
            await asyncio.sleep(0.8)

    except Exception as e:
        if verbose: print(f"\n    ✗ POLIMI: {e}")
    finally:
        await page.close()
    return files


# ── Strategia HTML generica ───────────────────────────────────────────────────

async def scarica_html(page, url: str, percorso_output: Path,
                       verbose: bool) -> tuple[list[str], str]:
    """Chiudi cookie + espandi sezioni + stampa PDF."""
    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(1)
        await chiudi_cookie(page)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(0.5)
        await page.evaluate("window.scrollTo(0, 0)")

        n_esp = await espandi_sezioni(page)
        if n_esp and verbose:
            print(f"\n    → espanse {n_esp} sezioni")
        await asyncio.sleep(0.5)

        if not await pagina_ha_contenuto_valido(page):
            if verbose: print(f"\n    ✗ HTML: pagina senza contenuto valido (URL probabilmente scaduto)")
            return [], ""

        if await stampa_pdf(page, percorso_output):
            return [str(percorso_output)], ""
        return [], ""
    except Exception as e:
        if verbose: print(f"\n    ✗ HTML: {e}")
        return [], ""


# ── Strategia UNIROMA1 (Sapienza course catalogue) ────────────────────────────

async def scarica_uniroma1(page, url: str, percorso_output: Path,
                           verbose: bool) -> tuple[list[str], str]:
    """
    corsidilaurea.uniroma1.it a volte mostra prima una scelta di canale
    (A-K / L-Z) prima del programma vero e proprio. Il bottone "Stampa PDF"
    della pagina lancia solo window.print(), quindi non va cliccato: si usa
    direttamente la stampa PDF di Playwright come per la strategia HTML.
    """
    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await chiudi_cookie(page)

        canale = page.locator("a[href*='?channel=']").first
        try:
            if await canale.is_visible(timeout=2000):
                await canale.click()
                await page.wait_for_load_state("networkidle", timeout=15000)
                await chiudi_cookie(page)
        except Exception:
            pass

        await asyncio.sleep(0.5)

        if not await pagina_ha_contenuto_valido(page):
            if verbose: print(f"\n    ✗ UNIROMA1: pagina senza contenuto valido")
            return [], ""

        if not await pagina_ha_programma(page):
            if verbose: print(f"\n    ✗ UNIROMA1: nessun programma compilato (solo dati generali)")
            return [], "senza_programma"

        if await stampa_pdf(page, percorso_output):
            return [str(percorso_output)], ""
        return [], ""
    except Exception as e:
        if verbose: print(f"\n    ✗ UNIROMA1: {e}")
        return [], ""


# ── Strategia PDF diretto ─────────────────────────────────────────────────────

async def scarica_pdf_diretto(context, url: str, percorso_output: Path,
                               verbose: bool) -> list[str]:
    page = await context.new_page()
    try:
        response = await page.goto(url, wait_until="commit", timeout=30000)
        if response and response.status == 200:
            body = await response.body()
            with open(percorso_output, "wb") as f:
                f.write(body)
            if percorso_output.stat().st_size > 500:
                return [str(percorso_output)]
        return []
    except Exception as e:
        if verbose: print(f"\n    ✗ PDF diretto: {e}")
        return []
    finally:
        await page.close()


# ── Main ──────────────────────────────────────────────────────────────────────

async def main_async(args):
    from playwright.async_api import async_playwright

    nome_xls = Path(args.input).stem
    cartella_output = Path(args.output) / nome_xls
    cartella_output.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  MATRIX — Scarica Programmi")
    print(f"{'='*60}")
    print(f"  Input:   {args.input}")
    print(f"  Output:  {cartella_output.resolve()}")
    if args.ateneo:
        print(f"  Ateneo:  {args.ateneo}")
    print()

    print("📂 Lettura file export...")
    righe = leggi_export_xls(args.input)
    print(f"   {len(righe)} insegnamenti trovati nel file")

    da_scaricare = []
    stats = {"pdf_diretto": 0, "cineca": 0, "unina": 0, "polimi": 0, "uniroma1": 0,
             "html": 0, "gestionale": 0, "senza_programma": 0, "non_disponibile": 0}
    n_multi_docente = 0
    filtro_ateneo = args.ateneo.lower().strip() if args.ateneo else ""

    for r in righe:
        if filtro_ateneo and filtro_ateneo not in r["ateneo"].lower():
            continue
        tipo = classifica_url(r["url_ins"])
        r["_tipo"] = tipo
        stats[tipo] += 1
        if tipo in ("pdf_diretto", "cineca", "unina", "polimi", "uniroma1", "html"):
            da_scaricare.append(r)
        if len(r["docenti"]) > 1:
            n_multi_docente += 1

    print(f"\n📊 Distribuzione URL:")
    print(f"   PDF diretto:          {stats['pdf_diretto']:4d}  → download diretto")
    print(f"   Course Catalogue:     {stats['cineca']:4d}  → click 'Salva PDF'")
    print(f"   UNINA:                {stats['unina']:4d}  → click 'Visualizza' per docente")
    print(f"   Polimi:               {stats['polimi']:4d}  → link schedaincarico per docente")
    print(f"   Uniroma1 (Sapienza):  {stats['uniroma1']:4d}  → scelta canale + stampa")
    print(f"   Pagina HTML (altro):  {stats['html']:4d}  → espandi sezioni + stampa")
    print(f"   Sistema gestionale:   {stats['gestionale']:4d}  → saltati")
    print(f"   Senza programma:      {stats['senza_programma']:4d}  → saltati (pagina esiste ma non pubblica il programma)")
    print(f"   Non disponibile:      {stats['non_disponibile']:4d}  → saltati")
    print(f"\n   Insegnamenti multi-docente: {n_multi_docente}")
    print(f"   Da processare: {len(da_scaricare)}")

    if args.random:
        import random
        random.shuffle(da_scaricare)
        print(f"   (ordine casuale attivato)")

    if args.limit:
        da_scaricare = da_scaricare[:args.limit]
        print(f"   (limite impostato: {args.limit})")

    if not da_scaricare:
        print("\nNessun URL da scaricare. Uscita.")
        return

    if args.dry_run:
        print("\n(anteprima --dry-run: nessun download eseguito)")
        return

    if not args.yes:
        input(f"\nPremi INVIO per avviare il download...")

    print("\n🌐 Avvio browser headless...")
    risultati = {"ok": 0, "pdf_totali": 0, "errore": 0, "saltati": 0, "senza_programma": 0}
    log_righe = []
    multi_doc_info = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            accept_downloads=True,
        )
        page_html = await context.new_page()

        for i, row in enumerate(da_scaricare, 1):
            url  = row["url_ins"]
            tipo = row["_tipo"]
            n_doc = len(row["docenti"])
            nome  = nome_file_pdf(row, i)
            dest  = cartella_output / nome

            label = {"pdf_diretto":"PDF","cineca":"CIN","unina":"UNI",
                     "polimi":"POL","uniroma1":"UR1","html":"HTM"}.get(tipo, "???")
            doc_label = f"👥{n_doc}" if n_doc > 1 else "👤 1"
            print(f"[{i:3d}/{len(da_scaricare)}] [{label}] "
                  f"{row['insegnamento'][:38]:<38} | "
                  f"{row['ateneo'][:14]:<14} | {doc_label}",
                  end=" ", flush=True)

            # Salta se già presente (solo per tipi a PDF singolo)
            if tipo in ("pdf_diretto", "cineca", "uniroma1", "html"):
                if dest.exists() and dest.stat().st_size > 500:
                    print("→ già presente")
                    risultati["saltati"] += 1
                    log_righe.append({**row, "esito": "saltato", "file": nome})
                    continue

            files_scaricati = []
            motivo = ""

            if tipo == "cineca":
                files_scaricati, motivo = await scarica_cineca(context, url, dest, args.verbose)
            elif tipo == "unina":
                files_scaricati = await scarica_unina(context, url, row, i, cartella_output, args.verbose)
            elif tipo == "polimi":
                files_scaricati = await scarica_polimi(context, url, row, i, cartella_output, args.verbose)
            elif tipo == "uniroma1":
                files_scaricati, motivo = await scarica_uniroma1(page_html, url, dest, args.verbose)
            elif tipo == "html":
                files_scaricati, motivo = await scarica_html(page_html, url, dest, args.verbose)
            elif tipo == "pdf_diretto":
                files_scaricati = await scarica_pdf_diretto(context, url, dest, args.verbose)

            if files_scaricati:
                n = len(files_scaricati)
                print(f"→ ✓ ({n} PDF)" if n > 1 else "→ ✓")
                risultati["ok"] += 1
                risultati["pdf_totali"] += n
                if n > 1:
                    multi_doc_info.append({
                        "insegnamento": row["insegnamento"],
                        "ateneo":       row["ateneo"],
                        "n_docenti":    n_doc,
                        "n_pdf":        n,
                    })
                for f in files_scaricati:
                    log_righe.append({**row, "esito": "ok", "file": Path(f).name})
            elif motivo == "senza_programma":
                print("→ ⏭ senza programma")
                if dest.exists(): dest.unlink()
                risultati["senza_programma"] += 1
                log_righe.append({**row, "esito": "senza_programma", "file": ""})
            else:
                print("→ ✗")
                if dest.exists(): dest.unlink()
                risultati["errore"] += 1
                log_righe.append({**row, "esito": "errore", "file": ""})

            if i < len(da_scaricare):
                await asyncio.sleep(args.delay)

        await browser.close()

    # ── Report finale ─────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  RISULTATI")
    print(f"{'='*60}")
    print(f"  Insegnamenti processati: {risultati['ok'] + risultati['errore'] + risultati['senza_programma']}")
    print(f"  Scaricati con successo:  {risultati['ok']}")
    print(f"  PDF totali creati:       {risultati['pdf_totali']}")
    print(f"  Errori:                  {risultati['errore']}")
    print(f"  Senza programma:         {risultati['senza_programma']}  (pagina esistente ma non ancora compilata dal docente)")
    print(f"  Già presenti (saltati):  {risultati['saltati']}")
    print(f"  PDF salvati in:          {cartella_output.resolve()}")

    if multi_doc_info:
        print(f"\n  ⚠️  INSEGNAMENTI CON PIÙ PDF ({len(multi_doc_info)}):")
        print(f"  Per questi insegnamenti sono stati scaricati più PDF")
        print(f"  (uno per docente). Verifica che i programmi siano distinti")
        print(f"  prima di caricarli su Matrix Framework Builder.")
        print()
        for m in multi_doc_info[:10]:
            print(f"    · {m['insegnamento'][:45]} · {m['ateneo']} "
                  f"({m['n_docenti']} docenti → {m['n_pdf']} PDF)")
        if len(multi_doc_info) > 10:
            print(f"    ... e altri {len(multi_doc_info)-10}. Vedi log_download.csv")

    # ── Log CSV ───────────────────────────────────────────────────────────────
    log_path = cartella_output / "log_download.csv"
    with open(log_path, "w", encoding="utf-8-sig") as f:
        f.write("insegnamento;ateneo;docente;n_docenti;url_ins;tipo;esito;file\n")
        for r in log_righe:
            f.write(";".join([
                f'"{r.get("insegnamento","")}"',
                f'"{r.get("ateneo","")}"',
                f'"{r.get("docente","")}"',
                f'{len(r.get("docenti",[]))}',
                f'"{r.get("url_ins","")}"',
                f'"{r.get("_tipo","")}"',
                f'"{r.get("esito","")}"',
                f'"{r.get("file","")}"',
            ]) + "\n")
    print(f"\n  Log CSV: {log_path.name}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Scarica programmi universitari come PDF da un export MyUniversity"
    )
    parser.add_argument("--input",   required=True,
                        help="File export MyUniversity (.xls o .csv)")
    parser.add_argument("--output",  default="./programmi_pdf",
                        help="Cartella output PDF (default: ./programmi_pdf)")
    parser.add_argument("--ateneo",  default=None,
                        help="Filtra per ateneo (es. 'Milano Politecnico', 'Napoli')")
    parser.add_argument("--limit",   type=int, default=None,
                        help="Limita a N insegnamenti (per test)")
    parser.add_argument("--random",  action="store_true",
                        help="Ordine casuale — utile con --limit")
    parser.add_argument("--delay",   type=float, default=1.5,
                        help="Secondi tra download (default: 1.5)")
    parser.add_argument("--verbose", action="store_true",
                        help="Output dettagliato")
    parser.add_argument("--yes",     action="store_true",
                        help="Non chiedere conferma prima di avviare il download (utile da script/GUI)")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run",
                        help="Mostra solo la distribuzione dei link, senza scaricare nulla")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Errore: file non trovato: {args.input}")
        sys.exit(1)

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
