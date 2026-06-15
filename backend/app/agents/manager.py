from typing import Dict, Any, Iterator
from app.agents.agent_runtime import research_blocking, research_stream


class AgentManager:
    """Thin wrapper over the agentic research runtime (see app/agents/agent_runtime.py)."""

    def run_workflow(self, user_request: str) -> Dict[str, Any]:
        return research_blocking(user_request)

    def stream_workflow(self, user_request: str) -> Iterator[Dict[str, Any]]:
        return research_stream(user_request)
