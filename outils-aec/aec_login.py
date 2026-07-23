#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aec_login.py — connexion AEC robuste & réutilisable (importé par les scripts).

Stratégie (dans l'ordre) :
  1. Déjà connecté (profil persistant) ?
  2. Auto-login via identifiants du Trousseau macOS (Keychain) — service
     « aec-ifitalie ». Le mot de passe N'EST jamais dans le code : il est lu à
     l'exécution via `security`. Coche « Rester connecté ». → zéro expiration.
  3. Restauration de session depuis data/new_cours/aec_state.json (filet).
  4. Sinon, attente d'une connexion manuelle.

Stocker les identifiants UNE fois (dans un Terminal) :
    security add-generic-password -U -s aec-ifitalie -a "ton.email@exemple.fr" -w
  (tape ton mot de passe AEC quand c'est demandé — il reste chiffré dans le Trousseau)
"""
from __future__ import annotations
import os, re, time, json, subprocess
from pathlib import Path

BASE = "https://ifitalie.aec.app/"
PROFIL = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "aec_exporter_profil_chrome"
STATE = Path(__file__).resolve().parent / "data" / "new_cours" / "aec_state.json"
SERVICE = "aec-ifitalie"
APP_MARKER = '[test="change_etablishment_branch_and_point_sale"]'


def _log(log, m):
    (log or print)(m)


def page_connectee(ctx):
    for pg in list(ctx.pages):
        try:
            if pg.locator(APP_MARKER).count() > 0:
                return pg
        except Exception:
            continue
    return None


def lire_keychain():
    """(email, password) depuis le Trousseau, ou (None, None)."""
    try:
        pw = subprocess.run(["security", "find-generic-password", "-s", SERVICE, "-w"],
                            capture_output=True, text=True, timeout=10)
        if pw.returncode != 0:
            return None, None
        meta = subprocess.run(["security", "find-generic-password", "-s", SERVICE],
                              capture_output=True, text=True, timeout=10)
        password = pw.stdout.strip()
        m = re.search(r'"acct"<blob>="([^"]*)"', meta.stdout)
        email = m.group(1) if m else ""
        if email and password:
            return email, password
    except Exception:
        pass
    return None, None


def _auto_login(ctx, page, log):
    email, pw = lire_keychain()
    if not (email and pw):
        return None
    _log(log, f"  🔐 identifiants Keychain trouvés ({email}) → auto-login")
    try:
        page.goto(BASE + "#/login", wait_until="domcontentloaded")
    except Exception:
        pass
    time.sleep(2)
    try:
        em = None
        for getter in (lambda: page.get_by_placeholder("Courrier électronique"),
                       lambda: page.locator('input[type="email"]'),
                       lambda: page.locator('input[type="text"]')):
            loc = getter()
            if loc.count() > 0:
                em = loc.first
                break
        pwd = page.locator('input[type="password"]')
        if em is None or pwd.count() == 0:
            _log(log, "  (champs de login introuvables)")
            return None
        em.fill(email)
        pwd.first.fill(pw)
        for sel in ('label:has-text("Rester connecté") input[type="checkbox"]',
                    'input[type="checkbox"]'):
            l = page.locator(sel)
            if l.count() > 0:
                try:
                    if not l.first.is_checked():
                        l.first.check()
                except Exception:
                    pass
                break
        clic_ok = False
        for getter in (lambda: page.get_by_role("button", name="Connexion"),
                       lambda: page.locator('button:has-text("Connexion")'),
                       lambda: page.locator('button[type="submit"]')):
            try:
                b = getter()
                if b.count() > 0:
                    b.first.click(timeout=6000, force=True)
                    clic_ok = True
                    break
            except Exception:
                continue
        if not clic_ok:
            # fallback : valider le formulaire en pressant Entrée dans le mot de passe
            try:
                pwd.first.press("Enter")
                clic_ok = True
            except Exception:
                pass
        _log(log, "  🔐 « Connexion » " + ("validée" if clic_ok else "NON validée (bouton injoignable)"))
    except Exception as e:
        _log(log, f"  (auto-login erreur: {e})")
        return None
    fin = time.time() + 30
    while time.time() < fin:
        pg = page_connectee(ctx)
        if pg:
            return pg
        time.sleep(1.5)
    return None


def _restaurer(ctx, page, log):
    if not STATE.exists():
        return None
    try:
        data = json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return None
    try:
        ctx.add_cookies(data.get("cookies", []))
    except Exception:
        pass
    try:
        page.goto(BASE, wait_until="domcontentloaded")
    except Exception:
        pass
    for o in data.get("origins", []):
        if "ifitalie.aec.app" in o.get("origin", ""):
            for it in o.get("localStorage", []):
                try:
                    page.evaluate("(kv)=>localStorage.setItem(kv[0],kv[1])", [it["name"], it["value"]])
                except Exception:
                    pass
    try:
        page.reload(wait_until="domcontentloaded")
    except Exception:
        pass
    fin = time.time() + 20
    while time.time() < fin:
        pg = page_connectee(ctx)
        if pg:
            return pg
        time.sleep(1.5)
    return None


def sauver_session(ctx, log=None):
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        ctx.storage_state(path=str(STATE))
        _log(log, "  💾 session sauvegardée (filet)")
    except Exception:
        pass


def assurer_connexion(ctx, page, log=None, attendre_manuel=True, t_manuel=300):
    """Renvoie une page connectée, ou None."""
    pg = page_connectee(ctx)
    if pg:
        _log(log, "✓ déjà connecté (profil).")
        return pg
    pg = _auto_login(ctx, page, log)
    if pg:
        _log(log, "✓ connecté via Keychain — ZÉRO retape. 🎉")
        sauver_session(ctx, log)
        return pg
    pg = _restaurer(ctx, page, log)
    if pg:
        _log(log, "✓ session restaurée.")
        return pg
    if not attendre_manuel:
        return None
    _log(log, "  👉 pas d'identifiants Keychain valides : connecte-toi manuellement (je ne touche pas au formulaire).")
    fin = time.time() + t_manuel
    while time.time() < fin:
        pg = page_connectee(ctx)
        if pg:
            sauver_session(ctx, log)
            return pg
        time.sleep(2)
    return None
