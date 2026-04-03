"""
EcoTrack AI - Auto Report Generator
=====================================
Generate laporan resmi berbahasa Indonesia secara otomatis
dari input minimal pengguna.

Menggunakan pendekatan template NLP tanpa API eksternal:
- Template berbasis kondisi (if/else logis)
- Variasi kalimat agar tidak monoton
- Format laporan formal sesuai standar Adiwiyata
"""

import random
from datetime import datetime
from typing import Optional, Dict
from enum import Enum


# ─── Template Fragments ───────────────────────────────────────────────────────

class ReportTemplates:
    """Kumpulan template kalimat dalam Bahasa Indonesia formal."""

    PEMBUKA = [
        "Kegiatan {nama_kegiatan} telah dilaksanakan pada {tanggal} bertempat di {lokasi}.",
        "Pada {tanggal}, {nama_pokja} menyelenggarakan kegiatan {nama_kegiatan} yang berlokasi di {lokasi}.",
        "Bertepatan dengan {tanggal}, telah terselenggara kegiatan {nama_kegiatan} oleh {nama_pokja} di {lokasi}.",
    ]

    PEMBUKA_TANPA_LOKASI = [
        "Kegiatan {nama_kegiatan} telah dilaksanakan pada {tanggal} oleh {nama_pokja}.",
        "Pada {tanggal}, {nama_pokja} berhasil melaksanakan kegiatan {nama_kegiatan}.",
    ]

    PESERTA_BANYAK = [
        "Kegiatan ini dihadiri oleh {peserta} peserta yang terdiri dari siswa dan anggota {nama_pokja}.",
        "Sebanyak {peserta} peserta turut berpartisipasi aktif dalam kegiatan ini.",
        "Kegiatan tersebut diikuti oleh {peserta} orang, menunjukkan antusiasme yang tinggi dari seluruh anggota.",
    ]

    PESERTA_SEDIKIT = [
        "Kegiatan ini diikuti oleh {peserta} peserta dari {nama_pokja}.",
        "Dengan {peserta} peserta yang hadir, kegiatan berlangsung secara fokus dan efektif.",
    ]

    DESKRIPSI_PREFIX = [
        "Dalam pelaksanaannya, ",
        "Secara teknis, ",
        "Adapun rangkaian kegiatan ini mencakup ",
    ]

    HASIL_POSITIF = [
        "Kegiatan ini berjalan dengan lancar dan menghasilkan {hasil}.",
        "Alhamdulillah, hasil yang dicapai adalah {hasil}.",
        "Melalui kegiatan ini, {nama_pokja} berhasil {hasil}.",
    ]

    KENDALA_ADA = [
        "Terdapat beberapa kendala dalam pelaksanaan, yaitu {kendala}. Namun hal ini tidak menghalangi jalannya kegiatan secara keseluruhan.",
        "Kegiatan ini menemui hambatan berupa {kendala}, yang ke depannya perlu menjadi bahan evaluasi bagi {nama_pokja}.",
        "Meskipun terdapat kendala {kendala}, kegiatan tetap dapat diselesaikan dengan baik berkat kerja sama seluruh peserta.",
    ]

    TANPA_KENDALA = [
        "Kegiatan berjalan dengan lancar tanpa kendala yang berarti.",
        "Tidak ditemukan hambatan signifikan dalam pelaksanaan kegiatan ini.",
    ]

    PENUTUP = [
        "Demikian laporan kegiatan {nama_kegiatan} yang dilaksanakan oleh {nama_pokja}. Diharapkan kegiatan serupa dapat terus dilaksanakan secara berkelanjutan demi mendukung program Adiwiyata sekolah.",
        "Kegiatan ini merupakan wujud nyata komitmen {nama_pokja} dalam mendukung program lingkungan sekolah. Diharapkan program ini dapat memberi dampak positif yang berkelanjutan.",
        "Laporan ini disusun sebagai bentuk pertanggungjawaban pelaksanaan kegiatan {nama_kegiatan}. Semoga hasil yang dicapai dapat menginspirasi seluruh warga sekolah untuk semakin peduli terhadap lingkungan.",
    ]

    REKOMENDASI_KENDALA = [
        "Untuk kegiatan berikutnya, perlu dipersiapkan {kendala_solusi} agar kendala serupa tidak terulang.",
        "Evaluasi akan dilakukan terhadap kendala yang muncul agar pelaksanaan berikutnya dapat lebih optimal.",
    ]


# ─── Format Helpers ───────────────────────────────────────────────────────────

NAMA_BULAN = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
    9: "September", 10: "Oktober", 11: "November", 12: "Desember",
}

HARI_ID = {
    0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis",
    4: "Jumat", 5: "Sabtu", 6: "Minggu",
}

def format_tanggal_indonesia(dt: datetime) -> str:
    """Format datetime ke string tanggal Indonesia formal."""
    hari  = HARI_ID[dt.weekday()]
    bulan = NAMA_BULAN[dt.month]
    return f"{hari}, {dt.day} {bulan} {dt.year}"


# ─── Report Generator ─────────────────────────────────────────────────────────

