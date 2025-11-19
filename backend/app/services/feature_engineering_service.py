import pandas as pd
import ta
from typing import List, Dict, Any

class FeatureEngineeringService:
    @staticmethod
    def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add technical indicators to the DataFrame.
        Expects columns: Open, High, Low, Close, Volume
        """
        if df.empty:
            return df
            
        # Ensure columns are correct types
        df['Close'] = df['Close'].astype(float)
        df['High'] = df['High'].astype(float)
        df['Low'] = df['Low'].astype(float)
        df['Volume'] = df['Volume'].astype(float)

        # Trend Indicators
        df['sma_20'] = ta.trend.sma_indicator(df['Close'], window=20)
        df['sma_50'] = ta.trend.sma_indicator(df['Close'], window=50)
        df['ema_20'] = ta.trend.ema_indicator(df['Close'], window=20)
        
        # Momentum Indicators
        df['rsi'] = ta.momentum.rsi(df['Close'], window=14)
        df['macd'] = ta.trend.macd_diff(df['Close'])
        
        # Volatility Indicators
        df['bollinger_hband'] = ta.volatility.bollinger_hband(df['Close'])
        df['bollinger_lband'] = ta.volatility.bollinger_lband(df['Close'])
        
        # Fill NaNs
        df.fillna(0, inplace=True)
        
        return df

    @staticmethod
    def process_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a list of dictionaries (from MarketDataService) and add indicators.
        """
        if not data:
            return []
            
        df = pd.DataFrame(data)
        
        # Check if required columns exist
        required_cols = ['Close', 'High', 'Low', 'Volume']
        if not all(col in df.columns for col in required_cols):
            # Try to map if case is different or missing
            return data
            
        df = FeatureEngineeringService.add_technical_indicators(df)
        
        return df.to_dict(orient="records")
