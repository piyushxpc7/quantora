import yfinance as yf
import pandas as pd
from typing import Dict, Any, Optional

class MarketDataService:
    @staticmethod
    def fetch_historical_data(ticker: str, period: str = "1y", interval: str = "1d") -> Dict[str, Any]:
        """
        Fetch historical data using yfinance.
        """
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval)
            
            if df.empty:
                return {"error": "No data found for ticker"}
            
            # Reset index to make Date a column
            df.reset_index(inplace=True)
            
            # Convert to list of dicts for JSON response
            data = df.to_dict(orient="records")
            
            return {
                "ticker": ticker,
                "period": period,
                "interval": interval,
                "count": len(data),
                "data": data
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def get_latest_price(ticker: str) -> Optional[float]:
        try:
            stock = yf.Ticker(ticker)
            # fast_info is faster for current price
            return stock.fast_info.last_price
        except:
            return None
