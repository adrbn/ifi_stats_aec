#!/usr/bin/env python3
"""
AEC Auto-Exporter for IFI Stats
================================
Automates the export of AEC statistics using Playwright.
Downloads are automatically saved and renamed, then zipped.

Usage:
    python aec_exporter.py

Requirements:
    pip install playwright
    playwright install chromium
"""

import os
import sys
import time
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("❌ Playwright not installed. Run:")
    print("   pip install playwright")
    print("   playwright install chromium")
    sys.exit(1)

# Configuration
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

class AECExporter:
    def __init__(self, download_dir: Path):
        self.download_dir = download_dir
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.files_by_year = {}  # {year: [file_paths]}
        self.failed_exports = []  # [(sede, year, semester, error_msg), ...]
        self.page = None
        self.browser = None
        self.context = None
        
    def log(self, message: str):
        """Print timestamped log message."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {message}")
    
    def wait(self, delay_type: str = 'short'):
        """Wait for specified delay."""
        time.sleep(CONFIG['DELAYS'].get(delay_type, 0.3))
    
    def start_browser(self):
        """Start browser with download configuration."""
        self.log("🚀 Starting browser...")
        self.playwright = sync_playwright().start()
        
        # Launch browser - user will need to log in
        self.browser = self.playwright.chromium.launch(
            headless=False,  # Must be visible for user to log in
            args=['--start-maximized']
        )
        
        self.context = self.browser.new_context(
            accept_downloads=True,
            viewport={'width': 1920, 'height': 1080}
        )
        
        self.page = self.context.new_page()
        self.log("✅ Browser started")
    
    def navigate_to_report(self):
        """Navigate to the report page."""
        self.log("📍 Navigating to AEC...")
        self.page.goto(CONFIG['URL'])
        
        # Wait for user to log in if needed
        self.log("⏳ Waiting for page to load (log in if needed)...")
        
        # Wait for the report library to appear
        try:
            self.page.wait_for_selector('aec-report-library-view', timeout=120000)
            self.log("✅ Report library loaded")
        except PlaywrightTimeout:
            self.log("❌ Timeout waiting for report library. Make sure you're logged in.")
            return False
        
        self.wait('medium')
        
        # Click on the report
        try:
            report_button = self.page.locator('h6.m-0:has-text("Heures-élèves: Elèves par Catégorie de Cours")')
            report_button.click()
            self.wait('long')
            self.log("✅ Report selected")
            return True
        except Exception as e:
            self.log(f"⚠️ Could not select report: {e}")
            return True  # May already be selected
    
    def open_establishment_dropdown(self):
        """Open the establishment dropdown."""
        button = self.page.locator('button[test="IDETABLISHMENT_BRANCHs"]')
        
        # Check if popup is already open
        popup = self.page.locator('kendo-popup kendo-treeview')
        if popup.count() > 0:
            button.click()
            self.wait('medium')
        
        button.click()
        self.wait('popup_wait')
        
        # Wait for tree items
        self.page.wait_for_selector('kendo-popup kendo-treeview li[role="treeitem"]', timeout=10000)
        self.wait('short')
    
    def clear_all_establishments(self):
        """Clear all establishment selections."""
        self.log("🧹 Clearing selections...")
        
        # All indices to clear (parents and children)
        all_indices = ['0_0', '0_0_0', '0_1', '0_1_0', '0_2', '0_2_0', '0_3', '0_3_0']
        
        for idx in all_indices:
            # Use aria-labelledby to find the specific checkbox
            checkbox = self.page.locator(f'kendo-popup input.k-checkbox[aria-labelledby="{idx}"]')
            if checkbox.count() > 0:
                class_attr = checkbox.get_attribute('class') or ''
                if 'k-checked' in class_attr:
                    checkbox.click()
                    self.wait('short')
    
    def select_establishment(self, sede: dict) -> bool:
        """Select a specific establishment."""
        self.log(f"🏛 Selecting: {sede['name']}...")
        
        self.open_establishment_dropdown()
        self.clear_all_establishments()
        self.wait('short')
        
        # Select the sede using aria-labelledby which is unique
        checkbox = self.page.locator(f'kendo-popup input.k-checkbox[aria-labelledby="{sede["treeIndex"]}"]')
        if checkbox.count() > 0:
            class_attr = checkbox.get_attribute('class') or ''
            if 'k-checked' not in class_attr:
                checkbox.click()
                self.wait('short')
                self.log(f"✓ Selected {sede['name']}")
        else:
            self.log(f"⚠️ Checkbox not found for {sede['name']}")
        
        # Close dropdown
        self.wait('short')
        self.page.locator('report-pane, .main-container, header').first.click()
        self.wait('medium')
        
        return True
    
    def select_period(self, year: int, month: str, is_start: bool = True):
        """Select a period from dropdown."""
        test_attr = 'IDPERIOD_Start' if is_start else 'IDPERIOD_End'
        period_text = f"{year}-{month}"
        
        self.log(f"📅 Selecting {'start' if is_start else 'end'}: {period_text}...")
        
        dropdown = self.page.locator(f'kendo-dropdownlist[test="{test_attr}"]')
        dropdown.click()
        self.wait('medium')
        
        # Try to find the period, may need to load more
        for attempt in range(5):
            items = self.page.locator('kendo-popup li[role="option"], kendo-popup div.text-ellipsis')
            
            for i in range(items.count()):
                item = items.nth(i)
                text = item.text_content() or ''
                if period_text in text:
                    item.click()
                    self.wait('medium')
                    return True
            
            # Try to load more periods
            more_button = self.page.locator('div.text-ellipsis:has-text("Voir les périodes les plus anciennes")')
            if more_button.count() > 0:
                more_button.click()
                self.wait('medium')
            else:
                break
        
        raise Exception(f"Could not find period: {period_text}")
    
    def perform_export(self, sede: dict, year: int, semester: str) -> Path:
        """Perform a single export and return the downloaded file path."""
        if semester == 'ANNUAL':
            period_config = CONFIG['ANNUAL']
            export_name = f"{sede['name']} - {year} année complète"
        else:
            period_config = CONFIG['SEMESTERS'][semester]
            export_name = f"{sede['name']} - {year} {period_config['label']}"
        
        self.log(f"\n{'='*50}")
        self.log(f"📊 Exporting: {export_name}")
        self.log(f"{'='*50}")
        
        # Select establishment
        self.select_establishment(sede)
        self.wait('medium')
        
        # Select periods
        self.select_period(year, period_config['startMonth'], is_start=True)
        self.wait('medium')
        self.select_period(year, period_config['endMonth'], is_start=False)
        self.wait('long')
        
        # Wait for data to load
        self.wait('long')
        
        # Click export button
        self.log("📥 Clicking export...")
        export_btn = self.page.locator('button[test="export"]')
        export_btn.click()
        self.wait('long')
        
        # Confirm export in modal and handle download
        self.log("⬇️ Downloading...")
        modal_export_btn = self.page.locator('kendo-window button[test="export"]')
        
        # Start waiting for download BEFORE clicking
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
        
        # Save with new name
        download.save_as(save_path)
        self.log(f"✅ Saved: {new_filename}")
        
        # Store by year
        if year not in self.files_by_year:
            self.files_by_year[year] = []
        self.files_by_year[year].append(save_path)
        self.wait('between_exports')
        
        return save_path
    
    def create_zip_for_year(self, year: int, semesters: list) -> Path:
        """Create ZIP file for a specific year."""
        files = self.files_by_year.get(year, [])
        if not files:
            self.log(f"⚠️ No files for year {year}")
            return None
        
        # Build semester suffix
        sem_suffix = ""
        if 'ANNUAL' in semesters:
            sem_suffix = "annuel"
        elif 'S1' in semesters and 'S2' in semesters:
            sem_suffix = "S1-S2"
        elif 'S1' in semesters:
            sem_suffix = "S1"
        elif 'S2' in semesters:
            sem_suffix = "S2"
        
        zip_filename = f"exports_AEC_{year}_{sem_suffix}.zip"
        zip_path = self.download_dir / zip_filename
        
        self.log(f"\n📦 Creating ZIP: {zip_filename}")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in files:
                zf.write(file_path, file_path.name)
                self.log(f"  + {file_path.name}")
        
        self.log(f"✅ ZIP created: {zip_path}")
        self.log(f"📊 Contains {len(files)} files")
        
        return zip_path
    
    def cleanup_individual_files(self):
        """Remove individual Excel files after zipping."""
        for year, files in self.files_by_year.items():
            for file_path in files:
                if file_path.exists():
                    file_path.unlink()
        self.log("🧹 Individual files cleaned up")
    
    def run(self, years: list, semesters: list, selected_sedi: list = None, max_retries: int = 2):
        """Run the full export process with automatic retry for failures."""
        # Use all sedi if none specified
        sedi_to_export = selected_sedi if selected_sedi else CONFIG['SEDI']
        
        # Reset failure tracking
        self.failed_exports = []
        
        self.log("="*60)
        self.log("🚀 AEC AUTO-EXPORTER")
        self.log("="*60)
        self.log(f"📅 Years: {', '.join(map(str, years))}")
        self.log(f"📆 Periods: {', '.join(semesters)}")
        self.log(f"🏛 Sedi: {', '.join(s['name'] for s in sedi_to_export)}")
        
        total = len(years) * len(semesters) * len(sedi_to_export)
        self.log(f"📊 Total exports: {total}")
        self.log("="*60)
        
        try:
            self.start_browser()
            
            if not self.navigate_to_report():
                return
            
            successful = 0
            failed = 0
            
            # First pass: try all exports
            for year in years:
                for semester in semesters:
                    for sede in sedi_to_export:
                        try:
                            self.perform_export(sede, year, semester)
                            successful += 1
                        except Exception as e:
                            error_msg = str(e)
                            self.log(f"❌ Failed: {sede['name']} {year} {semester} - {error_msg}")
                            self.failed_exports.append((sede, year, semester, error_msg))
                            failed += 1
            
            # Retry failed exports
            if self.failed_exports and max_retries > 0:
                self.log("\n" + "="*60)
                self.log(f"🔄 RETRYING {len(self.failed_exports)} FAILED EXPORTS")
                self.log("="*60)
                
                for retry_attempt in range(max_retries):
                    if not self.failed_exports:
                        break
                    
                    self.log(f"\n🔄 Retry attempt {retry_attempt + 1}/{max_retries}...")
                    
                    # Copy current failures to retry
                    exports_to_retry = self.failed_exports.copy()
                    self.failed_exports = []
                    
                    for sede, year, semester, prev_error in exports_to_retry:
                        self.log(f"  ↻ Retrying: {sede['name']} {year} {semester}...")
                        try:
                            # Small wait before retry
                            time.sleep(2)
                            self.perform_export(sede, year, semester)
                            successful += 1
                            failed -= 1
                            self.log(f"  ✅ Retry successful: {sede['name']} {year} {semester}")
                        except Exception as e:
                            error_msg = str(e)
                            self.log(f"  ❌ Retry failed: {sede['name']} {year} {semester} - {error_msg}")
                            self.failed_exports.append((sede, year, semester, error_msg))
            
            # Create one ZIP per year
            zip_paths = []
            for year in years:
                if year in self.files_by_year:
                    zip_path = self.create_zip_for_year(year, semesters)
                    if zip_path:
                        zip_paths.append(zip_path)
            
            self.cleanup_individual_files()
            
            # Summary
            self.log("\n" + "="*60)
            self.log("📊 EXPORT COMPLETE")
            self.log("="*60)
            self.log(f"✅ Successful: {successful}")
            self.log(f"❌ Failed: {len(self.failed_exports)}")
            self.log(f"📦 ZIP files created: {len(zip_paths)}")
            for zp in zip_paths:
                self.log(f"   📁 {zp.name}")
            
            # List remaining failures
            if self.failed_exports:
                self.log("\n⚠️ Exports still failing after retries:")
                for sede, year, semester, error_msg in self.failed_exports:
                    self.log(f"   • {sede['name']} {year} {semester}: {error_msg[:50]}...")
            
        except Exception as e:
            self.log(f"💥 Fatal error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.log("\n🛑 Press Enter to close browser...")
            input()
            if self.browser:
                self.browser.close()
            if hasattr(self, 'playwright'):
                self.playwright.stop()


def main():
    """Main entry point with interactive configuration."""
    print("\n" + "="*60)
    print("📊 AEC AUTO-EXPORTER FOR IFI STATS")
    print("="*60)
    
    # Get download directory - use project folder
    script_dir = Path(__file__).parent
    default_dir = script_dir / "AEC_exports"
    print(f"\n📁 Download directory: {default_dir}")
    
    # Get years
    print("\n📅 Enter years to export (comma-separated, e.g., 2023,2024,2025):")
    years_input = input("Years [2024,2025]: ").strip() or "2024,2025"
    years = [int(y.strip()) for y in years_input.split(',')]
    
    # Get period type (semester or annual)
    print("\n📆 Export type:")
    print("   1 = Semestre 1 (janvier-août)")
    print("   2 = Semestre 2 (septembre-décembre)")
    print("   12 = Les deux semestres (fichiers séparés)")
    print("   A = Année complète (un seul fichier par antenne)")
    period_input = input("Période [12]: ").strip().upper() or "12"
    
    semesters = []
    if period_input == 'A':
        semesters = ['ANNUAL']
    else:
        if '1' in period_input:
            semesters.append('S1')
        if '2' in period_input:
            semesters.append('S2')
    
    if not semesters:
        semesters = ['S1', 'S2']
    
    # Select sedi (all checked by default)
    print("\n🏛 Sélection des antennes:")
    print("   Appuyez sur Entrée pour toutes les antennes, ou")
    print("   Entrez les codes séparés par virgule (ex: IFM,IFF)")
    print("   Codes disponibles: IFM (Milano), IFF (Firenze), IFN (Napoli), IFP (Palermo)")
    sedi_input = input("Antennes [toutes]: ").strip().upper()
    
    selected_sedi = None
    if sedi_input:
        selected_codes = [s.strip() for s in sedi_input.split(',')]
        selected_sedi = [s for s in CONFIG['SEDI'] if s['code'] in selected_codes]
        if not selected_sedi:
            print("⚠️ Aucun code valide, utilisation de toutes les antennes")
            selected_sedi = None
    
    # Confirm
    sedi_to_show = selected_sedi if selected_sedi else CONFIG['SEDI']
    total = len(years) * len(semesters) * len(sedi_to_show)
    print(f"\n📊 This will export {total} files:")
    print(f"   Years: {years}")
    print(f"   Periods: {semesters}")
    print(f"   Sedi: {', '.join(s['name'] for s in sedi_to_show)}")
    
    confirm = input("\nProceed? [Y/n]: ").strip().lower()
    if confirm and confirm != 'y':
        print("❌ Cancelled")
        return
    
    # Run exporter
    exporter = AECExporter(default_dir)
    exporter.run(years, semesters, selected_sedi)


if __name__ == '__main__':
    main()
