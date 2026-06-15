from typing import Dict, Any
from app.agents.base_agent import BaseAgent
from app.services.llm_service import LLMService
from app.core.config import settings

SYSTEM = """You are a Chief Risk Officer at a hedge fund. Given portfolio risk metrics,
write a 2-sentence professional risk assessment. Mention VaR, CVaR, and whether the strategy
passes risk controls. Respond with JSON containing only a "narrative" field."""


class RiskAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="RiskAgent", role="Risk Manager")

    def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        metrics = message.get("metrics", {})
        cvar = metrics.get("cvar_95", 0.0)
        var = metrics.get("var_95", 0.0)
        sharpe = metrics.get("sharpe_ratio", 0.0)
        limit = settings.RISK_CVAR_LIMIT

        # Real risk gate: block if CVaR (loss) exceeds limit
        # cvar_95 is negative (a loss), so we check abs value
        risk_approved = abs(cvar) <= limit

        prompt = (
            f"Portfolio risk metrics: VaR(95%)={var:.2%}, CVaR(95%)={cvar:.2%}, "
            f"Sharpe={sharpe:.2f}, CVaR limit={limit:.2%}. "
            f"Risk {'APPROVED' if risk_approved else 'REJECTED'}."
        )
        narr = LLMService.generate_structured(SYSTEM, prompt)

        return {
            "agent": self.name,
            "status": "success",
            "output": narr.get("narrative", f"Risk check {'passed' if risk_approved else 'failed'}."),
            "risk_approved": risk_approved,
            "risk_metrics": {
                "var_95": var,
                "cvar_95": cvar,
                "cvar_limit": limit,
                "sharpe_ratio": sharpe,
            },
            "next_step": "portfolio",
        }
