from typing import Any, Dict, List, Optional
import json
from app.core.config import settings

try:
    from openai import OpenAI
    _openai_available = True
except ImportError:
    _openai_available = False


def _mock_response(prompt: str) -> str:
    p = prompt.lower()
    if "strategy" in p:
        return json.dumps({
            "strategy_name": "Momentum Strategy",
            "signal_type": "momentum",
            "universe": ["AAPL", "MSFT", "GOOGL"],
            "lookback_days": 20,
            "entry_threshold": 0.02,
            "exit_threshold": -0.01,
            "narrative": "Momentum strategy focusing on Tech sector with a 20-day lookback period based on RSI and MACD signals."
        })
    elif "backtest" in p:
        return json.dumps({"narrative": "Strategy shows strong momentum characteristics with consistent outperformance."})
    elif "risk" in p:
        return json.dumps({"narrative": "Risk metrics are within acceptable bounds. Portfolio shows resilience under stress scenarios."})
    elif "portfolio" in p:
        return json.dumps({"narrative": "HRP optimization yields a well-diversified allocation with controlled concentration risk."})
    return json.dumps({"narrative": "Request processed successfully."})


class LLMService:
    _client: Optional[Any] = None

    @classmethod
    def _get_client(cls):
        if cls._client is None and _openai_available and settings.OPENAI_API_KEY:
            cls._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return cls._client

    @classmethod
    def is_live(cls) -> bool:
        """True when a real OpenAI client is configured (vs offline mock)."""
        return cls._get_client() is not None

    @classmethod
    def generate_response(cls, prompt: str, system_role: str = "You are a helpful assistant.") -> str:
        client = cls._get_client()
        if client is None:
            return _mock_response(prompt)
        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_role},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
            )
            return response.choices[0].message.content or ""
        except Exception:
            return _mock_response(prompt)

    @classmethod
    def generate_structured(cls, system: str, prompt: str) -> Dict[str, Any]:
        client = cls._get_client()
        if client is None:
            return json.loads(_mock_response(prompt))
        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system + "\n\nRespond with valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=800,
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception:
            return json.loads(_mock_response(prompt))

    @classmethod
    def agent_turn(
        cls, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        One turn of an OpenAI tool-calling agent. Returns
        {"content": str, "tool_calls": [{"id","name","arguments": dict}]}
        or None when no live client is configured (caller should fall back to the mock agent).
        """
        client = cls._get_client()
        if client is None:
            return None
        try:
            resp = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=700,
            )
            msg = resp.choices[0].message
            tool_calls = []
            for tc in (msg.tool_calls or []):
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append({"id": tc.id, "name": tc.function.name, "arguments": args})
            return {"content": msg.content or "", "tool_calls": tool_calls}
        except Exception as e:
            return {"content": f"(LLM error, continuing) {e}", "tool_calls": []}
