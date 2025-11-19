from typing import Dict, Any
from app.agents.base_agent import BaseAgent
from app.services.llm_service import LLMService

class StrategyAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="StrategyAgent", role="Researcher")

    def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        user_intent = message.get("content", "")
        
        # Use LLM to generate strategy
        prompt = f"Generate a trading strategy based on: {user_intent}"
        response = LLMService.generate_response(prompt, system_role="You are a Senior Quant Researcher.")
        
        return {
            "agent": self.name,
            "status": "success",
            "output": response,
            "next_step": "backtest"
        }
