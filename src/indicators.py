import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from config.config import Config
import logging

logger = logging.getLogger(__name__)

class TechnicalIndicators:
    """Technical Indicators Calculator"""
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> Optional[float]:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return None
            
        prices_array = np.array(prices, dtype=float)
        ema = pd.Series(prices_array).ewm(span=period, adjust=False).mean().iloc[-1]
        return float(ema)
        
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 3) -> Optional[float]:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return None
            
        prices_array = np.array(prices, dtype=float)
        delta = np.diff(prices_array)
        
        gains  = np.where(delta > 0, delta, 0.0)
        losses = np.where(delta < 0, -delta, 0.0)
        
        avg_gains  = pd.Series(gains).rolling(window=period).mean().iloc[-1]
        avg_losses = pd.Series(losses).rolling(window=period).mean().iloc[-1]
        
        if avg_losses == 0:
            return 100.0
            
        rs  = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        return float(rsi)
        
    @staticmethod
    def calculate_adx(candles: List[Dict], period: int = 55) -> Optional[float]:
        """Calculate Average Directional Index using Wilder's smoothing.

        Returns proper ADX (smoothed DX), not raw DX.
        Requires at least period+1 candles; results stabilise with 2×period candles.
        """
        if len(candles) < period + 1:
            return None

        highs  = np.array([c['high']  for c in candles], dtype=float)
        lows   = np.array([c['low']   for c in candles], dtype=float)
        closes = np.array([c['close'] for c in candles], dtype=float)

        # True Range
        tr1 = highs[1:] - lows[1:]
        tr2 = np.abs(highs[1:] - closes[:-1])
        tr3 = np.abs(lows[1:]  - closes[:-1])
        tr  = np.maximum(np.maximum(tr1, tr2), tr3)

        # Directional Movement
        up_move   = highs[1:] - highs[:-1]
        down_move = lows[:-1] - lows[1:]

        plus_dm  = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

        # Wilder's smoothing: alpha = 1/period  (equiv. to EWM with adjust=False)
        alpha = 1.0 / period
        tr_s   = pd.Series(tr).ewm(alpha=alpha, adjust=False).mean().values
        pdm_s  = pd.Series(plus_dm).ewm(alpha=alpha, adjust=False).mean().values
        mdm_s  = pd.Series(minus_dm).ewm(alpha=alpha, adjust=False).mean().values

        # DI lines
        with np.errstate(divide='ignore', invalid='ignore'):
            plus_di  = np.where(tr_s != 0, 100.0 * pdm_s / tr_s, 0.0)
            minus_di = np.where(tr_s != 0, 100.0 * mdm_s / tr_s, 0.0)

            di_sum  = plus_di + minus_di
            di_diff = np.abs(plus_di - minus_di)
            dx = np.where(di_sum != 0, 100.0 * di_diff / di_sum, 0.0)

        # ADX = Wilder's smoothed DX  (this is the step that was missing before)
        adx = pd.Series(dx).ewm(alpha=alpha, adjust=False).mean().iloc[-1]
        return float(adx)

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
    def calculate_sma(prices: List[float], period: int) -> Optional[float]:
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
            
        # Current & previous price
        indicators['CURRENT_PRICE'] = closes[-1] if closes else None
        indicators['PREV_PRICE']    = closes[-2] if len(closes) > 1 else None

        # Previous RSI for crossover detection
        if len(closes) >= Config.RSI_PERIOD + 2:
            prev_rsi = cls.calculate_rsi(closes[:-1], Config.RSI_PERIOD)
            indicators['PREV_RSI_3'] = prev_rsi

        # ATR — untuk dynamic TP/SL
        atr = cls.calculate_atr(candles, Config.ATR_PERIOD)
        if atr is not None:
            indicators['ATR'] = atr

        return indicators
        
    @staticmethod
    def calculate_market_regime(candles: List[Dict]) -> Dict[str, float]:
        """Market Regime Filter — deteksi trending vs ranging.

        Bandingkan ADX periode pendek (20) vs panjang (60):
        - ADX_short > ADX_long  → trend sedang MENGUAT   → boleh masuk
        - ADX_short < ADX_long  → trend sedang MELEMAH   → skip
        - ADX_slope > 0         → ADX sedang naik        → konfirmasi trending

        Return dict berisi:
          'adx_short'  : ADX periode pendek (20)
          'adx_long'   : ADX periode panjang (60)
          'adx_slope'  : perubahan ADX short 5 candle terakhir
          'is_trending': True jika semua kondisi terpenuhi
        """
        short_p = Config.REGIME_ADX_SHORT  # 20
        long_p  = Config.REGIME_ADX_LONG   # 60

        if len(candles) < long_p + 1:
            return {'adx_short': 0.0, 'adx_long': 0.0, 'adx_slope': 0.0, 'is_trending': False}

        highs  = np.array([c['high']  for c in candles], dtype=float)
        lows   = np.array([c['low']   for c in candles], dtype=float)
        closes = np.array([c['close'] for c in candles], dtype=float)

        def _adx_series(period, n_last=6):
            tr1 = highs[1:] - lows[1:]
            tr2 = np.abs(highs[1:] - closes[:-1])
            tr3 = np.abs(lows[1:]  - closes[:-1])
            tr  = np.maximum(np.maximum(tr1, tr2), tr3)
            up  = highs[1:] - highs[:-1]
            dn  = lows[:-1] - lows[1:]
            pdm = np.where((up > dn) & (up > 0), up, 0.0)
            mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
            a   = 1.0 / period
            tr_s  = pd.Series(tr).ewm(alpha=a, adjust=False).mean().values
            pdm_s = pd.Series(pdm).ewm(alpha=a, adjust=False).mean().values
            mdm_s = pd.Series(mdm).ewm(alpha=a, adjust=False).mean().values
            with np.errstate(divide='ignore', invalid='ignore'):
                pdi = np.where(tr_s != 0, 100.0 * pdm_s / tr_s, 0.0)
                mdi = np.where(tr_s != 0, 100.0 * mdm_s / tr_s, 0.0)
                ds  = pdi + mdi
                dx  = np.where(ds != 0, 100.0 * np.abs(pdi - mdi) / ds, 0.0)
            adx_vals = pd.Series(dx).ewm(alpha=a, adjust=False).mean().values
            return adx_vals[-n_last:]   # kembalikan n nilai terakhir untuk slope

        short_vals = _adx_series(short_p, n_last=6)
        long_vals  = _adx_series(long_p,  n_last=2)

        adx_short = float(short_vals[-1])
        adx_long  = float(long_vals[-1])
        adx_slope = float(short_vals[-1] - short_vals[-4])  # perubahan 3 candle terakhir

        is_trending = (
            adx_short > adx_long and          # trend menguat
            adx_slope >= Config.REGIME_MIN_SLOPE  # arah naik (atau minimal datar)
        )

        return {
            'adx_short':   adx_short,
            'adx_long':    adx_long,
            'adx_slope':   adx_slope,
            'is_trending': is_trending,
        }

    @classmethod
    def analyze_market_condition(cls, indicators: Dict[str, float]) -> str:
        """Analyze current market condition"""
        if not indicators or 'ADX_55' not in indicators:
            return 'NO_SIGNAL'

        adx = indicators['ADX_55']

        if adx <= Config.ADX_THRESHOLD:
            return 'NO_TREND'

        # Market Regime Filter — cek apakah trend sedang menguat
        regime = indicators.get('MARKET_REGIME', {})
        if regime and not regime.get('is_trending', True):
            return 'RANGING'

        if adx > 30 and adx <= 50:
            return 'TRENDING'
        else:
            return 'STRONG_TREND'
            
    @classmethod
    def check_buy_signal(cls, indicators: Dict[str, float], prev_indicators: Dict[str, float] = None) -> bool:
        """Check if buy signal conditions are met"""
        try:
            required = ['EMA_50', 'RSI_3', 'ADX_55', 'CURRENT_PRICE', 'PREV_RSI_3']
            if not all(ind in indicators for ind in required):
                return False
                
            price_above_ema = indicators['CURRENT_PRICE'] > indicators['EMA_50']
            
            current_rsi = indicators['RSI_3']
            prev_rsi    = indicators['PREV_RSI_3']
            
            rsi_exiting_oversold = (
                prev_rsi <= Config.RSI_EXIT_OVERSOLD and 
                current_rsi > Config.RSI_EXIT_OVERSOLD
            )
            
            adx_strong  = indicators['ADX_55'] > Config.ADX_THRESHOLD
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
            required = ['EMA_50', 'RSI_3', 'ADX_55', 'CURRENT_PRICE', 'PREV_RSI_3']
            if not all(ind in indicators for ind in required):
                return False
                
            price_below_ema = indicators['CURRENT_PRICE'] < indicators['EMA_50']
            
            current_rsi = indicators['RSI_3']
            prev_rsi    = indicators['PREV_RSI_3']
            
            rsi_exiting_overbought = (
                prev_rsi >= Config.RSI_EXIT_OVERBOUGHT and 
                current_rsi < Config.RSI_EXIT_OVERBOUGHT
            )
            
            adx_strong   = indicators['ADX_55'] > Config.ADX_THRESHOLD
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
