from typing import Dict, Any
from app.agents.base_agent import BaseAgent
from app.services.llm_service import LLMService

class BacktestAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="BacktestAgent", role="Validator")

    def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        strategy_content = message.get("output", "")
        
        # Simulate backtesting logic
        # In real app, this would parse the strategy and run it against historical data
        prompt = f"Run backtest for strategy: {strategy_content}"
        response = LLMService.generate_response(prompt, system_role="You are a Quantitative Analyst.")
        
        return {
            "agent": self.name,
            "status": "success",
            "output": response,
            "metrics": {"cagr": 0.15, "sharpe": 1.8}, # Mock metrics
            "next_step": "risk"
        }
