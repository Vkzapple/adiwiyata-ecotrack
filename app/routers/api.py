"""
EcoTrack AI - API Routers
Semua endpoint FastAPI diorganisir per domain.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.models.database import get_db, Pokja, Kegiatan, Laporan, SkorPokja
from app.models.schemas import (
    PokjaCreate, PokjaUpdate, PokjaResponse,
    KegiatanCreate, KegiatanUpdate, KegiatanResponse,
    LaporanGenerateRequest, LaporanResponse,
    SkorPokjaResponse, DashboardResponse, InsightResponse,
)
from app.services.behavior_analysis import BehaviorAnalyzer, cluster_pokja
from app.services.report_generator import generate_laporan


# ═══════════════════════════════════════════════════════════════════════════════
# POKJA ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

router_pokja = APIRouter(prefix="/pokja", tags=["Pokja"])

@router_pokja.post("/", response_model=PokjaResponse, status_code=201)
def create_pokja(payload: PokjaCreate, db: Session = Depends(get_db)):
    """Buat Pokja baru."""
    existing = db.query(Pokja).filter(Pokja.nama == payload.nama).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Pokja '{payload.nama}' sudah ada.")

    pokja = Pokja(**payload.model_dump())
    db.add(pokja)
    db.commit()
    db.refresh(pokja)
    return pokja

@router_pokja.get("/", response_model=List[PokjaResponse])
def list_pokja(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Ambil semua Pokja (opsional filter status)."""
    q = db.query(Pokja)
    if status:
        q = q.filter(Pokja.status == status)
    return q.order_by(Pokja.nama).all()

@router_pokja.get("/{pokja_id}", response_model=PokjaResponse)
def get_pokja(pokja_id: int, db: Session = Depends(get_db)):
    """Ambil detail satu Pokja."""
    pokja = db.query(Pokja).filter(Pokja.id == pokja_id).first()
    if not pokja:
        raise HTTPException(status_code=404, detail="Pokja tidak ditemukan.")
    return pokja

@router_pokja.put("/{pokja_id}", response_model=PokjaResponse)
def update_pokja(pokja_id: int, payload: PokjaUpdate, db: Session = Depends(get_db)):
    """Update data Pokja."""
    pokja = db.query(Pokja).filter(Pokja.id == pokja_id).first()
    if not pokja:
        raise HTTPException(status_code=404, detail="Pokja tidak ditemukan.")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(pokja, field, value)

    db.commit()
    db.refresh(pokja)
    return pokja

@router_pokja.delete("/{pokja_id}", status_code=204)
def delete_pokja(pokja_id: int, db: Session = Depends(get_db)):
    """Hapus Pokja (soft delete: ubah ke archived)."""
    pokja = db.query(Pokja).filter(Pokja.id == pokja_id).first()
    if not pokja:
        raise HTTPException(status_code=404, detail="Pokja tidak ditemukan.")
    pokja.status = "archived"
    db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# KEGIATAN ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

router_kegiatan = APIRouter(prefix="/kegiatan", tags=["Kegiatan"])

@router_kegiatan.post("/", response_model=KegiatanResponse, status_code=201)
def create_kegiatan(payload: KegiatanCreate, db: Session = Depends(get_db)):
    """Input kegiatan baru."""
    # Validasi pokja exist
    pokja = db.query(Pokja).filter(Pokja.id == payload.pokja_id).first()
    if not pokja:
        raise HTTPException(status_code=404, detail="Pokja tidak ditemukan.")

    kegiatan = Kegiatan(**payload.model_dump())
    db.add(kegiatan)
    db.commit()
    db.refresh(kegiatan)
    return kegiatan

@router_kegiatan.get("/", response_model=List[KegiatanResponse])
def list_kegiatan(
    pokja_id : Optional[int] = None,
    status   : Optional[str] = None,
    limit    : int = 50,
    offset   : int = 0,
    db       : Session = Depends(get_db),
):
    """Ambil daftar kegiatan dengan filter opsional."""
    q = db.query(Kegiatan)
    if pokja_id:
        q = q.filter(Kegiatan.pokja_id == pokja_id)
    if status:
        q = q.filter(Kegiatan.status == status)
    return q.order_by(Kegiatan.tanggal.desc()).offset(offset).limit(limit).all()

