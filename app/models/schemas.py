"""
EcoTrack AI - Pydantic Schemas
Request & Response validation models
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class StatusKegiatanSchema(str, Enum):
    PLANNED   = "planned"
    ONGOING   = "ongoing"
    DONE      = "done"
    CANCELLED = "cancelled"


# ─── Pokja Schemas ────────────────────────────────────────────────────────────

class PokjaCreate(BaseModel):
    nama      : str = Field(..., min_length=2, max_length=100, example="Pokja Penghijauan")
    deskripsi : Optional[str] = Field(None, example="Kelompok kerja bidang penghijauan sekolah")
    ketua     : Optional[str] = Field(None, example="Budi Santoso")
    warna     : Optional[str] = Field("#4CAF50", example="#4CAF50")

class PokjaUpdate(BaseModel):
    nama      : Optional[str] = None
    deskripsi : Optional[str] = None
    ketua     : Optional[str] = None
    status    : Optional[str] = None
    warna     : Optional[str] = None

class PokjaResponse(BaseModel):
    id         : int
    nama       : str
    deskripsi  : Optional[str]
    ketua      : Optional[str]
    status     : str
    warna      : str
    created_at : datetime

    class Config:
        from_attributes = True


# ─── Kegiatan Schemas ─────────────────────────────────────────────────────────

class KegiatanCreate(BaseModel):
    pokja_id       : int
    judul          : str = Field(..., min_length=3, max_length=200)
    deskripsi      : Optional[str] = None
    tanggal        : datetime
    lokasi         : Optional[str] = None
    jumlah_peserta : Optional[int] = Field(0, ge=0)
    kendala        : Optional[str] = None
    hasil          : Optional[str] = None
    status         : StatusKegiatanSchema = StatusKegiatanSchema.PLANNED

    class Config:
        json_schema_extra = {
            "example": {
                "pokja_id": 1,
                "judul": "Penanaman Pohon Perindang",
                "tanggal": "2025-04-10T08:00:00",
                "lokasi": "Taman Sekolah Belakang",
                "jumlah_peserta": 25,
                "kendala": "Alat cangkul kurang",
                "status": "done"
            }
        }

class KegiatanUpdate(BaseModel):
    judul          : Optional[str] = None
    deskripsi      : Optional[str] = None
    tanggal        : Optional[datetime] = None
    lokasi         : Optional[str] = None
    jumlah_peserta : Optional[int] = None
    kendala        : Optional[str] = None
    hasil          : Optional[str] = None
    status         : Optional[StatusKegiatanSchema] = None

class KegiatanResponse(BaseModel):
    id             : int
    pokja_id       : int
    judul          : str
    deskripsi      : Optional[str]
    tanggal        : datetime
    lokasi         : Optional[str]
    jumlah_peserta : int
    kendala        : Optional[str]
    hasil          : Optional[str]
    status         : str
    created_at     : datetime

    class Config:
        from_attributes = True


# ─── Laporan Schemas ──────────────────────────────────────────────────────────

class LaporanGenerateRequest(BaseModel):
    """Input dari user untuk generate laporan otomatis."""
    kegiatan_id    : int
    nama_kegiatan  : str = Field(..., example="Penanaman Pohon")
    tanggal        : datetime
    lokasi         : Optional[str] = Field(None, example="Taman Belakang Sekolah")
    peserta        : int = Field(..., ge=0, example=25)
    deskripsi_kegiatan : Optional[str] = Field(None, example="Kegiatan menanam pohon perindang")
    kendala        : Optional[str] = Field(None, example="Kekurangan alat cangkul")
    hasil          : Optional[str] = Field(None, example="30 bibit berhasil ditanam")
    nama_pokja     : str = Field(..., example="Pokja Penghijauan")

class LaporanResponse(BaseModel):
    id               : int
    kegiatan_id      : Optional[int]
    pokja_id         : int
    judul            : str
    konten           : str
    is_auto_generated: bool
    created_at       : datetime

    class Config:
        from_attributes = True


# ─── Analytics Schemas ────────────────────────────────────────────────────────

class SkorPokjaResponse(BaseModel):
    pokja_id          : int
    pokja_nama        : str
    skor_total        : float
    skor_frekuensi    : float
    skor_konsistensi  : float
    skor_penyelesaian : float
    skor_partisipasi  : float
    label             : str
    insight           : Optional[str]
    calculated_at     : datetime

    class Config:
        from_attributes = True

class DashboardResponse(BaseModel):
    total_pokja          : int
    total_kegiatan       : int
    kegiatan_bulan_ini   : int
    pokja_teraktif       : Optional[str]
    pokja_perlu_perhatian: Optional[str]
    ranking_pokja        : List[SkorPokjaResponse]
    insight_global       : List[str]

class InsightResponse(BaseModel):
    pokja_id   : int
    pokja_nama : str
    insights   : List[str]
    label      : str
    skor       : float
