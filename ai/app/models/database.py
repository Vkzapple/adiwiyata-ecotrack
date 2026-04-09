

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime,
    Float, Boolean, ForeignKey, Enum
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func
import enum
from datetime import datetime

Base = declarative_base()

# ─── Enums ────────────────────────────────────────────────────────────────────

class StatusKegiatan(str, enum.Enum):
    PLANNED    = "planned"
    ONGOING    = "ongoing"
    DONE       = "done"
    CANCELLED  = "cancelled"

class StatusPokja(str, enum.Enum):
    ACTIVE   = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"

# ─── Tables ───────────────────────────────────────────────────────────────────

class Pokja(Base):
    """
    Kelompok Kerja (Working Group) dalam program Adiwiyata.
    Contoh: Pokja Penghijauan, Pokja Hidroponik, Pokja Energi, dll.
    """
    __tablename__ = "pokja"

    id          = Column(Integer, primary_key=True, index=True)
    nama        = Column(String(100), nullable=False, unique=True)
    deskripsi   = Column(Text, nullable=True)
    ketua       = Column(String(100), nullable=True)
    status      = Column(String(20), default=StatusPokja.ACTIVE)
    warna       = Column(String(7), default="#4CAF50")  # hex color untuk UI
    created_at  = Column(DateTime, default=func.now())
    updated_at  = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    kegiatan    = relationship("Kegiatan", back_populates="pokja", cascade="all, delete-orphan")
    laporan     = relationship("Laporan",  back_populates="pokja", cascade="all, delete-orphan")
    skor        = relationship("SkorPokja", back_populates="pokja", uselist=False)

    def __repr__(self):
        return f"<Pokja(id={self.id}, nama='{self.nama}', status='{self.status}')>"


class Kegiatan(Base):
    """
    Aktivitas / event yang dilakukan oleh suatu Pokja.
    Ini adalah unit data utama untuk analisis AI.
    """
    __tablename__ = "kegiatan"

    id              = Column(Integer, primary_key=True, index=True)
    pokja_id        = Column(Integer, ForeignKey("pokja.id"), nullable=False)
    judul           = Column(String(200), nullable=False)
    deskripsi       = Column(Text, nullable=True)
    tanggal         = Column(DateTime, nullable=False)
    lokasi          = Column(String(150), nullable=True)
    jumlah_peserta  = Column(Integer, default=0)
    kendala         = Column(Text, nullable=True)
    hasil           = Column(Text, nullable=True)
    status          = Column(String(20), default=StatusKegiatan.PLANNED)
    created_at      = Column(DateTime, default=func.now())
    updated_at      = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    pokja           = relationship("Pokja", back_populates="kegiatan")
    dokumentasi     = relationship("Dokumentasi", back_populates="kegiatan", cascade="all, delete-orphan")
    laporan         = relationship("Laporan", back_populates="kegiatan", uselist=False)

    def __repr__(self):
        return f"<Kegiatan(id={self.id}, judul='{self.judul}', status='{self.status}')>"


class Dokumentasi(Base):
    """
    File dokumentasi (foto/dokumen) yang terlampir pada suatu Kegiatan.
    Auto rename: pokja_tanggal_index.ext
    """
    __tablename__ = "dokumentasi"

    id           = Column(Integer, primary_key=True, index=True)
    kegiatan_id  = Column(Integer, ForeignKey("kegiatan.id"), nullable=False)
    filename     = Column(String(255), nullable=False)       # nama file asli
    stored_name  = Column(String(255), nullable=False)       # nama setelah rename otomatis
    file_path    = Column(String(500), nullable=False)       # path relatif di server
    file_type    = Column(String(50), nullable=True)         # image/pdf/etc
    file_size    = Column(Integer, nullable=True)            # bytes
    deskripsi    = Column(String(300), nullable=True)
    uploaded_at  = Column(DateTime, default=func.now())

    kegiatan     = relationship("Kegiatan", back_populates="dokumentasi")

    def __repr__(self):
        return f"<Dokumentasi(id={self.id}, stored_name='{self.stored_name}')>"

class Laporan(Base):
    __tablename__ = "laporan"

    id               = Column(Integer, primary_key=True, index=True)
    kegiatan_id      = Column(Integer, ForeignKey("kegiatan.id"), nullable=True, unique=True)
    pokja_id         = Column(Integer, ForeignKey("pokja.id"), nullable=False)
    judul            = Column(String(300), nullable=False)
    konten           = Column(Text, nullable=False)
    template_used    = Column(String(100), nullable=True)
    is_auto_generated= Column(Boolean, default=True)
    status_approve   = Column(String(20), default="pending")
    catatan_pengawas = Column(Text, nullable=True)
    approved_by      = Column(Integer, nullable=True)
    approved_at      = Column(DateTime, nullable=True)
    created_at       = Column(DateTime, default=func.now())
    updated_at       = Column(DateTime, default=func.now(), onupdate=func.now())

    kegiatan        = relationship("Kegiatan", back_populates="laporan")
    pokja           = relationship("Pokja", back_populates="laporan")

    def __repr__(self):
        return f"<Laporan(id={self.id}, judul='{self.judul[:40]}...')>"


class SkorPokja(Base):
    """
    Skor performa tiap Pokja yang dihitung ulang secara periodik.
    Digunakan untuk ranking dan insight AI.
    """
    __tablename__ = "skor_pokja"

    id                   = Column(Integer, primary_key=True, index=True)
    pokja_id             = Column(Integer, ForeignKey("pokja.id"), nullable=False, unique=True)
    skor_total           = Column(Float, default=0.0)        # 0–100
    skor_frekuensi       = Column(Float, default=0.0)        # berapa sering kegiatan
    skor_konsistensi     = Column(Float, default=0.0)        # konsistensi mingguan
    skor_penyelesaian    = Column(Float, default=0.0)        # % kegiatan selesai
    skor_partisipasi     = Column(Float, default=0.0)        # rata-rata peserta
    label                = Column(String(50), default="Belum Dinilai")  # "Sangat Aktif", "Aktif", dll
    insight              = Column(Text, nullable=True)       # kalimat insight AI
    calculated_at        = Column(DateTime, default=func.now())

    pokja                = relationship("Pokja", back_populates="skor")

    def __repr__(self):
        return f"<SkorPokja(pokja_id={self.pokja_id}, skor={self.skor_total:.1f}, label='{self.label}')>"


# ─── DB Setup ─────────────────────────────────────────────────────────────────

import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = (
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME')}"
)

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency injection untuk FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()