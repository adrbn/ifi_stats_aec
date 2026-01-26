#!/usr/bin/env python3
"""
AEC Auto-Exporter GUI - IFI Stats
==================================
Modern GUI for exporting AEC statistics.
Cross-platform: macOS & Windows

Usage:
    python aec_exporter_gui.py

Requirements:
    pip install customtkinter playwright
    playwright install chromium
"""

import os
import sys
import time
import threading
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Callable

# Check dependencies
try:
    import customtkinter as ctk
except ImportError:
    print("❌ CustomTkinter not installed. Run:")
    print("   pip install customtkinter")
    sys.exit(1)

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("❌ Playwright not installed. Run:")
    print("   pip install playwright")
    print("   playwright install chromium")
    sys.exit(1)

# ============================================================
# CONFIGURATION
# ============================================================

CONFIG = {
    'URL': 'https://ifitalie.aec.app/#/course/course-reports',
    'SEDI': [
        {'name': 'Milano', 'code': 'IFM', 'treeIndex': '0_0'},
        {'name': 'Firenze', 'code': 'IFF', 'treeIndex': '0_1'},
        {'name': 'Napoli', 'code': 'IFN', 'treeIndex': '0_2'},
        {'name': 'Palermo', 'code': 'IFP', 'treeIndex': '0_3'},
    ],
    'SEMESTERS': {
        'S1': {'startMonth': 'JANVIER', 'endMonth': 'AOUT', 'label': 'semestre 1'},
        'S2': {'startMonth': 'SEPTEMBRE', 'endMonth': 'DECEMBRE', 'label': 'semestre 2'},
    },
    'ANNUAL': {
        'startMonth': 'JANVIER',
        'endMonth': 'DECEMBRE',
        'label': 'année complète'
    },
    'DELAYS': {
        'short': 0.3,
        'medium': 0.6,
        'long': 1.2,
        'export': 2.5,
        'popup_wait': 1.2,
        'between_exports': 2.0,
    }
}

# ============================================================
# AEC EXPORTER ENGINE (same logic as CLI version)
# ============================================================

