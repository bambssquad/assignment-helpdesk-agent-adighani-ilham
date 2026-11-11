"""Uji 5 skenario wajib terhadap container yang SUDAH berjalan (HTTP asli ke http://localhost:8000/ask).

Jalankan:  python -m tests.curl_scenarios [base_url]      Hasil: docs/docker_test_results.json
"""

import json
import sys
import time

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
CASES = [
    ("1. RAG", "Apakah cuti yang tidak terpakai bisa dibawa ke tahun berikutnya?", "faq", "success"),
    ("2. RAG", "Berapa jam kerja standar per hari di perusahaan?", "faq", "success"),
    ("3. Tool call (ada)", "Tolong cek status TICKET-0011 saya", "ticket_status", "success"),
    ("4. Tool call (tidak ada)", "Apa status TICKET-9999?", "ticket_status", "not_found"),
    ("5. Ambigu / di luar cakupan", "Apa rekomendasi restoran enak dekat kantor?", "faq", "success"),
]
rows = []
for group, q, exp_i, exp_s in CASES:
    t0 = time.perf_counter()
    r = httpx.post(f"{BASE}/ask", json={"query": q}, timeout=300)
    b = r.json()
    ok = b.get("intent") == exp_i and b.get("status") == exp_s
    rows.append({"group": group, "query": q, "http": r.status_code, "response": b, "routed_correctly": ok,
                 "latency_s": round(time.perf_counter() - t0, 2)})
    print(f"[{group}] {'OK' if ok else 'MISMATCH'} {rows[-1]['latency_s']}s HTTP {r.status_code}\n  Q: {q}\n  -> {b}\n")
print("Routing benar:", sum(x["routed_correctly"] for x in rows), "/", len(rows))
json.dump(rows, open("docs/docker_test_results.json", "w"), ensure_ascii=False, indent=1)
