import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from .websocket_client import DerivWebSocketClient
from config.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PositionStatus(Enum):
    ACTIVE = "active"
    WIN = "win"
    LOSS = "loss"
    CLOSED = "closed"

class Position:
    """Trading position data structure"""
    def __init__(self, user_id: int, signal_type: str, entry_price: float, 
                 tp: float, sl: float, timeframe: str, is_manual: bool = False):
        self.user_id = user_id
        self.signal_type = signal_type  # BUY or SELL
        self.entry_price = entry_price
        self.tp = tp
        self.sl = sl
        self.timeframe = timeframe
        self.is_manual = is_manual
        self.status = PositionStatus.ACTIVE
        self.created_at = datetime.now()
        self.closed_at = None
        self.pnl = 0.0
        self.position_id = f"{user_id}_{int(self.created_at.timestamp())}"
        
    def update_pnl(self, current_price: float):
        """Update PnL based on current price"""
        if self.signal_type == 'BUY':
            self.pnl = current_price - self.entry_price
        else:  # SELL
            self.pnl = self.entry_price - current_price
            
    def check_close_conditions(self, current_price: float) -> Optional[str]:
        """Check if position should be closed"""
        if self.signal_type == 'BUY':
            if current_price >= self.tp:
                return 'TP'
            elif current_price <= self.sl:
                return 'SL'
        else:  # SELL
            if current_price <= self.tp:
                return 'TP'
            elif current_price >= self.sl:
                return 'SL'
                
        return None
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'position_id': self.position_id,
            'user_id': self.user_id,
            'signal_type': self.signal_type,
            'entry_price': self.entry_price,
            'tp': self.tp,
            'sl': self.sl,
            'timeframe': self.timeframe,
            'is_manual': self.is_manual,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'pnl': self.pnl
        }

