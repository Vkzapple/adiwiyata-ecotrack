const express = require("express");
const mysql = require("mysql2/promise");
const bcrypt = require("bcrypt");
const cors = require("cors");
const path = require("path");

const app = express();
app.use(express.json());
app.use(cors());

// 1) Serve frontend files so open via http://localhost:3000/static/admin/index.html (same-origin)
app.use(
    "/static",
    express.static(path.join(__dirname, "..", "website", "public", "static")),
);
app.use(express.static(path.join(__dirname, "..", "website", "public")));

// 2) Use a connection pool (mysql2/promise)
const pool = mysql.createPool({
    host: "127.0.0.1",
    user: "root",
    password: "",
    database: "adiwiyata",
    waitForConnections: true,
    connectionLimit: 10,
    queueLimit: 0,
});

// safer query wrapper: throw error so route-level try/catch can handle
async function query(sql, params = []) {
    try {
        const [rows] = await pool.execute(sql, params);
        return rows;
    } catch (err) {
        // attach query for easier debugging
        err.query = sql;
        throw err;
    }
}

// 3) Routes (async/await)
app.post("/api/login", async (req, res) => {
    const { email, password } = req.body;
    if (!email || !password)
        return res
            .status(400)
            .json({ message: "Email dan password wajib diisi" });

    try {
        const users = await query("SELECT * FROM users WHERE email = ?", [
            email,
        ]);
        if (users.length === 0)
            return res.status(401).json({ message: "User tidak ditemukan" });

        const user = users[0];
        const match = await bcrypt.compare(password, user.password || "");
        if (!match) return res.status(401).json({ message: "Password salah" });

        res.json({
            message: "Login Berhasil",
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
        return res
            .status(400)
            .json({ message: "Name, email, dan password wajib diisi" });

    try {
        const hashedPassword = await bcrypt.hash(password, 10);
        await query(
            "INSERT INTO users (name, email, password, role, pokja) VALUES (?, ?, ?, ?, ?)",
            [name, email, hashedPassword, role, pokja],
        );
        res.status(201).json({ message: "User berhasil dibuat" });
    } catch (err) {
        console.error(err);
        if (err && err.code === "ER_DUP_ENTRY")
            return res.status(400).json({ message: "Email sudah terdaftar" });
        res.status(500).json({ message: "Gagal mendaftarkan user" });
    }
});

app.get("/api/users", async (req, res) => {
    try {
        const users = await query(
            "SELECT id, name, email, role, pokja FROM users",
        );
        res.json(users);
    } catch (err) {
        console.error(err);
        res.status(500).json({ message: "Gagal mengambil data user" });
    }
});

app.delete("/api/users/:id", async (req, res) => {
    const { id } = req.params;
    try {
        await query("DELETE FROM users WHERE id = ?", [id]);
        res.json({ message: "User berhasil dihapus" });
    } catch (err) {
        console.error(err);
        res.status(500).json({ message: "Gagal menghapus user" });
    }
});

app.get("/api/pokja", async (req, res) => {
    try {
        const pokja = await query("SELECT * FROM pokja");
        res.json(pokja);
    } catch (err) {
        console.error(err);
        res.status(500).json({ message: "Gagal mengambil data pokja" });
    }
});

app.get("/api/health", (req, res) => res.json({ status: "ok" }));

// --- New: health-check DB before starting server ---
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
const AI_URL = "http://127.0.0.1:8000";
// Helper function
async function fetchAI(path, options = {}) {
    const response = await fetch(`${AI_URL}${path}`, options);
    return response.json();
}

app.get("/api/ai/dashboard", async (req, res) => {
    try {
        const data = await fetchAI("/analytics/dashboard");
        res.json(data);
    } catch (err) {
        res.status(503).json({ message: "AI service tidak tersedia" });
    }
});

app.get("/api/ai/ranking", async (req, res) => {
    try {
        const data = await fetchAI("/analytics/ranking");
        res.json(data);
    } catch (err) {
        res.status(503).json({ message: "AI service tidak tersedia" });
    }
});

app.get("/api/ai/insight/:pokja_id", async (req, res) => {
    try {
        const data = await fetchAI(`/analytics/pokja/${req.params.pokja_id}/insight`);
        res.json(data);
    } catch (err) {
        res.status(503).json({ message: "AI service tidak tersedia" });
    }
});

app.post("/api/ai/kegiatan", async (req, res) => {
    try {
        const data = await fetchAI("/kegiatan/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(req.body)
        });
        res.json(data);
    } catch (err) {
        res.status(503).json({ message: "AI service tidak tersedia" });
    }
});

app.post("/api/ai/laporan/generate", async (req, res) => {
    try {
        const data = await fetchAI("/laporan/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(req.body)
        });
        res.json(data);
    } catch (err) {
        res.status(503).json({ message: "AI service tidak tersedia" });
    }
});

app.post("/api/ai/recalculate", async (req, res) => {
    try {
        const data = await fetchAI("/analytics/recalculate", { method: "POST" });
        res.json(data);
    } catch (err) {
        res.status(503).json({ message: "AI service tidak tersedia" });
    }
});
let server = null;
async function start() {
    try {
        await testDbConnection();
        const PORT = process.env.PORT || 3001;
        server = app.listen(PORT, () => {
            console.log(`Server backend berjalan di http://localhost:${PORT}`);
        });
    } catch (err) {
        console.error("Gagal menghubungkan ke database. Server tidak dimulai.");
        console.error(err && err.message ? err.message : err);

        try {
            await pool.end();
        } catch (e) {

        }
        process.exit(1);
    }
}

async function shutdown(code = 0) {
    console.log("Shutdown initiated...");
    if (server) {
        server.close(() => console.log("HTTP server closed"));
    }
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

process.on("unhandledRejection", (reason) => {
    console.error("Unhandled Rejection at:", reason);

});
process.on("uncaughtException", (err) => {
    console.error("Uncaught Exception:", err);

    shutdown(1);
});

start();
