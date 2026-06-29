import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from config.config import Config
import logging

logger = logging.getLogger(__name__)

class TechnicalIndicators:
    """Technical Indicators Calculator"""
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return None
            
        prices_array = np.array(prices[-period:])
        ema = pd.Series(prices_array).ewm(span=period, adjust=False).mean().iloc[-1]
        return float(ema)
        
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 3) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return None
            
        prices_array = np.array(prices)
        delta = np.diff(prices_array)
        
        # Separate gains and losses
        gains = np.where(delta > 0, delta, 0)
        losses = np.where(delta < 0, -delta, 0)
        
        # Calculate average gains and losses
        avg_gains = pd.Series(gains).rolling(window=period).mean().iloc[-1]
        avg_losses = pd.Series(losses).rolling(window=period).mean().iloc[-1]
        
        if avg_losses == 0:
            return 100.0
            
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)
        
    @staticmethod
    def calculate_adx(candles: List[Dict], period: int = 55) -> float:
        """Calculate Average Directional Index"""
        if len(candles) < period + 1:
            return None
            
        # Extract OHLC data
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        closes = [c['close'] for c in candles]
        
        # Calculate True Range
        tr1 = np.array(highs[1:]) - np.array(lows[1:])
        tr2 = abs(np.array(highs[1:]) - np.array(closes[:-1]))
        tr3 = abs(np.array(lows[1:]) - np.array(closes[:-1]))
        
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        tr = np.concatenate([[0], tr])  # Add 0 for first candle
        
        # Calculate +DM and -DM
        up_move = np.array(highs[1:]) - np.array(highs[:-1])
        down_move = np.array(lows[:-1]) - np.array(lows[1:])
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        plus_dm = np.concatenate([[0], plus_dm])
        minus_dm = np.concatenate([[0], minus_dm])
        
        # Calculate smoothed values
        tr_smooth = pd.Series(tr).rolling(window=period).sum().iloc[-1]
        plus_dm_smooth = pd.Series(plus_dm).rolling(window=period).sum().iloc[-1]
        minus_dm_smooth = pd.Series(minus_dm).rolling(window=period).sum().iloc[-1]
        
        if tr_smooth == 0:
            return 0.0
            
        # Calculate +DI and -DI
        plus_di = 100 * (plus_dm_smooth / tr_smooth)
        minus_di = 100 * (minus_dm_smooth / tr_smooth)
        
        # Calculate DX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) != 0 else 0
        
        return float(dx)
        
    @staticmethod
    def calculate_atr(candles: List[Dict], period: int = 14) -> Optional[float]:
        """Calculate Average True Range — ukuran volatilitas market"""
        if len(candles) < period + 1:
            return None

        highs  = [c['high']  for c in candles]
        lows   = [c['low']   for c in candles]
        closes = [c['close'] for c in candles]

        trs = []
        for i in range(1, len(candles)):
            tr = max(
                highs[i]  - lows[i],
                abs(highs[i]  - closes[i - 1]),
                abs(lows[i]   - closes[i - 1]),
            )
            trs.append(tr)

        atr = float(np.mean(trs[-period:]))
        return atr

    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> float:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return None
            
        return float(np.mean(prices[-period:]))
        
    @staticmethod
    def get_price_data(candles: List[Dict], price_type: str = 'close') -> List[float]:
        """Extract price data from candles"""
        if price_type == 'close':
            return [c['close'] for c in candles]
        elif price_type == 'high':
            return [c['high'] for c in candles]
        elif price_type == 'low':
            return [c['low'] for c in candles]
        elif price_type == 'open':
            return [c['open'] for c in candles]
        elif price_type == 'typical':
            return [(c['high'] + c['low'] + c['close']) / 3 for c in candles]
        else:
            return [c['close'] for c in candles]
            
    @classmethod
    def calculate_all_indicators(cls, candles: List[Dict], interval: str) -> Dict[str, float]:
        """Calculate all technical indicators"""
        if len(candles) < Config.EMA_PERIOD + 1:
            return {}
            
        closes = cls.get_price_data(candles, 'close')
        
        indicators = {}
        
        # EMA 50
        ema_50 = cls.calculate_ema(closes, Config.EMA_PERIOD)
        if ema_50 is not None:
            indicators['EMA_50'] = ema_50
            
        # RSI 3
        rsi_3 = cls.calculate_rsi(closes, Config.RSI_PERIOD)
        if rsi_3 is not None:
            indicators['RSI_3'] = rsi_3
            
        # ADX 55
        adx_55 = cls.calculate_adx(candles, Config.ADX_PERIOD)
        if adx_55 is not None:
            indicators['ADX_55'] = adx_55
            
        # Current price
        indicators['CURRENT_PRICE'] = closes[-1] if closes else None
        indicators['PREV_PRICE'] = closes[-2] if len(closes) > 1 else None

        # Previous RSI for signal detection
        if len(closes) >= Config.RSI_PERIOD + 2:
            prev_rsi = cls.calculate_rsi(closes[:-1], Config.RSI_PERIOD)
            indicators['PREV_RSI_3'] = prev_rsi

        # ATR — untuk dynamic TP/SL
        atr = cls.calculate_atr(candles, Config.ATR_PERIOD)
        if atr is not None:
            indicators['ATR'] = atr

        return indicators
        
    @classmethod
    def analyze_market_condition(cls, indicators: Dict[str, float]) -> str:
        """Analyze current market condition"""
        if not indicators or 'ADX_55' not in indicators:
            return 'NO_SIGNAL'
            
        adx = indicators['ADX_55']
        
        if adx <= Config.ADX_THRESHOLD:
            return 'NO_TREND'
        elif adx > 30 and adx <= 50:
            return 'TRENDING'
        else:
            return 'STRONG_TREND'
            
    @classmethod
    def check_buy_signal(cls, indicators: Dict[str, float], prev_indicators: Dict[str, float] = None) -> bool:
        """Check if buy signal conditions are met"""
        try:
            # Check if we have all required indicators
            required = ['EMA_50', 'RSI_3', 'ADX_55', 'CURRENT_PRICE', 'PREV_RSI_3']
            if not all(ind in indicators for ind in required):
                return False
                
            # Condition 1: Price above EMA 50
            price_above_ema = indicators['CURRENT_PRICE'] > indicators['EMA_50']
            
            # Condition 2 & 3: RSI was oversold and now exiting
            current_rsi = indicators['RSI_3']
            prev_rsi = indicators['PREV_RSI_3']
            
            rsi_exiting_oversold = (
                prev_rsi <= Config.RSI_EXIT_OVERSOLD and 
                current_rsi > Config.RSI_EXIT_OVERSOLD
            )
            
            # Condition 4: ADX > 30
            adx_strong = indicators['ADX_55'] > Config.ADX_THRESHOLD
            
            # Additional: RSI in acceptable range
            rsi_in_range = Config.RSI_EXIT_OVERSOLD <= current_rsi <= 50
            
            return (
                price_above_ema and 
                rsi_exiting_oversold and 
                adx_strong and 
                rsi_in_range
            )
            
        except Exception as e:
            logger.error(f"Error checking buy signal: {e}")
            return False
            
    @classmethod
    def check_sell_signal(cls, indicators: Dict[str, float], prev_indicators: Dict[str, float] = None) -> bool:
        """Check if sell signal conditions are met"""
        try:
            # Check if we have all required indicators
            required = ['EMA_50', 'RSI_3', 'ADX_55', 'CURRENT_PRICE', 'PREV_RSI_3']
            if not all(ind in indicators for ind in required):
                return False
                
            # Condition 1: Price below EMA 50
            price_below_ema = indicators['CURRENT_PRICE'] < indicators['EMA_50']
            
            # Condition 2 & 3: RSI was overbought and now exiting
            current_rsi = indicators['RSI_3']
            prev_rsi = indicators['PREV_RSI_3']
            
            rsi_exiting_overbought = (
                prev_rsi >= Config.RSI_EXIT_OVERBOUGHT and 
                current_rsi < Config.RSI_EXIT_OVERBOUGHT
            )
            
            # Condition 4: ADX > 30
            adx_strong = indicators['ADX_55'] > Config.ADX_THRESHOLD
            
            # Additional: RSI in acceptable range
            rsi_in_range = 50 <= current_rsi <= Config.RSI_EXIT_OVERBOUGHT
            
            return (
                price_below_ema and 
                rsi_exiting_overbought and 
                adx_strong and 
                rsi_in_range
            )
            
        except Exception as e:
            logger.error(f"Error checking sell signal: {e}")
            return False