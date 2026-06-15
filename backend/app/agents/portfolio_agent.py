from typing import Dict, Any
from app.agents.base_agent import BaseAgent
from app.services.llm_service import LLMService
from app.quant.portfolio import optimize_portfolio

SYSTEM = """You are a Portfolio Manager at a hedge fund. Given HRP/Mean-Variance optimized
portfolio weights and metrics, write a 2-sentence professional assessment of the allocation.
Respond with JSON containing only a "narrative" field."""


class PortfolioAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="PortfolioAgent", role="Portfolio Manager")

    def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        universe = message.get("universe", ["AAPL", "MSFT", "GOOGL"])
        opt_result = optimize_portfolio(universe, method="hrp")
        weights = opt_result.get("weights", {})

        prompt = f"Portfolio optimization result: {opt_result}"
        narr = LLMService.generate_structured(SYSTEM, prompt)

        return {
            "agent": self.name,
            "status": "success",
            "output": narr.get("narrative", "Portfolio optimized."),
            "final_allocation": weights,
            "optimization_method": opt_result.get("method", "hrp"),
            "next_step": "execution",
        }
