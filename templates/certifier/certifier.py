# certifier/certifier.py
import os, time, json, threading
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from . import registry as reg
from .graders import apply_grader
from .packs import load_external_packs, questions_for

@dataclass
class CertifierConfig:
    infrastructure_agent_id: str
    registry_url: Optional[str]
    mongo_uri: Optional[str] = None
    mongo_db: str = "nest"
    mongo_facts_coll: str = "agent_facts"
    agent_facts_path: str = "agent_facts.json"
    caps_dir: str = "capability_packs"
    default_capability: str = "general"
    default_agent_id: Optional[str] = None
    period_seconds: int = 3600
    max_caps_per_run: int = 5
    claimed_only: bool = True
    # A2A classes
    A2AClient: Any = None
    Message: Any = None
    TextContent: Any = None
    MessageRole: Any = None

_LOCK = threading.Lock()

def _save_json_atomic(path: str, data: dict):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def load_agent_facts(path: str) -> dict:
    if not os.path.exists(path):
        return {"runs": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"runs": []}

def _persist_run(cfg: CertifierConfig, run: dict):
    with _LOCK:
        data = load_agent_facts(cfg.agent_facts_path)
        data.setdefault("runs", []).append(run)
        _save_json_atomic(cfg.agent_facts_path, data)
    if cfg.mongo_uri:
        try:
            from pymongo import MongoClient
            cli = MongoClient(cfg.mongo_uri, serverSelectionTimeoutMS=3000)
            db = cli[cfg.mongo_db]
            col = db[cfg.mongo_facts_coll]
            col.insert_one(run)
        except Exception:
            pass

def _discover_capabilities(cfg: CertifierConfig, agent_url: str) -> List[str]:
    meta = reg.whoami(agent_url, cfg.A2AClient, cfg.Message, cfg.TextContent, cfg.MessageRole)
    if not meta:
        return []
    caps = meta.get("capabilities") or []
    return [str(c).strip().lower() for c in caps if isinstance(c, str)]

def _select_agent(cfg: CertifierConfig, candidate: Optional[str]) -> Optional[Tuple[str, str]]:
    if candidate:
        url = reg.lookup_agent_url(cfg.registry_url, candidate)
        return (candidate, url) if url else None
    agents = reg.list_agents(cfg.registry_url)
    if not agents:
        return None
    # simple round robin via time
    idx = int(time.time()) % len(agents)
    chosen = agents[idx]
    return chosen["agent_id"], chosen["agent_url"]

def _caps_to_test(requested: str, claimed: List[str], cfg: CertifierConfig) -> List[str]:
    req = (requested or "").strip().lower()
    if req != "all":
        return [req]
    if cfg.claimed_only and claimed:
        caps = claimed[:]
    else:
        # all known: union of claimed plus a generic “general”
        caps = sorted(set((claimed or []) + ["general"]))
    return caps[: cfg.max_caps_per_run]

def run_certification_once(cfg: CertifierConfig,
                           agent_id: Optional[str] = None,
                           capability: str = "general",
                           num_questions: int = 10) -> dict:
    chosen = _select_agent(cfg, agent_id or cfg.default_agent_id)
    if not chosen:
        raise RuntimeError("No agent available / not found in registry")
    target_id, target_url = chosen

    claimed_caps = _discover_capabilities(cfg, target_url)
    external = load_external_packs(cfg.caps_dir)

    cap_runs: List[dict] = []
    total_q, total_correct, total_score = 0, 0, 0

    for cap in _caps_to_test(capability, claimed_caps, cfg):
        qs = questions_for(cap, num_questions, external)
        claimed = cap in claimed_caps if claimed_caps else False

        results = []
        correct_count = 0
        score_sum = 0

        for idx, q in enumerate(qs, start=1):
            resp_text = reg.a2a_ask(
                target_url, q["prompt"], conv_id=f"certify-{target_id}-{cap}",
                A2AClient=cfg.A2AClient, Message=cfg.Message, TextContent=cfg.TextContent, MessageRole=cfg.MessageRole
            )
            ok, score, detail = apply_grader(q, resp_text)
            correct_count += 1 if ok else 0
            score_sum += score
            results.append({
                "index": idx,
                "prompt": q["prompt"],
                "grade": q.get("grade"),
                "expected": q.get("expected"),
                "response": resp_text,
                "correct": ok,
                "score_1_to_5": score,
                "detail": detail,
            })

        total_q += len(qs); total_correct += correct_count; total_score += score_sum
        cap_runs.append({
            "capability": cap,
            "capability_claimed": claimed,
            "num_questions": len(qs),
            "results": results,
            "summary": {
                "correct": correct_count,
                "accuracy": round(correct_count / max(1, len(qs)), 3),
                "avg_score": round(score_sum / max(1, len(qs)), 3),
            }
        })

    run = {
        "run_id": f"{target_id}-{int(time.time())}",
        "at": datetime.utcnow().isoformat() + "Z",
        "infrastructure_agent_id": cfg.infrastructure_agent_id,
        "target_agent_id": target_id,
        "target_agent_url": target_url,
        "claimed_capabilities": claimed_caps,
        "tested_capabilities": [cr["capability"] for cr in cap_runs],
        "capability_runs": cap_runs,
        "summary": {
            "total_questions": total_q,
            "total_correct": total_correct,
            "overall_accuracy": round(total_correct / max(1, total_q), 3),
            "overall_avg_score": round(total_score / max(1, total_q), 3),
        }
    }
    _persist_run(cfg, run)
    return run

def _loop(cfg: CertifierConfig):
    while True:
        try:
            run_certification_once(cfg, capability=cfg.default_capability)
        except Exception as e:
            print(f"[certifier] run failed: {e}")
        time.sleep(max(5, cfg.period_seconds))

def start_certifier_loop(cfg: CertifierConfig):
    t = threading.Thread(target=_loop, args=(cfg,), daemon=True)
    t.start()

def query_recent_runs(agent_facts_path: str, *, agent_id: str | None = None,
                      capability: str | None = None, last: int = 3) -> dict:
    data = load_agent_facts(agent_facts_path)
    runs = data.get("runs", [])
    out = []
    for r in reversed(runs):
        if agent_id and r.get("target_agent_id") != agent_id:
            continue
        if capability and (capability not in r.get("tested_capabilities", [])):
            continue
        out.append({
            "run_id": r.get("run_id"),
            "at": r.get("at"),
            "target_agent_id": r.get("target_agent_id"),
            "tested_capabilities": r.get("tested_capabilities"),
            "summary": r.get("summary"),
        })
        if len(out) >= last:
            break
    return {"last_runs": out}
