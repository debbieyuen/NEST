# certifier/graders.py
import json, re
from typing import Any, List, Tuple, Optional

_NUM = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")

def extract_first_number(text: str) -> Optional[float]:
    if not text:
        return None
    m = _NUM.search(text.replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None

def grade_numeric(expected: float, response: Optional[str]) -> Tuple[bool, int, str]:
    got = extract_first_number(response or "")
    if got is None:
        return False, 1, "no numeric value found"
    err = abs(got - expected) if expected == 0 else abs((got - expected) / expected)
    if err == 0:       return True, 5, "exact"
    if err < 1e-3:     return True, 4, f"rel_err={err:.2e}"
    if err < 1e-2:     return False, 3, f"close rel_err={err:.2e}"
    if err < 5e-2:     return False, 2, f"far rel_err={err:.2e}"
    return False, 1, f"wrong rel_err={err:.2e}"

def grade_exact(expected: str, response: Optional[str]) -> Tuple[bool, int, str]:
    resp = (response or "").strip()
    ok = (resp == expected)
    return ok, (5 if ok else 1), ("match" if ok else f"expected '{expected}'")

def grade_keywords(expected_keywords: List[str], response: Optional[str]) -> Tuple[bool, int, str]:
    resp = (response or "").lower()
    hits = sum(1 for k in expected_keywords if k.lower() in resp)
    ratio = hits / max(1, len(expected_keywords))
    if ratio >= 0.9: return True, 5, f"keywords {hits}/{len(expected_keywords)}"
    if ratio >= 0.7: return True, 4, f"keywords {hits}/{len(expected_keywords)}"
    if ratio >= 0.5: return False, 3, f"keywords {hits}/{len(expected_keywords)}"
    if ratio >= 0.3: return False, 2, f"keywords {hits}/{len(expected_keywords)}"
    return False, 1, f"keywords {hits}/{len(expected_keywords)}"

def grade_range(expected_min: float, expected_max: float, response: Optional[str]) -> Tuple[bool, int, str]:
    got = extract_first_number(response or "")
    if got is None:
        return False, 1, "no numeric value found"
    ok = expected_min <= got <= expected_max
    return ok, (5 if ok else 1), f"value={got} expected [{expected_min},{expected_max}]"

def grade_json_keys(required_keys: List[str], response: Optional[str]) -> Tuple[bool, int, str]:
    try:
        obj = json.loads(response or "")
    except Exception:
        return False, 1, "invalid JSON"
    miss = [k for k in required_keys if k not in obj]
    ok = not miss
    score = 5 if ok else max(1, 5 - len(miss))
    return ok, score, ("ok" if ok else f"missing: {', '.join(miss)}")

def grade_list_csv_numeric(expected_list: List[float], response: Optional[str]) -> Tuple[bool, int, str]:
    if not response:
        return False, 1, "empty"
    nums = [float(m.group(0)) for m in _NUM.finditer(response.replace(" ", ""))]
    ok = len(nums) == len(expected_list) and all(abs(a - b) < 1e-9 for a, b in zip(nums, expected_list))
    return ok, (5 if ok else 1), f"got={nums} expected={expected_list}"

def apply_grader(q: dict, response: Optional[str]) -> Tuple[bool, int, str]:
    t = q.get("grade")
    exp = q.get("expected")
    if t == "numeric":        return grade_numeric(float(exp), response)
    if t == "exact":          return grade_exact(str(exp), response)
    if t == "keywords":       return grade_keywords(list(exp), response)
    if t == "range":          return grade_range(float(exp[0]), float(exp[1]), response)
    if t == "json_keys":      return grade_json_keys(list(exp), response)
    if t == "list_csv_numeric": return grade_list_csv_numeric([float(x) for x in exp], response)
    # fallback
    if exp is not None:       return grade_exact(str(exp), response)
    return False, 1, "no grader"
