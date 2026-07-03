#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scout jetable : dumpe l'arbre COMPLET du filtre Période d'AEC (all-courses)
pour comprendre le mapping période <-> mois, et pourquoi janv–avr 2026 a fui."""
from __future__ import annotations
import json, time
from pathlib import Path
from playwright.sync_api import sync_playwright
import aec_login
import export_cours_aec as exp

OUT = Path(__file__).parent / "data" / "new_cours"


def main():
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(exp.PROFIL.resolve()), headless=False,
            accept_downloads=True, args=["--start-maximized"], no_viewport=True)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(exp.BASE + exp.ROUTE)
        page = aec_login.assurer_connexion(ctx, page, log=print)
        exp.aller_all_courses(page)
        # ouvrir le filtre période
        exp.ouvrir_filtre(page, '[test="IDPERIODs"]', "periode",
                          '.k-animation-container .k-treeview-leaf, kendo-popup .k-treeview-leaf')
        # charger toutes les périodes (anciennes) + tout déplier
        for _ in range(16):
            try:
                link = page.get_by_text("Voir les périodes les plus anciennes")
                if link.count() and link.first.is_visible():
                    link.first.click(); time.sleep(0.8)
                else:
                    break
            except Exception:
                break
        # déplier chaque noeud (flèches d'expand)
        for _ in range(6):
            toggles = page.locator('.k-animation-container .k-treeview-toggle, kendo-popup .k-treeview-toggle')
            n = toggles.count(); changed = 0
            for i in range(n):
                try:
                    t = toggles.nth(i)
                    # état fermé => cliquer
                    cls = t.get_attribute("class") or ""
                    if "k-i-caret-alt-right" in cls or "k-i-expand" in cls or "collaps" in cls:
                        t.click(); changed += 1; time.sleep(0.15)
                except Exception:
                    continue
            if changed == 0:
                break
        # dump complet: chaque item avec profondeur, texte, aria, checked
        tree = page.evaluate("""() => {
            const rows=[];
            document.querySelectorAll('.k-animation-container li.k-treeview-item, kendo-popup li.k-treeview-item').forEach(li=>{
                const leaf=li.querySelector(':scope > div .k-treeview-leaf, :scope > .k-treeview-leaf, :scope div.k-treeview-leaf');
                const cb=li.querySelector(':scope > div input.k-checkbox, :scope input.k-checkbox');
                // profondeur = nb d'ancêtres li.k-treeview-item
                let d=0,p=li.parentElement; while(p){ if(p.matches && p.matches('li.k-treeview-item')) d++; p=p.parentElement; }
                rows.push({
                    depth:d,
                    txt:(leaf?leaf.innerText:'').replace(/\\s+/g,' ').trim().slice(0,40),
                    aria:cb?cb.getAttribute('aria-labelledby'):'',
                    checked: cb ? (cb.className||'').includes('k-checked') : null
                });
            });
            return rows;
        }""")
        (OUT / "_scout_periodes_tree.json").write_text(json.dumps(tree, ensure_ascii=False, indent=1))
        print(f"\n=== ARBRE PÉRIODES ({len(tree)} noeuds) ===")
        for r in tree:
            print(("  " * r["depth"]) + f"[{r['aria']}] {r['txt']}  {'✓' if r['checked'] else ''}")
        page.screenshot(path=str(OUT / "_scout_periodes.png"))
        time.sleep(1)
        ctx.close()


if __name__ == "__main__":
    main()
