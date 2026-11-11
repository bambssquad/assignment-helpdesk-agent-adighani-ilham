# IT Helpdesk Assistant — RAG + Router + Tool Call (FastAPI + Docker)

Individual Assignment 4 · AI Engineering Bootcamp · Adighani Ilham (CAI58)

Backend API yang menggabungkan **RAG** (menjawab pertanyaan kebijakan dari knowledge base) dan **router / mini-agent** (mengenali permintaan cek status tiket lalu mengambil datanya lewat *tool call*) dalam satu endpoint `POST /ask`, dikemas dalam container Docker.

## 1. Problem statement

**Objective.** Tim People & IT Operations menerima ratusan pertanyaan berulang. Sistem ini menjawab otomatis dua jenis permintaan dalam satu endpoint, tanpa karyawan perlu memilih "menu" lebih dulu.

| Jenis permintaan | Contoh | Ditangani oleh |
|---|---|---|
| Informasi / kebijakan (`faq`) | "berapa jatah cuti tahunan saya?", "cara reset password VPN?" | RAG: semantic search (FAISS) + LLM |
| Cek status tiket (`ticket_status`) | "apa status TICKET-0005?" | Tool call: lookup `data/mock_tickets.csv` |

**Asumsi & batasan**
- Knowledge base (31 FAQ) dan data tiket (15 tiket mock) dipakai apa adanya dari starter repo; tidak ada integrasi ke sistem tiket sungguhan.
- Satu pesan = satu intent (tidak ada pesan campuran "jawab cuti **dan** cek tiket").
- Tidak ada autentikasi/otorisasi: siapa pun bisa menanyakan tiket mana pun (cukup untuk prototype, tidak untuk produksi).
- Respons tool call hanya memuat kategori, subjek, status, dan tanggal update; nama karyawan pada data tiket sengaja tidak ditampilkan.
- Format nomor tiket `TICKET-XXXX` (4 digit); input seperti `ticket-7` dinormalisasi menjadi `TICKET-0007`.

## 2. Desain workflow

```
            POST /ask {"query": "..."}
                      │
                      ▼
            ┌───────────────────┐
            │  detect_intent()  │  keyword (default) atau LLM (INTENT_MODE=llm)
            └───────┬───────────┘
        faq │       │ ticket_status        │ lainnya
            ▼       ▼                      ▼
   ┌──────────────┐ ┌────────────────────┐ status "error",
   │ RAG (rag.py) │ │ extract_ticket_id()│ intent "unknown" (HTTP 400)
   │ embed query  │ │ + get_ticket_status│
   │ FAISS top-3  │ │ (tools.py)         │
   │ prompt + LLM │ └─────────┬──────────┘
   └──────┬───────┘           │
          └─────────┬─────────┘
                    ▼
     {"status": ..., "intent": ..., "data": ...}
```

**Kriteria intent**
- `ticket_status`: ada nomor tiket (`TICKET-0042`, `ticket-7`, `tiket 0015`), **atau** ada kata "tiket/ticket" bersama kata status (status, cek, progres, update, lacak, …) dan bukan kalimat tanya prosedur ("bagaimana cara …"). Tanpa nomor, sistem membalas `needs_input` dan meminta nomor tiket.
- `faq`: semua yang lain, termasuk "bagaimana cara membuat tiket baru?" dan pertanyaan di luar topik (RAG yang memutuskan bahwa jawabannya tidak ada).
- `unknown`: query kosong / label LLM tidak dikenali.

Status response: `success` · `not_found` (tiket tidak ada) · `needs_input` (nomor tiket belum disebut) · `error` (LLM gagal → HTTP 503; intent tak dikenali → HTTP 400).

## 3. Struktur project

```
app/
├── main.py     # FastAPI: /ask, /health, startup (bangun index), error handling
├── router.py   # intent detection (keyword / LLM), ekstraksi ticket_id, routing
├── rag.py      # build_index, semantic_search (FAISS), prompt Persona/Task/Context/Format, jawaban LLM
├── tools.py    # get_ticket_status (pandas), tidak crash bila tiket tidak ada
├── llm.py      # client Gemini (lazy), retry, cache embedding
└── config.py   # semua konfigurasi dari environment variable
data/           # knowledge base + mock tiket (dari starter)
tests/          # router_eval, run_scenarios, curl_scenarios, intent_llm_eval
docs/           # hasil pengujian (JSON) dari eksekusi nyata
Dockerfile · .dockerignore · .env.example · requirements.txt
```

