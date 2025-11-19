from typing import Dict, Any
from app.agents.base_agent import BaseAgent
from app.services.llm_service import LLMService

class PortfolioAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="PortfolioAgent", role="Portfolio Manager")

    def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        risk_analysis = message.get("output", "")
        
        # Simulate portfolio optimization
        prompt = f"Optimize portfolio based on: {risk_analysis}"
        response = LLMService.generate_response(prompt, system_role="You are a Portfolio Manager.")
        
        return {
            "agent": self.name,
            "status": "success",
            "output": response,
            "final_allocation": {"AAPL": 0.3, "MSFT": 0.3, "GOOGL": 0.2, "CASH": 0.2},
            "next_step": "execution"
        }
