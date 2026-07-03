#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ré-export COMPLET du périmètre 25-26 : sélectionne les nœuds de période
2024+2025+2026 ENSEMBLE (les sessions « 2025-2026 » / « fév 2026 » sont rangées
par année de création, pas par date de cours) → un seul export → filtrage par
Date début en aval. Corrige la fuite janv–avr 2026 de l'export par année."""
from __future__ import annotations
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
import aec_login
import export_cours_aec as exp

OUT = Path(__file__).parent / "data" / "new_cours"
CIBLE = OUT / "cours_2526_frais.xlsx"
ANNEES = ["2024", "2025", "2026"]


def main():
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(exp.PROFIL.resolve()), headless=False,
            accept_downloads=True, args=["--start-maximized"], no_viewport=True)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(exp.BASE + exp.ROUTE)
        page = aec_login.assurer_connexion(ctx, page, log=print)
        if not page:
            print("✗ pas connecté"); ctx.close(); return
        exp.aller_all_courses(page)
        print(f"page = {page.url}")
        exp.select_all_centres(page)
        # sélectionne les 3 années de période EN UN SEUL COUP (cascade -> toutes leurs sessions)
        ok = exp.set_periods(page, ANNEES)
        print(f"set_periods({ANNEES}) -> {ok}")
        exp.attendre_preload(page); time.sleep(2)
        res = exp.exporter(page, CIBLE)
        if res:
            exp.verifier(CIBLE)
        print("Terminé.")
        time.sleep(1)
        ctx.close()


if __name__ == "__main__":
    main()
