# certifier/questions.py
import os, glob, json, math
from typing import Dict, Any, List
from .graders import keywords_from_text

CAP_PACKS_DIR = os.getenv("CAPABILITY_PACKS_DIR", "capability_packs")

def _builtin_pack_general(n: int) -> List[Dict[str, Any]]:
    base = [
        {"prompt": "Reply with exactly the string: CERTIFIER_ECHO", "grade": "exact", "expected": "CERTIFIER_ECHO"},
        {"prompt": "Return a valid JSON object with keys: title, steps.", "grade": "json_keys", "expected": ["title","steps"]},
        {"prompt": "List three safety considerations when handling user passwords.", "grade": "keywords", "expected": ["hashing","salt","rate limit"]},
        {"prompt": "What HTTP status code means Unauthorized? Return only the number.", "grade": "numeric", "expected": 401.0},
        {"prompt": "Extract and return only the number from: 'Users increased by 1250 last week.'", "grade": "numeric", "expected": 1250.0},
    ]
    out = []
    i = 0
    while len(out) < n:
        out.append(base[i % len(base)]); i += 1
    return out

def _builtin_pack_math(n: int) -> List[Dict[str, Any]]:
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
        out.append(bank[i % len(bank)]); i += 1
    return out

def _builtin_pack_coffee(n: int) -> List[Dict[str, Any]]:
    bank = [
        {"prompt": "What brew water temperature (°C) is typical for espresso? Return a number.", "grade": "range", "expected": [90.0, 96.0]},
        {"prompt": "List three essential steps to pull an espresso shot.", "grade": "keywords", "expected": ["grind","tamp","extract"]},
        {"prompt": "What is a common espresso brew ratio 1:x? Return only x.", "grade": "numeric", "expected": 2.0},
        {"prompt": "Name two variables to adjust if a shot is channeling.", "grade": "keywords", "expected": ["distribution","tamp"]},
        {"prompt": "Return JSON with keys: beans, grind_size, brew_time_s.", "grade": "json_keys", "expected": ["beans","grind_size","brew_time_s"]},
    ]
    out, i = [], 0
    while len(out) < n:
        out.append(bank[i % len(bank)]); i += 1
    return out

def _builtin_pack_physics(n: int) -> List[Dict[str, Any]]:
    bank = [
        {"prompt": "What is g on Earth in m/s^2? Return a number.", "grade": "range", "expected": [9.7, 9.9]},
        {"prompt": "State Newton's second law succinctly.", "grade": "keywords", "expected": ["force","mass","acceleration"]},
        {"prompt": "Kinetic energy of 2 kg object at 3 m/s (J)? Return the number.", "grade": "numeric", "expected": 0.5*2*3*3},
        {"prompt": "What is the SI unit of force?", "grade": "keywords", "expected": ["newton"]},
        {"prompt": "Return JSON with keys: law, formula (F=ma).", "grade": "json_keys", "expected": ["law","formula"]},
    ]
    out, i = [], 0
    while len(out) < n:
        out.append(bank[i % len(bank)]); i += 1
    return out

def _builtin_pack_art(n: int) -> List[Dict[str, Any]]:
    bank = [
        {"prompt": "List three characteristics of Impressionism.", "grade": "keywords", "expected": ["light","brushstroke","outdoor"]},
        {"prompt": "Name two artists associated with Cubism.", "grade": "keywords", "expected": ["picasso","braque"]},
        {"prompt": "What is chiaroscuro?", "grade": "keywords", "expected": ["light","shadow"]},
        {"prompt": "Return JSON with keys: style, elements.", "grade": "json_keys", "expected": ["style","elements"]},
        {"prompt": "Which movement emphasized feelings and individual experience in late 18th–early 19th c. Europe?", "grade": "keywords", "expected": ["romanticism"]},
    ]
    out
