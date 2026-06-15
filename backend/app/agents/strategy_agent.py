from typing import Dict, Any
from app.agents.base_agent import BaseAgent
from app.services.llm_service import LLMService

SYSTEM = """You are a Senior Quantitative Researcher at a top hedge fund.
Given a user's trading idea, output a JSON object with these fields:
- strategy_name (string)
- signal_type: one of "momentum", "mean_reversion", "trend_following"
- universe: list of 3-5 ticker symbols (US equities)
- lookback_days: integer 10-60
- entry_threshold: float 0.005-0.05
- exit_threshold: float -0.05 to -0.001
- narrative: 2-sentence explanation of the strategy rationale
"""


class StrategyAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="StrategyAgent", role="Researcher")

    def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        user_intent = message.get("content", "")
        prompt = f"Design a quantitative trading strategy for: {user_intent}"
        params = LLMService.generate_structured(SYSTEM, prompt)

        return {
            "agent": self.name,
            "status": "success",
            "strategy_params": params,
            "output": params.get("narrative", "Strategy generated."),
            "next_step": "backtest",
        }