Keputusan desain: embedding `gemini-embedding-001` (3072 dimensi; `text-embedding-004` di starter sudah tidak tersedia), vektor dinormalisasi L2 + `IndexFlatIP` (cosine similarity), index dibangun **sekali saat startup** (embedding di-cache ke disk), client Gemini dibuat *lazy* sehingga aplikasi tetap hidup tanpa API key (tool call tetap jalan, FAQ membalas error terstruktur).

## 4. Menjalankan

API key **tidak** ada di repo. Salin `.env.example` menjadi `.env` dan isi `GEMINI_API_KEY` milikmu sendiri (`.env` di-ignore oleh git dan docker).

**Lokal (tanpa Docker)**
```bash
pip install -r requirements.txt
cp .env.example .env        # isi GEMINI_API_KEY
uvicorn app.main:app --reload
```

**Docker**
```bash
docker build -t it-helpdesk-assistant .
docker run -p 8000:8000 --env-file .env it-helpdesk-assistant
```

**Coba endpoint**
```bash
curl -s localhost:8000/health
curl -s -X POST localhost:8000/ask -H "Content-Type: application/json" \
     -d '{"query": "berapa jatah cuti tahunan saya?"}'
curl -s -X POST localhost:8000/ask -H "Content-Type: application/json" \
     -d '{"query": "apa status TICKET-0005?"}'
```

Konfigurasi opsional lewat environment variable: `LLM_MODEL` (default `gemini-3.8-flash`), `EMBED_MODEL`, `INTENT_MODE` (`keyword` default / `llm`), `INTENT_LLM_MODEL`, `TOP_K`.

## 5. Hasil pengujian

Semua angka di bawah berasal dari eksekusi nyata; keluaran mentah ada di folder `docs/`.

### 5.1 Lima skenario wajib — container Docker, HTTP asli (`docs/docker_test_results.json`)

Container dijalankan dari image yang di-build dari `Dockerfile` ini, lalu `/ask` dipanggil lewat HTTP (`python -m tests.curl_scenarios`). Model LLM saat pengujian ini `gemini-3.5-flash-lite` (diatur lewat environment variable `LLM_MODEL`).

| # | Query | Intent terdeteksi | Status | Router benar? | Observasi |
|---|---|---|---|---|---|
| 1 | "Apakah cuti yang tidak terpakai bisa dibawa ke tahun berikutnya?" | faq | success | ✅ | Jawaban sesuai FAQ 3 (maks. 6 hari, dipakai di kuartal pertama), menyebut sumber |
| 2 | "Berapa jam kerja standar per hari di perusahaan?" | faq | success | ✅ | Sesuai FAQ 26 (8 jam, Senin–Jumat, masuk 08.00–10.00) |
| 3 | "Tolong cek status TICKET-0011 saya" | ticket_status | success | ✅ | Data dari CSV: status *Menunggu Persetujuan*, update 2026-08-25; tanpa LLM (≈0,02 dtk) |
| 4 | "Apa status TICKET-9999?" | ticket_status | not_found | ✅ | Pesan informatif, tidak crash |
| 5 | "Apa rekomendasi restoran enak dekat kantor?" (di luar cakupan) | faq | success | ✅ | LLM menyatakan belum punya informasi, tidak mengarang rekomendasi |

**Routing benar 5/5.**

### 5.2 Uji kedua — in-process (TestClient), query berbeda, model `gemini-3.8-flash` (`docs/test_results.json`)

