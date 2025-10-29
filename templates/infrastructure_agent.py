#!/usr/bin/env python3
"""
NANDA Infrastructure Agent

Agent that bridges structural mismatches between how systems authenticate and how agents behave.
A trust fabric that carries verifiable proof of who the agent is, what is allowed to do, and for whom. 
"""
# sends a question and gets a response. Fix the agent facts and decides to get a certifications or not. 
# Agent orchestrator 
# https://github.com/projnanda/AgentOrchestrator 


import os
import sys
import json
import re
import requests
from datetime import datetime

# Add the streamlined adapter to the path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from nanda_core.core.adapter import NANDA

# A2A client
try:
    from python_a2a import A2AClient, Message, TextContent, MessageRole
except Exception:
    A2AClient = None  

# Infrastructure and Certifier Agent
from templates.certifier import (
    CertifierConfig,
    run_certification_once,
    start_certifier_loop,
    load_agent_facts,
    query_recent_runs,
)

# Config via env
AGENT_ID = os.getenv("AGENT_ID", "infra-agent")
AGENT_NAME = os.getenv("AGENT_NAME", "Infrastructure Agent")
PORT = int(os.getenv("PORT", "6030"))
REGISTRY_URL = os.getenv("REGISTRY_URL")          # e.g. https://registry.example.com
PUBLIC_URL = os.getenv("PUBLIC_URL")              # e.g. https://infra.example.com
ENABLE_TELEMETRY = os.getenv("ENABLE_TELEMETRY", "false").lower() in {"1", "true", "yes"}
REGISTER_ON_START = os.getenv("REGISTER_ON_START")  # allow override
if REGISTER_ON_START is None:
    # Default: register if a registry URL is present
    REGISTER_ON_START = bool(REGISTRY_URL)
else:
    REGISTER_ON_START = REGISTER_ON_START.lower() in {"1", "true", "yes"}

MONGO_URI = os.getenv("MONGO_URI")     
AWS_REGION = os.getenv("AWS_REGION")

# Certifier Wiring
AGENT_FACTS_PATH = os.getenv("AGENT_FACTS_PATH", "agent_facts.json")
CAP_PACKS_DIR    = os.getenv("CAPABILITY_PACKS_DIR", "capability_packs")

ENABLE_CERTIFIER = os.getenv("ENABLE_CERTIFIER", "false").lower() in {"1","true","yes"}
CERT_PERIOD_S    = int(os.getenv("CERTIFIER_PERIOD_SECONDS", "3600"))
CERT_NUM_Q       = int(os.getenv("CERTIFIER_NUM_QUESTIONS", "10"))
CERT_CAPABILITY  = os.getenv("CERTIFIER_CAPABILITY", "general")   # or "all"
CERT_AGENT_ID    = os.getenv("CERTIFIER_AGENT_ID")                # optional pin
CERT_MAX_CAPS    = int(os.getenv("CERTIFIER_MAX_CAPS_PER_RUN", "5"))
CERT_CLAIMED_ONLY= os.getenv("CERTIFIER_ONLY_CLAIMED", "true").lower() in {"1","true","yes"}

CERT_CFG = CertifierConfig(
    infrastructure_agent_id=AGENT_ID,
    registry_url=REGISTRY_URL,
    mongo_uri=MONGO_URI,
    mongo_db=os.getenv("MONGO_DB", "nest"),
    mongo_facts_coll=os.getenv("MONGO_FACTS_COLL", "agent_facts"),
    agent_facts_path=AGENT_FACTS_PATH,
    caps_dir=CAP_PACKS_DIR,
    default_capability=CERT_CAPABILITY,
    default_agent_id=CERT_AGENT_ID,
    period_seconds=CERT_PERIOD_S,
    max_caps_per_run=CERT_MAX_CAPS,
    claimed_only=CERT_CLAIMED_ONLY,
    A2AClient=A2AClient, Message=Message, TextContent=TextContent, MessageRole=MessageRole,
)


