const express = require("express");
const mysql = require("mysql2/promise");
const bcrypt = require("bcrypt");
const cors = require("cors");
const path = require("path");
const jwt = require("jsonwebtoken");

const app = express();
app.use(express.json());
app.use(cors());

app.use(
    "/static",
    express.static(path.join(__dirname, "..", "website", "public", "static")),
);
app.use(express.static(path.join(__dirname, "..", "website", "public")));

require('dotenv').config();

// ─── JWT Helpers ─────────────────────────────────────────────────────────────

const JWT_SECRET = process.env.JWT_SECRET;
const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || "8h";

function generateToken(payload) {
    return jwt.sign(payload, JWT_SECRET, { expiresIn: JWT_EXPIRES_IN });
}

// Middleware: cek JWT di header Authorization
function authenticateToken(req, res, next) {
    const authHeader = req.headers["authorization"];
    const token = authHeader && authHeader.split(" ")[1]; // "Bearer <token>"

    if (!token) {
        return res.status(401).json({ message: "Token tidak ditemukan" });
    }

    try {
        const decoded = jwt.verify(token, JWT_SECRET);
        req.user = decoded; // { id, name, role, pokja }
        next();
    } catch (err) {
        if (err.name === "TokenExpiredError") {
            return res.status(401).json({ message: "Token sudah kadaluarsa, silakan login ulang" });
        }
        return res.status(403).json({ message: "Token tidak valid" });
    }
}

// Middleware: cek role tertentu (opsional, pakai di route admin)
function requireRole(...roles) {
    return (req, res, next) => {
        if (!roles.includes(req.user?.role)) {
            return res.status(403).json({ message: "Akses ditolak: role tidak sesuai" });
        }
        next();
    };
}

// ─── DB Pool ─────────────────────────────────────────────────────────────────

const pool = mysql.createPool({
    host: process.env.MYSQLHOST,
    port: process.env.MYSQLPORT,
    user: process.env.MYSQLUSER,
    password: process.env.MYSQLPASSWORD,
    database: process.env.MYSQLDATABASE,
    waitForConnections: true,
    connectionLimit: 10,
    queueLimit: 0,
});

async function query(sql, params = []) {
    try {
        const [rows] = await pool.execute(sql, params);
        return rows;
    } catch (err) {
        err.query = sql;
        throw err;
    }
}

// ─── Auth Routes (PUBLIC) ─────────────────────────────────────────────────────

app.post("/api/login", async (req, res) => {
    const { email, password } = req.body;
    if (!email || !password)
        return res.status(400).json({ message: "Email dan password wajib diisi" });

    try {
        const users = await query("SELECT * FROM users WHERE email = ?", [email]);
        if (users.length === 0)
            return res.status(401).json({ message: "User tidak ditemukan" });

        const user = users[0];
        const match = await bcrypt.compare(password, user.password || "");
        if (!match)
            return res.status(401).json({ message: "Password salah" });

        // Generate JWT
        const token = generateToken({
            id: user.id,
            name: user.name,
            role: user.role,
            pokja: user.pokja,
        });

        res.json({
            message: "Login Berhasil",
            token, // ← kirim token ke client
            user: {
                id: user.id,
                name: user.name,
                role: user.role,
                pokja: user.pokja,
            },
        });
    } catch (err) {
        console.error(err);
        res.status(500).json({ message: "Kesalahan Server" });
    }
});

app.post("/api/register", async (req, res) => {
    const { name, email, password, role, pokja } = req.body;
    if (!name || !email || !password)
        return res.status(400).json({ message: "Name, email, dan password wajib diisi" });

    const cleanPokja = (pokja && pokja !== "undefined") ? pokja : null;

    try {
        const hashedPassword = await bcrypt.hash(password, 10);
        await query(
            "INSERT INTO users (name, email, password, role, pokja) VALUES (?, ?, ?, ?, ?)",
            [name, email, hashedPassword, role || "ketua", cleanPokja],
        );
        res.status(201).json({ message: "User berhasil dibuat" });
    } catch (err) {
        console.error(err);
        if (err && err.code === "ER_DUP_ENTRY")
            return res.status(400).json({ message: "Email sudah terdaftar" });
        res.status(500).json({ message: "Gagal mendaftarkan user" });
    }
});

// Cek token masih valid (dipakai frontend saat refresh halaman)
app.get("/api/auth/me", authenticateToken, (req, res) => {
    res.json({ user: req.user });
});

// ─── User Routes (PROTECTED) ──────────────────────────────────────────────────

// Hanya admin/pengawas yang bisa lihat semua user
app.get("/api/users", authenticateToken, requireRole("admin", "pengawas"), async (req, res) => {
    try {
        const users = await query("SELECT id, name, email, role, pokja FROM users");
        res.json(users);
    } catch (err) {
        console.error(err);
        res.status(500).json({ message: "Gagal mengambil data user" });
    }
});

// Hanya admin yang bisa hapus user
app.delete("/api/users/:id", authenticateToken, requireRole("admin"), async (req, res) => {
    const { id } = req.params;
    try {
        await query("DELETE FROM users WHERE id = ?", [id]);
        res.json({ message: "User berhasil dihapus" });
    } catch (err) {
        console.error(err);
        res.status(500).json({ message: "Gagal menghapus user" });
    }
});

// ─── Health ───────────────────────────────────────────────────────────────────

app.get("/api/health", (req, res) => res.json({ status: "ok" }));

// ─── AI Proxy Routes (PROTECTED) ─────────────────────────────────────────────

const AI_URL = process.env.AI_URL || "http://127.0.0.1:8000";

async function fetchAI(path, options = {}) {
    const response = await fetch(`${AI_URL}${path}`, options);
    return response.json();
}

