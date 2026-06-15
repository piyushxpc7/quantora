from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.config import settings
from app.models.paper import PaperPosition, PaperTrade, PaperSnapshot
from app.models.monitoring import MonitoredStrategy
from app.models.workflow import WorkflowRun
from app.quant import paper_broker as broker


async def _positions(db: AsyncSession) -> List[PaperPosition]:
    res = await db.execute(select(PaperPosition))
    return list(res.scalars().all())


async def _cash(db: AsyncSession) -> float:
    """Cash = starting cash − net invested at cost basis (derived from positions)."""
    invested = sum(p.shares * p.avg_price for p in await _positions(db))
    return settings.PAPER_STARTING_CASH - invested


async def get_account(db: AsyncSession) -> Dict[str, Any]:
    positions = await _positions(db)
    tickers = [p.ticker for p in positions if p.shares > 0]
    prices = broker.latest_prices(tickers) if tickers else {}

    pos_out, market_value = [], 0.0
    for p in positions:
        if p.shares <= 0:
            continue
        last = prices.get(p.ticker, p.avg_price)
        mv = p.shares * last
        market_value += mv
        upnl = (last - p.avg_price) * p.shares
        pos_out.append({
            "ticker": p.ticker,
            "shares": round(p.shares, 4),
            "avg_price": round(p.avg_price, 2),
            "last_price": round(last, 2),
            "market_value": round(mv, 2),
            "unrealized_pnl": round(upnl, 2),
            "unrealized_pct": round((last / p.avg_price - 1) if p.avg_price else 0.0, 4),
        })

    cash = await _cash(db)
    equity = cash + market_value
    for p in pos_out:
        p["weight"] = round(p["market_value"] / equity, 4) if equity else 0.0

    snaps = (await db.execute(select(PaperSnapshot).order_by(PaperSnapshot.created_at))).scalars().all()
    curve = [{"date": s.created_at.isoformat()[:19] if s.created_at else "", "value": round(s.equity, 2)} for s in snaps]
    if not curve:
        curve = [{"date": "start", "value": settings.PAPER_STARTING_CASH}, {"date": "now", "value": round(equity, 2)}]

    return {
        "cash": round(cash, 2),
        "equity": round(equity, 2),
        "starting_cash": settings.PAPER_STARTING_CASH,
        "pnl": round(equity - settings.PAPER_STARTING_CASH, 2),
        "pnl_pct": round(equity / settings.PAPER_STARTING_CASH - 1, 4),
        "positions": sorted(pos_out, key=lambda x: -x["market_value"]),
        "equity_curve": curve,
    }


async def _target_weights(db: AsyncSession, strat: MonitoredStrategy) -> Dict[str, float]:
    weights: Dict[str, float] = {}
    if strat.run_id:
        run = (await db.execute(select(WorkflowRun).where(WorkflowRun.id == strat.run_id))).scalar_one_or_none()
        if run and run.final_allocation:
            weights = {k: float(v) for k, v in run.final_allocation.items()}
    if not weights and strat.universe:
        w = 1.0 / len(strat.universe)
        weights = {t: w for t in strat.universe}
    return weights


async def rebalance(db: AsyncSession, strategy_id: int) -> Dict[str, Any]:
    strat = (await db.execute(
        select(MonitoredStrategy).where(MonitoredStrategy.id == strategy_id)
    )).scalar_one_or_none()
    if strat is None:
        return {"error": "strategy not found"}

    weights = await _target_weights(db, strat)
    if not weights:
        return {"error": "no target weights for strategy"}

    # --- Pre-trade risk gate ---
    approved, cvar = broker.risk_check(weights)
    if not approved:
        reason = f"Blocked: target CVaR {cvar:.2%} exceeds limit {settings.RISK_CVAR_LIMIT:.2%}"
        db.add(PaperTrade(ticker="PORTFOLIO", side="rebalance", shares=0, price=0,
                          status="blocked", reason=reason, strategy_id=strategy_id))
        await db.commit()
        return {"status": "blocked", "cvar": round(cvar, 4), "reason": reason}

    acct = await get_account(db)
    equity = acct["equity"]
    prices = broker.latest_prices(list(weights.keys()))
    target_shares = broker.compute_target_shares(weights, equity, prices)

    existing = {p.ticker: p for p in await _positions(db)}
    trades: List[Dict[str, Any]] = []

    # Close positions no longer targeted
    for ticker, pos in existing.items():
        if ticker not in target_shares and pos.shares > 0:
            px = broker.latest_prices([ticker]).get(ticker, pos.avg_price)
            db.add(PaperTrade(ticker=ticker, side="sell", shares=pos.shares, price=px,
                              status="filled", reason=f"exit ({strat.name})", strategy_id=strategy_id))
            trades.append({"ticker": ticker, "side": "sell", "shares": round(pos.shares, 4)})
            pos.shares = 0.0

    # Move toward targets
    for ticker, tgt in target_shares.items():
        px = prices.get(ticker)
        if not px:
            continue
        pos = existing.get(ticker)
        cur = pos.shares if pos else 0.0
        delta = round(tgt - cur, 4)
        if abs(delta) * px < 1:  # ignore dust
            continue
        side = "buy" if delta > 0 else "sell"
        if pos is None:
            pos = PaperPosition(ticker=ticker, shares=0.0, avg_price=px)
            db.add(pos)
            existing[ticker] = pos
        # update avg price on buys
        if delta > 0:
            total_cost = pos.shares * pos.avg_price + delta * px
            pos.shares = round(pos.shares + delta, 4)
            pos.avg_price = round(total_cost / pos.shares, 4) if pos.shares else px
        else:
            pos.shares = round(pos.shares + delta, 4)
        db.add(PaperTrade(ticker=ticker, side=side, shares=abs(delta), price=px,
                          status="filled", reason=f"rebalance ({strat.name})", strategy_id=strategy_id))
        trades.append({"ticker": ticker, "side": side, "shares": abs(delta), "price": round(px, 2)})

    await db.commit()
    acct2 = await get_account(db)
    db.add(PaperSnapshot(equity=acct2["equity"], cash=acct2["cash"]))
    await db.commit()
    return {"status": "filled", "cvar": round(cvar, 4), "trades": trades, "equity": acct2["equity"]}


async def list_trades(db: AsyncSession, limit: int = 40) -> List[PaperTrade]:
    res = await db.execute(select(PaperTrade).order_by(desc(PaperTrade.created_at)).limit(limit))
    return list(res.scalars().all())
