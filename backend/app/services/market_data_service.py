import time
import csv
import io
import urllib.request
import yfinance as yf
import pandas as pd
from typing import Dict, Any, Optional

# Map yfinance "period" strings to an approximate number of calendar days for Stooq trimming.
_PERIOD_DAYS = {"6mo": 182, "1y": 365, "2y": 730, "3y": 1095, "5y": 1825, "10y": 3650}


class MarketDataService:
    # Simple in-process cache: {(ticker, period, interval): (timestamp, payload)}
    _cache: Dict[tuple, tuple] = {}
    _CACHE_TTL = 60 * 30  # 30 minutes

    @staticmethod
    def _stooq_history(ticker: str, period: str) -> Dict[str, Any]:
        """Free fallback data source (Stooq CSV) when yfinance is unavailable/rate-limited."""
        try:
            url = f"https://stooq.com/q/d/l/?s={ticker.lower()}.us&i=d"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                text = resp.read().decode("utf-8", "ignore")
            rows = list(csv.DictReader(io.StringIO(text)))
            if not rows or "Close" not in rows[0]:
                return {"error": "Stooq returned no data"}
            days = _PERIOD_DAYS.get(period, 730)
            rows = rows[-min(len(rows), int(days / 1.4)):]  # ~trading days
            data = [{
                "Date": r["Date"],
                "Open": float(r["Open"]), "High": float(r["High"]),
                "Low": float(r["Low"]), "Close": float(r["Close"]),
                "Volume": float(r.get("Volume") or 0),
            } for r in rows if r.get("Close") not in (None, "", "N/D")]
            if not data:
                return {"error": "Stooq parse empty"}
            return {"ticker": ticker, "period": period, "interval": "1d", "count": len(data), "data": data, "source": "stooq"}
        except Exception as e:
            return {"error": f"Stooq fallback failed: {e}"}

    @classmethod
    def fetch_historical_data(cls, ticker: str, period: str = "1y", interval: str = "1d") -> Dict[str, Any]:
        """Fetch OHLCV via yfinance, falling back to Stooq, with a short-lived cache."""
        key = (ticker, period, interval)
        cached = cls._cache.get(key)
        if cached and (time.time() - cached[0]) < cls._CACHE_TTL:
            return cached[1]

        payload: Dict[str, Any]
        try:
            df = yf.Ticker(ticker).history(period=period, interval=interval)
            if df.empty:
                payload = cls._stooq_history(ticker, period)
            else:
                df.reset_index(inplace=True)
                payload = {
                    "ticker": ticker, "period": period, "interval": interval,
                    "count": len(df), "data": df.to_dict(orient="records"), "source": "yfinance",
                }
        except Exception:
            payload = cls._stooq_history(ticker, period)

        if "error" not in payload:
            cls._cache[key] = (time.time(), payload)
        return payload

    @classmethod
    def get_latest_price(cls, ticker: str) -> Optional[float]:
        try:
            price = yf.Ticker(ticker).fast_info.last_price
            if price:
                return float(price)
        except Exception:
            pass
        # Fallback: last close from history (cached/Stooq)
        hist = cls.fetch_historical_data(ticker, period="6mo", interval="1d")
        if "data" in hist and hist["data"]:
            try:
                return float(hist["data"][-1]["Close"])
            except Exception:
                return None
        return None