class AutoReportGenerator:
    """
    Generator laporan otomatis berbasis template.
    
    Cara pakai:
        gen = AutoReportGenerator()
        laporan = gen.generate(
            nama_kegiatan="Penanaman Pohon",
            nama_pokja="Pokja Penghijauan",
            tanggal=datetime.now(),
            peserta=25,
            kendala="Alat cangkul kurang",
            hasil="30 bibit berhasil ditanam"
        )
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Args:
            seed: Set seed untuk hasil konsisten (berguna untuk testing).
                  None = acak setiap kali.
        """
        if seed is not None:
            random.seed(seed)

    def _pick(self, templates: list, **kwargs) -> str:
        """Pilih template acak dan isi dengan variabel."""
        template = random.choice(templates)
        try:
            return template.format(**kwargs)
        except KeyError:
            # Fallback: return template tanpa format
            return template

    def generate(
        self,
        nama_kegiatan        : str,
        nama_pokja           : str,
        tanggal              : datetime,
        peserta              : int,
        lokasi               : Optional[str] = None,
        deskripsi_kegiatan   : Optional[str] = None,
        kendala              : Optional[str] = None,
        hasil                : Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Generate laporan kegiatan otomatis.
        
        Returns:
            Dict berisi:
            - judul: judul laporan
            - konten: isi laporan dalam paragraf
            - metadata: info tambahan
        """
        tanggal_str = format_tanggal_indonesia(tanggal)
        ctx = dict(
            nama_kegiatan = nama_kegiatan,
            nama_pokja    = nama_pokja,
            tanggal       = tanggal_str,
            lokasi        = lokasi or "sekolah",
            peserta       = peserta,
        )

        paragraphs = []

        # ── 1. Pembuka ──────────────────────────────────────────────────────
        if lokasi:
            paragraphs.append(self._pick(ReportTemplates.PEMBUKA, **ctx))
        else:
            paragraphs.append(self._pick(ReportTemplates.PEMBUKA_TANPA_LOKASI, **ctx))

        # ── 2. Peserta ──────────────────────────────────────────────────────
        if peserta >= 20:
            paragraphs.append(self._pick(ReportTemplates.PESERTA_BANYAK, **ctx))
        else:
            paragraphs.append(self._pick(ReportTemplates.PESERTA_SEDIKIT, **ctx))

        # ── 3. Deskripsi Kegiatan (jika ada) ────────────────────────────────
        if deskripsi_kegiatan:
            prefix = self._pick(ReportTemplates.DESKRIPSI_PREFIX)
            # Pastikan deskripsi diawali huruf kecil setelah prefix
            desc_clean = deskripsi_kegiatan.strip()
            if desc_clean and desc_clean[0].isupper() and prefix.endswith((" ", "\n")):
                desc_clean = desc_clean[0].lower() + desc_clean[1:]
            paragraphs.append(f"{prefix}{desc_clean}.")

        # ── 4. Kendala ──────────────────────────────────────────────────────
        if kendala and kendala.strip():
            paragraphs.append(self._pick(
                ReportTemplates.KENDALA_ADA,
                kendala=kendala.lower(), **ctx
            ))
        else:
            paragraphs.append(self._pick(ReportTemplates.TANPA_KENDALA))

        # ── 5. Hasil ────────────────────────────────────────────────────────
        if hasil and hasil.strip():
            paragraphs.append(self._pick(
                ReportTemplates.HASIL_POSITIF,
                hasil=hasil.lower(), **ctx
            ))

        # ── 6. Penutup ──────────────────────────────────────────────────────
        paragraphs.append(self._pick(ReportTemplates.PENUTUP, **ctx))

        konten = "\n\n".join(paragraphs)

        judul = (
            f"Laporan Kegiatan {nama_kegiatan} — {nama_pokja} "
            f"({tanggal.strftime('%d/%m/%Y')})"
        )

        return {
            "judul"   : judul,
            "konten"  : konten,
            "template": "standard_v1",
            "metadata": {
                "generated_at"  : datetime.now().isoformat(),
                "peserta"       : peserta,
                "has_kendala"   : bool(kendala and kendala.strip()),
                "has_hasil"     : bool(hasil and hasil.strip()),
                "paragraph_count": len(paragraphs),
            }
        }

    def generate_summary(self, kegiatan_list: list, pokja_nama: str) -> str:
        """
        Generate ringkasan bulanan untuk satu Pokja.
        
        Args:
            kegiatan_list: list dict [{judul, tanggal, status, peserta}, ...]
            pokja_nama: nama Pokja
        
        Returns:
            String paragraf ringkasan
        """
        total    = len(kegiatan_list)
        done     = sum(1 for k in kegiatan_list if k.get("status") == "done")
        total_p  = sum(k.get("jumlah_peserta", 0) for k in kegiatan_list)
        avg_p    = int(total_p / total) if total > 0 else 0

        lines = [
            f"Ringkasan aktivitas {pokja_nama} mencatat total {total} kegiatan "
            f"dalam periode ini, dengan {done} kegiatan berhasil diselesaikan.",
        ]
        if avg_p > 0:
            lines.append(
                f"Rata-rata peserta per kegiatan adalah {avg_p} orang, "
                "menunjukkan partisipasi yang aktif dari seluruh anggota."
            )
        if total - done > 0:
            lines.append(
                f"Sebanyak {total - done} kegiatan masih dalam proses atau belum selesai "
                "dan memerlukan tindak lanjut."
            )
        return " ".join(lines)


# ─── Quick-use function ───────────────────────────────────────────────────────

def generate_laporan(
    nama_kegiatan      : str,
    nama_pokja         : str,
    tanggal            : datetime,
    peserta            : int,
    lokasi             : Optional[str] = None,
    deskripsi_kegiatan : Optional[str] = None,
    kendala            : Optional[str] = None,
    hasil              : Optional[str] = None,
) -> Dict:
    """Shortcut function untuk generate laporan tanpa instansiasi class."""
    gen = AutoReportGenerator()
    return gen.generate(
        nama_kegiatan       = nama_kegiatan,
        nama_pokja          = nama_pokja,
        tanggal             = tanggal,
        peserta             = peserta,
        lokasi              = lokasi,
        deskripsi_kegiatan  = deskripsi_kegiatan,
        kendala             = kendala,
        hasil               = hasil,
    )
