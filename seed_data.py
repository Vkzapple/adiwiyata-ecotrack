"""
EcoTrack AI - Seed Data Script
================================
Isi database dengan data contoh untuk demo & testing.

Jalankan:
    python seed_data.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timedelta
import random

from app.models.database import create_tables, SessionLocal, Pokja, Kegiatan, Laporan
from app.services.behavior_analysis import BehaviorAnalyzer
from app.services.report_generator import generate_laporan


def seed():
    create_tables()
    db = SessionLocal()

    print("🌱 Memulai seeding data EcoTrack AI...\n")

    # ── 1. Pokja ──────────────────────────────────────────────────────────────
    pokja_data = [
        {"nama": "Pokja Penghijauan",    "deskripsi": "Bertanggung jawab atas penghijauan dan penanaman pohon di lingkungan sekolah", "ketua": "Ibu Sari",    "warna": "#4CAF50"},
        {"nama": "Pokja Hidroponik",     "deskripsi": "Mengelola kebun hidroponik sekolah dan budidaya sayuran tanpa tanah",          "ketua": "Pak Budi",    "warna": "#2196F3"},
        {"nama": "Pokja Energi",         "deskripsi": "Mengawasi penggunaan energi dan implementasi energi terbarukan",               "ketua": "Ibu Dewi",    "warna": "#FF9800"},
        {"nama": "Pokja Sampah",         "deskripsi": "Mengelola program 3R (Reduce, Reuse, Recycle) dan bank sampah sekolah",        "ketua": "Pak Rudi",    "warna": "#795548"},
        {"nama": "Pokja Air Bersih",     "deskripsi": "Memantau kualitas air dan konservasi sumber daya air sekolah",                 "ketua": "Bu Ani",      "warna": "#00BCD4"},
    ]

    pokja_ids = {}
    for p in pokja_data:
        existing = db.query(Pokja).filter(Pokja.nama == p["nama"]).first()
        if not existing:
            obj = Pokja(**p)
            db.add(obj)
            db.flush()
            pokja_ids[p["nama"]] = obj.id
            print(f"  ✅ Pokja: {p['nama']}")
        else:
            pokja_ids[p["nama"]] = existing.id
            print(f"  ⏭️  Pokja sudah ada: {p['nama']}")
    db.commit()

    # ── 2. Kegiatan (dengan pola berbeda-beda per Pokja) ─────────────────────
    now = datetime.now()

    kegiatan_templates = {
        "Pokja Penghijauan": [
            ("Penanaman Pohon Perindang",       30, "Taman Belakang Sekolah", "Alat cangkul kurang",          "50 bibit berhasil ditanam"),
            ("Perawatan Tanaman Toga",          15, "Kebun Toga Sekolah",      None,                           "Tanaman toga terawat dan subur"),
            ("Workshop Teknik Pembibitan",      40, "Laboratorium Biologi",    None,                           "Siswa memahami teknik pembibitan"),
            ("Pemupukan Tanaman Sekolah",       20, "Area Sekolah",            "Pupuk organik terbatas",       "Semua tanaman terpupuk"),
            ("Dokumentasi Koleksi Tanaman",     10, "Taman Sekolah",           None,                           "100 foto terdokumentasi dengan QR"),
        ],
        "Pokja Hidroponik": [
            ("Penyemaian Benih Selada",         12, "Kebun Hidroponik",        None,                           "200 benih berhasil disemai"),
            ("Perawatan Instalasi Hidroponik",  8,  "Greenhouse",              "Pompa air rusak sementara",    "Instalasi berfungsi normal kembali"),
            ("Panen Sayuran Hidroponik",        20, "Kebun Hidroponik",        None,                           "15 kg sayuran berhasil dipanen"),
        ],
        "Pokja Energi": [
            ("Audit Penggunaan Listrik",        5,  "Seluruh Area Sekolah",    None,                           "Laporan audit selesai"),
            ("Sosialisasi Hemat Energi",        120,"Aula Sekolah",            "Proyektor bermasalah",         "Siswa paham pentingnya hemat energi"),
            ("Pemasangan Lampu LED Hemat Energi", 8, "Ruang Kelas",           None,                           "20 ruang kelas terpasang LED"),
            ("Pemeriksaan Panel Surya",         4,  "Atap Gedung Utama",       None,                           "Panel surya berfungsi optimal"),
        ],
        "Pokja Sampah": [
            ("Pemilahan Sampah Organik & Anorganik", 35, "Kantin Sekolah",    "Tempat sampah kurang",         "Siswa mulai memilah sampah dengan benar"),
            ("Pelatihan Daur Ulang Sampah",     50, "Lapangan Sekolah",        None,                           "10 produk daur ulang berhasil dibuat"),
        ],
        "Pokja Air Bersih": [
            ("Pengujian Kualitas Air",          6,  "Laboratorium",             None,                           "Air dinyatakan aman untuk dikonsumsi"),
        ],
    }

    # Generate kegiatan dengan tanggal bervariasi
    # Penghijauan = sangat aktif (banyak kegiatan recent)
    # Hidroponik  = aktif tapi ada gap
    # Energi      = aktif
    # Sampah      = kurang aktif (sedikit kegiatan)
    # Air Bersih  = tidak aktif (hanya 1 kegiatan lama)

    date_configs = {
        "Pokja Penghijauan": [1, 8, 15, 28, 35],        # 5 kegiatan, konsisten
        "Pokja Hidroponik":  [5, 20, 50],                # 3 kegiatan, ada gap
        "Pokja Energi":      [3, 14, 22, 40],            # 4 kegiatan
        "Pokja Sampah":      [60, 75],                   # 2 kegiatan, sudah lama
        "Pokja Air Bersih":  [80],                       # 1 kegiatan, paling lama
    }

    for pokja_nama, templates in kegiatan_templates.items():
        pokja_id  = pokja_ids.get(pokja_nama)
        days_back = date_configs.get(pokja_nama, [30])

        for i, (judul, peserta, lokasi, kendala, hasil) in enumerate(templates):
            if i >= len(days_back):
                break
            tanggal = now - timedelta(days=days_back[i])
            status  = "done" if days_back[i] > 3 else "ongoing"

            existing = db.query(Kegiatan).filter(
                Kegiatan.pokja_id == pokja_id,
                Kegiatan.judul == judul
            ).first()

            if not existing:
                k = Kegiatan(
                    pokja_id       = pokja_id,
                    judul          = judul,
                    tanggal        = tanggal,
                    lokasi         = lokasi,
                    jumlah_peserta = peserta,
                    kendala        = kendala,
                    hasil          = hasil,
                    status         = status,
                )
                db.add(k)
                db.flush()

                # Generate laporan otomatis
                report = generate_laporan(
                    nama_kegiatan      = judul,
                    nama_pokja         = pokja_nama,
                    tanggal            = tanggal,
                    peserta            = peserta,
                    lokasi             = lokasi,
                    kendala            = kendala,
                    hasil              = hasil,
                )
                l = Laporan(
                    kegiatan_id       = k.id,
                    pokja_id          = pokja_id,
                    judul             = report["judul"],
                    konten            = report["konten"],
                    template_used     = report["template"],
                    is_auto_generated = True,
                )
                db.add(l)
                print(f"  📝 Kegiatan: {judul[:45]}")

    db.commit()

    # ── 3. Run AI Analysis ────────────────────────────────────────────────────
    print("\n🤖 Menjalankan AI Behavior Analysis...")
    analyzer = BehaviorAnalyzer(db)
    results  = analyzer.analyze_all()
    analyzer.save_scores(results)

    print("\n📊 Hasil Scoring Pokja:")
    print("─" * 60)
    for r in results:
        bar = "█" * int(r["skor_total"] / 10)
        print(f"  {r['pokja_nama']:<25} {r['skor_total']:5.1f}/100  {bar:<10}  [{r['label']}]")

    print("\n💡 Global Insights:")
    insights = analyzer.generate_global_insights(results)
    for ins in insights:
        print(f"  {ins}")

    print("\n✅ Seeding selesai! Jalankan server dengan: uvicorn main:app --reload")
    db.close()


if __name__ == "__main__":
    seed()
