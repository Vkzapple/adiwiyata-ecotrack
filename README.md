# 🌱 EcoTrack AI — Smart Adiwiyata Management System

> **Backend Python** untuk sistem manajemen program Adiwiyata berbasis kecerdasan buatan.
> Dirancang untuk lomba inovasi Web 4.0 — mengubah data kegiatan menjadi *decision support system*.

---

## 📦 Struktur Proyek

```
ecotrack/
├── main.py                          # Entry point FastAPI
├── seed_data.py                     # Script isi data contoh
├── requirements.txt
└── app/
    ├── models/
    │   ├── database.py              # SQLAlchemy ORM models + DB setup
    │   └── schemas.py               # Pydantic request/response schemas
    ├── services/
    │   ├── behavior_analysis.py     # 🤖 AI Behavior Analysis + Scoring
    │   └── report_generator.py      # ✨ Auto Report Generator (NLP)
    └── routers/
        └── api.py                   # FastAPI endpoints semua domain
```

---

## 🚀 Cara Menjalankan

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Isi Data Contoh (opsional, untuk demo)
```bash
python seed_data.py
```

### 3. Jalankan Server
```bash
uvicorn main:app --reload --port 8000
```

### 4. Buka Dokumentasi API Interaktif
```
http://localhost:8000/docs
```

---

## 🗄️ Database Design

### Tabel `pokja`
| Kolom       | Tipe        | Keterangan                          |
|-------------|-------------|-------------------------------------|
| id          | INTEGER PK  | Auto-increment                      |
| nama        | VARCHAR(100)| Nama Pokja (unique)                 |
| deskripsi   | TEXT        | Deskripsi singkat                   |
| ketua       | VARCHAR(100)| Nama penanggung jawab               |
| status      | VARCHAR(20) | active / inactive / archived        |
| warna       | VARCHAR(7)  | Hex color untuk tampilan UI         |
| created_at  | DATETIME    | Timestamp pembuatan                 |

### Tabel `kegiatan`
| Kolom           | Tipe        | Keterangan                      |
|-----------------|-------------|----------------------------------|
| id              | INTEGER PK  | Auto-increment                  |
| pokja_id        | INTEGER FK  | Referensi ke tabel pokja        |
| judul           | VARCHAR(200)| Nama kegiatan                   |
| tanggal         | DATETIME    | Tanggal pelaksanaan             |
| lokasi          | VARCHAR(150)| Tempat kegiatan                 |
| jumlah_peserta  | INTEGER     | Jumlah peserta                  |
| kendala         | TEXT        | Kendala yang dihadapi           |
| hasil           | TEXT        | Hasil/output kegiatan           |
| status          | VARCHAR(20) | planned/ongoing/done/cancelled  |

### Tabel `dokumentasi`
| Kolom       | Tipe        | Keterangan                          |
|-------------|-------------|-------------------------------------|
| id          | INTEGER PK  |                                     |
| kegiatan_id | INTEGER FK  | Referensi ke kegiatan               |
| filename    | VARCHAR(255)| Nama file asli upload               |
| stored_name | VARCHAR(255)| Nama setelah auto-rename            |
| file_path   | VARCHAR(500)| Path relatif penyimpanan            |
| file_type   | VARCHAR(50) | image/pdf/dll                       |
| file_size   | INTEGER     | Ukuran file (bytes)                 |

### Tabel `laporan`
| Kolom             | Tipe    | Keterangan                        |
|-------------------|---------|-----------------------------------|
| id                | INTEGER PK |                                |
| kegiatan_id       | INTEGER FK | One-to-one dengan kegiatan    |
| pokja_id          | INTEGER FK |                                |
| judul             | VARCHAR(300) | Judul laporan               |
| konten            | TEXT    | Paragraf laporan (auto-generated) |
| is_auto_generated | BOOLEAN | True = dibuat oleh sistem         |

### Tabel `skor_pokja`
| Kolom              | Tipe    | Keterangan                         |
|--------------------|---------|-------------------------------------|
| id                 | INTEGER PK |                                  |
| pokja_id           | INTEGER FK | One-to-one dengan pokja          |
| skor_total         | FLOAT   | 0–100, skor keseluruhan             |
| skor_frekuensi     | FLOAT   | Komponen: frekuensi kegiatan        |
| skor_konsistensi   | FLOAT   | Komponen: konsistensi mingguan      |
| skor_penyelesaian  | FLOAT   | Komponen: % kegiatan selesai        |
| skor_partisipasi   | FLOAT   | Komponen: rata-rata peserta         |
| label              | VARCHAR | Sangat Aktif / Aktif / ... dll      |
| insight            | TEXT    | Kalimat AI dalam Bahasa Indonesia   |
| calculated_at      | DATETIME| Waktu kalkulasi terakhir            |

---

## 🤖 AI Behavior Analysis

### Cara Kerja Scoring

Setiap Pokja dinilai berdasarkan **4 komponen** dengan bobot:

| Komponen       | Bobot | Penjelasan                                      |
|----------------|-------|-------------------------------------------------|
| Frekuensi      | 30%   | Seberapa sering kegiatan dilakukan              |
| Konsistensi    | 30%   | Kerataan aktivitas mingguan (ada/tidaknya gap)  |
| Penyelesaian   | 25%   | Persentase kegiatan berstatus `done`            |
| Partisipasi    | 15%   | Rata-rata peserta vs rata-rata global           |

