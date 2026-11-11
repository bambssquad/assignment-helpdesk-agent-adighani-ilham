"""Evaluasi intent detection mode LLM pada dataset yang sama dengan mode keyword (butuh GEMINI_API_KEY).

Jalankan:  INTENT_LLM_MODEL=gemini-3.1-flash-lite python -m tests.intent_llm_eval
Hasil disimpan ke docs/intent_llm_eval.json. Mode keyword dipakai sebagai pembanding.
"""

import json
from concurrent.futures import ThreadPoolExecutor

from app import config
from app.llm import LLMError
from app.router import _detect_intent_llm, detect_intent_keyword
from tests.cases import CASES


def run(case):
    q, exp, _ = case
    try:
        got = _detect_intent_llm(q)
    except LLMError as e:
        got = f"ERROR: {e}"
    return {"query": q, "expected": exp, "llm": got, "keyword": detect_intent_keyword(q), "llm_ok": got == exp}


with ThreadPoolExecutor(max_workers=4) as ex:
    rows = list(ex.map(run, CASES))

valid = [r for r in rows if not r["llm"].startswith("ERROR")]
for r in rows:
    print(f"{'OK ' if r['llm_ok'] else 'XX '} {r['query']!r:60} llm={r['llm']} keyword={r['keyword']}")
print(f"\nModel: {config.INTENT_LLM_MODEL} | LLM benar {sum(r['llm_ok'] for r in valid)}/{len(valid)} (error API: {len(rows) - len(valid)}) | "
      f"keyword benar {sum(r['keyword'] == r['expected'] for r in rows)}/{len(rows)}")
json.dump({"model": config.INTENT_LLM_MODEL, "rows": rows}, open("docs/intent_llm_eval.json", "w"), ensure_ascii=False, indent=1)
