from typing import List, Dict

class LLMService:
    @staticmethod
    def generate_response(prompt: str, system_role: str = "You are a helpful assistant.") -> str:
        """
        Mock LLM response generation.
        In a real implementation, this would call OpenAI/Anthropic APIs.
        """
        # Simple mock logic based on keywords
        if "strategy" in prompt.lower():
            return "Based on current market conditions, I recommend a Momentum Strategy focusing on Tech sector with a 20-day lookback period."
        elif "backtest" in prompt.lower():
            return "Backtest complete. CAGR: 15%, Max Drawdown: -12%, Sharpe Ratio: 1.8."
        elif "risk" in prompt.lower():
            return "Risk Analysis: VaR (95%) is 2.5%. Portfolio is within risk limits."
        elif "portfolio" in prompt.lower():
            return "Optimization complete. Recommended allocation: AAPL 30%, MSFT 30%, GOOGL 20%, CASH 20%."
        else:
            return "I received your request and am processing it."
