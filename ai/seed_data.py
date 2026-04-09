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

    # ── 1. Pokja (16 Pokja) ─────────────────────────────────────────────
    pokja_data = [
        {"nama": "Pokja Penghijauan", "deskripsi": "Penghijauan sekolah", "ketua": "Ibu Sari", "warna": "#4CAF50"},
        {"nama": "Pokja Hidroponik", "deskripsi": "Kebun hidroponik", "ketua": "Pak Budi", "warna": "#2196F3"},
        {"nama": "Pokja Energi", "deskripsi": "Manajemen energi", "ketua": "Ibu Dewi", "warna": "#FF9800"},
        {"nama": "Pokja Sampah", "deskripsi": "Pengelolaan sampah", "ketua": "Pak Rudi", "warna": "#795548"},
        {"nama": "Pokja Air Bersih", "deskripsi": "Konservasi air", "ketua": "Bu Ani", "warna": "#00BCD4"},

        {"nama": "Pokja Kebersihan", "deskripsi": "Kebersihan lingkungan", "ketua": "Pak Joko", "warna": "#9C27B0"},
        {"nama": "Pokja Komposting", "deskripsi": "Pengolahan kompos", "ketua": "Bu Lina", "warna": "#8BC34A"},
        {"nama": "Pokja Taman", "deskripsi": "Perawatan taman", "ketua": "Pak Agus", "warna": "#CDDC39"},
        {"nama": "Pokja Edukasi Lingkungan", "deskripsi": "Edukasi siswa", "ketua": "Bu Rina", "warna": "#FFC107"},
        {"nama": "Pokja Bank Sampah", "deskripsi": "Manajemen bank sampah", "ketua": "Pak Dedi", "warna": "#FF5722"},

        {"nama": "Pokja Biopori", "deskripsi": "Lubang resapan air", "ketua": "Pak Andi", "warna": "#607D8B"},
        {"nama": "Pokja Urban Farming", "deskripsi": "Pertanian kota", "ketua": "Bu Maya", "warna": "#4CAF50"},
        {"nama": "Pokja Sanitasi", "deskripsi": "Sanitasi sekolah", "ketua": "Pak Yudi", "warna": "#00ACC1"},
        {"nama": "Pokja Konservasi", "deskripsi": "Konservasi lingkungan", "ketua": "Bu Sinta", "warna": "#FF9800"},
        {"nama": "Pokja Inovasi", "deskripsi": "Inovasi teknologi", "ketua": "Pak Rizky", "warna": "#3F51B5"},
        {"nama": "Pokja Dokumentasi", "deskripsi": "Dokumentasi kegiatan", "ketua": "Bu Nia", "warna": "#E91E63"},
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

    db.commit()

    # ── 2. Generate 120+ Kegiatan ───────────────────────────────────────
    print("\n📊 Generating kegiatan...")

    now = datetime.now()
    total_kegiatan = 130  # biar aman >120

    all_pokja_ids = list(pokja_ids.values())

    for i in range(total_kegiatan):
        pokja_id = random.choice(all_pokja_ids)
        tanggal = now - timedelta(days=random.randint(1, 90))

        k = Kegiatan(
            pokja_id=pokja_id,
            judul=f"Kegiatan Lingkungan #{i+1}",
            tanggal=tanggal,
            lokasi="Area Sekolah",
            jumlah_peserta=random.randint(5, 100),
            kendala=None if random.random() > 0.3 else "Kendala teknis ringan",
            hasil="Kegiatan berjalan dengan baik",
            status="done" if random.random() > 0.2 else "ongoing",
        )
        db.add(k)
        db.flush()

        # ── Generate laporan AI otomatis ──
        report = generate_laporan(
            nama_kegiatan=k.judul,
            nama_pokja="Pokja",
            tanggal=tanggal,
            peserta=k.jumlah_peserta,
            lokasi=k.lokasi,
            kendala=k.kendala,
            hasil=k.hasil,
        )

        l = Laporan(
            kegiatan_id=k.id,
            pokja_id=pokja_id,
            judul=report["judul"],
            konten=report["konten"],
            template_used=report["template"],
            is_auto_generated=True,
        )
        db.add(l)

        if (i + 1) % 20 == 0:
            print(f"  🚀 {i+1} kegiatan dibuat...")

    db.commit()

    # ── 3. Simulasi jumlah anggota ──────────────────────────────────────
    total_anggota = 385
    print(f"\n👥 Total anggota terdaftar: {total_anggota}")

    # ── 4. Run AI Behavior Analysis ─────────────────────────────────────
    print("\n🤖 Menjalankan AI Behavior Analysis...")

    analyzer = BehaviorAnalyzer(db)
    results = analyzer.analyze_all()
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

    print("\n✅ Seeding selesai!")
    print("👉 Jalankan server: uvicorn main:app --reload")

    db.close()


if __name__ == "__main__":
    seed()