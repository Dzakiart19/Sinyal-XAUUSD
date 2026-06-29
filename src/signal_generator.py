import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from .websocket_client import DerivWebSocketClient
from .indicators import TechnicalIndicators
from config.config import Config

logger = logging.getLogger(__name__)

class Signal:
    """Trading signal data structure"""
    def __init__(self, signal_type: str, price: float, ema_50: float, rsi: float, adx: float, 
                 timestamp: datetime, timeframe: str, tp: float, sl: float):
        self.signal_type = signal_type  # BUY or SELL
        self.entry_price = price
        self.ema_50 = ema_50
        self.rsi = rsi
        self.adx = adx
        self.timestamp = timestamp
        self.timeframe = timeframe
        self.tp = tp
        self.sl = sl
        self.candle_id = f"{timestamp.strftime('%Y%m%d%H%M')}_{timeframe}"
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'signal_type': self.signal_type,
            'entry_price': self.entry_price,
            'ema_50': self.ema_50,
            'rsi': self.rsi,
            'adx': self.adx,
            'timestamp': self.timestamp.isoformat(),
            'timeframe': self.timeframe,
            'tp': self.tp,
            'sl': self.sl,
            'candle_id': self.candle_id
        }

class SignalGenerator:
    """XAUUSD Scalping Signal Generator"""
    
    def __init__(self, ws_client: DerivWebSocketClient):
        self.ws_client = ws_client
        self.indicators = TechnicalIndicators()
        self.last_signals = {
            'M1': {},
            'M5': {}
        }
        self.signal_callbacks = []
        self.is_running = False
        self.processed_candles = set()   # Track processed candles to avoid duplicates
        self._MAX_PROCESSED = 500         # Cap agar tidak tumbuh tak terbatas (OOM guard)
        
        # Register callbacks with WebSocket client
        self.ws_client.register_callback('candle_update', self._on_candle_update)
        self.ws_client.register_callback('tick_update', self._on_tick_update)
        
    async def start(self):
        """Start signal generation"""
        self.is_running = True
        logger.info("Signal generator started")
        
        # Start signal scanning loop
        asyncio.create_task(self._signal_scanning_loop())
        
    async def stop(self):
        """Stop signal generation"""
        self.is_running = False
        logger.info("Signal generator stopped")
        
    def register_signal_callback(self, callback: Callable):
        """Register callback for new signals"""
        self.signal_callbacks.append(callback)
        
    async def _signal_scanning_loop(self):
        """Main signal scanning loop"""
        while self.is_running:
            try:
                # Wait for WebSocket to be ready
                if not self.ws_client.is_ready():
                    await asyncio.sleep(1)
                    continue
                    
                # Scan both timeframes
                await self._scan_timeframe('M1')
                await self._scan_timeframe('M5')
                
                # Wait before next scan
                await asyncio.sleep(Config.SIGNAL_CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in signal scanning loop: {e}")
                await asyncio.sleep(5)
                
    async def _scan_timeframe(self, timeframe: str):
        """Scan for signals on specific timeframe"""
        try:
            candles = self.ws_client.get_candles(timeframe)
            
            if len(candles) < Config.EMA_PERIOD + 5:
                return
                
            # Calculate indicators
            indicators = self.indicators.calculate_all_indicators(candles, timeframe)
            
            if not indicators:
                return
                
            # Check for duplicate candle (already processed)
            latest_candle = candles[-1]
            candle_key = f"{timeframe}_{latest_candle['epoch']}"
            
            if candle_key in self.processed_candles:
                return
                
            # Check market condition
            market_condition = self.indicators.analyze_market_condition(indicators)
            
            if market_condition == 'NO_TREND':
                return  # Skip if ADX too low
                
            # Check for signals
            buy_signal = self.indicators.check_buy_signal(indicators)
            sell_signal = self.indicators.check_sell_signal(indicators)
            
            # Generate signal if found
            if buy_signal:
                signal = self._create_signal('BUY', indicators, timeframe)
                if signal and self._is_valid_signal(signal):
                    self.processed_candles.add(candle_key)
                    self._trim_processed_candles()
                    await self._emit_signal(signal)
                    
            elif sell_signal:
                signal = self._create_signal('SELL', indicators, timeframe)
                if signal and self._is_valid_signal(signal):
                    self.processed_candles.add(candle_key)
                    self._trim_processed_candles()
                    await self._emit_signal(signal)
                    
        except Exception as e:
            logger.error(f"Error scanning {timeframe}: {e}")
            
    def _create_signal(self, signal_type: str, indicators: Dict, timeframe: str) -> Optional[Signal]:
        """Create signal from indicators"""
        try:
            current_price = indicators['CURRENT_PRICE']
            ema_50 = indicators['EMA_50']
            rsi = indicators['RSI_3']
            adx = indicators['ADX_55']

            # Dynamic TP/SL based on ATR — menyesuaikan volatilitas market
            atr = indicators.get('ATR')
            if atr and atr > 0:
                raw_sl = atr * Config.ATR_SL_MULT
                raw_tp = atr * Config.ATR_TP_MULT
                # Clamp dalam batas MIN/MAX agar tidak ekstrem
                sl_dist = max(Config.MIN_SL, min(raw_sl, Config.MAX_SL))
                tp_dist = max(Config.MIN_SL, min(raw_tp, Config.MAX_SL))
            else:
                # Fallback jika ATR belum tersedia
                sl_dist = 3.0
                tp_dist = 3.0

            if signal_type == 'BUY':
                tp = current_price + tp_dist
                sl = current_price - sl_dist
            else:  # SELL
                tp = current_price - tp_dist
                sl = current_price + sl_dist
                
            signal = Signal(
                signal_type=signal_type,
                price=current_price,
                ema_50=ema_50,
                rsi=rsi,
                adx=adx,
                timestamp=datetime.now(),
                timeframe=timeframe,
                tp=tp,
                sl=sl
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Error creating signal: {e}")
            return None
            
    def _is_valid_signal(self, signal: Signal) -> bool:
        """Check if signal is valid (not duplicate)"""
        timeframe = signal.timeframe
        candle_id = signal.candle_id
        
        # Check if we already have a signal for this candle
        if candle_id in self.last_signals[timeframe]:
            return False
            
        # Store signal
        self.last_signals[timeframe][candle_id] = signal
        
        # Keep only last 10 signals per timeframe
        if len(self.last_signals[timeframe]) > 10:
            oldest_key = min(self.last_signals[timeframe].keys())
            del self.last_signals[timeframe][oldest_key]
            
        return True
        
    async def _emit_signal(self, signal: Signal):
        """Emit signal to all registered callbacks"""
        logger.info(f"New signal generated: {signal.signal_type} on {signal.timeframe} - "
                   f"Price: {signal.entry_price:.2f}, RSI: {signal.rsi:.2f}, ADX: {signal.adx:.2f}")
        
        for callback in self.signal_callbacks:
            try:
                await callback(signal)
            except Exception as e:
                logger.error(f"Error in signal callback: {e}")
                
    def _trim_processed_candles(self):
        """Buang entri lama jika set melebihi batas — cegah memory leak"""
        if len(self.processed_candles) > self._MAX_PROCESSED:
            # Hapus separuh entri terlama (set tidak ordered, jadi hapus sembarangan tapi aman)
            excess = len(self.processed_candles) - (self._MAX_PROCESSED // 2)
            for key in list(self.processed_candles)[:excess]:
                self.processed_candles.discard(key)

    async def _on_candle_update(self, interval: str, candle: Dict):
        """Handle candle update from WebSocket"""
        # This will trigger immediate signal check
        # The scanning loop will handle the actual signal generation
        pass
        
    async def _on_tick_update(self, tick: Dict):
        """Handle tick update from WebSocket"""
        # For scalping, we might want to use tick data for more precise entries
        # But for now, we'll stick to candle-based signals
        pass
        
    async def generate_manual_signal(self, user_id: int) -> Optional[Signal]:
        """Generate manual signal for specific user"""
        try:
            # Wait for WebSocket to be ready
            if not self.ws_client.is_ready():
                return None
                
            # Note: Active position check is handled in telegram_bot.py before calling this or processing results
            
            # Get latest data from both timeframes
            m1_candles = self.ws_client.get_candles('M1')
            m5_candles = self.ws_client.get_candles('M5')
            
            # Prioritize M5 for stronger signals, fallback to M1
            for timeframe, candles in [('M5', m5_candles), ('M1', m1_candles)]:
                if len(candles) < Config.EMA_PERIOD + 5:
                    continue
                    
                indicators = self.indicators.calculate_all_indicators(candles, timeframe)
                
                if not indicators:
                    continue
                    
                # Check market condition
                market_condition = self.indicators.analyze_market_condition(indicators)
                
                if market_condition == 'NO_TREND':
                    continue
                    
                # Check for signals
                buy_signal = self.indicators.check_buy_signal(indicators)
                sell_signal = self.indicators.check_sell_signal(indicators)
                
                if buy_signal or sell_signal:
                    signal_type = 'BUY' if buy_signal else 'SELL'
                    signal = self._create_signal(signal_type, indicators, timeframe)
                    
                    if signal:
                        # Mark as manual signal
                        signal.candle_id = f"MANUAL_{user_id}_{signal.candle_id}"
                        return signal
                        
            return None
            
        except Exception as e:
            logger.error(f"Error generating manual signal: {e}")
            return None
            
    def get_last_signal(self, timeframe: str) -> Optional[Signal]:
        """Get the most recent signal for timeframe"""
        if not self.last_signals[timeframe]:
            return None
            
        latest_key = max(self.last_signals[timeframe].keys())
        return self.last_signals[timeframe][latest_key]
        
    def get_signal_history(self, timeframe: str, count: int = 5) -> List[Signal]:
        """Get signal history for timeframe"""
        signals = list(self.last_signals[timeframe].values())
        return sorted(signals, key=lambda s: s.timestamp, reverse=True)[:count]