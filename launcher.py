"""
OSCAR Desktop Launcher
======================
Cross-platform entry point for the OSCAR desktop application.

Flow:
  1. Validate license (offline RSA check)
  2. Find a free TCP port
  3. Start Streamlit server in a child process (multiprocessing)
  4. Wait for server to be ready (HTTP polling)
  5. Open a native PyWebView window pointing at localhost:<port>
  6. On window close: terminate server process and exit

Compatible with PyInstaller --onedir (macOS .app, Windows .exe, Linux binary).
"""

import multiprocessing
import os
import sys
import socket
import time
import urllib.request
import urllib.error


# ── Helpers ──────────────────────────────────────────────────────────────────

def resource_path(*parts):
    """Resolve a path relative to the bundle root (works frozen and in dev)."""
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *parts)


def find_free_port():
    """Return an available TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_server(url, timeout=90):
    """Poll url until it responds or timeout (seconds) is reached."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return True
        except Exception:
            time.sleep(0.4)
    return False


def show_error(title, message):
    """Display an error dialog using tkinter (always available)."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
    except Exception:
        print(f"[OSCAR ERROR] {title}: {message}", file=sys.stderr)


# ── Streamlit server process ──────────────────────────────────────────────────
# IMPORTANT: This function must be defined at module level (not nested) so that
# multiprocessing can pickle it correctly in PyInstaller frozen apps.

def _streamlit_worker(script_path, port):
    """
    Runs inside a child process spawned by multiprocessing.
    Starts the Streamlit server on the given port.
    """
    # Point Streamlit at the bundled config & secrets so it doesn't warn
    streamlit_config_dir = resource_path(".streamlit")
    os.environ["STREAMLIT_CONFIG_DIR"] = streamlit_config_dir

    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    os.environ["STREAMLIT_SERVER_PORT"] = str(port)
    os.environ["STREAMLIT_SERVER_ADDRESS"] = "localhost"
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    os.environ["STREAMLIT_BROWSER_SERVER_ADDRESS"] = "localhost"
    os.environ["STREAMLIT_SERVER_ENABLE_STATIC_SERVING"] = "false"
    os.environ["STREAMLIT_LOGGER_LEVEL"] = "error"

    import streamlit.web.cli as stcli

    sys.argv = [
        "streamlit", "run",
        script_path,
        f"--server.port={port}",
        "--server.headless=true",
        "--server.address=localhost",
        "--browser.gatherUsageStats=false",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false",
    ]
    stcli.main()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # ── 1. License validation ────────────────────────────────────────────────
    from license_validator import find_license_file, validate_license, LicenseError, get_config_dir

    license_path = find_license_file()

    if license_path is None:
        config_dir = get_config_dir()
        show_error(
            "OSCAR — Licence requise",
            "Aucun fichier de licence trouvé.\n\n"
            "Déposez votre fichier oscar_license.lic dans :\n"
            f"  {config_dir}\n\n"
            "Contactez votre administrateur pour obtenir une licence."
        )
        sys.exit(1)

    try:
        license_info = validate_license(license_path)
    except LicenseError as e:
        show_error(
            "OSCAR — Licence invalide",
            f"La licence est invalide ou expirée.\n\n{e}\n\n"
            "Contactez votre administrateur."
        )
        sys.exit(1)

    # Warn if expiry is close (< 30 days) — non-blocking
    if 0 < license_info.days_remaining <= 30:
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showwarning(
                "OSCAR — Licence bientôt expirée",
                f"Votre licence expire dans {license_info.days_remaining} jour(s) "
                f"(le {license_info.expiry}).\n\nContactez votre administrateur pour la renouveler."
            )
            root.destroy()
        except Exception:
            pass

    # ── 2. Ensure Streamlit home dir exists (silences "No secrets found") ───
    import pathlib
    streamlit_home = pathlib.Path.home() / ".streamlit"
    streamlit_home.mkdir(exist_ok=True)
    secrets_path = streamlit_home / "secrets.toml"
    if not secrets_path.exists():
        secrets_path.write_text("# OSCAR — aucun secret configuré\n")

    # ── 3. Find free port ────────────────────────────────────────────────────
    port = find_free_port()
    url = f"http://localhost:{port}"

    # ── 4. Start Streamlit server ────────────────────────────────────────────
    script_path = resource_path("dashboard_aec_v2.py")

    # Signal to the dashboard that it runs inside the desktop app:
    # the license check above already validated the user, so the login page is skipped.
    os.environ["OSCAR_DESKTOP_MODE"] = "1"
    os.environ["OSCAR_LICENSE_CUSTOMER"] = license_info.customer or "OSCAR"

    server = multiprocessing.Process(
        target=_streamlit_worker,
        args=(script_path, port),
        daemon=True,
    )
    server.start()

    # ── 5. Wait for server ───────────────────────────────────────────────────
    if not wait_for_server(url, timeout=90):
        server.terminate()
        server.join(timeout=5)
        show_error(
            "OSCAR — Erreur de démarrage",
            "Le serveur OSCAR n'a pas pu démarrer dans le temps imparti.\n"
            "Réessayez. Si le problème persiste, redémarrez l'application."
        )
        sys.exit(1)

    # ── 6. Open native window ────────────────────────────────────────────────
    window_title = "OSCAR v3.0"
    if license_info.customer:
        window_title += f"  —  {license_info.customer}"

    try:
        import webview

        webview.create_window(
            title=window_title,
            url=url,
            width=1440,
            height=900,
            min_size=(900, 600),
            resizable=True,
            text_select=True,
        )
        webview.start(debug=False)

    except ImportError:
        # PyWebView not available — fall back to system browser
        import webbrowser
        webbrowser.open(url)
        print(f"[OSCAR] Opened in browser: {url}")
        print("[OSCAR] Close this terminal window to quit.")
        try:
            server.join()
        except KeyboardInterrupt:
            pass

    finally:
        # ── 7. Clean up ──────────────────────────────────────────────────────
        if server.is_alive():
            server.terminate()
            server.join(timeout=5)


# ── Entry point ───────────────────────────────────────────────────────────────
# freeze_support() MUST be inside __main__ guard and AFTER all function
# definitions — this is the required pattern for PyInstaller + multiprocessing.
if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
