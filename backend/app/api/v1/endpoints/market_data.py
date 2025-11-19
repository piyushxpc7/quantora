from app.services.feature_engineering_service import FeatureEngineeringService

router = APIRouter()

@router.get("/historical/{ticker}")
def get_historical_data(
    ticker: str,
    period: str = Query("1y", description="Data period (e.g., 1d, 1mo, 1y)"),
    interval: str = Query("1d", description="Data interval (e.g., 1m, 1h, 1d)"),
    include_indicators: bool = Query(False, description="Include technical indicators")
):
    """
    Fetch historical OHLCV data for a ticker.
    """
    result = MarketDataService.fetch_historical_data(ticker, period, interval)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    if include_indicators and "data" in result:
        result["data"] = FeatureEngineeringService.process_data(result["data"])
        
    return result

@router.get("/price/{ticker}")
def get_latest_price(ticker: str):
    """
    Get the latest price for a ticker.
    """
    price = MarketDataService.get_latest_price(ticker)
    if price is None:
        raise HTTPException(status_code=404, detail="Ticker not found")
    return {"ticker": ticker, "price": price}