@router_kegiatan.get("/{kegiatan_id}", response_model=KegiatanResponse)
def get_kegiatan(kegiatan_id: int, db: Session = Depends(get_db)):
    """Ambil detail satu kegiatan."""
    k = db.query(Kegiatan).filter(Kegiatan.id == kegiatan_id).first()
    if not k:
        raise HTTPException(status_code=404, detail="Kegiatan tidak ditemukan.")
    return k

@router_kegiatan.put("/{kegiatan_id}", response_model=KegiatanResponse)
def update_kegiatan(
    kegiatan_id: int,
    payload: KegiatanUpdate,
    db: Session = Depends(get_db)
):
    """Update data kegiatan."""
    k = db.query(Kegiatan).filter(Kegiatan.id == kegiatan_id).first()
    if not k:
        raise HTTPException(status_code=404, detail="Kegiatan tidak ditemukan.")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(k, field, value)

    db.commit()
    db.refresh(k)
    return k

@router_kegiatan.delete("/{kegiatan_id}", status_code=204)
def delete_kegiatan(kegiatan_id: int, db: Session = Depends(get_db)):
    """Hapus kegiatan."""
    k = db.query(Kegiatan).filter(Kegiatan.id == kegiatan_id).first()
    if not k:
        raise HTTPException(status_code=404, detail="Kegiatan tidak ditemukan.")
    db.delete(k)
    db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# LAPORAN ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

router_laporan = APIRouter(prefix="/laporan", tags=["Laporan"])

@router_laporan.post("/generate", response_model=LaporanResponse, status_code=201)
def generate_report(payload: LaporanGenerateRequest, db: Session = Depends(get_db)):
    """
    Generate laporan otomatis dari input user.
    Sistem akan mengisi paragraf laporan secara otomatis.
    """
    # Ambil pokja dari kegiatan
    kegiatan = db.query(Kegiatan).filter(Kegiatan.id == payload.kegiatan_id).first()
    if not kegiatan:
        raise HTTPException(status_code=404, detail="Kegiatan tidak ditemukan.")

    # Cek apakah laporan sudah ada
    existing = db.query(Laporan).filter(Laporan.kegiatan_id == payload.kegiatan_id).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Laporan untuk kegiatan ini sudah ada (id={existing.id}). "
                   "Gunakan PUT untuk update."
        )

    # Generate konten
    result = generate_laporan(
        nama_kegiatan       = payload.nama_kegiatan,
        nama_pokja          = payload.nama_pokja,
        tanggal             = payload.tanggal,
        peserta             = payload.peserta,
        lokasi              = payload.lokasi,
        deskripsi_kegiatan  = payload.deskripsi_kegiatan,
        kendala             = payload.kendala,
        hasil               = payload.hasil,
    )

    laporan = Laporan(
        kegiatan_id       = payload.kegiatan_id,
        pokja_id          = kegiatan.pokja_id,
        judul             = result["judul"],
        konten            = result["konten"],
        template_used     = result["template"],
        is_auto_generated = True,
    )
    db.add(laporan)
    db.commit()
    db.refresh(laporan)
    return laporan

@router_laporan.get("/", response_model=List[LaporanResponse])
def list_laporan(
    pokja_id: Optional[int] = None,
    limit   : int = 20,
    db      : Session = Depends(get_db)
):
    """Ambil daftar laporan."""
    q = db.query(Laporan)
    if pokja_id:
        q = q.filter(Laporan.pokja_id == pokja_id)
    return q.order_by(Laporan.created_at.desc()).limit(limit).all()

