"""
EcoTrack AI - AI Behavior Analysis Service
=========================================
Komponen intisistem EcoTrack.

Menganalisis pola aktivitas setiap Pokja menggunakan:
- Pandas untuk agregasi & time-series
- Scikit-learn untuk clustering sederhana
- Rule-based scoring untuk transparansi hasil

Output:
- Skor performa tiap Pokja (0–100)
- Label aktifitas ("Sangat Aktif", "Aktif", "Kurang Aktif", "Tidak Aktif")
- Insight tekstual otomatis dalam Bahasa Indonesia
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session

try:
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from app.models.database import Pokja, Kegiatan, SkorPokja


# ─── Konstanta ────────────────────────────────────────────────────────────────

LABEL_THRESHOLDS = {
    "Sangat Aktif" : (80, 100),
    "Aktif"        : (60, 80),
    "Cukup Aktif"  : (40, 60),
    "Kurang Aktif" : (20, 40),
    "Tidak Aktif"  : (0,  20),
}

WEIGHT = {
    "frekuensi"    : 0.30,
    "konsistensi"  : 0.30,
    "penyelesaian" : 0.25,
    "partisipasi"  : 0.15,
}

LOOKBACK_DAYS = 90   # rentang analisis default (3 bulan)
WEEK_LOOKBACK = 2    # untuk deteksi "mati" mingguan


# ─── Core Analysis ────────────────────────────────────────────────────────────

class BehaviorAnalyzer:
    """
    Mesin analisis perilaku Pokja.
    
    Cara pakai:
        analyzer = BehaviorAnalyzer(db_session)
        results  = analyzer.analyze_all()
    """

    def __init__(self, db: Session, lookback_days: int = LOOKBACK_DAYS):
        self.db           = db
        self.lookback_days = lookback_days
        self.cutoff_date  = datetime.now() - timedelta(days=lookback_days)
        self._df          = None   # di-cache setelah load pertama

    # ── Data Loading ──────────────────────────────────────────────────────────

    def _load_dataframe(self) -> pd.DataFrame:
        """Load semua kegiatan dari DB ke Pandas DataFrame."""
        if self._df is not None:
            return self._df

        rows = (
            self.db.query(
                Kegiatan.id,
                Kegiatan.pokja_id,
                Kegiatan.tanggal,
                Kegiatan.status,
                Kegiatan.jumlah_peserta,
                Pokja.nama.label("pokja_nama"),
            )
            .join(Pokja, Kegiatan.pokja_id == Pokja.id)
            .filter(Kegiatan.tanggal >= self.cutoff_date)
            .all()
        )

        if not rows:
            return pd.DataFrame(columns=[
                "id", "pokja_id", "tanggal", "status",
                "jumlah_peserta", "pokja_nama"
            ])

        self._df = pd.DataFrame(rows, columns=[
            "id", "pokja_id", "tanggal", "status",
            "jumlah_peserta", "pokja_nama"
        ])
        self._df["tanggal"] = pd.to_datetime(self._df["tanggal"])
        self._df["minggu"]  = self._df["tanggal"].dt.to_period("W")
        return self._df

    # ── Individual Scoring ────────────────────────────────────────────────────

    def _score_frekuensi(self, pokja_df: pd.DataFrame, total_weeks: int) -> float:
        """
        Skor frekuensi: seberapa sering Pokja melakukan kegiatan.
        Target ideal = minimal 1 kegiatan per 2 minggu.
        """
        n_kegiatan = len(pokja_df)
        target     = total_weeks / 2
        raw        = min(n_kegiatan / max(target, 1), 1.0)
        return round(raw * 100, 2)

    def _score_konsistensi(self, pokja_df: pd.DataFrame, all_weeks: pd.PeriodIndex) -> float:
        """
        Skor konsistensi: seberapa merata Pokja aktif tiap minggu.
        Pokja yang absen lama akan mendapat skor rendah.
        """
        if pokja_df.empty:
            return 0.0

        minggu_aktif    = set(pokja_df["minggu"].unique())
        total_weeks     = len(all_weeks)
        minggu_hadir    = sum(1 for w in all_weeks if w in minggu_aktif)

        # Penalty untuk gap mingguan terpanjang
        weeks_list      = sorted(pokja_df["minggu"].unique())
        max_gap         = 0
        for i in range(1, len(weeks_list)):
            gap = (weeks_list[i] - weeks_list[i-1]).n
            if gap > max_gap:
                max_gap = gap

        base_score  = (minggu_hadir / max(total_weeks, 1)) * 100
        gap_penalty = min(max_gap * 3, 30)    # max penalti 30 poin
        return round(max(base_score - gap_penalty, 0), 2)

    def _score_penyelesaian(self, pokja_df: pd.DataFrame) -> float:
        """
        Skor penyelesaian: persentase kegiatan yang benar-benar selesai (status=done).
        """
        if pokja_df.empty:
            return 0.0
        n_done  = (pokja_df["status"] == "done").sum()
        return round((n_done / len(pokja_df)) * 100, 2)

    def _score_partisipasi(self, pokja_df: pd.DataFrame, global_avg: float) -> float:
        """
        Skor partisipasi: rata-rata peserta dibandingkan rata-rata global.
        """
        if pokja_df.empty or global_avg == 0:
            return 0.0
        local_avg = pokja_df["jumlah_peserta"].mean()
        ratio     = local_avg / global_avg
        return round(min(ratio * 70, 100), 2)   # cap 100, base 70 = rata-rata

    def _get_label(self, skor: float) -> str:
        for label, (lo, hi) in LABEL_THRESHOLDS.items():
            if lo <= skor <= hi:
                return label
        return "Tidak Aktif"

    # ── Insight Generator ─────────────────────────────────────────────────────

    def _generate_insight(
        self,
        nama         : str,
        skor         : float,
        label        : str,
        n_kegiatan   : int,
        n_done       : int,
        konsistensi  : float,
        last_activity: Optional[datetime],
        weeks_inactive: int,
    ) -> str:
        """
        Generate kalimat insight dalam Bahasa Indonesia
        berdasarkan kondisi Pokja.
        """
        parts = []

        # Status utama
        if label == "Sangat Aktif":
            parts.append(f"{nama} menunjukkan performa luar biasa dengan skor {skor:.0f}/100.")
        elif label == "Aktif":
            parts.append(f"{nama} berjalan dengan baik (skor {skor:.0f}/100).")
        elif label == "Cukup Aktif":
            parts.append(f"{nama} cukup aktif namun masih ada ruang peningkatan (skor {skor:.0f}/100).")
        elif label == "Kurang Aktif":
            parts.append(f"⚠️ {nama} perlu perhatian — aktivitas di bawah rata-rata (skor {skor:.0f}/100).")
        else:
            parts.append(f"🚨 {nama} tidak aktif dalam periode analisis (skor {skor:.0f}/100).")

        # Penyelesaian kegiatan
        if n_kegiatan > 0:
            pct = (n_done / n_kegiatan) * 100
            if pct == 100:
                parts.append(f"Semua {n_kegiatan} kegiatan berhasil diselesaikan — sangat konsisten!")
            elif pct >= 70:
                parts.append(f"{n_done} dari {n_kegiatan} kegiatan selesai ({pct:.0f}%).")
            else:
                parts.append(f"Hanya {n_done} dari {n_kegiatan} kegiatan yang selesai ({pct:.0f}%) — perlu ditingkatkan.")

        # Konsistensi mingguan
        if konsistensi < 30:
            parts.append("Konsistensi mingguan sangat rendah — ada gap aktivitas yang panjang.")
        elif konsistensi >= 70:
            parts.append("Konsistensi mingguan sangat baik — aktivitas terdistribusi merata.")

        # Deteksi non-aktif terakhir
        if weeks_inactive >= 2:
            parts.append(f"Tidak ada kegiatan dalam {weeks_inactive} minggu terakhir — segera tindak lanjuti!")
        elif last_activity:
            days_since = (datetime.now() - last_activity).days
            if days_since <= 7:
                parts.append("Terakhir aktif minggu ini — pertahankan momentum!")

        return " ".join(parts)

    # ── Weeks Inactive Detector ───────────────────────────────────────────────

    def _weeks_inactive(self, pokja_df: pd.DataFrame) -> int:
        """Hitung berapa minggu terakhir Pokja tidak ada kegiatan."""
        if pokja_df.empty:
            return int(self.lookback_days / 7)
        latest  = pokja_df["tanggal"].max()
        delta   = datetime.now() - latest.to_pydatetime()
        return max(int(delta.days / 7), 0)

    # ── Main Analysis ─────────────────────────────────────────────────────────

    def analyze_pokja(self, pokja_id: int) -> Dict:
        """Analisis satu Pokja secara mendetail."""
        df         = self._load_dataframe()
        pokja_obj  = self.db.query(Pokja).filter(Pokja.id == pokja_id).first()
        if not pokja_obj:
            raise ValueError(f"Pokja dengan id={pokja_id} tidak ditemukan.")

        pokja_df   = df[df["pokja_id"] == pokja_id].copy()
        all_weeks  = pd.period_range(
            start=self.cutoff_date, end=datetime.now(), freq="W"
        )
        total_weeks    = len(all_weeks)
        global_avg_peserta = df["jumlah_peserta"].mean() if not df.empty else 0

        s_frek  = self._score_frekuensi(pokja_df, total_weeks)
        s_kons  = self._score_konsistensi(pokja_df, all_weeks)
        s_seles = self._score_penyelesaian(pokja_df)
        s_parti = self._score_partisipasi(pokja_df, global_avg_peserta)

        skor_total = (
            s_frek  * WEIGHT["frekuensi"]    +
            s_kons  * WEIGHT["konsistensi"]  +
            s_seles * WEIGHT["penyelesaian"] +
            s_parti * WEIGHT["partisipasi"]
        )
        skor_total = round(min(skor_total, 100), 2)
        label      = self._get_label(skor_total)

        n_kegiatan   = len(pokja_df)
        n_done       = int((pokja_df["status"] == "done").sum()) if not pokja_df.empty else 0
        last_activity= pokja_df["tanggal"].max().to_pydatetime() if not pokja_df.empty else None
        weeks_inactive = self._weeks_inactive(pokja_df)

        insight = self._generate_insight(
            pokja_obj.nama, skor_total, label,
            n_kegiatan, n_done, s_kons, last_activity, weeks_inactive
        )

        return {
            "pokja_id"          : pokja_id,
            "pokja_nama"        : pokja_obj.nama,
            "skor_total"        : skor_total,
            "skor_frekuensi"    : s_frek,
            "skor_konsistensi"  : s_kons,
            "skor_penyelesaian" : s_seles,
            "skor_partisipasi"  : s_parti,
            "label"             : label,
            "insight"           : insight,
            "n_kegiatan"        : n_kegiatan,
            "weeks_inactive"    : weeks_inactive,
        }

    def analyze_all(self) -> List[Dict]:
        """Analisis semua Pokja, urutkan berdasarkan skor."""
        pokja_list = self.db.query(Pokja).filter(Pokja.status != "archived").all()
        results    = []
        for p in pokja_list:
            try:
                r = self.analyze_pokja(p.id)
                results.append(r)
            except Exception as e:
                results.append({
                    "pokja_id"   : p.id,
                    "pokja_nama" : p.nama,
                    "skor_total" : 0.0,
                    "label"      : "Error",
                    "insight"    : f"Gagal menganalisis: {str(e)}",
                    "error"      : True,
                })

        results.sort(key=lambda x: x["skor_total"], reverse=True)
        return results

    def save_scores(self, results: List[Dict]) -> None:
        """Simpan hasil scoring ke tabel skor_pokja."""
        for r in results:
            existing = (
                self.db.query(SkorPokja)
                .filter(SkorPokja.pokja_id == r["pokja_id"])
                .first()
            )
            if existing:
                existing.skor_total        = r.get("skor_total", 0)
                existing.skor_frekuensi    = r.get("skor_frekuensi", 0)
                existing.skor_konsistensi  = r.get("skor_konsistensi", 0)
                existing.skor_penyelesaian = r.get("skor_penyelesaian", 0)
                existing.skor_partisipasi  = r.get("skor_partisipasi", 0)
                existing.label             = r.get("label", "")
                existing.insight           = r.get("insight", "")
                existing.calculated_at     = datetime.now()
            else:
                new_skor = SkorPokja(
                    pokja_id          = r["pokja_id"],
                    skor_total        = r.get("skor_total", 0),
                    skor_frekuensi    = r.get("skor_frekuensi", 0),
                    skor_konsistensi  = r.get("skor_konsistensi", 0),
                    skor_penyelesaian = r.get("skor_penyelesaian", 0),
                    skor_partisipasi  = r.get("skor_partisipasi", 0),
                    label             = r.get("label", ""),
                    insight           = r.get("insight", ""),
                )
                self.db.add(new_skor)
        self.db.commit()

    def generate_global_insights(self, results: List[Dict]) -> List[str]:
        """
        Generate daftar insight global dari semua hasil analisis.
        Digunakan di dashboard utama.
        """
        if not results:
            return ["Belum ada data kegiatan yang cukup untuk dianalisis."]

        insights = []
        active   = [r for r in results if r.get("skor_total", 0) >= 60]
        inactive = [r for r in results if r.get("weeks_inactive", 0) >= WEEK_LOOKBACK]

        if active:
            top = active[0]["pokja_nama"]
            insights.append(f"🏆 {top} adalah Pokja paling aktif saat ini.")

        if len(active) > 1:
            aktif_names = ", ".join(r["pokja_nama"] for r in active[:3])
            insights.append(f"✅ Pokja dengan performa baik: {aktif_names}.")

        if inactive:
            mati_names = ", ".join(r["pokja_nama"] for r in inactive[:3])
            insights.append(
                f"⚠️ Pokja tidak aktif ≥{WEEK_LOOKBACK} minggu: {mati_names} — perlu follow-up segera."
            )

        avg_skor = sum(r.get("skor_total", 0) for r in results) / len(results)
        insights.append(f"📊 Rata-rata skor performa seluruh Pokja: {avg_skor:.1f}/100.")

        low_completion = [
            r for r in results
            if r.get("skor_penyelesaian", 100) < 50 and r.get("n_kegiatan", 0) > 0
        ]
        if low_completion:
            names = ", ".join(r["pokja_nama"] for r in low_completion)
            insights.append(f"📝 Pokja dengan tingkat penyelesaian rendah: {names} — cek status kegiatan.")

        return insights


# ─── Clustering (optional, butuh scikit-learn) ────────────────────────────────

def cluster_pokja(results: List[Dict], n_clusters: int = 3) -> List[Dict]:
    """
    Gunakan K-Means untuk mengelompokkan Pokja ke dalam cluster performa.
    Dijalankan hanya jika scikit-learn tersedia dan data cukup.
    """
    if not SKLEARN_AVAILABLE or len(results) < n_clusters:
        return results

    features = np.array([
        [
            r.get("skor_frekuensi", 0),
            r.get("skor_konsistensi", 0),
            r.get("skor_penyelesaian", 0),
        ]
        for r in results
    ])

    scaler   = MinMaxScaler()
    scaled   = scaler.fit_transform(features)
    kmeans   = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels   = kmeans.fit_predict(scaled)

    cluster_names = {
        0: "Kelompok Performa Tinggi",
        1: "Kelompok Performa Sedang",
        2: "Kelompok Performa Rendah",
    }

    # Sort cluster by center scores
    centers  = kmeans.cluster_centers_
    order    = np.argsort(-centers[:, 0])  # sort by frekuensi desc
    remap    = {int(order[i]): i for i in range(n_clusters)}

    for i, r in enumerate(results):
        cluster_idx    = int(labels[i])
        remapped       = remap[cluster_idx]
        r["cluster"]   = remapped
        r["cluster_name"] = cluster_names.get(remapped, f"Cluster {remapped}")

    return results
