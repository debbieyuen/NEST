#!/usr/bin/env python3
"""
NANDA Infrastructure Agent

Agent that bridges structural mismatches between how systems authenticate and how agents behave.
A trust fabric that carries verifiable proof of who the agent is, what is allowed to do, and for whom. 
"""

import os
import sys
from datetime import datetime

# Add the streamlined adapter to the path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from nanda_core.core.adapter import NANDA

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
• Send: '@other_agent message' (to talk to other agents)

🛑 Press Ctrl+C to stop
    """)
    
    try:
        nanda.start(register=False)  # Set to True if you have a registry
    except KeyboardInterrupt:
        print("\n🛑 Custom agent stopped")


if __name__ == "__main__":
    main()

