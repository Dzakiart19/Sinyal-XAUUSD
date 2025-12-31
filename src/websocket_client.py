import asyncio
import json
import websockets
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from config.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DerivWebSocketClient:
    def __init__(self):
        self.url = Config.DERIV_WS_URL
        self.symbol = Config.SYMBOL
        self.websocket = None
        self.is_connected = False
        self.subscriptions = {}
        self.candle_data = {
            'M1': [],
            'M5': []
        }
        self.tick_data = []
        self.last_tick = None
        self.callbacks = {}
        self.history_fetched = False
        
    async def connect(self):
        """Connect to Deriv WebSocket"""
        try:
            self.websocket = await websockets.connect(self.url)
            self.is_connected = True
            logger.info(f"Connected to Deriv WebSocket: {self.url}")
            
            # Start listening for messages
            asyncio.create_task(self._listen())
            
            # Authorize if token is available
            token = os.getenv('DERIV_API_TOKEN')
            if token:
                logger.info("Authorizing with Deriv API...")
                await self._send({"authorize": token})
            
            # Subscribe to tick data
            await self.subscribe_ticks()
            
            # Fetch historical candles
            await self.fetch_candle_history()
            
            # Subscribe to live candles
            await self.subscribe_candles('60')  # M1
            await self.subscribe_candles('300') # M5
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            self.is_connected = False
            
    async def disconnect(self):
        """Disconnect from WebSocket"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info("Disconnected from Deriv WebSocket")
            
    async def _listen(self):
        """Listen for incoming messages"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self._handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.is_connected = False
            await self._reconnect()
        except Exception as e:
            logger.error(f"Error in listen: {e}")
            self.is_connected = False
            
    async def _reconnect(self):
        """Reconnect on connection loss"""
        while not self.is_connected:
            logger.info("Attempting to reconnect...")
            await asyncio.sleep(5)
            await self.connect()
            
    async def _handle_message(self, data: Dict[str, Any]):
        """Handle incoming WebSocket messages"""
        try:
            if 'tick' in data:
                tick = data['tick']
                self.last_tick = {
                    'symbol': tick['symbol'],
                    'price': float(tick['quote']),
                    'epoch': tick['epoch'],
                    'datetime': datetime.fromtimestamp(tick['epoch'])
                }
                self.tick_data.append(self.last_tick)
                
                # Keep only last 1000 ticks
                if len(self.tick_data) > 1000:
                    self.tick_data.pop(0)
                    
                # Trigger callback for tick updates
                if 'tick_update' in self.callbacks:
                    await self.callbacks['tick_update'](self.last_tick)
                    
            elif 'ohlc' in data:
                ohlc = data['ohlc']
                candle = {
                    'open': float(ohlc['open']),
                    'high': float(ohlc['high']),
                    'low': float(ohlc['low']),
                    'close': float(ohlc['close']),
                    'epoch': ohlc['epoch'],
                    'datetime': datetime.fromtimestamp(ohlc['epoch']),
                    'interval': 'M1' if int(ohlc['granularity']) == 60 else 'M5'
                }
                
                # Update candle data
                interval = candle['interval']
                if interval in self.candle_data:
                    self._update_candle(interval, candle)
                    
                    # Trigger callback for candle updates
                    if 'candle_update' in self.callbacks:
                        await self.callbacks['candle_update'](interval, candle)

            elif 'history' in data:
                # Handle historical data response
                echo = data.get('echo_req', {})
                interval_secs = echo.get('granularity')
                interval = 'M1' if interval_secs == 60 else 'M5'
                history = data['history']
                times = history['times']
                prices = history['prices'] # This is for ticks, but let's check candles
                
                if 'candles' in data: # Usually it's in a different field for history request with style='candles'
                   pass
            
            elif 'candles' in data:
                echo = data.get('echo_req', {})
                interval_secs = echo.get('granularity')
                interval = 'M1' if interval_secs == 60 else 'M5'
                for c in data['candles']:
                    candle = {
                        'open': float(c['open']),
                        'high': float(c['high']),
                        'low': float(c['low']),
                        'close': float(c['close']),
                        'epoch': c['epoch'],
                        'datetime': datetime.fromtimestamp(c['epoch']),
                        'interval': interval
                    }
                    self._update_candle(interval, candle)
                logger.info(f"Loaded {len(data['candles'])} historical candles for {interval}")

            elif 'authorize' in data:
                logger.info("Successfully authorized with Deriv API")
                        
            elif 'error' in data:
                logger.error(f"Deriv API Error: {data['error']}")
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            
    def _update_candle(self, interval: str, new_candle: Dict):
        """Update candle data for interval"""
        candles = self.candle_data[interval]
        
        # Check if this is a new candle or update to existing
        if candles and candles[-1]['epoch'] == new_candle['epoch']:
            # Update existing candle
            candles[-1] = new_candle
        else:
            # Add new candle
            candles.append(new_candle)
            
            # Keep only configured number of candles
            max_candles = Config.M1_CANDLE_COUNT if interval == 'M1' else Config.M5_CANDLE_COUNT
            if len(candles) > max_candles:
                candles.pop(0)
                
    async def subscribe_ticks(self):
        """Subscribe to tick data"""
        subscribe_msg = {
            "ticks": self.symbol,
            "subscribe": 1
        }
        await self._send(subscribe_msg)
        logger.info(f"Subscribed to tick data for {self.symbol}")
        
    async def subscribe_candles(self, interval: str):
        """Subscribe to candle data"""
        # For live subscription, use ticks_history with subscribe: 1
        subscribe_msg = {
            "ticks_history": self.symbol,
            "subscribe": 1,
            "granularity": int(interval),
            "style": "candles",
            "end": "latest",
            "count": 1
        }
        await self._send(subscribe_msg)
        logger.info(f"Subscribed to {interval}s candles for {self.symbol}")
        
    async def fetch_candle_history(self):
        """Fetch historical candle data"""
        try:
            # Fetch M1 candles
            await self._fetch_candles('60', Config.M1_CANDLE_COUNT)
            
            # Fetch M5 candles
            await self._fetch_candles('300', Config.M5_CANDLE_COUNT)
            
            self.history_fetched = True
            logger.info("Historical candle data fetch requests sent")
            
        except Exception as e:
            logger.error(f"Error fetching candle history: {e}")
            
    async def _fetch_candles(self, granularity: str, count: int):
        """Fetch candles for specific granularity"""
        request_msg = {
            "ticks_history": self.symbol,
            "adjust_start_time": 1,
            "count": count,
            "end": "latest",
            "granularity": int(granularity),
            "style": "candles"
        }
        await self._send(request_msg)
        
    async def _send(self, message: Dict):
        """Send message through WebSocket"""
        if self.is_connected and self.websocket:
            await self.websocket.send(json.dumps(message))
        else:
            logger.warning("WebSocket not connected, cannot send message")
            
    def register_callback(self, event: str, callback: Callable):
        """Register callback for events"""
        self.callbacks[event] = callback
        
    def get_latest_price(self) -> Optional[float]:
        """Get latest tick price"""
        return self.last_tick['price'] if self.last_tick else None
        
    def get_candles(self, interval: str) -> List[Dict]:
        """Get candle data for interval"""
        return self.candle_data.get(interval, [])
        
    def is_ready(self) -> bool:
        """Check if client has enough data"""
        return (self.is_connected and 
                self.history_fetched and 
                len(self.candle_data['M1']) >= Config.EMA_PERIOD and
                len(self.candle_data['M5']) >= Config.EMA_PERIOD)
