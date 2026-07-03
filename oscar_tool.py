#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
oscar_tool.py — OUTIL UNIQUE (néophyte). Met à jour les cours OSCAR de bout en
bout : export AEC (tous centres) → fusion + déduplication → indicateurs OSCAR
(année scolaire + secteur).

Lancer :
    python oscar_tool.py          # fenêtre graphique (logs en direct)
    python oscar_tool.py --cli    # terminal, avec questions
"""
from __future__ import annotations
import os
import sys
import queue
import threading
import subprocess
from pathlib import Path
from datetime import date, datetime

ICI = Path(__file__).resolve().parent
OUT_DIR = ICI / "data" / "new_cours"
PY = sys.executable  # le venv a playwright + pandas + customtkinter

ETAPES = [
    ("Export AEC (année(s) ciblée(s))", "export_cours_aec.py"),
    ("Mise à jour du cache (vérifs)", "update_cache.py"),
    ("Indicateurs OSCAR", "oscar_cours.py"),
]
FICHIER_RESULTAT = OUT_DIR / "oscar_indicateurs_cours.xlsx"


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #
def ouvrir_chemin(p):
    """Ouvre un fichier/dossier dans le système (cross-platform)."""
    p = str(p)
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", p])
        elif os.name == "nt":
            os.startfile(p)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", p])
    except Exception:
        pass


def reveler(p):
    """Affiche le fichier dans le Finder/Explorateur (sélectionné), sans l'ouvrir."""
    p = str(p)
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", "-R", p])
        elif os.name == "nt":
            subprocess.Popen(["explorer", f"/select,{p}"])
        else:
            ouvrir_chemin(str(Path(p).parent))
    except Exception:
        pass


def keychain_ok():
    """True/False si les identifiants AEC sont dans le Trousseau (macOS), None ailleurs."""
    if sys.platform != "darwin":
        return None
    try:
        return subprocess.run(["security", "find-generic-password", "-s", "aec-ifitalie"],
                              capture_output=True).returncode == 0
    except Exception:
        return False


def derniere_maj():
    if FICHIER_RESULTAT.exists():
        return datetime.fromtimestamp(FICHIER_RESULTAT.stat().st_mtime).strftime("%d/%m/%Y à %H:%M")
    return None