def _lookup_agent_url(agent_id: str) -> str | None:
    """Query the registry for an agent's base URL."""
    if not REGISTRY_URL:
        return None
    try:
        r = requests.get(f"{REGISTRY_URL}/lookup/{agent_id}", timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data.get("agent_url")
    except Exception:
        pass
    return None


def _a2a_whoami(agent_url: str, conversation_id: str = "verify-0") -> dict | None:
    """Send /whoami to the target agent and parse JSON."""
    if not agent_url:
        return None
    if not agent_url.endswith("/a2a"):
        agent_url = f"{agent_url}/a2a"
    if not A2AClient:
        return None

    try:
        client = A2AClient(agent_url, timeout=20)
        resp = client.send_message(
            Message(
                role=MessageRole.USER,
                content=TextContent(text="/whoami"),
                conversation_id=conversation_id,
            )
        )
        raw = None
        if hasattr(resp, "parts") and resp.parts:
            raw = getattr(resp.parts[0], "text", None)
        if not raw:
            raw = str(resp)

        # Extract first JSON object
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            return None
        return json.loads(m.group(0))
    except Exception:
        return None


def _verify_agent(expected: dict) -> tuple[bool, str]:
    """
    expected keys you can pass:
      - agent_id (required)
      - domain
      - specialization
      - capability  (single capability to check)
    """
    agent_id = expected.get("agent_id")
    if not agent_id:
        return False, "expected.agent_id is required"

    url = _lookup_agent_url(agent_id)
    if not url:
        return False, f"agent '{agent_id}' not found in registry"

    meta = _a2a_whoami(url)
    if not meta:
        return False, f"agent '{agent_id}' did not return /whoami metadata"

    checks = []
    checks.append(("agent_id", meta.get("agent_id") == agent_id))
    if "domain" in expected:
        checks.append(("domain", meta.get("domain") == expected["domain"]))
    if "specialization" in expected:
        checks.append(("specialization", meta.get("specialization") == expected["specialization"]))
    if "capability" in expected:
        caps = meta.get("capabilities") or []
        checks.append(("capability", expected["capability"] in caps))

    ok = all(flag for _, flag in checks) if checks else True
    details = ", ".join(f"{name}={'OK' if flag else 'NO'}" for name, flag in checks) or "no checks supplied"
    return ok, details

def _ensure_ec2_ready() -> str:
    return "ec2:skipped"  # TODO: add boto3 checks here later


def _log_to_mongo(record: dict) -> str:
    if not MONGO_URI:
        return "mongo:disabled"
    try:
        from pymongo import MongoClient
        cli = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        db = cli[os.getenv("MONGO_DB", "nest")]
        col = db[os.getenv("MONGO_CERTS_COLL", "certifications")]
        col.insert_one(record)
        return "mongo:ok"
    except Exception as e:
        return f"mongo:error:{e}"
    
def infra_agent_logic(message: str, conversation_id: str) -> str:
    """
    Define your agent's behavior here.
    
    Args:
        message: The incoming message text
        conversation_id: Unique conversation identifier
        
    Returns:
        Your agent's response string
    """
    
    # Example: Simple keyword-based responses
    # message_lower = message.lower() 
    message_lower = message.lower().strip()

    # whoami (self-ident)
    if message_lower in {"whoami", "/whoami"}:
        me = {
            "agent_id": AGENT_ID,
            "agent_name": AGENT_NAME,
            "domain": os.getenv("DOMAIN", "infrastructure"),
            "specialization": os.getenv("SPECIALIZATION", "cloud devops sre"),
            "capabilities": [c.strip() for c in os.getenv("CAPABILITIES", "verify,runbook").split(",") if c.strip()],
            "public_url": PUBLIC_URL,
            "registry_url": REGISTRY_URL,
        }
        return json.dumps(me, indent=2)

    # verify command
    if message_lower.startswith("verify "):
        # Parse key=value pairs
        tokens = [p for p in message.split() if "=" in p]
        expected = {k: v for k, v in (p.split("=", 1) for p in tokens)}
        ok, details = _verify_agent(expected)

        _ = _ensure_ec2_ready()
        mongo_status = _log_to_mongo({
            "kind": "verification",
            "expected": expected,
            "result": "PASS" if ok else "FAIL",
            "details": details,
            "at": datetime.utcnow().isoformat() + "Z",
        })

        return f"{'PASS' if ok else 'FAIL'} — {details} ({mongo_status})"
    
    # certification
    if message_lower.startswith("certify"):
        tokens = [p for p in message.split() if "=" in p]
        params = {k: v for k, v in (p.split("=", 1) for p in tokens)}
        tgt = params.get("agent_id")
        cap = params.get("capability", CERT_CAPABILITY)
        try:
            num = int(params.get("num", str(CERT_NUM_Q)))
        except Exception:
            num = CERT_NUM_Q
        try:
            run = run_certification_once(CERT_CFG, agent_id=tgt, capability=cap, num_questions=num)
            return json.dumps({
                "run_id": run["run_id"],
                "target_agent_id": run["target_agent_id"],
                "tested_capabilities": run["tested_capabilities"],
                "summary": run["summary"],
            }, indent=2)
        except Exception as e:
            return f"certify: error: {e}"

    # certification results
    if message_lower.startswith("agentfacts"):
        tokens = [p for p in message.split() if "=" in p]
        params = {k: v for k, v in (p.split("=", 1) for p in tokens)}
        aid = params.get("agent_id")
        cap = params.get("capability")
        last = int(params.get("last", "3"))
        try:
            data = query_recent_runs(AGENT_FACTS_PATH, agent_id=aid, capability=cap, last=last)
            return json.dumps(data, indent=2)
        except Exception as e:
            return f"agentfacts: error: {e}"

    if "hello" in message_lower or "hi" in message_lower:
        return "Hello! I'm a custom NANDA infrastructure agent. How can I help you?"
    
    elif "time" in message_lower:
        from datetime import datetime
        return f"Current time: {datetime.now().strftime('%H:%M:%S')}"
    
    elif "help" in message_lower:
        return """I'm a custom agent. I can:
        • Respond to greetings
        • Tell you the time  
        • Answer basic questions
        • Route messages to other agents with @agent_id
        • Verify other agents, e.g.: verify agent_id=<id> capability=<capability>
        • Certify agents:
            - certify [agent_id=<id>] [capability=general|all|<cap>] [num=10]
            - agentfacts [agent_id=<id>] [capability=<cap>] [last=3]
        
        What would you like to do?"""
    
    elif "calculate" in message_lower or any(op in message for op in ['+', '-', '*', '/']):
        try:
            # Simple calculator (be careful with eval in production!)
            expression = message.replace('calculate', '').strip()
            result = eval(expression)
            return f"Result: {result}"
        except:
            return "I can help with simple math. Try: 5 + 3"
    
    else:
        # Default response
        return f"I received: '{message}'. Type 'help' for what I can do!"


def main():
    """Main function to start your custom infrastructure agent"""
    
    # Check for API key (if your agent needs external services)
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️ ANTHROPIC_API_KEY not set (may be needed for some features)")
    
    # Start periodic certification if enabled
    if ENABLE_CERTIFIER:
        print(f"🔁 Certifier loop enabled: every {CERT_CFG.period_seconds}s | capability={CERT_CFG.default_capability} | agent={CERT_CFG.default_agent_id or 'round-robin'}")
        start_certifier_loop(CERT_CFG)

    # Create your NANDA agent (modify these parameters)
    nanda = NANDA(
        agent_id="infra_agent",           # Change this to your agent name
        agent_logic=infra_agent_logic,    # Your agent logic function
        port=6030,                            # Change port if needed
        registry_url=None,                    # Add registry URL if you have one
        public_url=None,                      # Add public URL for registration
        enable_telemetry=False                # Enable to track usage
    )
    
    print("""
🤖 Custom NANDA Infrastructure Agent Starting
===============================
Agent ID: {AGENT_ID}
Port: {PORT}
Type: Custom Logic
Registry URL: {REGISTRY_URL or '(none)'}
Public URL: {PUBLIC_URL or '(none)'}
Register on start: {REGISTER_ON_START}
===============================

📝 Test your agent:
• Send: 'hello'
• Send: 'what time is it?'
• Send: 'calculate 5 + 3'
• Send: 'help'
• Send: 'whoami'
• Send: 'verify agent_id=<id> capability=<capability>'
• Send: '@other_agent message' (to talk to other agents)

🛑 Press Ctrl+C to stop
    """)
    
    try:
        nanda.start(register=False)  # Set to True if you have a registry
    except KeyboardInterrupt:
        print("\n🛑 Custom agent stopped")


if __name__ == "__main__":
    main()

