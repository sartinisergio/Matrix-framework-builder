#!/usr/bin/env python3
"""
scarica_programmi_gui.py
-------------------------
Interfaccia grafica per scarica_programmi.py: permette di scegliere il file
di export, i parametri e avviare il download senza usare il Prompt dei comandi.
"""

import os
import subprocess
import sys
import threading
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

CARTELLA_SCRIPT = Path(__file__).resolve().parent
SCRIPT_DOWNLOAD = CARTELLA_SCRIPT / "scarica_programmi.py"
SCRIPT_VERIFICA = CARTELLA_SCRIPT / "verifica_pdf.py"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MATRIX — Scarica Programmi")
        self.geometry("820x640")
        self.minsize(680, 480)

        self.processo = None
        self._costruisci_interfaccia()
        self._aggiorna_lista_file()

    # ── Interfaccia ────────────────────────────────────────────────────────

    def _costruisci_interfaccia(self):
        pad = {"padx": 10, "pady": 6}

        frame_form = ttk.Frame(self)
        frame_form.pack(fill="x", **pad)

        # File di export
        ttk.Label(frame_form, text="File di export (.xls/.xlsx/.csv):").grid(row=0, column=0, sticky="w")
        self.var_file = tk.StringVar()
        self.combo_file = ttk.Combobox(frame_form, textvariable=self.var_file, width=50)
        self.combo_file.grid(row=1, column=0, columnspan=2, sticky="we", pady=(0, 6))
        ttk.Button(frame_form, text="Sfoglia…", command=self._scegli_file).grid(row=1, column=2, padx=(6, 0))
        ttk.Button(frame_form, text="Aggiorna elenco", command=self._aggiorna_lista_file).grid(row=1, column=3, padx=(6, 0))

        # Ateneo / limite / delay
        ttk.Label(frame_form, text="Filtra per ateneo (opzionale):").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.var_ateneo = tk.StringVar()
        ttk.Entry(frame_form, textvariable=self.var_ateneo, width=30).grid(row=3, column=0, sticky="w")

        ttk.Label(frame_form, text="Limite insegnamenti (vuoto = tutti):").grid(row=2, column=1, sticky="w", pady=(8, 0))
        self.var_limite = tk.StringVar()
        ttk.Entry(frame_form, textvariable=self.var_limite, width=10).grid(row=3, column=1, sticky="w")

        ttk.Label(frame_form, text="Attesa tra i download (secondi):").grid(row=2, column=2, sticky="w", pady=(8, 0))
        self.var_delay = tk.StringVar(value="1.5")
        ttk.Entry(frame_form, textvariable=self.var_delay, width=8).grid(row=3, column=2, sticky="w")

        # Checkbox
        frame_opz = ttk.Frame(self)
        frame_opz.pack(fill="x", padx=10)
        self.var_random = tk.BooleanVar()
        self.var_verbose = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame_opz, text="Ordine casuale", variable=self.var_random).pack(side="left")
        ttk.Checkbutton(frame_opz, text="Output dettagliato", variable=self.var_verbose).pack(side="left", padx=(16, 0))

        # Cartella output
        frame_out = ttk.Frame(self)
        frame_out.pack(fill="x", **pad)
        ttk.Label(frame_out, text="Cartella output:").pack(side="left")
        self.var_output = tk.StringVar(value=str(CARTELLA_SCRIPT / "programmi_pdf"))
        ttk.Entry(frame_out, textvariable=self.var_output).pack(side="left", fill="x", expand=True, padx=(6, 6))
        ttk.Button(frame_out, text="Sfoglia…", command=self._scegli_cartella_output).pack(side="left")

        # Pulsanti azione
        frame_azioni = ttk.Frame(self)
        frame_azioni.pack(fill="x", **pad)
        self.btn_anteprima = ttk.Button(frame_azioni, text="🔍 Anteprima (nessun download)", command=self._avvia_anteprima)
        self.btn_anteprima.pack(side="left")
        self.btn_avvia = ttk.Button(frame_azioni, text="▶ Avvia download", command=self._avvia_download)
        self.btn_avvia.pack(side="left", padx=(8, 0))
        self.btn_stop = ttk.Button(frame_azioni, text="⏹ Interrompi", command=self._interrompi, state="disabled")
        self.btn_stop.pack(side="left", padx=(8, 0))
        self.btn_verifica = ttk.Button(frame_azioni, text="🔎 Verifica PDF scaricati", command=self._avvia_verifica)
        self.btn_verifica.pack(side="left", padx=(8, 0))

        self.var_stato = tk.StringVar(value="Pronto.")
        ttk.Label(frame_azioni, textvariable=self.var_stato).pack(side="right")

        # Output testuale
        frame_out_testo = ttk.Frame(self)
        frame_out_testo.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.testo = tk.Text(frame_out_testo, wrap="word", bg="#111", fg="#ddd", insertbackground="#ddd")
        scroll = ttk.Scrollbar(frame_out_testo, command=self.testo.yview)
        self.testo.configure(yscrollcommand=scroll.set)
        self.testo.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        frame_form.columnconfigure(0, weight=1)

    # ── Helper file ────────────────────────────────────────────────────────

    def _aggiorna_lista_file(self):
        estensioni = (".xls", ".xlsx", ".csv")
        trovati = sorted(
            f.name for f in CARTELLA_SCRIPT.iterdir()
            if f.is_file() and f.suffix.lower() in estensioni
        )
        self.combo_file["values"] = trovati
        if trovati and not self.var_file.get():
            self.var_file.set(trovati[0])

    def _scegli_file(self):
        percorso = filedialog.askopenfilename(
            initialdir=str(CARTELLA_SCRIPT),
            title="Scegli il file di export",
            filetypes=[("Export MyUniversity", "*.xls *.xlsx *.csv"), ("Tutti i file", "*.*")],
        )
        if percorso:
            self.var_file.set(percorso)

    def _scegli_cartella_output(self):
        percorso = filedialog.askdirectory(initialdir=self.var_output.get() or str(CARTELLA_SCRIPT))
        if percorso:
            self.var_output.set(percorso)

    # ── Costruzione comando ───────────────────────────────────────────────

    def _costruisci_comando(self, dry_run: bool) -> list[str] | None:
        file_input = self.var_file.get().strip()
        if not file_input:
            messagebox.showerror("Errore", "Seleziona un file di export.")
            return None

        percorso_input = Path(file_input)
        if not percorso_input.is_absolute():
            percorso_input = CARTELLA_SCRIPT / file_input
        if not percorso_input.exists():
            messagebox.showerror("Errore", f"File non trovato:\n{percorso_input}")
            return None

        cmd = [sys.executable, "-u", str(SCRIPT_DOWNLOAD), "--input", str(percorso_input)]

        output = self.var_output.get().strip()
        if output:
            cmd += ["--output", output]

        ateneo = self.var_ateneo.get().strip()
        if ateneo:
            cmd += ["--ateneo", ateneo]

        limite = self.var_limite.get().strip()
        if limite:
            if not limite.isdigit():
                messagebox.showerror("Errore", "Il limite deve essere un numero intero.")
                return None
            cmd += ["--limit", limite]

        delay = self.var_delay.get().strip()
        if delay:
            try:
                float(delay)
            except ValueError:
                messagebox.showerror("Errore", "L'attesa deve essere un numero (es. 1.5).")
                return None
            cmd += ["--delay", delay]

        if self.var_random.get():
            cmd.append("--random")
        if self.var_verbose.get():
            cmd.append("--verbose")

        if dry_run:
            cmd.append("--dry-run")
        else:
            cmd.append("--yes")

        return cmd

    # ── Avvio processo ────────────────────────────────────────────────────

    def _avvia_anteprima(self):
        self._avvia(dry_run=True)

    def _avvia_download(self):
        self._avvia(dry_run=False)

    def _avvia(self, dry_run: bool):
        cmd = self._costruisci_comando(dry_run=dry_run)
        if cmd is None:
            return
        self._esegui(cmd, "Anteprima in corso…" if dry_run else "Download in corso…")

    def _avvia_verifica(self):
        file_input = self.var_file.get().strip()
        if not file_input:
            messagebox.showerror("Errore", "Seleziona prima un file di export: la verifica controlla la sua cartella di output.")
            return
        cartella_pdf = Path(self.var_output.get().strip() or (CARTELLA_SCRIPT / "programmi_pdf")) / Path(file_input).stem
        if not cartella_pdf.is_dir():
            messagebox.showerror("Errore", f"Nessuna cartella di PDF trovata:\n{cartella_pdf}\n\nScarica prima i programmi di questo file.")
            return
        cmd = [sys.executable, "-u", str(SCRIPT_VERIFICA), "--cartella", str(cartella_pdf)]
        self._esegui(cmd, "Verifica in corso…")

    def _esegui(self, cmd: list[str], etichetta_stato: str):
        if self.processo is not None:
            messagebox.showinfo("In corso", "Un'operazione è già in esecuzione.")
            return

        self.testo.delete("1.0", "end")
        self._log(f"$ {' '.join(cmd)}\n\n")
        self.var_stato.set(etichetta_stato)
        self.btn_anteprima.config(state="disabled")
        self.btn_avvia.config(state="disabled")
        self.btn_verifica.config(state="disabled")
        self.btn_stop.config(state="normal")

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        self.processo = subprocess.Popen(
            cmd,
            cwd=str(CARTELLA_SCRIPT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        threading.Thread(target=self._leggi_output, daemon=True).start()

    def _leggi_output(self):
        assert self.processo is not None
        for riga in self.processo.stdout:
            self.after(0, self._log, riga)
        codice = self.processo.wait()
        self.after(0, self._fine_processo, codice)

    def _log(self, testo: str):
        self.testo.insert("end", testo)
        self.testo.see("end")

    def _fine_processo(self, codice: int):
        self.processo = None
        self.btn_anteprima.config(state="normal")
        self.btn_avvia.config(state="normal")
        self.btn_verifica.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.var_stato.set("Completato." if codice == 0 else f"Terminato (codice {codice}).")

    def _interrompi(self):
        if self.processo is not None:
            self.processo.terminate()
            self._log("\n\n[Interrotto dall'utente]\n")


if __name__ == "__main__":
    App().mainloop()