def run_pipeline(cutoff_months, annees=None, log=print, on_step=None, should_stop=None):
    """Lance les 3 étapes en sous-processus, streame les logs.
    annees=None → l'export prend 2023→année courante ; sinon liste (ex. ['2026'])."""
    env = dict(os.environ)
    env["OSCAR_CUTOFF_MONTHS"] = str(cutoff_months)
    env["PYTHONUNBUFFERED"] = "1"
    if annees:
        env["OSCAR_ANNEES"] = ",".join(annees)
    for i, (titre, script) in enumerate(ETAPES, 1):
        if should_stop and should_stop():
            log("⏹️ Arrêt demandé."); return False
        if on_step:
            on_step("start", i, titre)
        log("\n" + "═" * 58)
        log(f"▶ Étape {i}/3 — {titre}")
        log("═" * 58)
        try:
            p = subprocess.Popen(
                [PY, str(ICI / script)], cwd=str(ICI), env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        except Exception as e:  # noqa: BLE001
            log(f"❌ impossible de lancer {script} : {e}")
            if on_step:
                on_step("done", i, False)
            return False
        for line in p.stdout:
            log(line.rstrip("\n"))
            if should_stop and should_stop():
                p.terminate(); log("⏹️ Arrêt.")
                if on_step:
                    on_step("done", i, False)
                return False
        p.wait()
        ok = p.returncode == 0
        if on_step:
            on_step("done", i, ok)
        if not ok:
            log(f"❌ Étape « {titre} » a échoué (code {p.returncode}).")
            return False
    log("\n🎉 TERMINÉ — fichiers à jour dans data/new_cours/")
    return True


# --------------------------------------------------------------------------- #
#  MODE TERMINAL
# --------------------------------------------------------------------------- #
def main_cli():
    print("=" * 58)
    print("  Récupération / MAJ des cours depuis AEC (terminal)")
    print("=" * 58)
    maj = derniere_maj()
    print(f"Dernière mise à jour : {maj}" if maj else "Jamais mis à jour.")
    print("\nMode :  1) Rapide — année en cours seulement, fusionnée au cache (~2 min, recommandé)")
    print("        2) Complète — reconstruction 2023 → aujourd'hui (~6 min)")
    mode = input("Choix [1] : ").strip() or "1"
    annees = ([str(y) for y in range(2023, date.today().year + 1)] if mode == "2"
              else [str(date.today().year)])
    rep = input("Année en cours : écoulé + combien de mois ? [1] : ").strip() or "1"
    try:
        n = int(rep)
    except ValueError:
        n = 1
    print("\n⚠️  Ne sois PAS connecté à AEC ailleurs pendant le run (AEC = session unique).")
    print("    Une fenêtre Chrome va s'ouvrir ; connexion automatique (Trousseau).\n")
    ok = run_pipeline(n, annees=annees, log=lambda m: print(m, flush=True))
    if ok:
        print(f"\n✅ Terminé → {FICHIER_RESULTAT}")
        reveler(FICHIER_RESULTAT)
    else:
        print("\n❌ Échec (voir logs ci-dessus).")


# --------------------------------------------------------------------------- #
#  MODE GRAPHIQUE
# --------------------------------------------------------------------------- #
def main_gui():
    import customtkinter as ctk

    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    app = ctk.CTk()
    app.title("Récupération des cours depuis AEC")
    app.geometry("840x820")
    app.minsize(760, 720)
    state = {"running": False, "stop": False, "q": queue.Queue(), "step_lbls": []}

    # ---------- En-tête ----------
    head = ctk.CTkFrame(app, fg_color="transparent")
    head.pack(fill="x", padx=24, pady=(18, 4))
    ctk.CTkLabel(head, text="📥 Récupération / MAJ des cours — AEC",
                 font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w")
    maj = derniere_maj()
    ctk.CTkLabel(head, text=(f"Dernière mise à jour : {maj}" if maj else "Jamais mis à jour — lance une première fois."),
                 text_color="gray").pack(anchor="w")
    ctk.CTkLabel(head, text="Cache blindé · par défaut, ne re-télécharge que l'année en cours (incrémental).",
                 text_color="gray").pack(anchor="w")

    # ---------- Options ----------
    card = ctk.CTkFrame(app, corner_radius=14)
    card.pack(fill="x", padx=24, pady=12)
    ctk.CTkLabel(card, text="⚙️  Options", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=18, pady=(14, 6))

    # mode
    row1 = ctk.CTkFrame(card, fg_color="transparent"); row1.pack(fill="x", padx=18, pady=4)
    ctk.CTkLabel(row1, text="Données :", width=170, anchor="w").pack(side="left")
    mode = ctk.CTkSegmentedButton(row1, values=["Rapide (année en cours)", "Complète (2023 → auj.)"])
    mode.set("Rapide (année en cours)")
    mode.pack(side="left", fill="x", expand=True)

    # cutoff
    row2 = ctk.CTkFrame(card, fg_color="transparent"); row2.pack(fill="x", padx=18, pady=4)
    ctk.CTkLabel(row2, text="Année en cours jusqu'à :", width=170, anchor="w").pack(side="left")
    cutoff = ctk.CTkSegmentedButton(row2, values=["aujourd'hui", "+1 mois", "+2 mois", "+3 mois"])
    cutoff.set("+1 mois")
    cutoff.pack(side="left", fill="x", expand=True)

    # ouvrir à la fin
    row3 = ctk.CTkFrame(card, fg_color="transparent"); row3.pack(fill="x", padx=18, pady=(4, 14))
    open_end = ctk.CTkCheckBox(row3, text="Montrer le fichier résultat à la fin (dans le Finder)")
    open_end.select()
    open_end.pack(side="left")

    # ---------- Pré-checks ----------
    kc = keychain_ok()
    if kc is True:
        kc_txt, kc_col = "🔑 Identifiants AEC (Trousseau) : trouvés ✅", "#16a34a"
    elif kc is False:
        kc_txt, kc_col = "🔑 Identifiants AEC absents du Trousseau → connexion manuelle (voir README)", "#d97706"
    else:
        kc_txt, kc_col = "🔑 Windows : connexion manuelle mémorisée par le profil", "gray"
    ctk.CTkLabel(app, text=kc_txt, text_color=kc_col).pack(anchor="w", padx=28)
    ctk.CTkLabel(app, text="⚠️ Ne sois pas connecté à AEC ailleurs pendant le run (AEC = une seule session).",
                 text_color="#d97706").pack(anchor="w", padx=28, pady=(2, 6))

    # ---------- Boutons ----------
    btns = ctk.CTkFrame(app, fg_color="transparent"); btns.pack(fill="x", padx=24)
    start_btn = ctk.CTkButton(btns, text="▶  Lancer la mise à jour", height=48,
                              font=ctk.CTkFont(size=16, weight="bold"),
                              fg_color="#22c55e", hover_color="#16a34a")
    start_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))
    stop_btn = ctk.CTkButton(btns, text="⏹ Arrêter", height=48, width=120,
                             fg_color="#ef4444", hover_color="#dc2626", state="disabled")
    stop_btn.pack(side="right")

    # ---------- Étapes ----------
    steps = ctk.CTkFrame(app, fg_color="transparent"); steps.pack(fill="x", padx=28, pady=(12, 2))
    for titre, _ in ETAPES:
        lbl = ctk.CTkLabel(steps, text=f"⚪️  {titre}", anchor="w", font=ctk.CTkFont(size=13))
        lbl.pack(anchor="w")
        state["step_lbls"].append(lbl)

    prog = ctk.CTkProgressBar(app); prog.pack(fill="x", padx=24, pady=(10, 2)); prog.set(0)
    status = ctk.CTkLabel(app, text="Prêt.", text_color="gray"); status.pack()

    # ---------- Logs ----------
    logbox = ctk.CTkTextbox(app, font=ctk.CTkFont(
        family="Monaco" if sys.platform == "darwin" else "Consolas", size=11))
    logbox.pack(fill="both", expand=True, padx=24, pady=(10, 6))

    foot = ctk.CTkFrame(app, fg_color="transparent"); foot.pack(fill="x", padx=24, pady=(0, 14))
    ctk.CTkButton(foot, text="📂 Ouvrir le dossier", width=160, fg_color="gray30", hover_color="gray40",
                  command=lambda: ouvrir_chemin(OUT_DIR)).pack(side="left")
    open_res_btn = ctk.CTkButton(foot, text="📊 Ouvrir les indicateurs", width=180, fg_color="gray30",
                                 hover_color="gray40", command=lambda: ouvrir_chemin(FICHIER_RESULTAT),
                                 state="normal" if FICHIER_RESULTAT.exists() else "disabled")
    open_res_btn.pack(side="left", padx=8)

    def save_logs():
        f = OUT_DIR / "oscar_tool_logs.txt"
        try:
            f.write_text(logbox.get("1.0", "end"), encoding="utf-8")
            ouvrir_chemin(f)
        except Exception:
            pass
    ctk.CTkButton(foot, text="💾 Enregistrer les logs", width=180, fg_color="gray30",
                  hover_color="gray40", command=save_logs).pack(side="right")

    # ---------- Mécanique ----------
    def push(m): state["q"].put(("log", m))

    def on_step(kind, i, *rest):
        state["q"].put(("step", kind, i, rest))

    def pump():
        try:
            while True:
                item = state["q"].get_nowait()
                if item[0] == "step":
                    _, kind, i, rest = item
                    lbl = state["step_lbls"][i - 1]
                    if kind == "start":
                        lbl.configure(text=f"⏳  {ETAPES[i-1][0]} …")
                        prog.set((i - 0.5) / (len(ETAPES) + 0.0))
                        status.configure(text=f"Étape {i}/3 : {ETAPES[i-1][0]} …")
                    else:  # done
                        ok = rest[0]
                        lbl.configure(text=f"{'✅' if ok else '❌'}  {ETAPES[i-1][0]}")
                        prog.set(i / float(len(ETAPES)))
                else:
                    logbox.insert("end", item[1] + "\n"); logbox.see("end")
        except queue.Empty:
            pass
        app.after(100, pump)

    def set_running(on):
        state["running"] = on
        start_btn.configure(state="disabled" if on else "normal")
        stop_btn.configure(state="normal" if on else "disabled")
        for w in (mode, cutoff):
            try:
                w.configure(state="disabled" if on else "normal")
            except Exception:
                pass

    def worker(n, annees, open_at_end):
        ok = run_pipeline(n, annees=annees, log=push, on_step=on_step, should_stop=lambda: state["stop"])

        def done():
            status.configure(text="Terminé ✅" if ok else "Arrêté / échec ❌")
            set_running(False)
            if FICHIER_RESULTAT.exists():
                open_res_btn.configure(state="normal")
            if ok and open_at_end and FICHIER_RESULTAT.exists():
                reveler(FICHIER_RESULTAT)   # montre le fichier final dans le Finder
        app.after(0, done)

    def start():
        if state["running"]:
            return
        n = {"aujourd'hui": 0, "+1 mois": 1, "+2 mois": 2, "+3 mois": 3}.get(cutoff.get(), 1)
        if mode.get().startswith("Rapide"):
            annees = [str(date.today().year)]                                  # incrémental
        else:
            annees = [str(y) for y in range(2023, date.today().year + 1)]      # reconstruction
        for lbl, (titre, _) in zip(state["step_lbls"], ETAPES):
            lbl.configure(text=f"⚪️  {titre}")
        logbox.delete("1.0", "end"); prog.set(0)
        state["stop"] = False
        set_running(True)
        status.configure(text="Démarrage… (une fenêtre Chrome va s'ouvrir)")
        threading.Thread(target=worker, args=(n, annees, bool(open_end.get())), daemon=True).start()

    def stop():
        state["stop"] = True
        status.configure(text="Arrêt demandé…")

    start_btn.configure(command=start)
    stop_btn.configure(command=stop)
    pump()
    app.mainloop()


if __name__ == "__main__":
    if "--cli" in sys.argv or "--terminal" in sys.argv:
        main_cli()
    else:
        try:
            main_gui()
        except Exception as e:  # noqa: BLE001
            print(f"(GUI indisponible : {e}) → bascule en mode terminal.\n")
            main_cli()
