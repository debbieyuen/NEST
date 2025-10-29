# certifier/registry.py
import json, re, requests
from typing import Optional, Tuple, Dict, Any, List

def list_agents(registry_url: Optional[str]) -> List[Dict[str, Any]]:
    if not registry_url:
        return []
    try:
        r = requests.get(f"{registry_url}/list", timeout=10)
        if r.status_code == 200:
            data = r.json()
            agents = data.get("agents") or []
            out = []
            for a in agents:
                aid = a.get("agent_id") or a.get("id")
                url = a.get("agent_url") or a.get("url")
                if aid and url:
                    out.append({"agent_id": aid, "agent_url": url})
            return out
    except Exception:
        pass
    return []

def lookup_agent_url(registry_url: Optional[str], agent_id: str) -> Optional[str]:
    if not registry_url:
        return None
    try:
        r = requests.get(f"{registry_url}/lookup/{agent_id}", timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data.get("agent_url")
    except Exception:
        pass
    return None

_JSON = re.compile(r"\{.*\}", re.DOTALL)

def whoami(agent_url: str, A2AClient, Message, TextContent, MessageRole) -> Optional[Dict[str, Any]]:
    if not agent_url:
        return None
    if not agent_url.endswith("/a2a"):
        agent_url = f"{agent_url}/a2a"
    if not A2AClient:
        return None
    try:
        client = A2AClient(agent_url, timeout=20)
        resp = client.send_message(Message(role=MessageRole.USER, content=TextContent(text="/whoami"), conversation_id="verify-0"))
        raw = None
        if hasattr(resp, "parts") and resp.parts:
            raw = getattr(resp.parts[0], "text", None)
        if not raw:
            raw = str(resp)
        m = _JSON.search(raw or "")
        if not m:
            return None
        return json.loads(m.group(0))
    except Exception:
        return None

def a2a_ask(agent_url: str, question: str, conv_id: str, A2AClient, Message, TextContent, MessageRole) -> Optional[str]:
    if not agent_url:
        return None
    if not agent_url.endswith("/a2a"):
        agent_url = f"{agent_url}/a2a"
    if not A2AClient:
        return None
    try:
        client = A2AClient(agent_url, timeout=40)
        resp = client.send_message(
            Message(role=MessageRole.USER, content=TextContent(text=question), conversation_id=conv_id)
        )
        if hasattr(resp, "parts") and resp.parts:
            text = getattr(resp.parts[0], "text", None)
            if text:
                return text.strip()
        return str(resp).strip()
    except Exception:
        return None
