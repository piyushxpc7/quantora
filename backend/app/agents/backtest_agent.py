from typing import Dict, Any
from app.agents.base_agent import BaseAgent
from app.services.llm_service import LLMService
from app.quant.backtester import run_backtest

SYSTEM = """You are a Quantitative Analyst. Given backtest performance metrics, write a 2-sentence
professional assessment. Be specific about the Sharpe ratio, CAGR, and max drawdown.
Respond with JSON containing only a "narrative" field."""


class BacktestAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="BacktestAgent", role="Validator")

    def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        params = message.get("strategy_params", {})
        universe = params.get("universe", ["AAPL", "MSFT", "GOOGL"])
        signal_type = params.get("signal_type", "momentum")
        lookback_days = params.get("lookback_days", 20)
        entry_threshold = params.get("entry_threshold", 0.02)

        result = run_backtest(
            universe=universe,
            signal_type=signal_type,
            lookback_days=lookback_days,
            entry_threshold=entry_threshold,
        )

        if "error" in result:
            return {
                "agent": self.name,
                "status": "error",
                "output": result["error"],
                "metrics": {},
                "equity_curve": [],
                "next_step": "risk",
            }

        metrics = result.get("metrics", {})
        prompt = f"Backtest results: {metrics}"
        narr = LLMService.generate_structured(SYSTEM, prompt)

        return {
            "agent": self.name,
            "status": "success",
            "output": narr.get("narrative", "Backtest complete."),
            "metrics": metrics,
            "equity_curve": result.get("equity_curve", []),
            "universe": universe,
            "next_step": "risk",
        }
