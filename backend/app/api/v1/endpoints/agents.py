from fastapi import APIRouter, HTTPException, Body
from app.agents.manager import AgentManager

router = APIRouter()
manager = AgentManager()

@router.post("/workflow")
def run_agent_workflow(
    request: str = Body(..., embed=True, description="User request for trading strategy")
):
    """
    Trigger the multi-agent workflow.
    """
    try:
        result = manager.run_workflow(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
