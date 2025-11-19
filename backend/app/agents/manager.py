from typing import Dict, Any
from app.agents.strategy_agent import StrategyAgent
from app.agents.backtest_agent import BacktestAgent
from app.agents.risk_agent import RiskAgent
from app.agents.portfolio_agent import PortfolioAgent

class AgentManager:
    def __init__(self):
        self.strategy_agent = StrategyAgent()
        self.backtest_agent = BacktestAgent()
        self.risk_agent = RiskAgent()
        self.portfolio_agent = PortfolioAgent()

    def run_workflow(self, user_request: str) -> Dict[str, Any]:
        """
        Run the full agent workflow: Strategy -> Backtest -> Risk -> Portfolio
        """
        workflow_log = []
        
        # Step 1: Strategy
        msg = {"content": user_request}
        strategy_result = self.strategy_agent.process(msg)
        workflow_log.append(strategy_result)
        
        # Step 2: Backtest
        backtest_result = self.backtest_agent.process(strategy_result)
        workflow_log.append(backtest_result)
        
        # Step 3: Risk
        risk_result = self.risk_agent.process(backtest_result)
        workflow_log.append(risk_result)
        
        # Step 4: Portfolio
        if risk_result.get("risk_approved"):
            portfolio_result = self.portfolio_agent.process(risk_result)
            workflow_log.append(portfolio_result)
        else:
            workflow_log.append({"agent": "System", "status": "halted", "reason": "Risk check failed"})
            
        return {
            "status": "completed",
            "workflow_log": workflow_log,
            "final_output": workflow_log[-1]
        }