class PositionTracker:
    """Real-time position tracking system"""
    
    def __init__(self):
        self.positions: Dict[str, Position] = {}  # position_id -> Position
        self.user_positions: Dict[int, List[str]] = {}  # user_id -> [position_ids]
        self.ws_client = None
        self.notification_callback = None
        self.is_tracking = False
        self.tracking_task = None
        self.price_history: List[float] = []
        
        # File for persistence
        self.data_file = os.path.join(Config.DATA_DIR, 'positions.json')
        
        # Load existing data
        self._load_positions()

    def set_notification_callback(self, callback):
        """Set callback for sending result notifications"""
        self.notification_callback = callback
        
    def set_websocket_client(self, ws_client: DerivWebSocketClient):
        """Set WebSocket client for price updates"""
        self.ws_client = ws_client
        
    async def start_tracking(self):
        """Start position tracking"""
        if self.is_tracking:
            return
            
        self.is_tracking = True
        self.tracking_task = asyncio.create_task(self._tracking_loop())
        logger.info("Position tracking started")
        
    async def stop_tracking(self):
        """Stop position tracking"""
        self.is_tracking = False
        if self.tracking_task:
            self.tracking_task.cancel()
        logger.info("Position tracking stopped")
        
    def create_position(self, user_id: int, signal_type: str, entry_price: float,
                       tp: float, sl: float, timeframe: str, is_manual: bool = False) -> Position:
        """Create new position"""
        position = Position(
            user_id=user_id,
            signal_type=signal_type,
            entry_price=entry_price,
            tp=tp,
            sl=sl,
            timeframe=timeframe,
            is_manual=is_manual
        )
        
        # Store position
        self.positions[position.position_id] = position
        
        # Add to user's positions
        if user_id not in self.user_positions:
            self.user_positions[user_id] = []
        self.user_positions[user_id].append(position.position_id)
        
        # Save to file
        self._save_positions()
        
        logger.info(f"Created position {position.position_id} for user {user_id}")
        return position
        
    def get_position(self, position_id: str) -> Optional[Position]:
        """Get position by ID"""
        return self.positions.get(position_id)
        
    def get_user_positions(self, user_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all positions for user"""
        if user_id not in self.user_positions:
            return []
            
        positions = []
        for pos_id in self.user_positions[user_id]:
            position = self.positions.get(pos_id)
            if position:
                if active_only and position.status == PositionStatus.ACTIVE:
                    positions.append(position.to_dict())
                elif not active_only:
                    positions.append(position.to_dict())
                    
        # Sort by creation time (newest first)
        positions.sort(key=lambda x: x['created_at'], reverse=True)
        return positions
        
    def get_active_positions(self) -> List[Position]:
        """Get all active positions"""
        return [pos for pos in self.positions.values() 
                if pos.status == PositionStatus.ACTIVE]
                
    async def _tracking_loop(self):
        """Main tracking loop - runs every 5 seconds"""
        try:
            while self.is_tracking:
                if self.ws_client and self.ws_client.is_connected:
                    current_price = self.ws_client.get_latest_price()
                    
                    if current_price:
                        # Update price history
                        self.price_history.append(current_price)
                        if len(self.price_history) > 100:
                            self.price_history.pop(0)
                            
                        # Check all active positions
                        active_positions = self.get_active_positions()
                        
                        for position in active_positions:
                            # Update PnL
                            position.update_pnl(current_price)
                            
                            # Check close conditions
                            close_reason = position.check_close_conditions(current_price)
                            
                            if close_reason:
                                await self._close_position(position, close_reason, current_price)
                                
                # Wait before next check
                await asyncio.sleep(Config.PRICE_TRACKING_INTERVAL)
                
        except asyncio.CancelledError:
            logger.info("Position tracking loop cancelled")
        except Exception as e:
            logger.error(f"Error in tracking loop: {e}")
            
    async def _close_position(self, position: Position, close_reason: str, close_price: float):
        """Close position and send notification"""
        try:
            # Update position status
            position.status = PositionStatus.WIN if close_reason == 'TP' else PositionStatus.LOSS
            position.closed_at = datetime.now()
            position.pnl = close_price - position.entry_price if position.signal_type == 'BUY' else position.entry_price - close_price
            
            # Save to file
            self._save_positions()
            
            # Update statistics
            from .statistics import StatisticsManager
            stats_manager = StatisticsManager()
            stats_manager.record_trade(
                user_id=position.user_id,
                signal_type=position.signal_type,
                result=close_reason,
                pnl=position.pnl,
                timeframe=position.timeframe,
                is_manual=position.is_manual
            )
            
            # Get user statistics
            winrate = stats_manager.calculate_winrate(position.user_id)
            
            # Format result message
            result_emoji = "🎯" if close_reason == 'TP' else "🛑"
            result_text = "WIN" if close_reason == 'TP' else "LOSS"
            
            result_message = f"""
{result_emoji} *XAUUSD RESULT*

📊 *Signal:* {position.signal_type}
💰 *Entry:* ${position.entry_price:.2f}
🎯 *TP:* ${position.tp:.2f}
🛑 *SL:* ${position.sl:.2f}
🏁 *Close:* ${close_price:.2f}

📈 *Result:* *{result_text}*
💵 *PnL:* ${position.pnl:+.2f}
🎯 *Winrate:* {winrate:.2f}%

⏰ *Time Closed:* {position.closed_at.strftime('%Y-%m-%d %H:%M:%S')}
⏱️ *Duration:* {self._format_duration(position.created_at, position.closed_at)}

🔄 Bot mencari sinyal baru...
            """
            
            # Send notification via callback
            if self.notification_callback:
                try:
                    await self.notification_callback(position.user_id, result_message)
                except Exception as e:
                    logger.error(f"Failed to send result to user {position.user_id}: {e}")
                    
            logger.info(f"Position {position.position_id} closed: {result_text} "
                       f"(PnL: ${position.pnl:.2f})")
                       
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            
    def _format_duration(self, start: datetime, end: datetime) -> str:
        """Format duration between two timestamps"""
        duration = end - start
        hours = int(duration.total_seconds() // 3600)
        minutes = int((duration.total_seconds() % 3600) // 60)
        seconds = int(duration.total_seconds() % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
            
    def _save_positions(self):
        """Save positions to file"""
        try:
            data = {
                'positions': [pos.to_dict() for pos in self.positions.values()],
                'user_positions': self.user_positions,
                'last_save': datetime.now().isoformat()
            }
            
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving positions: {e}")
            
    def _load_positions(self):
        """Load positions from file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    
                # Load positions
                for pos_data in data.get('positions', []):
                    position = Position(
                        user_id=pos_data['user_id'],
                        signal_type=pos_data['signal_type'],
                        entry_price=pos_data['entry_price'],
                        tp=pos_data['tp'],
                        sl=pos_data['sl'],
                        timeframe=pos_data['timeframe'],
                        is_manual=pos_data.get('is_manual', False)
                    )
                    position.position_id = pos_data['position_id']
                    position.status = PositionStatus(pos_data['status'])
                    position.created_at = datetime.fromisoformat(pos_data['created_at'])
                    position.closed_at = datetime.fromisoformat(pos_data['closed_at']) if pos_data['closed_at'] else None
                    position.pnl = pos_data.get('pnl', 0.0)
                    
                    self.positions[position.position_id] = position
                    
                # Load user positions mapping
                self.user_positions = {int(k): v for k, v in data.get('user_positions', {}).items()}
                
                logger.info(f"Loaded {len(self.positions)} positions from file")
                
        except Exception as e:
            logger.error(f"Error loading positions: {e}")
            
    def reset_user_positions(self, user_id: int):
        """Reset all positions for user"""
        if user_id in self.user_positions:
            # Remove positions
            for pos_id in self.user_positions[user_id]:
                if pos_id in self.positions:
                    del self.positions[pos_id]
                    
            # Clear user's position list
            self.user_positions[user_id] = []
            
            # Save to file
            self._save_positions()
            
            logger.info(f"Reset positions for user {user_id}")
            
    def get_position_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get position statistics for user"""
        positions = self.get_user_positions(user_id, active_only=False)
        
        total = len(positions)
        wins = len([p for p in positions if p['status'] == 'win'])
        losses = len([p for p in positions if p['status'] == 'loss'])
        active = len([p for p in positions if p['status'] == 'active'])
        
        total_pnl = sum(p['pnl'] for p in positions if p['status'] in ['win', 'loss'])
        
        return {
            'total_positions': total,
            'active_positions': active,
            'wins': wins,
            'losses': losses,
            'winrate': (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0,
            'total_pnl': total_pnl
        }