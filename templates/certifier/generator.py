# templates/certifier/generator.py
import re
from typing import List, Dict, Any

_STOP = {"the","a","an","and","or","for","to","of","with","in","on","by","at","from","is","are","be"}
_TOKEN = re.compile(r"[A-Za-z0-9_]+")

def keywords_from_text(s: str, max_k: int = 5) -> List[str]:
    if not s:
        return []
    toks = [t.lower() for t in _TOKEN.findall(s)]
    toks = [t for t in toks if t not in _STOP and len(t) >= 3]
    seen, out = set(), []
    for t in toks:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:max_k]

def general_questions(cap_or_spec: str, n: int) -> List[Dict[str, Any]]:
    """
    Produce n self-verifiable, grader-friendly questions seeded by any capability/specialization text.
    """
    kws = keywords_from_text(cap_or_spec, 5) or ["general","task","quality","metrics","safety"]
    a, b = 17, 29
    celsius = 37.0
    fahrenheit = celsius * 9.0/5.0 + 32.0
    lst_in, lst_sorted = [7,3,11,-2,5], sorted([7,3,11,-2,5])

    pool: List[Dict[str, Any]] = [
        {"prompt": f"Reply with EXACTLY this string and nothing else: CERTIFIER_ECHO::{kws[0].upper()}",
         "grade": "exact", "expected": f"CERTIFIER_ECHO::{kws[0].upper()}"},
        {"prompt": "Return a JSON object with keys: role, inputs, outputs. Do not include extra commentary.",
         "grade": "json_keys", "expected": ["role","inputs","outputs"]},
        {"prompt": f"In one sentence, mention all of these terms exactly once: {', '.join(kws[:3])}.",
         "grade": "keywords", "expected": kws[:3]},
        {"prompt": f"Compute {a} + {b}. Return only the number.",
         "grade": "numeric", "expected": float(a+b)},
        {"prompt": f"Convert {celsius} °C to °F. Return only the number.",
         "grade": "numeric", "expected": float(fahrenheit)},
        {"prompt": f"Sort the numbers {lst_in} in ascending order and return them as CSV without spaces.",
         "grade": "list_csv_numeric", "expected": [float(x) for x in lst_sorted]},
        {"prompt": f"List two crucial considerations for quality in {kws[0]} systems.",
         "grade": "keywords", "expected": ["testing","monitoring"]},
        {"prompt": "Return JSON with keys: capability, specialization, metric. Do not include extra text.",
         "grade": "json_keys", "expected": ["capability","specialization","metric"]},
        {"prompt": "Extract and return only the number from this sentence: 'Throughput improved by 1250 requests/sec after tuning.'",
         "grade": "numeric", "expected": 1250.0},
        {"prompt": "Reply with EXACTLY: OK", "grade": "exact", "expected": "OK"},
        {"prompt": f"In one sentence, include these words: {', '.join(kws[:2])}, reliability.",
         "grade": "keywords", "expected": kws[:2] + ["reliability"]},
        {"prompt": "Return JSON with keys: name, version, compliance.",
         "grade": "json_keys", "expected": ["name","version","compliance"]},
    ]

    out, i = [], 0
    while len(out) < n:
        out.append(pool[i % len(pool)])
        i += 1
    return out
