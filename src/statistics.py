import json
import os
import os.path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

from config.config import Config

logger = logging.getLogger(__name__)

class TradeRecord:
    """Individual trade record"""
    def __init__(self, user_id: int, signal_type: str, result: str, pnl: float,
                 timeframe: str, is_manual: bool = False):
        self.user_id = user_id
        self.signal_type = signal_type  # BUY or SELL
        self.result = result  # TP (WIN) or SL (LOSS)
        self.pnl = pnl
        self.timeframe = timeframe
        self.is_manual = is_manual
        self.timestamp = datetime.now()
        self.trade_id = f"{user_id}_{int(self.timestamp.timestamp())}"
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'trade_id': self.trade_id,
            'user_id': self.user_id,
            'signal_type': self.signal_type,
            'result': self.result,
            'pnl': self.pnl,
            'timeframe': self.timeframe,
            'is_manual': self.is_manual,
            'timestamp': self.timestamp.isoformat()
        }

class StatisticsManager:
    """Trading statistics and analytics"""
    
    def __init__(self):
        self.trades: Dict[str, TradeRecord] = {}  # trade_id -> TradeRecord
        self.user_trades: Dict[int, List[str]] = {}  # user_id -> [trade_ids]
        self.data_file = os.path.join(Config.DATA_DIR, 'statistics.json')
        
        # Load existing data
        self._load_statistics()
        
    def record_trade(self, user_id: int, signal_type: str, result: str, 
                    pnl: float, timeframe: str, is_manual: bool = False):
        """Record a completed trade"""
        trade = TradeRecord(
            user_id=user_id,
            signal_type=signal_type,
            result=result,
            pnl=pnl,
            timeframe=timeframe,
            is_manual=is_manual
        )
        
        # Store trade
        self.trades[trade.trade_id] = trade
        
        # Add to user's trades — guard duplicate IDs
        if user_id not in self.user_trades:
            self.user_trades[user_id] = []
        if trade.trade_id not in self.user_trades[user_id]:
            self.user_trades[user_id].append(trade.trade_id)
        
        # Keep only last 1000 trades per user
        if len(self.user_trades[user_id]) > 1000:
            # Remove oldest trades
            oldest_trades = sorted(self.user_trades[user_id], 
                                 key=lambda x: self.trades[x].timestamp)[:-1000]
            for trade_id in oldest_trades:
                del self.trades[trade_id]
                self.user_trades[user_id].remove(trade_id)
                
        # Save to file
        self._save_statistics()
        
        logger.info(f"Recorded trade {trade.trade_id}: {result} ${pnl:.2f}")
        
    def get_user_trades(self, user_id: int, days: int = 30) -> List[TradeRecord]:
        """Get user's trades within specified period"""
        if user_id not in self.user_trades:
            return []
            
        cutoff_date = datetime.now() - timedelta(days=days)
        trades = []
        
        for trade_id in self.user_trades[user_id]:
            if trade_id in self.trades:
                trade = self.trades[trade_id]
                if trade.timestamp >= cutoff_date:
                    trades.append(trade)
                    
        # Sort by timestamp (newest first)
        trades.sort(key=lambda x: x.timestamp, reverse=True)
        return trades
        
    def calculate_winrate(self, user_id: int, days: int = 30) -> float:
        """Calculate win rate for user"""
        trades = self.get_user_trades(user_id, days)
        
        if not trades:
            return 0.0
            
        wins = sum(1 for trade in trades if trade.result == 'TP')
        total_trades = len(trades)
        
        return (wins / total_trades) * 100 if total_trades > 0 else 0.0
        
    def get_user_stats(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive user statistics"""
        trades = self.get_user_trades(user_id, days)
        
        if not trades:
            return {
                'total_signals': 0,
                'win_count': 0,
                'loss_count': 0,
                'winrate': 0.0,
                'total_pnl': 0.0,
                'avg_pnl': 0.0,
                'period_days': days,
                'last_signal': None,
                'best_trade': None,
                'worst_trade': None,
                'avg_trade_duration': None
            }
            
        # Basic stats
        total_signals = len(trades)
        wins = [trade for trade in trades if trade.result == 'TP']
        losses = [trade for trade in trades if trade.result == 'SL']
        win_count = len(wins)
        loss_count = len(losses)
        winrate = (win_count / total_signals) * 100 if total_signals > 0 else 0
        
        # PnL stats
        total_pnl = sum(trade.pnl for trade in trades)
        avg_pnl = total_pnl / total_signals if total_signals > 0 else 0
        
        # Best/worst trades
        best_trade = max(trades, key=lambda x: x.pnl) if trades else None
        worst_trade = min(trades, key=lambda x: x.pnl) if trades else None
        
        # Timeframe breakdown
        timeframe_stats = {}
        for trade in trades:
            tf = trade.timeframe
            if tf not in timeframe_stats:
                timeframe_stats[tf] = {'count': 0, 'wins': 0, 'pnl': 0}
            timeframe_stats[tf]['count'] += 1
            if trade.result == 'TP':
                timeframe_stats[tf]['wins'] += 1
            timeframe_stats[tf]['pnl'] += trade.pnl
            
        # Manual vs auto signals
        manual_signals = [t for t in trades if t.is_manual]
        auto_signals = [t for t in trades if not t.is_manual]
        
        return {
            'total_signals': total_signals,
            'win_count': win_count,
            'loss_count': loss_count,
            'winrate': winrate,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'period_days': days,
            'last_signal': trades[0].timestamp.strftime('%Y-%m-%d %H:%M') if trades else None,
            'best_trade': {
                'signal_type': best_trade.signal_type,
                'result': best_trade.result,
                'pnl': best_trade.pnl,
                'timeframe': best_trade.timeframe,
                'date': best_trade.timestamp.strftime('%Y-%m-%d %H:%M')
            } if best_trade else None,
            'worst_trade': {
                'signal_type': worst_trade.signal_type,
                'result': worst_trade.result,
                'pnl': worst_trade.pnl,
                'timeframe': worst_trade.timeframe,
                'date': worst_trade.timestamp.strftime('%Y-%m-%d %H:%M')
            } if worst_trade else None,
            'timeframe_breakdown': timeframe_stats,
            'manual_signals': {
                'count': len(manual_signals),
                'winrate': (sum(1 for t in manual_signals if t.result == 'TP') / len(manual_signals) * 100) if manual_signals else 0,
                'pnl': sum(t.pnl for t in manual_signals)
            },
            'auto_signals': {
                'count': len(auto_signals),
                'winrate': (sum(1 for t in auto_signals if t.result == 'TP') / len(auto_signals) * 100) if auto_signals else 0,
                'pnl': sum(t.pnl for t in auto_signals)
            }
        }
        
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global bot statistics"""
        all_trades = list(self.trades.values())
        
        if not all_trades:
            return {
                'total_trades': 0,
                'total_users': 0,
                'global_winrate': 0,
                'total_pnl': 0,
                'avg_pnl_per_trade': 0,
                'most_profitable_timeframe': None,
                'best_performing_user': None
            }
            
        total_trades = len(all_trades)
        total_users = len(set(trade.user_id for trade in all_trades))
        total_pnl = sum(trade.pnl for trade in all_trades)
        avg_pnl_per_trade = total_pnl / total_trades if total_trades > 0 else 0
        
        # Global winrate
        global_wins = sum(1 for trade in all_trades if trade.result == 'TP')
        global_winrate = (global_wins / total_trades) * 100 if total_trades > 0 else 0
        
        # Timeframe performance
        timeframe_stats = {}
        for trade in all_trades:
            tf = trade.timeframe
            if tf not in timeframe_stats:
                timeframe_stats[tf] = {'trades': 0, 'wins': 0, 'pnl': 0}
            timeframe_stats[tf]['trades'] += 1
            if trade.result == 'TP':
                timeframe_stats[tf]['wins'] += 1
            timeframe_stats[tf]['pnl'] += trade.pnl
            
        # Find most profitable timeframe
        most_profitable_tf = None
        best_tf_pnl = float('-inf')
        for tf, stats in timeframe_stats.items():
            if stats['pnl'] > best_tf_pnl:
                best_tf_pnl = stats['pnl']
                most_profitable_tf = tf
                
        # Best performing user (by winrate, min 10 trades)
        user_stats = {}
        for trade in all_trades:
            uid = trade.user_id
            if uid not in user_stats:
                user_stats[uid] = {'trades': 0, 'wins': 0}
            user_stats[uid]['trades'] += 1
            if trade.result == 'TP':
                user_stats[uid]['wins'] += 1
                
        best_user = None
        best_winrate = 0
        for uid, stats in user_stats.items():
            if stats['trades'] >= 10:  # Minimum 10 trades
                winrate = (stats['wins'] / stats['trades']) * 100
                if winrate > best_winrate:
                    best_winrate = winrate
                    best_user = uid
                    
        return {
            'total_trades': total_trades,
            'total_users': total_users,
            'global_winrate': global_winrate,
            'total_pnl': total_pnl,
            'avg_pnl_per_trade': avg_pnl_per_trade,
            'most_profitable_timeframe': {
                'timeframe': most_profitable_tf,
                'pnl': best_tf_pnl,
                'stats': timeframe_stats.get(most_profitable_tf, {}) if most_profitable_tf else {}
            },
            'best_performing_user': {
                'user_id': best_user,
                'winrate': best_winrate
            } if best_user else None,
            'timeframe_breakdown': timeframe_stats
        }
        
    def reset_user_stats(self, user_id: int):
        """Reset all statistics for user"""
        if user_id in self.user_trades:
            # Remove all trades for this user
            for trade_id in self.user_trades[user_id]:
                if trade_id in self.trades:
                    del self.trades[trade_id]
                    
            # Clear user's trade list
            self.user_trades[user_id] = []
            
            # Save to file
            self._save_statistics()
            
            logger.info(f"Reset statistics for user {user_id}")
            
    def _save_statistics(self):
        """Save statistics to file — Bug #5 fix: atomic write via temp+rename"""
        try:
            data = {
                'trades': [trade.to_dict() for trade in self.trades.values()],
                'user_trades': self.user_trades,
                'last_save': datetime.now().isoformat()
            }
            tmp_path = self.data_file + '.tmp'
            with open(tmp_path, 'w') as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, self.data_file)
                
        except Exception as e:
            logger.error(f"Error saving statistics: {e}")
            
    def _load_statistics(self):
        """Load statistics from file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    
                # Load trades
                for trade_data in data.get('trades', []):
                    trade = TradeRecord(
                        user_id=trade_data['user_id'],
                        signal_type=trade_data['signal_type'],
                        result=trade_data['result'],
                        pnl=trade_data['pnl'],
                        timeframe=trade_data['timeframe'],
                        is_manual=trade_data.get('is_manual', False)
                    )
                    trade.trade_id = trade_data['trade_id']
                    trade.timestamp = datetime.fromisoformat(trade_data['timestamp'])
                    
                    self.trades[trade.trade_id] = trade
                    
                # Load user trades mapping
                self.user_trades = {int(k): v for k, v in data.get('user_trades', {}).items()}
                
                logger.info(f"Loaded {len(self.trades)} trades from file")
                
        except Exception as e:
            logger.error(f"Error loading statistics: {e}")
            
    def export_user_trades(self, user_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Export user's trades in CSV-friendly format"""
        trades = self.get_user_trades(user_id, days)
        
        export_data = []
        for trade in trades:
            export_data.append({
                'Date': trade.timestamp.strftime('%Y-%m-%d'),
                'Time': trade.timestamp.strftime('%H:%M:%S'),
                'Signal': trade.signal_type,
                'Result': trade.result,
                'PnL': trade.pnl,
                'Timeframe': trade.timeframe,
                'Manual': 'Yes' if trade.is_manual else 'No'
            })
            
        return export_data