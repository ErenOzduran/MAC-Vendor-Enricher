#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import subprocess
import stat
import re
import json
import ssl
import urllib.request
import urllib.error
import tkinter as tk

# macOS ve Windows'ta SSL Sertifika doğrulama hatasını (CERTIFICATE_VERIFY_FAILED) aşmak için context
SSL_CONTEXT = ssl._create_unverified_context()

# PyInstaller (_MEIPASS) ve Normal Çalışma İçin Dizin Tespiti
if getattr(sys, 'frozen', False):
    BUNDLE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    EXEC_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    EXEC_DIR = BUNDLE_DIR

BUNDLED_DATASET = os.path.join(BUNDLE_DIR, "oui_dataset.json")
BUNDLED_VENDORS = os.path.join(BUNDLE_DIR, "network_vendors.json")

# API'den çekilen en doğru verilerin kaydedildiği dinamik önbellek
USER_CACHE_FILE = os.path.join(os.path.expanduser("~"), ".mac_vendor_cache.json")

# macOS'un tek haneli hex (0:3c gibi) ARP çıktılarını da yakalayan gelişmiş MAC Regex'i
MAC_REGEX = re.compile(
    r'(?<![0-9A-Fa-f:])((?:[0-9A-Fa-f]{1,2}\s*[:-]\s*){5}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4})(?![0-9A-Fa-f:])(?!\s*\()'
)

