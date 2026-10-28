#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import subprocess
import os

# Tkinter otomatik kontrolü (Linux için)
try:
    import tkinter as tk
except ImportError:
    try:
        if sys.platform.startswith('linux'):
            subprocess.check_call(["sudo", "apt-get", "update"])
            subprocess.check_call(["sudo", "apt-get", "install", "-y", "python3-tk"])
        import tkinter as tk
    except Exception:
        sys.exit(1)

import re
import json
import urllib.request
import urllib.error
import threading

# Dosya yolları (Derlenmiş .exe içinde veya normal çalışmada doğru konumlanma)
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if not getattr(sys, 'frozen', False) else os.path.dirname(os.path.executable)
DATASET_FILE = os.path.join(BASE_DIR, "oui_dataset.json")
NET_VENDORS_FILE = os.path.join(BASE_DIR, "network_vendors.json")

MAC_REGEX = re.compile(
    r'\b((?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}|(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4})\b(?!\s*\()'
)

class StandaloneMacEnricher:
    def __init__(self, root):
        self.root = root
        self.root.withdraw() # Arka planda tam gizli hayalet servis (Arayüz penceresi yok)
        
        self.oui_dataset = {}
        self.network_keywords = ["cisco", "meraki", "fortinet", "aruba", "hewlett packard", "hpe", "juniper", "nokia", "palo alto", "ubiquiti", "mikrotik", "huawei", "tp-link", "tp link"]
        
        self.load_files()
        self.create_desktop_shortcut_if_needed()
        
        self.last_clipboard = ""
        self.active_popup = None
        self.root.after(400, self.clipboard_monitor)

    def load_files(self):
        # Network anahtar kelimeleri dosyası
        if not os.path.exists(NET_VENDORS_FILE):
            try:
                with open(NET_VENDORS_FILE, "w", encoding="utf-8") as f:
                    json.dump({"network_keywords": self.network_keywords}, f, indent=2, ensure_ascii=False)
            except:
                pass
        else:
            try:
                with open(NET_VENDORS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.network_keywords = [kw.lower() for kw in data.get("network_keywords", self.network_keywords)]
            except:
                pass

        # Yerel önbellek veri seti
        if os.path.exists(DATASET_FILE):
            try:
                with open(DATASET_FILE, "r", encoding="utf-8") as f:
                    self.oui_dataset = json.load(f)
            except:
                self.oui_dataset = {}

    def save_cache(self):
        try:
            with open(DATASET_FILE, "w", encoding="utf-8") as f:
                json.dump(self.oui_dataset, f, indent=2, ensure_ascii=False)
        except:
            pass

    def create_desktop_shortcut_if_needed(self):
        """Windows'ta ilk açılışta masaüstüne otomatik kısayol oluşturur (Harici modül gerektirmez)"""
        if sys.platform.startswith('win'):
            try:
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                shortcut_path = os.path.join(desktop, "MAC Vendor Enricher.lnk")
                if not os.path.exists(shortcut_path):
                    target = sys.executable if getattr(sys, 'frozen', False) else __file__
                    ps_script = (
                        f"$WshShell = New-Object -comObject WScript.Shell; "
                        f"$Shortcut = $WshShell.CreateShortcut('{shortcut_path}'); "
                        f"$Shortcut.TargetPath = '{target}'; "
                        f"$Shortcut.WorkingDirectory = '{os.path.dirname(target)}'; "
                        f"$Shortcut.Save()"
                    )
                    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script], capture_output=True)
            except:
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
        except:
            pass
        
        return "Bilinmeyen Üretici"

    def show_clean_popup(self, title, items_list):
        if self.active_popup:
            try:
                self.active_popup.destroy()
            except:
                pass

        self.active_popup = tk.Toplevel(self.root)
        self.active_popup.overrideredirect(True)
        self.active_popup.attributes("-topmost", True)
        self.active_popup.attributes("-alpha", 0.95)
        self.active_popup.configure(bg="#1e1e1e")

        screen_width = self.active_popup.winfo_screenwidth()
        popup_width = 440
        popup_height = 70 + (len(items_list) * 25)
        self.active_popup.geometry(f"{popup_width}x{popup_height}+{screen_width - popup_width - 20}+30")

        frame = tk.Frame(self.active_popup, bg="#1e1e1e", padx=12, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        lbl_title = tk.Label(frame, text=f"🔍 {title}", fg="#4fc3f7", bg="#1e1e1e", font=("Segoe UI", 10, "bold"))
        lbl_title.pack(anchor=tk.W, pady=(0, 6))

        for item in items_list:
            color = "#ff9800" if "[NETWORK DEVICE]" in item else "#a5d6a7"
            lbl_item = tk.Label(frame, text=item, fg=color, bg="#1e1e1e", font=("Consolas", 9), anchor="w")
            lbl_item.pack(fill=tk.X, anchor=tk.W)

        self.active_popup.after(5000, self.close_popup)

    def close_popup(self):
        if self.active_popup:
            try:
                self.active_popup.destroy()
            except:
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
        except:
            pass

        self.root.after(400, self.clipboard_monitor)

if __name__ == "__main__":
    root = tk.Tk()
    app = StandaloneMacEnricher(root)
    root.mainloop()
