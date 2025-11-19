from fastapi import APIRouter

from app.api.v1.endpoints import market_data, drift, agents

api_router = APIRouter()

@api_router.get("/health")
def health_check():
    return {"status": "healthy", "module": "api_v1"}

api_router.include_router(market_data.router, prefix="/market-data", tags=["market-data"])
api_router.include_router(drift.router, prefix="/drift", tags=["drift"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