class AECExporterEngine:
    """Core export engine - separated from GUI."""
    
    def __init__(self, download_dir: Path, log_callback: Callable[[str], None] = None):
        self.download_dir = download_dir
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.files_by_year = {}
        self.failed_exports = []  # [(sede, year, semester, error_msg), ...]
        self.page = None
        self.browser = None
        self.context = None
        self.playwright = None
        self.log_callback = log_callback or print
        self.is_running = False
        self.should_stop = False
        
    def log(self, message: str):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_callback(f"[{timestamp}] {message}")
    
    def wait(self, delay_type: str = 'short'):
        time.sleep(CONFIG['DELAYS'].get(delay_type, 0.3))
    
    def stop(self):
        """Signal to stop the export process."""
        self.should_stop = True
        self.log("⏹️ Arrêt demandé...")
    
    def start_browser(self):
        self.log("🚀 Démarrage du navigateur...")
        self.playwright = sync_playwright().start()
        
        self.browser = self.playwright.chromium.launch(
            headless=False,
            args=['--start-maximized']
        )
        
        self.context = self.browser.new_context(
            accept_downloads=True,
            viewport={'width': 1920, 'height': 1080}
        )
        
        self.page = self.context.new_page()
        self.log("✅ Navigateur démarré")
    
    def close_browser(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        self.log("🛑 Navigateur fermé")
    
    def navigate_to_report(self) -> bool:
        self.log("📍 Navigation vers AEC...")
        self.page.goto(CONFIG['URL'])
        self.log("⏳ En attente (connectez-vous si nécessaire)...")
        
        try:
            self.page.wait_for_selector('aec-report-library-view', timeout=120000)
            self.log("✅ Page rapport chargée")
        except PlaywrightTimeout:
            self.log("❌ Timeout - Assurez-vous d'être connecté.")
            return False
        
        self.wait('medium')
        
        try:
            report_button = self.page.locator('h6.m-0:has-text("Heures-élèves: Elèves par Catégorie de Cours")')
            report_button.click()
            self.wait('long')
            self.log("✅ Rapport sélectionné")
            return True
        except Exception as e:
            self.log(f"⚠️ Rapport déjà sélectionné ou erreur: {e}")
            return True
    
    def open_establishment_dropdown(self):
        button = self.page.locator('button[test="IDETABLISHMENT_BRANCHs"]')
        popup = self.page.locator('kendo-popup kendo-treeview')
        if popup.count() > 0:
            button.click()
            self.wait('medium')
        button.click()
        self.wait('popup_wait')
        self.page.wait_for_selector('kendo-popup kendo-treeview li[role="treeitem"]', timeout=10000)
        self.wait('short')
    
    def clear_all_establishments(self):
        all_indices = ['0_0', '0_0_0', '0_1', '0_1_0', '0_2', '0_2_0', '0_3', '0_3_0']
        for idx in all_indices:
            checkbox = self.page.locator(f'kendo-popup input.k-checkbox[aria-labelledby="{idx}"]')
            if checkbox.count() > 0:
                class_attr = checkbox.get_attribute('class') or ''
                if 'k-checked' in class_attr:
                    checkbox.click()
                    self.wait('short')
    
    def select_establishment(self, sede: dict) -> bool:
        self.log(f"🏛️ Sélection: {sede['name']}...")
        self.open_establishment_dropdown()
        self.clear_all_establishments()
        self.wait('short')
        
        checkbox = self.page.locator(f'kendo-popup input.k-checkbox[aria-labelledby="{sede["treeIndex"]}"]')
        if checkbox.count() > 0:
            class_attr = checkbox.get_attribute('class') or ''
            if 'k-checked' not in class_attr:
                checkbox.click()
                self.wait('short')
        
        self.wait('short')
        self.page.locator('report-pane, .main-container, header').first.click()
        self.wait('medium')
        return True
    
    def select_period(self, year: int, month: str, is_start: bool = True):
        test_attr = 'IDPERIOD_Start' if is_start else 'IDPERIOD_End'
        period_text = f"{year}-{month}"
        
        dropdown = self.page.locator(f'kendo-dropdownlist[test="{test_attr}"]')
        dropdown.click()
        self.wait('medium')
        
        for attempt in range(5):
            items = self.page.locator('kendo-popup li[role="option"], kendo-popup div.text-ellipsis')
            for i in range(items.count()):
                item = items.nth(i)
                text = item.text_content() or ''
                if period_text in text:
                    item.click()
                    self.wait('medium')
                    return True
            
            more_button = self.page.locator('div.text-ellipsis:has-text("Voir les périodes les plus anciennes")')
            if more_button.count() > 0:
                more_button.click()
                self.wait('medium')
            else:
                break
        
        raise Exception(f"Période introuvable: {period_text}")
    
    def perform_export(self, sede: dict, year: int, semester: str) -> Path:
        if semester == 'ANNUAL':
            period_config = CONFIG['ANNUAL']
            export_name = f"{sede['name']} - {year} année complète"
        else:
            period_config = CONFIG['SEMESTERS'][semester]
            export_name = f"{sede['name']} - {year} {period_config['label']}"
        self.log(f"📊 Export: {export_name}")
        
        self.select_establishment(sede)
        self.wait('medium')
        
        self.select_period(year, period_config['startMonth'], is_start=True)
        self.wait('medium')
        self.select_period(year, period_config['endMonth'], is_start=False)
        self.wait('long')
        self.wait('long')
        
        self.log("📥 Clic export...")
        export_btn = self.page.locator('button[test="export"]')
        export_btn.click()
        self.wait('long')
        
        self.log("⬇️ Téléchargement...")
        modal_export_btn = self.page.locator('kendo-window button[test="export"]')
        
        with self.page.expect_download(timeout=30000) as download_info:
            modal_export_btn.click()
        
        download = download_info.value
        
        # Generate proper filename
        if semester == 'ANNUAL':
            new_filename = f"export AEC {year} {sede['code']}.xlsx"
        else:
            sem_num = '1' if semester == 'S1' else '2'
            new_filename = f"export AEC semestre {sem_num} {year} {sede['code']}.xlsx"
        save_path = self.download_dir / new_filename
        download.save_as(save_path)
        self.log(f"✅ Enregistré: {new_filename}")
        
        if year not in self.files_by_year:
            self.files_by_year[year] = []
        self.files_by_year[year].append(save_path)
        self.wait('between_exports')
        
        return save_path
    
    def create_zip_for_year(self, year: int, semesters: list) -> Path:
        files = self.files_by_year.get(year, [])
        if not files:
            return None
        
        # Build semester suffix
        if 'ANNUAL' in semesters:
            sem_suffix = "annuel"
        elif 'S1' in semesters and 'S2' in semesters:
            sem_suffix = "S1-S2"
        elif 'S1' in semesters:
            sem_suffix = "S1"
        else:
            sem_suffix = "S2"
            
        zip_filename = f"exports_AEC_{year}_{sem_suffix}.zip"
        zip_path = self.download_dir / zip_filename
        
        self.log(f"📦 Création ZIP: {zip_filename}")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in files:
                zf.write(file_path, file_path.name)
        
        self.log(f"✅ ZIP créé ({len(files)} fichiers)")
        return zip_path
    
    def cleanup_individual_files(self):
        for year, files in self.files_by_year.items():
            for file_path in files:
                if file_path.exists():
                    file_path.unlink()
    
    def run(self, years: list, semesters: list, selected_sedi: list = None, progress_callback: Callable[[int, int], None] = None, max_retries: int = 2):
        self.is_running = True
        self.should_stop = False
        self.files_by_year = {}
        self.failed_exports = []
        
        # Use selected sedi or all
        sedi_to_export = selected_sedi if selected_sedi else CONFIG['SEDI']
        
        total = len(years) * len(semesters) * len(sedi_to_export)
        current = 0
        
        self.log("=" * 50)
        self.log("🚀 DÉMARRAGE EXPORT AEC")
        self.log("=" * 50)
        self.log(f"📅 Années: {', '.join(map(str, years))}")
        self.log(f"📆 Périodes: {', '.join(semesters)}")
        self.log(f"🏛 Antennes: {', '.join(s['name'] for s in sedi_to_export)}")
        self.log(f"📊 Total: {total} fichiers")
        
        try:
            self.start_browser()
            
            if not self.navigate_to_report():
                self.is_running = False
                return False
            
            successful = 0
            failed = 0
            
            # First pass: try all exports
            for year in years:
                if self.should_stop:
                    break
                for semester in semesters:
                    if self.should_stop:
                        break
                    for sede in sedi_to_export:
                        if self.should_stop:
                            break
                        try:
                            self.perform_export(sede, year, semester)
                            successful += 1
                        except Exception as e:
                            error_msg = str(e)
                            self.log(f"❌ Échec: {sede['name']} {year} {semester} - {error_msg}")
                            self.failed_exports.append((sede, year, semester, error_msg))
                            failed += 1
                        
                        current += 1
                        if progress_callback:
                            progress_callback(current, total)
            
            # Retry failed exports
            if self.failed_exports and max_retries > 0 and not self.should_stop:
                self.log("")
                self.log("=" * 50)
                self.log(f"🔄 RETRY DES {len(self.failed_exports)} EXPORTS ÉCHOUÉS")
                self.log("=" * 50)
                
                for retry_attempt in range(max_retries):
                    if not self.failed_exports or self.should_stop:
                        break
                    
                    self.log(f"\n🔄 Tentative {retry_attempt + 1}/{max_retries}...")
                    
                    exports_to_retry = self.failed_exports.copy()
                    self.failed_exports = []
                    
                    for sede, year, semester, prev_error in exports_to_retry:
                        if self.should_stop:
                            break
                        self.log(f"  ↻ Retry: {sede['name']} {year} {semester}...")
                        try:
                            time.sleep(2)
                            self.perform_export(sede, year, semester)
                            successful += 1
                            failed -= 1
                            self.log(f"  ✅ Retry réussi!")
                        except Exception as e:
                            error_msg = str(e)
                            self.log(f"  ❌ Retry échoué: {error_msg[:50]}")
                            self.failed_exports.append((sede, year, semester, error_msg))
            
            # Create ZIPs
            zip_paths = []
            for year in years:
                if year in self.files_by_year:
                    zip_path = self.create_zip_for_year(year, semesters)
                    if zip_path:
                        zip_paths.append(zip_path)
            
            self.cleanup_individual_files()
            
            self.log("")
            self.log("=" * 50)
            self.log("✅ EXPORT TERMINÉ")
            self.log("=" * 50)
            self.log(f"✅ Réussis: {successful}")
            self.log(f"❌ Échoués: {len(self.failed_exports)}")
            self.log(f"📦 ZIPs créés: {len(zip_paths)}")
            
            if self.failed_exports:
                self.log("\n⚠️ Exports toujours en échec:")
                for sede, year, semester, error_msg in self.failed_exports:
                    self.log(f"   • {sede['name']} {year} {semester}")
            
            return True
            
        except Exception as e:
            self.log(f"💥 Erreur fatale: {e}")
            return False
        
        finally:
            self.close_browser()
            self.is_running = False


# ============================================================
# MODERN GUI WITH CUSTOMTKINTER
# ============================================================

class AECExporterGUI(ctk.CTk):
    """Modern Apple-like GUI for AEC Exporter."""
    
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.title("AEC Exporter - IFI Stats")
        self.geometry("700x900")
        self.minsize(600, 850)
        
        # Theme
        ctk.set_appearance_mode("system")  # Follow system dark/light mode
        ctk.set_default_color_theme("blue")
        
        # State
        self.exporter = None
        self.export_thread = None
        
        # Build UI
        self._create_ui()
        
        # Set default download directory
        script_dir = Path(__file__).parent
        self.download_dir = script_dir / "AEC_exports"
        self.dir_label.configure(text=str(self.download_dir))
    
    def _create_ui(self):
        """Build the user interface."""
        
        # Main container with padding
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=30, pady=30)
        
        # ========== HEADER ==========
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))
        
        title_label = ctk.CTkLabel(
            header_frame, 
            text="📊 AEC Exporter",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title_label.pack()
        
        subtitle_label = ctk.CTkLabel(
            header_frame, 
            text="Institut français Italia - Export automatique des statistiques",
            font=ctk.CTkFont(size=13),
            text_color="gray"
        )
        subtitle_label.pack(pady=(5, 0))
        
        # ========== BUTTONS (at top for visibility) ==========
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(0, 15))
        
        self.start_btn = ctk.CTkButton(
            btn_frame,
            text="▶️  Démarrer l'export",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            corner_radius=12,
            fg_color="#22c55e",
            hover_color="#16a34a",
            command=self._start_export
        )
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.stop_btn = ctk.CTkButton(
            btn_frame,
            text="⏹️  Arrêter",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            corner_radius=12,
            fg_color="#ef4444",
            hover_color="#dc2626",
            state="disabled",
            command=self._stop_export
        )
        self.stop_btn.pack(side="right", fill="x", expand=True, padx=(10, 0))
        
        # ========== CONFIGURATION CARD ==========
        config_card = ctk.CTkFrame(self.main_frame, corner_radius=15)
        config_card.pack(fill="x", pady=(0, 15))
        
        config_title = ctk.CTkLabel(
            config_card, 
            text="⚙️ Configuration",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        config_title.pack(anchor="w", padx=20, pady=(15, 10))
        
        # Download directory
        dir_frame = ctk.CTkFrame(config_card, fg_color="transparent")
        dir_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        dir_label_title = ctk.CTkLabel(dir_frame, text="📁 Dossier de destination:", font=ctk.CTkFont(size=13))
        dir_label_title.pack(anchor="w")
        
        dir_row = ctk.CTkFrame(dir_frame, fg_color="transparent")
        dir_row.pack(fill="x", pady=(5, 0))
        
        self.dir_label = ctk.CTkLabel(
            dir_row, 
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            wraplength=500,
            justify="left"
        )
        self.dir_label.pack(side="left", fill="x", expand=True)
        
        change_dir_btn = ctk.CTkButton(
            dir_row, 
            text="Modifier",
            width=80,
            height=28,
            font=ctk.CTkFont(size=12),
            command=self._choose_directory
        )
        change_dir_btn.pack(side="right")
        
        # ========== YEARS SELECTION ==========
        years_card = ctk.CTkFrame(self.main_frame, corner_radius=15)
        years_card.pack(fill="x", pady=(0, 15))
        
        years_title = ctk.CTkLabel(
            years_card, 
            text="📅 Années",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        years_title.pack(anchor="w", padx=20, pady=(15, 10))
        
        years_frame = ctk.CTkFrame(years_card, fg_color="transparent")
        years_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        self.year_vars = {}
        current_year = datetime.now().year
        years_to_show = list(range(current_year - 3, current_year + 2))
        
        for i, year in enumerate(years_to_show):
            var = ctk.BooleanVar(value=(year >= current_year - 1))
            self.year_vars[year] = var
            
            cb = ctk.CTkCheckBox(
                years_frame,
                text=str(year),
                variable=var,
                font=ctk.CTkFont(size=14),
                checkbox_width=22,
                checkbox_height=22,
                corner_radius=6
            )
            cb.grid(row=0, column=i, padx=10, pady=5)
        
        # ========== SEMESTERS SELECTION ==========
        sem_card = ctk.CTkFrame(self.main_frame, corner_radius=15)
        sem_card.pack(fill="x", pady=(0, 15))
        
        sem_title = ctk.CTkLabel(
            sem_card, 
            text="📆 Type de période",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        sem_title.pack(anchor="w", padx=20, pady=(15, 10))
        
        # Period type radio buttons
        self.period_type_var = ctk.StringVar(value="semesters")
        
        period_type_frame = ctk.CTkFrame(sem_card, fg_color="transparent")
        period_type_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        sem_radio = ctk.CTkRadioButton(
            period_type_frame,
            text="Par semestre",
            variable=self.period_type_var,
            value="semesters",
            font=ctk.CTkFont(size=14),
            command=self._toggle_period_options
        )
        sem_radio.pack(side="left", padx=(0, 20))
        
        annual_radio = ctk.CTkRadioButton(
            period_type_frame,
            text="Année complète",
            variable=self.period_type_var,
            value="annual",
            font=ctk.CTkFont(size=14),
            command=self._toggle_period_options
        )
        annual_radio.pack(side="left")
        
        # Semester checkboxes (shown only when "Par semestre" is selected)
        self.sem_options_frame = ctk.CTkFrame(sem_card, fg_color="transparent")
        self.sem_options_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        self.s1_var = ctk.BooleanVar(value=True)
        self.s2_var = ctk.BooleanVar(value=True)
        
        self.s1_cb = ctk.CTkCheckBox(
            self.sem_options_frame,
            text="S1 (Janvier → Août)",
            variable=self.s1_var,
            font=ctk.CTkFont(size=14),
            checkbox_width=22,
            checkbox_height=22,
            corner_radius=6
        )
        self.s1_cb.pack(side="left", padx=(0, 30))
        
        self.s2_cb = ctk.CTkCheckBox(
            self.sem_options_frame,
            text="S2 (Septembre → Décembre)",
            variable=self.s2_var,
            font=ctk.CTkFont(size=14),
            checkbox_width=22,
            checkbox_height=22,
            corner_radius=6
        )
        self.s2_cb.pack(side="left")
        
        # ========== SEDI SELECTION ==========
        sedi_card = ctk.CTkFrame(self.main_frame, corner_radius=15)
        sedi_card.pack(fill="x", pady=(0, 15))
        
        sedi_title = ctk.CTkLabel(
            sedi_card, 
            text="🏛️ Antennes",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        sedi_title.pack(anchor="w", padx=20, pady=(15, 10))
        
        sedi_frame = ctk.CTkFrame(sedi_card, fg_color="transparent")
        sedi_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        self.sedi_vars = {}
        for sede in CONFIG['SEDI']:
            var = ctk.BooleanVar(value=True)  # All checked by default
            self.sedi_vars[sede['code']] = var
            
            cb = ctk.CTkCheckBox(
                sedi_frame,
                text=f"{sede['name']} ({sede['code']})",
                variable=var,
                font=ctk.CTkFont(size=13),
                checkbox_width=20,
                checkbox_height=20,
                corner_radius=5
            )
            cb.pack(side="left", padx=10)
        
        # ========== PROGRESS ==========
        progress_card = ctk.CTkFrame(self.main_frame, corner_radius=15)
        progress_card.pack(fill="x", pady=(0, 15))
        
        progress_title = ctk.CTkLabel(
            progress_card, 
            text="📈 Progression",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        progress_title.pack(anchor="w", padx=20, pady=(15, 10))
        
        self.progress_bar = ctk.CTkProgressBar(progress_card, height=12, corner_radius=6)
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 5))
        self.progress_bar.set(0)
        
        self.progress_label = ctk.CTkLabel(
            progress_card,
            text="En attente...",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.progress_label.pack(pady=(0, 15))
        
        # ========== LOGS ==========
        log_card = ctk.CTkFrame(self.main_frame, corner_radius=15)
        log_card.pack(fill="both", expand=True, pady=(0, 15))
        
        log_title = ctk.CTkLabel(
            log_card, 
            text="📋 Logs",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        log_title.pack(anchor="w", padx=20, pady=(15, 10))
        
        self.log_textbox = ctk.CTkTextbox(
            log_card,
            font=ctk.CTkFont(family="Monaco" if sys.platform == "darwin" else "Consolas", size=11),
            corner_radius=10,
            wrap="word"
        )
        self.log_textbox.pack(fill="both", expand=True, padx=20, pady=(0, 15))
    
    def _choose_directory(self):
        """Open directory chooser dialog."""
        from tkinter import filedialog
        dir_path = filedialog.askdirectory(
            title="Choisir le dossier de destination",
            initialdir=self.download_dir
        )
        if dir_path:
            self.download_dir = Path(dir_path)
            self.dir_label.configure(text=str(self.download_dir))
    
    def _toggle_period_options(self):
        """Show/hide semester checkboxes based on period type."""
        if self.period_type_var.get() == "annual":
            self.s1_cb.configure(state="disabled")
            self.s2_cb.configure(state="disabled")
        else:
            self.s1_cb.configure(state="normal")
            self.s2_cb.configure(state="normal")
    
    def _log(self, message: str):
        """Add message to log (thread-safe)."""
        self.after(0, lambda: self._append_log(message))
    
    def _append_log(self, message: str):
        """Append message to log textbox."""
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
    
    def _update_progress(self, current: int, total: int):
        """Update progress bar (thread-safe)."""
        self.after(0, lambda: self._set_progress(current, total))
    
    def _set_progress(self, current: int, total: int):
        """Set progress bar value."""
        progress = current / total if total > 0 else 0
        self.progress_bar.set(progress)
        self.progress_label.configure(text=f"{current} / {total} exports")
    
    def _start_export(self):
        """Start the export process."""
        # Get selected years
        years = [year for year, var in self.year_vars.items() if var.get()]
        if not years:
            self._log("❌ Sélectionnez au moins une année!")
            return
        
        # Get selected periods (semesters or annual)
        semesters = []
        if self.period_type_var.get() == "annual":
            semesters = ['ANNUAL']
        else:
            if self.s1_var.get():
                semesters.append('S1')
            if self.s2_var.get():
                semesters.append('S2')
        
        if not semesters:
            self._log("❌ Sélectionnez au moins un semestre!")
            return
        
        # Get selected sedi
        selected_sedi = [
            sede for sede in CONFIG['SEDI']
            if self.sedi_vars[sede['code']].get()
        ]
        
        if not selected_sedi:
            self._log("❌ Sélectionnez au moins une antenne!")
            return
        
        # Update UI
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.log_textbox.delete("1.0", "end")
        
        # Create exporter
        self.exporter = AECExporterEngine(
            download_dir=self.download_dir,
            log_callback=self._log
        )
        
        # Run in thread
        def run_export():
            try:
                self.exporter.run(
                    years=sorted(years),
                    semesters=semesters,
                    selected_sedi=selected_sedi,
                    progress_callback=self._update_progress
                )
            finally:
                self.after(0, self._export_finished)
        
        self.export_thread = threading.Thread(target=run_export, daemon=True)
        self.export_thread.start()
    
    def _stop_export(self):
        """Stop the export process."""
        if self.exporter:
            self.exporter.stop()
    
    def _export_finished(self):
        """Called when export is finished."""
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.progress_label.configure(text="Terminé ✅")


# ============================================================
# MAIN
# ============================================================

def main():
    app = AECExporterGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