| Query | Intent | Status | Observasi |
|---|---|---|---|
| "Berapa jatah cuti tahunan untuk karyawan tetap?" | faq | success | 12 hari, minimal masa kerja 3 bulan (FAQ 1) ✅ |
| "kalau lupa password VPN, caranya reset gimana ya?" | faq | success | Parafrase informal tetap menemukan FAQ 8 ✅ |
| "Tolong cek status TICKET-0005 saya" | ticket_status | success | Data tiket benar ✅ |
| "Apa status TICKET-9999?" | ticket_status | not_found | ✅ |
| "Bisa bantu pesankan tiket pesawat ke Bali untuk dinas?" | faq | success | Mengandung kata "tiket" tetapi tidak salah dirutekan ke tool; LLM menyatakan belum punya informasi ✅ |
| "cek status tiket saya dong" (tanpa nomor) | ticket_status | needs_input | Meminta nomor tiket ✅ |
| "Laptop kerja saya rusak, berapa lama diperbaiki dan siapa yang harus dihubungi?" | faq | success | Menggabungkan FAQ 15 dan 16; "1–3 hari kerja" sesuai KB ✅ |
| (query kosong) | – | – | HTTP 422 dari validasi Pydantic ✅ |

Latensi pada run ini 57–106 detik per jawaban RAG. Penyebabnya bukan kode: free tier Gemini mengembalikan error 429/503 dan pemanggilan di-retry (terlihat di log). Pada run Docker di 5.1 (model lite) jawaban RAG 1,5–4,5 detik.

### 5.3 Akurasi router (17 query berlabel, `docs/router_eval.json`, `docs/intent_llm_eval.json`)

| Mode | Intent benar | Ekstraksi ticket_id |
|---|---|---|
| `keyword` (baseline, default) | 15/17 = 88% | 17/17 |
| `llm` (`gemini-3.1-flash-lite`) | 17/17 | – |

Dua kesalahan mode keyword: *"permintaan akses saya sudah diproses belum?"* (tidak menyebut kata "tiket") dan *"kenapa tiket saya belum dibalas 3 hari?"* (diawali kata tanya sehingga dianggap pertanyaan prosedur). Keduanya sengaja saya masukkan sebagai kasus sulit. Perhatian: dataset 17 query ditulis sendiri dan kasus sulitnya dibuat setelah melihat kelemahan aturan keyword, jadi 17/17 untuk mode LLM tidak boleh dibaca sebagai akurasi umum.

## 6. Keterbatasan yang ditemukan

1. **Intent keyword rapuh pada permintaan implisit** (lihat 5.3). Mode LLM lebih tahan tetapi menambah satu panggilan LLM (latensi dan kuota) per request; bila LLM gagal, router jatuh ke keyword.
2. **Free tier Gemini**: kuota harian terbatas dan sering 429/503. Selama pengerjaan, beberapa model kehabisan kuota sehingga pengujian dibagi ke beberapa model (`gemini-3.8-flash`, `gemini-3.7-flash` kuotanya habis sebelum pengujian selesai, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`); hasil tiap tabel menyebut modelnya. Pada kegagalan LLM API membalas HTTP 503 dengan body terstruktur (sudah teruji di container saat kuota habis), bukan crash.
3. **RAG tidak punya ambang kemiripan**: vector search selalu mengembalikan 3 FAQ terdekat walau tidak relevan (query restoran). Pencegah halusinasi hanya instruksi prompt ("jawab hanya dari Context"); pada 2 query di luar cakupan yang diuji, LLM menolak dengan benar, tetapi itu sampel kecil.
4. **Query multi-intent** (pesan yang berisi pertanyaan kebijakan sekaligus cek tiket) hanya diproses sebagai satu intent.
5. **Tidak ada otorisasi** pada cek tiket, data tiket dibaca dari CSV (tidak real-time), dan knowledge base hanya dibaca saat startup (perubahan CSV butuh restart).
6. **Docker di lingkungan pengerjaan**: sandbox saya memakai proxy dengan sertifikat sendiri, sehingga saat `docker build` lokal saya menambahkan sertifikat proxy lewat `Dockerfile` sementara di luar repo (isi langkah lain identik). Build dengan `Dockerfile` persis seperti di repo ini diverifikasi terpisah oleh GitHub Actions (`.github/workflows/docker-ci.yml`).

## 7. Catatan repository

`.github/workflows/import-starter.yml` hanya dipakai sekali untuk mengimpor starter repo (ZIP) ke repository ini; ia tidak berjalan lagi karena ada guard `if [ -d app ]`.
