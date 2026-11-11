"""Uji end-to-end endpoint /ask (FastAPI TestClient, LLM Gemini sungguhan) untuk 5 skenario wajib + beberapa tambahan.

Butuh GEMINI_API_KEY di environment / .env.  Jalankan dari root repo:  python -m tests.run_scenarios
Hasil disimpan ke docs/test_results.json.
"""

import json
import time

from fastapi.testclient import TestClient

from app.main import app

# (kelompok, query, intent yang diharapkan, status yang diharapkan)
SCENARIOS = [
    ("1. RAG (kebijakan)", "Berapa jatah cuti tahunan untuk karyawan tetap?", "faq", "success"),
    ("2. RAG (parafrase)", "kalau lupa password VPN, caranya reset gimana ya?", "faq", "success"),
    ("3. Tool call (ada)", "Tolong cek status TICKET-0005 saya", "ticket_status", "success"),
    ("4. Tool call (tidak ada)", "Apa status TICKET-9999?", "ticket_status", "not_found"),
    ("5. Ambigu / di luar cakupan", "Bisa bantu pesankan tiket pesawat ke Bali untuk dinas?", "faq", "success"),
    ("Tambahan A. tanpa nomor tiket", "cek status tiket saya dong", "ticket_status", "needs_input"),
    ("Tambahan B. RAG multi-topik", "Laptop kerja saya rusak, berapa lama diperbaiki dan siapa yang harus dihubungi?", "faq", "success"),
]

rows = []
with TestClient(app) as client:
    print("health:", client.get("/health").json())
    for group, query, exp_intent, exp_status in SCENARIOS:
        t0 = time.perf_counter()
        r = client.post("/ask", json={"query": query})
        dt = time.perf_counter() - t0
        body = r.json()
        ok = body.get("intent") == exp_intent and body.get("status") == exp_status
        rows.append({"group": group, "query": query, "http": r.status_code, "expected_intent": exp_intent,
                     "expected_status": exp_status, "response": body, "routed_correctly": ok,
                     "latency_s": round(dt, 2)})
        print(f"\n[{group}] {'OK' if ok else 'MISMATCH'}  ({dt:.1f}s, HTTP {r.status_code})\n  Q: {query}\n  -> {body}")
    r = client.post("/ask", json={"query": ""})
    rows.append({"group": "Tambahan C. query kosong", "query": "", "http": r.status_code, "response": r.json()})
    print("\n[query kosong] HTTP", r.status_code)

n_ok = sum(1 for x in rows if x.get("routed_correctly"))
n = sum(1 for x in rows if "routed_correctly" in x)
print(f"\nRouting benar: {n_ok}/{n}")
json.dump(rows, open("docs/test_results.json", "w"), ensure_ascii=False, indent=1)