class StandaloneMacEnricher:
    def __init__(self, root):
        self.root = root
        self.root.withdraw()
        
        self.api_cache = {}
        self.fallback_dataset = {}
        
        self.network_keywords = [
            "cisco", "meraki", "fortinet", "aruba", "hewlett packard", 
            "hpe", "juniper", "nokia", "palo alto", "ubiquiti", 
            "mikrotik", "huawei", "tp-link", "tp link", "mercusys",
            "keenetic", "zyxel", "d-link", "netgear", "extreme networks", "brocade", "ruijie"
        ]
        
        self.load_files()
        self.setup_desktop_Integration()
        
        self.last_clipboard = ""
        self.active_popup = None
        self.popup_timer = None
        
        # İlk açılış bildirimi (6 saniye kalır)
        self.show_clean_popup("MAC Vendor Enricher Aktif", ["Cross-platform pano dinleme başladı..."], duration=6000)
        self.root.after(350, self.clipboard_monitor)

    def normalize_mac_and_oui(self, mac_str):
        """macOS'un 1c:93:c4:0:3c:ad gibi eksik sıfırlı MAC adreslerini 1C93C4003CAD formatına tamamlar."""
        mac_str = mac_str.strip()
        if '.' in mac_str:
            clean_hex = re.sub(r'[^0-9A-Fa-f]', '', mac_str).upper()
        else:
            sep = ':' if ':' in mac_str else '-'
            parts = [p.strip().zfill(2) for p in mac_str.split(sep)]
            clean_hex = "".join(parts).upper()
        return clean_hex, clean_hex[:6]

    def normalize_oui_dict(self, raw_dict):
        cleaned = {}
        if isinstance(raw_dict, dict):
            for k, v in raw_dict.items():
                clean_k = re.sub(r'[^0-9A-Fa-f]', '', str(k)).upper()[:6]
                if len(clean_k) == 6 and v and "Bilinmeyen" not in str(v):
                    cleaned[clean_k] = str(v)
        return cleaned

    def load_files(self):
        if os.path.exists(BUNDLED_VENDORS):
            try:
                with open(BUNDLED_VENDORS, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    loaded_kws = [kw.lower() for kw in data.get("network_keywords", [])]
                    self.network_keywords = list(set(self.network_keywords + loaded_kws))
            except Exception:
                pass

        if os.path.exists(BUNDLED_DATASET):
            try:
                with open(BUNDLED_DATASET, "r", encoding="utf-8") as f:
                    self.fallback_dataset = self.normalize_oui_dict(json.load(f))
            except Exception:
                pass

        if os.path.exists(USER_CACHE_FILE):
            try:
                with open(USER_CACHE_FILE, "r", encoding="utf-8") as f:
                    self.api_cache = self.normalize_oui_dict(json.load(f))
            except Exception:
                pass

    def save_cache(self):
        try:
            with open(USER_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.api_cache, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def setup_desktop_Integration(self):
        if not getattr(sys, 'frozen', False):
            return

        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.exists(desktop):
            return

        target_exec = os.path.abspath(sys.executable)

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
                    st = os.stat(desktop_file)
                    os.chmod(desktop_file, st.st_mode | stat.S_IEXEC)
                    subprocess.run(["gio", "set", desktop_file, "metadata::trusted", "true"], capture_output=True)
                except Exception:
                    pass

    def clean_vendor_name(self, vendor_str):
        v = vendor_str.split(",")[0]
        for suffix in ["Corporation", "Inc.", "Inc", "Technologies", "Technology", "Co.", "Ltd.", "Ltd", "Limited", "GmbH"]:
            v = re.sub(rf'\b{re.escape(suffix)}\b\.?', '', v, flags=re.IGNORECASE)
        return re.sub(r'\s+', ' ', v).strip(" .,-")

    def fetch_vendor(self, mac_str):
        full_hex, clean_oui = self.normalize_mac_and_oui(mac_str)

        # 1. Özel Protokol Adresleri Kontrolü (Broadcast & Multicast)
        if full_hex == "FFFFFFFFFFFF":
            return "Broadcast Adresi"
        if clean_oui.startswith("01005E") or clean_oui.startswith("3333"):
            return "Multicast Adresi"

        # 2. Önbellekte Varsa Getir
        if clean_oui in self.api_cache:
            return self.api_cache[clean_oui]

        # 3. Canlı API 1: maclookup.app (macOS SSL Context destekli)
        try:
            url = f"https://api.maclookup.app/v2/macs/{clean_oui}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=2.5, context=SSL_CONTEXT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                company = data.get("company", "").strip()
                if company:
                    vendor_clean = self.clean_vendor_name(company)
                    self.api_cache[clean_oui] = vendor_clean
                    self.save_cache()
                    return vendor_clean
        except Exception:
            pass

        # 4. Canlı API 2: macvendors.com (macOS SSL Context destekli)
        try:
            url2 = f"https://api.macvendors.com/{clean_oui}"
            req2 = urllib.request.Request(url2, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req2, timeout=2.5, context=SSL_CONTEXT) as resp2:
                vendor = resp2.read().decode("utf-8").strip()
                if vendor and "errors" not in vendor.lower():
                    vendor_clean = self.clean_vendor_name(vendor)
                    self.api_cache[clean_oui] = vendor_clean
                    self.save_cache()
                    return vendor_clean
        except Exception:
            pass

        # 5. Yedek (Fallback) Veri Seti
        if clean_oui in self.fallback_dataset:
            return self.fallback_dataset[clean_oui]

        # 6. Rastgele / Gizli MAC (Locally Administered Address - LAA) Kontrolü
        if len(clean_oui) == 6 and clean_oui[1] in ('2', '6', 'A', 'E'):
            return "Gizli/Rastgele MAC (LAA)"
        
        return "Bilinmeyen Üretici"

    def get_clipboard_text(self):
        for clip_type in ("CLIPBOARD", "PRIMARY"):
            try:
                text = self.root.selection_get(selection=clip_type)
                if text and text.strip():
                    clean_text = text.replace('\u200b', '').replace('\xa0', ' ')
                    if clip_type == "CLIPBOARD":
                        return clean_text
            except Exception:
                pass
        try:
            return self.root.clipboard_get().replace('\u200b', '').replace('\xa0', ' ')
        except Exception:
            return ""

    def show_clean_popup(self, title, items_list, duration=12000):
        if self.popup_timer:
            try:
                self.root.after_cancel(self.popup_timer)
            except Exception:
                pass
            self.popup_timer = None

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
        popup_width = 500
        popup_height = 70 + (len(items_list) * 24)
        self.active_popup.geometry(f"{popup_width}x{popup_height}+{screen_width - popup_width - 20}+35")

        frame = tk.Frame(self.active_popup, bg="#1e1e1e", padx=12, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        lbl_title = tk.Label(
            frame, 
            text=f"🔍 {title}  [✕ Kapat]", 
            fg="#4fc3f7", 
            bg="#1e1e1e", 
            font=("Sans", 10, "bold"),
            cursor="hand2"
        )
        lbl_title.pack(anchor=tk.W, pady=(0, 6))

        # Pencerenin herhangi bir yerine tıklandığında anında kapat
        self.active_popup.bind("<Button-1>", lambda e: self.close_popup())
        frame.bind("<Button-1>", lambda e: self.close_popup())
        lbl_title.bind("<Button-1>", lambda e: self.close_popup())

        for item in items_list:
            color = "#ff9800" if "[NETWORK DEVICE]" in item else "#a5d6a7"
            lbl_item = tk.Label(frame, text=item, fg=color, bg="#1e1e1e", font=("Monospace", 9), anchor="w")
            lbl_item.pack(fill=tk.X, anchor=tk.W)
            lbl_item.bind("<Button-1>", lambda e: self.close_popup())

        # Cihaz sayısına göre dinamik süre: En az 12 saniye, çoklu listede 25 saniyeye kadar ekranda kalır
        dynamic_duration = min(25000, max(duration, len(items_list) * 2500))
        self.popup_timer = self.root.after(dynamic_duration, self.close_popup)

    def close_popup(self):
        if self.popup_timer:
            try:
                self.root.after_cancel(self.popup_timer)
            except Exception:
                pass
            self.popup_timer = None

        if self.active_popup:
            try:
                self.active_popup.destroy()
            except Exception:
                pass
            self.active_popup = None

    def clipboard_monitor(self):
        try:
            current_clip = self.get_clipboard_text()
            if current_clip and current_clip != self.last_clipboard and len(current_clip) < 100000:
                matches = list(MAC_REGEX.finditer(current_clip))
                if matches:
                    detected_summary = []
                    
                    def replacer(match):
                        raw_mac = match.group(1)
                        mac = re.sub(r'\s+', '', raw_mac)
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
                            detected_summary[:14], # Uzun ARP tablolarında ilk 14 cihazı göster
                            duration=12000
                        )
                else:
                    self.last_clipboard = current_clip
        except Exception:
            pass

        self.root.after(350, self.clipboard_monitor)

if __name__ == "__main__":
    root = tk.Tk()
    app = StandaloneMacEnricher(root)
    root.mainloop()
