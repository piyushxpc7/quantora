from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories import paper_repo as repo

router = APIRouter()


@router.get("/account")
async def account(db: AsyncSession = Depends(get_db)):
    return await repo.get_account(db)


@router.post("/rebalance")
async def rebalance(strategy_id: int = Body(..., embed=True), db: AsyncSession = Depends(get_db)):
    return await repo.rebalance(db, strategy_id)


@router.get("/trades")
async def trades(db: AsyncSession = Depends(get_db)):
    return [
        {
            "id": t.id,
            "ticker": t.ticker,
            "side": t.side,
            "shares": round(t.shares, 4),
            "price": round(t.price, 2),
            "status": t.status,
            "reason": t.reason,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in await repo.list_trades(db)
    ]