@router_laporan.get("/{laporan_id}", response_model=LaporanResponse)
def get_laporan(laporan_id: int, db: Session = Depends(get_db)):
    """Ambil satu laporan."""
    l = db.query(Laporan).filter(Laporan.id == laporan_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan.")
    return l


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYTICS ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

router_analytics = APIRouter(prefix="/analytics", tags=["Analytics & AI"])

@router_analytics.post("/recalculate")
def recalculate_scores(db: Session = Depends(get_db)):
    """
    Trigger ulang kalkulasi skor semua Pokja.
    Jalankan setelah ada input kegiatan baru.
    """
    analyzer = BehaviorAnalyzer(db)
    results  = analyzer.analyze_all()
    analyzer.save_scores(results)
    return {
        "status" : "success",
        "message": f"Skor {len(results)} Pokja berhasil diperbarui.",
        "results": results,
    }

@router_analytics.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)):
    """
    Ambil data lengkap untuk dashboard utama.
    Termasuk ranking Pokja, insight global, dan statistik kegiatan.
    """
    analyzer = BehaviorAnalyzer(db)
    results  = analyzer.analyze_all()
    analyzer.save_scores(results)
    insights = analyzer.generate_global_insights(results)

    now   = datetime.now()
    bulan_ini_kegiatan = (
        db.query(Kegiatan)
        .filter(
            Kegiatan.tanggal >= datetime(now.year, now.month, 1)
        )
        .count()
    )

    active_results   = [r for r in results if r.get("skor_total", 0) >= 60]
    inactive_results = [r for r in results if r.get("skor_total", 0) < 40]

    # Build skor response list
    skor_list = []
    for r in results:
        skor_obj = db.query(SkorPokja).filter(SkorPokja.pokja_id == r["pokja_id"]).first()
        if skor_obj:
            skor_list.append(SkorPokjaResponse(
                pokja_id          = r["pokja_id"],
                pokja_nama        = r["pokja_nama"],
                skor_total        = r["skor_total"],
                skor_frekuensi    = r.get("skor_frekuensi", 0),
                skor_konsistensi  = r.get("skor_konsistensi", 0),
                skor_penyelesaian = r.get("skor_penyelesaian", 0),
                skor_partisipasi  = r.get("skor_partisipasi", 0),
                label             = r["label"],
                insight           = r.get("insight"),
                calculated_at     = skor_obj.calculated_at,
            ))

    return DashboardResponse(
        total_pokja           = db.query(Pokja).filter(Pokja.status != "archived").count(),
        total_kegiatan        = db.query(Kegiatan).count(),
        kegiatan_bulan_ini    = bulan_ini_kegiatan,
        pokja_teraktif        = active_results[0]["pokja_nama"] if active_results else None,
        pokja_perlu_perhatian = inactive_results[0]["pokja_nama"] if inactive_results else None,
        ranking_pokja         = skor_list,
        insight_global        = insights,
    )

@router_analytics.get("/pokja/{pokja_id}/insight", response_model=InsightResponse)
def get_pokja_insight(pokja_id: int, db: Session = Depends(get_db)):
    """
    Dapatkan insight AI mendalam untuk satu Pokja.
    Menampilkan analisis aktivitas, konsistensi, dan rekomendasi.
    """
    analyzer = BehaviorAnalyzer(db)
    try:
        result = analyzer.analyze_pokja(pokja_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return InsightResponse(
        pokja_id   = pokja_id,
        pokja_nama = result["pokja_nama"],
        insights   = [result["insight"]],
        label      = result["label"],
        skor       = result["skor_total"],
    )

@router_analytics.get("/ranking")
def get_ranking(
    with_cluster: bool = False,
    db: Session = Depends(get_db)
):
    """
    Ranking semua Pokja berdasarkan skor performa.
    Set with_cluster=true untuk tambahan segmentasi K-Means.
    """
    analyzer = BehaviorAnalyzer(db)
    results  = analyzer.analyze_all()

    if with_cluster:
        results = cluster_pokja(results)

    return {
        "generated_at": datetime.now().isoformat(),
        "ranking"     : results,
    }