### Label Otomatis

| Skor     | Label         |
|----------|---------------|
| 80–100   | Sangat Aktif  |
| 60–80    | Aktif         |
| 40–60    | Cukup Aktif   |
| 20–40    | Kurang Aktif  |
| 0–20     | Tidak Aktif   |

### Insight Otomatis (contoh output)
```
⚠️ Pokja Sampah perlu perhatian — aktivitas di bawah rata-rata (skor 38/100).
Hanya 1 dari 2 kegiatan yang selesai (50%) — perlu ditingkatkan.
Tidak ada kegiatan dalam 5 minggu terakhir — segera tindak lanjuti!
```

### K-Means Clustering (opsional)
Pokja dikelompokkan menjadi 3 cluster menggunakan `scikit-learn`:
- **Cluster 0**: Performa Tinggi
- **Cluster 1**: Performa Sedang  
- **Cluster 2**: Performa Rendah

---

## ✨ Auto Report Generator

Input minimal dari user → paragraf laporan formal otomatis.

### Contoh Input
```json
{
  "nama_kegiatan": "Penanaman Pohon",
  "nama_pokja": "Pokja Penghijauan",
  "tanggal": "2025-04-10T08:00:00",
  "peserta": 25,
  "lokasi": "Taman Belakang Sekolah",
  "kendala": "Alat cangkul kurang",
  "hasil": "30 bibit berhasil ditanam"
}
```

### Contoh Output
```
Kegiatan Penanaman Pohon telah dilaksanakan pada Kamis, 10 April 2025 
bertempat di Taman Belakang Sekolah.

Kegiatan tersebut diikuti oleh 25 orang, menunjukkan antusiasme yang 
tinggi dari seluruh anggota.

Terdapat beberapa kendala dalam pelaksanaan, yaitu alat cangkul kurang. 
Namun hal ini tidak menghalangi jalannya kegiatan secara keseluruhan.

Melalui kegiatan ini, Pokja Penghijauan berhasil 30 bibit berhasil ditanam.

Laporan ini disusun sebagai bentuk pertanggungjawaban pelaksanaan kegiatan 
Penanaman Pohon. Semoga hasil yang dicapai dapat menginspirasi seluruh warga 
sekolah untuk semakin peduli terhadap lingkungan.
```

> **Catatan**: Template menggunakan variasi kalimat acak sehingga laporan tidak terkesan monoton.

---

## 📊 API Endpoints

### Pokja
| Method | Endpoint          | Fungsi                    |
|--------|-------------------|---------------------------|
| POST   | /pokja/           | Buat Pokja baru           |
| GET    | /pokja/           | List semua Pokja          |
| GET    | /pokja/{id}       | Detail satu Pokja         |
| PUT    | /pokja/{id}       | Update Pokja              |
| DELETE | /pokja/{id}       | Soft-delete Pokja         |

### Kegiatan
| Method | Endpoint              | Fungsi                      |
|--------|-----------------------|-----------------------------|
| POST   | /kegiatan/            | Input kegiatan baru         |
| GET    | /kegiatan/            | List kegiatan (filter pokja)|
| GET    | /kegiatan/{id}        | Detail kegiatan             |
| PUT    | /kegiatan/{id}        | Update kegiatan             |
| DELETE | /kegiatan/{id}        | Hapus kegiatan              |

### Laporan
| Method | Endpoint              | Fungsi                        |
|--------|-----------------------|-------------------------------|
| POST   | /laporan/generate     | Generate laporan otomatis     |
| GET    | /laporan/             | List laporan                  |
| GET    | /laporan/{id}         | Ambil satu laporan            |

### Analytics & AI
| Method | Endpoint                        | Fungsi                          |
|--------|---------------------------------|---------------------------------|
| POST   | /analytics/recalculate          | Hitung ulang semua skor         |
| GET    | /analytics/dashboard            | Data lengkap dashboard          |
| GET    | /analytics/ranking              | Ranking Pokja + K-Means opsional|
| GET    | /analytics/pokja/{id}/insight   | Insight AI satu Pokja           |

---

## 🔧 Tech Stack

| Komponen     | Teknologi               |
|--------------|-------------------------|
| Framework    | FastAPI                 |
| Database ORM | SQLAlchemy + SQLite     |
| Validasi     | Pydantic v2             |
| Data Processing | Pandas + NumPy       |
| ML / Scoring | Scikit-learn (K-Means)  |
| Server       | Uvicorn (ASGI)          |

---

## 💡 Nilai Inovasi untuk Lomba

1. **Bukan sekadar CRUD** — sistem ini adalah *decision support system* yang memberikan insight
2. **AI tanpa API berbayar** — semua analisis berjalan lokal dengan algoritma rule-based + ML ringan
3. **Auto Report** — mengurangi beban administrasi secara signifikan
4. **Scoring transparan** — setiap komponen skor bisa dilihat dan dijelaskan
5. **Siap dikembangkan** — arsitektur modular memudahkan penambahan fitur (QR, notifikasi, dll)
This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
