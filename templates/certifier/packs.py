# certifier/packs.py
import os, json, glob
from typing import Dict, List, Any, Callable
from .generator import general_questions

# Built-in example packs (you can add more or remove if you want only-general)
def pack_general(n: int):   return general_questions("general", n)
def pack_math(n: int):
    bank = [
        {"prompt": "Compute 13 + 29.", "grade": "numeric", "expected": 42.0},
        {"prompt": "Compute 144 - 57.", "grade": "numeric", "expected": 87.0},
        {"prompt": "Compute 12 * 17.", "grade": "numeric", "expected": 204.0},
        {"prompt": "Compute 144 / 12. Return only the number.", "grade": "numeric", "expected": 12.0},
        {"prompt": "What is 2^10? Return only the number.", "grade": "numeric", "expected": 1024.0},
        {"prompt": "What is sqrt(196)? Return only the number.", "grade": "numeric", "expected": 14.0},
        {"prompt": "What is 7! ?", "grade": "numeric", "expected": 5040.0},
        {"prompt": "What is the gcd of 84 and 30?", "grade": "numeric", "expected": 6.0},
        {"prompt": "Solve for x: 3x + 5 = 26. Give only x.", "grade": "numeric", "expected": 7.0},
        {"prompt": "Determinant of [[2,1],[3,4]]?", "grade": "numeric", "expected": 5.0},
    ]
    out, i = [], 0
    while len(out) < n:
        out.append(bank[i % len(bank)])
        i += 1
    return out

BUILTIN: Dict[str, Callable[[int], List[dict]]] = {
    "general": pack_general,
    "math": pack_math,
}

def load_external_packs(dirpath: str) -> Dict[str, List[Dict[str, Any]]]:
    packs: Dict[str, List[Dict[str, Any]]] = {}
    try:
        if not os.path.isdir(dirpath):
            return packs
        for path in glob.glob(os.path.join(dirpath, "*.json")):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cap = str(data.get("capability", "")).strip().lower()
            qs = data.get("questions") or []
            if cap and isinstance(qs, list) and qs:
                packs[cap] = qs
    except Exception:
        pass
    return packs

def repeat_to_n(qs: List[dict], n: int) -> List[dict]:
    out, i = [], 0
    while len(out) < n:
        out.append(qs[i % len(qs)])
        i += 1
    return out

def questions_for(capability: str, n: int, external_packs: Dict[str, List[dict]]):
    cap = (capability or "").strip().lower()
    if cap in external_packs:
        return repeat_to_n(external_packs[cap], n)
    if cap in BUILTIN:
        return BUILTIN[cap](n)
    # fallback: generate general questions seeded by the raw capability text
    return general_questions(capability, n)