app.get("/api/ai/dashboard", authenticateToken, async (req, res) => {
    try {
        const data = await fetchAI("/analytics/dashboard");
        res.json(data);
    } catch (err) {
        res.status(503).json({ message: "AI service tidak tersedia" });
    }
});

app.get("/api/ai/ranking", authenticateToken, async (req, res) => {
    try {
        const data = await fetchAI("/analytics/ranking");
        res.json(data);
    } catch (err) {
        res.status(503).json({ message: "AI service tidak tersedia" });
    }
});

app.get("/api/ai/insight/:pokja_id", authenticateToken, async (req, res) => {
    try {
        const data = await fetchAI(`/analytics/pokja/${req.params.pokja_id}/insight`);
        res.json(data);
    } catch (err) {
        res.status(503).json({ message: "AI service tidak tersedia" });
    }
});

app.post("/api/ai/kegiatan", authenticateToken, async (req, res) => {
    try {
        const data = await fetchAI("/kegiatan/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(req.body),
        });
        res.json(data);
    } catch (err) {
        res.status(503).json({ message: "AI service tidak tersedia" });
    }
});

app.post("/api/ai/laporan/generate", authenticateToken, async (req, res) => {
    try {
        const data = await fetchAI("/laporan/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(req.body),
        });
        res.json(data);
    } catch (err) {
        res.status(503).json({ message: "AI service tidak tersedia" });
    }
});

app.post("/api/laporan/:id/review", authenticateToken, requireRole("pengawas", "admin"), async (req, res) => {
    const { id } = req.params;
    const { status_approve, catatan_pengawas, approved_by } = req.body;
    try {
        await query(
            `UPDATE laporan SET status_approve=?, catatan_pengawas=?, approved_by=?, approved_at=NOW() WHERE id=?`,
            [status_approve, catatan_pengawas, approved_by, id],
        );
        res.json({ message: "Laporan berhasil diperbarui" });
    } catch (err) {
        console.error(err);
        res.status(500).json({ message: "Gagal memperbarui laporan" });
    }
});

app.get("/api/laporan/", authenticateToken, async (req, res) => {
    try {
        const data = await fetchAI("/laporan/");
        res.json(data);
    } catch (err) {
        res.status(503).json({ message: "AI service tidak tersedia" });
    }
});

app.get("/api/kegiatan/", authenticateToken, async (req, res) => {
    try {
        const qs = req.query.pokja_id ? `?pokja_id=${req.query.pokja_id}` : "";
        const data = await fetchAI(`/kegiatan/${qs}`);
        res.json(data);
    } catch (err) {
        res.status(503).json({ message: "AI service tidak tersedia" });
    }
});

app.get("/api/kegiatan/:id", authenticateToken, async (req, res) => {
    try {
        const data = await fetchAI(`/kegiatan/${req.params.id}`);
        res.json(data);
    } catch (err) {
        res.status(503).json({ message: "AI service tidak tersedia" });
    }
});

app.delete("/api/kegiatan/:id", authenticateToken, async (req, res) => {
    try {
        const data = await fetchAI(`/kegiatan/${req.params.id}`, { method: "DELETE" });
        res.json(data);
    } catch (err) {
        res.status(503).json({ message: "AI service tidak tersedia" });
    }
});

app.post("/api/ai/dokumentasi/upload", authenticateToken, async (req, res) => {
    try {
        const fetch = (await import("node-fetch")).default;
        const response = await fetch(`${AI_URL}/dokumentasi/upload`, {
            method: "POST",
            headers: req.headers,
            body: req,
        });
        const data = await response.json();
        res.status(response.status).json(data);
    } catch (err) {
        res.status(503).json({ message: "AI service tidak tersedia" });
    }
});

app.get("/api/pokja", authenticateToken, async (req, res) => {
    try {
        const data = await fetchAI("/pokja/");
        res.json(data);
    } catch (err) {
        res.status(503).json({ message: "AI service tidak tersedia" });
    }
});

app.post("/api/ai/recalculate", authenticateToken, requireRole("admin", "pengawas"), async (req, res) => {
    try {
        const data = await fetchAI("/analytics/recalculate", { method: "POST" });
        res.json(data);
    } catch (err) {
        res.status(503).json({ message: "AI service tidak tersedia" });
    }
});

// ─── Server Start & Shutdown ──────────────────────────────────────────────────

async function testDbConnection() {
    let conn;
    try {
        conn = await pool.getConnection();
        await conn.ping();
        console.log("Koneksi DB OK (ping berhasil)");
    } finally {
        if (conn) conn.release();
    }
}

let server = null;

async function start() {
    if (!JWT_SECRET) {
        console.error("FATAL: JWT_SECRET belum diset di .env!");
        process.exit(1);
    }

    try {
        await testDbConnection();
        const PORT = process.env.PORT || 3001;
        server = app.listen(PORT, "0.0.0.0", () => {
            console.log(`Server berjalan di http://0.0.0.0:${PORT}`);
        });
    } catch (err) {
        console.error("Gagal menghubungkan ke database. Server tidak dimulai.");
        console.error(err && err.message ? err.message : err);
        try { await pool.end(); } catch (e) {}
        process.exit(1);
    }
}

async function shutdown(code = 0) {
    console.log("Shutdown initiated...");
    if (server) server.close(() => console.log("HTTP server closed"));
    try {
        await pool.end();
        console.log("DB pool closed");
    } catch (e) {
        console.error("Error closing pool:", e);
    }
    process.exit(code);
}

process.on("SIGINT", () => shutdown(0));
process.on("SIGTERM", () => shutdown(0));
process.on("unhandledRejection", (reason) => { console.error("Unhandled Rejection:", reason); });
process.on("uncaughtException", (err) => { console.error("Uncaught Exception:", err); shutdown(1); });

start();