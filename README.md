# 🔍 MAC Vendor Enricher (Plug & Play)

[![Build and Release Multi-Platform](https://github.com/ErenOzduran/MAC-Vendor-Enricher/actions/workflows/build.yml/badge.svg)](https://github.com/ErenOzduran/MAC-Vendor-Enricher/actions)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-blue)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](#)

**MAC Vendor Enricher**, ağ ve sistem mühendislerinin günlük operasyonlarını hızlandırmak için tasarlanmış, arka planda sessizce çalışan **Tak-Çalıştır (Plug & Play)** bir pano (clipboard) dinleme ve zenginleştirme aracıdır.

Terminalden, log dosyalarından, switch/firewall arayüzlerinden veya ARP tablolarından kopyaladığınız metinlerin içindeki MAC adreslerini anında tespit eder; üretici (OUI Vendor) bilgisini yanına ekler ve ekranın sağ üst köşesinde şık bir **HUD Popup** bildirimi gösterir.

---

## ✨ Temel Özellikler (Key Features)

* **⚡ Sıfır Kurulum (Zero-Friction Plug & Play):** Python veya ek kütüphane kurulumu gerektirmez. İşletim sisteminize uygun dosyayı indirip doğrudan çalıştırabilirsiniz.
* **🌐 Akıllı Ağ Cihazı Tespiti (`[NETWORK DEVICE]`):** Cisco, Fortinet, Nokia, Juniper, Aruba, HPE, Palo Alto, MikroTik, Huawei, TP-Link ve Ubiquiti gibi kritik ağ donanımlarını otomatik tanır ve turuncu vurguyla işaretler.
* **📋 Otomatik Pano Zenginleştirme:** Kopyaladığınız (`Ctrl+C`) metindeki MAC adresini bozmadan yanına üreticisini ekler. Yapıştırdığınızda (`Ctrl+V`) doğrudan zenginleştirilmiş metni yapıştırırsınız:
  * *Kopyalanan:* `40:ed:00:xx:xx:xx (TP-Link Systems Inc)`
  * *Yapıştırılan:* `40:ed:00:xx:xx:xx (TP-Link [NETWORK DEVICE])`
* **🔄 Çoklu Format Desteği:** Standart (`00:1A:2B:3C:4D:5E (Ayecom Technology Co.)`), Windows (`00-1A-2B-3C-4D-5E (Ayecom Technology Co.)`) ve Cisco (`001a.2b3c.4d5e (Ayecom Technology Co.)`) MAC formatlarının tamamını aynı anda yakalar.
* **🚀 Çevrimdışı Önbellek + Çift Yedekli API:** Gömülü OUI veri seti sayesinde milisaniyeler içinde çevrimdışı yanıt verir. Listede olmayan yeni MAC adreslerini yedekli API mimarisiyle sorgular ve yerel önbelleğe (`~/.mac_vendor_cache.json`) kaydeder.
* **🖥️ Otomatik Masaüstü Entegrasyonu:** İlk çalıştırmada Windows (`.lnk`) ve Linux (`.desktop`) üzerinde masaüstünüze çift tıklanabilir uygulama kısayolunu otomatik oluşturur.

---

## 📥 İndirme ve Kurulum (Download & Quick Start)

Uygulamayı kullanmak için kodlarla veya terminalle uğraşmanıza gerek yoktur. **[GitHub Releases](https://github.com/ErenOzduran/MAC-Vendor-Enricher/releases/latest)** sayfasından işletim sisteminize uygun paketi indirin:

| İşletim Sistemi | Doğrudan İndirme Linki | Nasıl Çalıştırılır? |
| :--- | :--- | :--- |
| **🪟 Windows** | [**MAC-Vendor-Enricher-Windows.exe**](https://github.com/ErenOzduran/MAC-Vendor-Enricher/releases/latest/download/MAC-Vendor-Enricher-Windows.exe) | İndirin ve çift tıklayın. Arka planda çalışmaya başlayacak ve masaüstünüze kısayol oluşturacaktır. |
| **🐧 Linux** | [**MAC-Vendor-Enricher-Linux.tar.gz**](https://github.com/ErenOzduran/MAC-Vendor-Enricher/releases/latest/download/MAC-Vendor-Enricher-Linux.tar.gz) | Arşivi klasöre çıkarın. İlk açılışta sağ tıklayıp **"Run as a Program"** (Program Olarak Çalıştır) deyin; masaüstünüze kalıcı kısayol oluşacaktır. |
| **🍎 macOS** | [**MAC-Vendor-Enricher-macOS.zip**](https://github.com/ErenOzduran/MAC-Vendor-Enricher/releases/latest/download/MAC-Vendor-Enricher-macOS.zip) | `.zip` arşivini çıkarın ve `MAC-Vendor-Enricher.app` uygulamasına çift tıklayın. |

---

## 🛠️ Nasıl Çalışır? (Usage Example)

1. Uygulamayı başlatın (Sağ üstte *"MAC Vendor Enricher Aktif"* bildirimini göreceksiniz).
2. Terminalde veya herhangi bir ekranda içinde MAC adresi geçen bir çıktıyı kopyalayın (`Ctrl+C` veya seçip sağ tık `Copy`). Örneğin:
   ```text
   gateway (192.168.1.1) at 40:ed:00:xx:xx:xx (TP-Link Systems Inc) [ether] on wlp3s0
