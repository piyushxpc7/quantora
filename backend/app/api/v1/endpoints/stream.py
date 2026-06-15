import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.market_data_service import MarketDataService

router = APIRouter()

WATCH_TICKERS = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA"]


@router.websocket("/prices")
async def stream_prices(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            prices = {}
            for ticker in WATCH_TICKERS:
                price = MarketDataService.get_latest_price(ticker)
                if price is not None:
                    prices[ticker] = round(price, 2)
            await websocket.send_text(json.dumps(prices))
            await asyncio.sleep(15)
    except WebSocketDisconnect:
        pass
