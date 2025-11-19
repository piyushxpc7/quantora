from typing import Dict, Any
from app.agents.base_agent import BaseAgent
from app.services.llm_service import LLMService

class RiskAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="RiskAgent", role="Risk Manager")

    def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        backtest_results = message.get("output", "")
        
        # Simulate risk analysis
        prompt = f"Analyze risk for: {backtest_results}"
        response = LLMService.generate_response(prompt, system_role="You are a Risk Manager.")
        
        return {
            "agent": self.name,
            "status": "success",
            "output": response,
            "risk_approved": True,
            "next_step": "portfolio"
        }
