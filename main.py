"""
EcoTrack AI — Smart Adiwiyata Management System
================================================
Backend FastAPI utama.

Jalankan:
    uvicorn main:app --reload --port 8000

Dokumentasi API:
    http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.models.database import create_tables
from app.routers.api import router_pokja, router_kegiatan, router_laporan, router_analytics


# ─── App Lifecycle ────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inisialisasi database saat startup."""
    create_tables()
    print("✅ EcoTrack AI - Database siap")
    yield
    print("👋 EcoTrack AI - Shutdown")


# ─── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title       = "EcoTrack AI — Smart Adiwiyata Management System",
    description = """
## 🌱 EcoTrack AI Backend API

Sistem manajemen Adiwiyata berbasis kecerdasan buatan untuk:
- **Smart Input** kegiatan Pokja
- **AI Behavior Analysis** — deteksi Pokja aktif/tidak aktif
- **Auto Report Generator** — laporan otomatis dari input minimal
- **Activity Scoring** — ranking performa Pokja
- **Dashboard Analytics** — visualisasi data real-time

### Endpoint Utama
| Domain     | Prefix       | Fungsi                        |
|------------|--------------|-------------------------------|
| Pokja      | /pokja       | CRUD kelompok kerja           |
| Kegiatan   | /kegiatan    | Input & manajemen aktivitas   |
| Laporan    | /laporan     | Generate & akses laporan      |
| Analytics  | /analytics   | AI scoring & dashboard        |
    """,
    version     = "1.0.0",
    lifespan    = lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],   # Ganti dengan domain frontend di production
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(router_pokja)
app.include_router(router_kegiatan)
app.include_router(router_laporan)
app.include_router(router_analytics)

# ─── Root ─────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Root"])
def root():
    return {
        "app"    : "EcoTrack AI",
        "version": "1.0.0",
        "status" : "running",
        "docs"   : "/docs",
        "message": "🌱 Smart Adiwiyata Management System siap digunakan!",
    }

@app.get("/health", tags=["Root"])
def health():
    return {"status": "ok", "timestamp": __import__("datetime").datetime.now().isoformat()}
