"""Evaluasi router (tanpa memanggil LLM): akurasi intent detection mode keyword + ekstraksi ticket_id.

Jalankan dari root repo:  python -m tests.router_eval
Hasil disimpan ke docs/router_eval.json.
"""

import json

from app.router import detect_intent_keyword, extract_ticket_id
from tests.cases import CASES

rows, ok_intent, ok_id = [], 0, 0
for q, exp_intent, exp_id in CASES:
    got_intent = detect_intent_keyword(q)
    got_id = extract_ticket_id(q) if got_intent == "ticket_status" else None
    i_ok, id_ok = got_intent == exp_intent, got_id == exp_id
    ok_intent += i_ok
    ok_id += id_ok
    rows.append({"query": q, "expected": exp_intent, "got": got_intent, "intent_ok": i_ok,
                 "expected_ticket_id": exp_id, "got_ticket_id": got_id, "id_ok": id_ok})
    print(f"{'OK ' if i_ok and id_ok else 'XX '} {q!r:60} -> {got_intent} {got_id}")

n = len(CASES)
print(f"\nAkurasi intent: {ok_intent}/{n} = {ok_intent / n:.0%} | ekstraksi ticket_id: {ok_id}/{n}")
json.dump({"mode": "keyword", "n": n, "intent_accuracy": ok_intent / n, "rows": rows},
          open("docs/router_eval.json", "w"), ensure_ascii=False, indent=1)
