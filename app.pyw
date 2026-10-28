#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import subprocess
import stat
import re
import json
import urllib.request
import urllib.error
import tkinter as tk

# 1. PyInstaller (_MEIPASS) ve Normal Çalışma İçin Kusursuz Yol Tespiti
if getattr(sys, 'frozen', False):
    # Gömülü JSON dosyalarının çıkartıldığı geçici dizin
    BUNDLE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    # Çalışan binary/exe'nin bulunduğu gerçek dizin (önbellek kaydı için)
    EXEC_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    EXEC_DIR = BUNDLE_DIR

BUNDLED_DATASET = os.path.join(BUNDLE_DIR, "oui_dataset.json")
BUNDLED_VENDORS = os.path.join(BUNDLE_DIR, "network_vendors.json")

# Kullanıcının yeni öğrendiği MAC adreslerini kaydedeceği yerel önbellek
USER_CACHE_FILE = os.path.join(EXEC_DIR, "oui_dataset_cache.json")

MAC_REGEX = re.compile(
    r'\b((?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}|(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4})\b(?!\s*\()'
)

class StandaloneMacEnricher:
    def __init__(self, root):
        self.root = root
        self.root.withdraw()  # Arka planda gizli çalışır
        
        self.oui_dataset = {}
        self.network_keywords = [
            "cisco", "meraki", "fortinet", "aruba", "hewlett packard", 
            "hpe", "juniper", "nokia", "palo alto", "ubiquiti", 
            "mikrotik", "huawei", "tp-link", "extreme networks", "brocade"
        ]
        
        self.load_files()
        self.setup_desktop_Integration()
        
        self.last_clipboard = ""
        self.active_popup = None
        
        # İlk çalıştırmada kullanıcıya servisin aktif olduğunu bildiren mini bildirim
        self.show_clean_popup("MAC Vendor Enricher Aktif", ["Arka planda pano dinleniyor..."])
        self.root.after(400, self.clipboard_monitor)

    def load_files(self):
        # 1. Gömülü Network Vendors dosyasını oku
        if os.path.exists(BUNDLED_VENDORS):
            try:
                with open(BUNDLED_VENDORS, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.network_keywords = [kw.lower() for kw in data.get("network_keywords", self.network_keywords)]
            except Exception:
                pass

        # 2. Gömülü OUI Dataset dosyasını oku
        if os.path.exists(BUNDLED_DATASET):
            try:
                with open(BUNDLED_DATASET, "r", encoding="utf-8") as f:
                    self.oui_dataset.update(json.load(f))
            except Exception:
                pass

        # 3. Varsa sonradan öğrenilen yerel önbelleği üstüne ekle
        if os.path.exists(USER_CACHE_FILE):
            try:
                with open(USER_CACHE_FILE, "r", encoding="utf-8") as f:
                    self.oui_dataset.update(json.load(f))
            except Exception:
                pass

    def save_cache(self):
        try:
            with open(USER_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.oui_dataset, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def setup_desktop_Integration(self):
        """Windows ve Linux'ta masaüstüne çift tıklanabilir gerçek kısayol oluşturur."""
        if not getattr(sys, 'frozen', False):
            return

        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.exists(desktop):
            return

        target_exec = os.path.abspath(sys.executable)

        # Windows için .lnk kısayolu
        if sys.platform.startswith('win'):
            shortcut_path = os.path.join(desktop, "MAC Vendor Enricher.lnk")
            if not os.path.exists(shortcut_path):
                try:
                    ps_script = (
                        f"$WshShell = New-Object -comObject WScript.Shell; "
                        f"$Shortcut = $WshShell.CreateShortcut('{shortcut_path}'); "
                        f"$Shortcut.TargetPath = '{target_exec}'; "
                        f"$Shortcut.WorkingDirectory = '{EXEC_DIR}'; "
                        f"$Shortcut.Save()"
                    )
                    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script], capture_output=True)
                except Exception:
                    pass

        # Linux için LibreOffice sorununu çözen gerçek .desktop başlatıcısı
        elif sys.platform.startswith('linux'):
            desktop_file = os.path.join(desktop, "MAC-Vendor-Enricher.desktop")
            if not os.path.exists(desktop_file):
                try:
                    content = (
                        "[Desktop Entry]\n"
                        "Version=1.0\n"
                        "Type=Application\n"
                        "Name=MAC Vendor Enricher\n"
                        "Comment=Arka Plan MAC Adresi Zenginlestirici\n"
                        f"Exec=\"{target_exec}\"\n"
                        f"Path={EXEC_DIR}\n"
                        "Terminal=false\n"
                        "StartupNotify=false\n"
                        "Categories=Utility;Network;\n"
                    )
                    with open(desktop_file, "w", encoding="utf-8") as f:
                        f.write(content)
                    # Dosyaya çalıştırma izni ver
                    st = os.stat(desktop_file)
                    os.chmod(desktop_file, st.st_mode | stat.S_IEXEC)
                    # Ubuntu GNOME üzerinde "Allow Launching" (Güvenilir) olarak işaretle
                    subprocess.run(["gio", "set", desktop_file, "metadata::trusted", "true"], capture_output=True)
                except Exception:
                    pass

    def fetch_vendor(self, mac_str):
        clean_oui = re.sub(r'[^0-9A-Fa-f]', '', mac_str).upper()[:6]
        if clean_oui in self.oui_dataset:
            return self.oui_dataset[clean_oui]

        try:
            url = f"https://api.macvendors.com/{mac_str}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                vendor = resp.read().decode("utf-8").strip()
                vendor_clean = vendor.split(",")[0].replace("Corporation", "").replace("Inc.", "").strip()
                self.oui_dataset[clean_oui] = vendor_clean
                self.save_cache()
                return vendor_clean
        except Exception:
            pass
        
        return "Bilinmeyen Üretici"

    def show_clean_popup(self, title, items_list):
        if self.active_popup:
            try:
                self.active_popup.destroy()
            except Exception:
                pass

        self.active_popup = tk.Toplevel(self.root)
        self.active_popup.overrideredirect(True)
        self.active_popup.attributes("-topmost", True)
        try:
            self.active_popup.attributes("-alpha", 0.95)
        except Exception:
            pass
        self.active_popup.configure(bg="#1e1e1e")

        screen_width = self.active_popup.winfo_screenwidth()
        popup_width = 450
        popup_height = 65 + (len(items_list) * 24)
        self.active_popup.geometry(f"{popup_width}x{popup_height}+{screen_width - popup_width - 20}+35")

        frame = tk.Frame(self.active_popup, bg="#1e1e1e", padx=12, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        lbl_title = tk.Label(frame, text=f"🔍 {title}", fg="#4fc3f7", bg="#1e1e1e", font=("Sans", 10, "bold"))
        lbl_title.pack(anchor=tk.W, pady=(0, 6))

        for item in items_list:
            color = "#ff9800" if "[NETWORK DEVICE]" in item else "#a5d6a7"
            lbl_item = tk.Label(frame, text=item, fg=color, bg="#1e1e1e", font=("Monospace", 9), anchor="w")
            lbl_item.pack(fill=tk.X, anchor=tk.W)

        self.active_popup.after(4500, self.close_popup)

    def close_popup(self):
        if self.active_popup:
            try:
                self.active_popup.destroy()
            except Exception:
                pass
            self.active_popup = None

    def clipboard_monitor(self):
        try:
            current_clip = self.root.clipboard_get()
            if current_clip != self.last_clipboard and len(current_clip) < 100000:
                matches = list(MAC_REGEX.finditer(current_clip))
                if matches:
                    detected_summary = []
                    
                    def replacer(match):
                        mac = match.group(1)
                        vendor = self.fetch_vendor(mac)
                        
                        is_net = any(kw in vendor.lower() for kw in self.network_keywords)
                        tag = f"{vendor} [NETWORK DEVICE]" if is_net else vendor
                        
                        detected_summary.append(f"{mac} ➔ {tag}")
                        return f"{mac} ({tag})"

                    enriched = MAC_REGEX.sub(replacer, current_clip)
                    
                    self.root.clipboard_clear()
                    self.root.clipboard_append(enriched)
                    self.root.update()
                    self.last_clipboard = enriched

                    if detected_summary:
                        self.show_clean_popup(
                            f"MAC Tespit Edildi ({len(detected_summary)} Cihaz)",
                            detected_summary
                        )
                else:
                    self.last_clipboard = current_clip
        except Exception:
            pass

        self.root.after(400, self.clipboard_monitor)

if __name__ == "__main__":
    root = tk.Tk()
    app = StandaloneMacEnricher(root)
    root.mainloop()
