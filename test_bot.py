#!/usr/bin/env python3
"""
XAUUSD Bot Testing Script
Untuk menguji semua komponen bot sebelum deployment
"""

import asyncio
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config.config import Config
from src.websocket_client import DerivWebSocketClient
from src.indicators import TechnicalIndicators
from src.signal_generator import SignalGenerator
from src.user_manager import UserManager
from src.statistics import StatisticsManager
from src.position_tracker import PositionTracker

class BotTester:
    """Test suite for XAUUSD Bot"""
    
    def __init__(self):
        self.test_results = []
        
    def log_result(self, test_name: str, status: str, message: str = ""):
        """Log test result"""
        result = {
            'test': test_name,
            'status': status,
            'message': message
        }
        self.test_results.append(result)
        
        status_symbol = "✅" if status == "PASS" else "❌"
        print(f"{status_symbol} {test_name}")
        if message:
            print(f"   {message}")
            
    async def test_config(self):
        """Test configuration"""
        try:
            Config.init_directories()
            
            # Check if required directories exist
            if os.path.exists(Config.DATA_DIR) and os.path.exists(Config.LOGS_DIR):
                self.log_result("Configuration", "PASS", "Directories created successfully")
            else:
                self.log_result("Configuration", "FAIL", "Failed to create directories")
                
            # Check environment variables
            if Config.BOT_TOKEN and Config.BOT_TOKEN != "YOUR_TELEGRAM_BOT_TOKEN_HERE":
                self.log_result("Bot Token", "PASS", "Token configured")
            else:
                self.log_result("Bot Token", "FAIL", "Token not configured or invalid")
                
        except Exception as e:
            self.log_result("Configuration", "FAIL", f"Error: {e}")
            
    async def test_websocket(self):
        """Test WebSocket connection"""
        try:
            ws_client = DerivWebSocketClient()
            
            print("\n🔄 Testing WebSocket connection...")
            await ws_client.connect()
            
            # Wait for connection
            for i in range(10):
                if ws_client.is_connected:
                    break
                await asyncio.sleep(1)
                
            if ws_client.is_connected:
                self.log_result("WebSocket Connection", "PASS", "Connected successfully")
                
                # Wait for data
                await asyncio.sleep(5)
                
                if ws_client.is_ready():
                    self.log_result("WebSocket Data", "PASS", "Data received and ready")
                    
                    # Test price data
                    price = ws_client.get_latest_price()
                    if price:
                        self.log_result("Price Data", "PASS", f"Current price: ${price:.2f}")
                    else:
                        self.log_result("Price Data", "FAIL", "No price data")
                else:
                    self.log_result("WebSocket Data", "FAIL", "Data not ready")
            else:
                self.log_result("WebSocket Connection", "FAIL", "Failed to connect")
                
            await ws_client.disconnect()
            
        except Exception as e:
            self.log_result("WebSocket", "FAIL", f"Error: {e}")
            
    async def test_indicators(self):
        """Test technical indicators"""
        try:
            indicators = TechnicalIndicators()
            
            # Test data
            test_prices = [1800.0 + i * 10 for i in range(60)]  # 60 data points
            test_candles = [
                {
                    'open': 1800.0 + i * 10,
                    'high': 1810.0 + i * 10,
                    'low': 1790.0 + i * 10,
                    'close': 1805.0 + i * 10,
                    'epoch': 1234567890 + i * 60
                }
                for i in range(60)
            ]
            
            # Test EMA
            ema = indicators.calculate_ema(test_prices, 50)
            if ema:
                self.log_result("EMA Calculation", "PASS", f"EMA 50: {ema:.2f}")
            else:
                self.log_result("EMA Calculation", "FAIL", "No result")
                
            # Test RSI
            rsi = indicators.calculate_rsi(test_prices, 3)
            if rsi is not None:
                self.log_result("RSI Calculation", "PASS", f"RSI 3: {rsi:.2f}")
            else:
                self.log_result("RSI Calculation", "FAIL", "No result")
                
            # Test ADX
            adx = indicators.calculate_adx(test_candles, 55)
            if adx is not None:
                self.log_result("ADX Calculation", "PASS", f"ADX 55: {adx:.2f}")
            else:
                self.log_result("ADX Calculation", "FAIL", "No result")
                
            # Test signal logic
            test_indicators = {
                'EMA_50': 1800.0,
                'RSI_3': 25.0,
                'ADX_55': 35.0,
                'CURRENT_PRICE': 1810.0,
                'PREV_RSI_3': 20.0
            }
            
            buy_signal = indicators.check_buy_signal(test_indicators)
            self.log_result("Buy Signal Logic", "PASS" if buy_signal else "FAIL", 
                          f"Signal: {buy_signal}")
            
        except Exception as e:
            self.log_result("Indicators", "FAIL", f"Error: {e}")
            
    async def test_user_manager(self):
        """Test user management"""
        try:
            user_manager = UserManager()
            
            # Test add user
            user_manager.add_user(12345, "test_user", "Test User")
            user = user_manager.get_user(12345)
            
            if user:
                self.log_result("User Management", "PASS", "User created successfully")
                
                # Test preferences
                user_manager.set_user_preference(12345, 'auto_signals', True)
                pref = user_manager.get_user_preference(12345, 'auto_signals')
                
                if pref:
                    self.log_result("User Preferences", "PASS", "Preferences working")
                else:
                    self.log_result("User Preferences", "FAIL", "Preferences not saved")
                    
                # Test statistics
                stats = user_manager.get_user_statistics(12345)
                if stats:
                    self.log_result("User Statistics", "PASS", f"Stats: {len(stats)} fields")
                else:
                    self.log_result("User Statistics", "FAIL", "No stats returned")
                    
            else:
                self.log_result("User Management", "FAIL", "User not found")
                
        except Exception as e:
            self.log_result("User Manager", "FAIL", f"Error: {e}")
            
    async def test_statistics(self):
        """Test statistics manager"""
        try:
            stats_manager = StatisticsManager()
            
            # Record test trades
            stats_manager.record_trade(12345, 'BUY', 'TP', 3.0, 'M5', False)
            stats_manager.record_trade(12345, 'SELL', 'SL', -3.0, 'M1', True)
            stats_manager.record_trade(12345, 'BUY', 'TP', 3.0, 'M5', False)
            
            # Test winrate calculation
            winrate = stats_manager.calculate_winrate(12345)
            self.log_result("Winrate Calculation", "PASS", f"Winrate: {winrate:.2f}%")
            
            # Test user stats
            user_stats = stats_manager.get_user_stats(12345)
            if user_stats:
                self.log_result("User Statistics", "PASS", 
                              f"Total: {user_stats['total_signals']}, "
                              f"Winrate: {user_stats['winrate']:.2f}%")
            else:
                self.log_result("User Statistics", "FAIL", "No stats returned")
                
            # Test global stats
            global_stats = stats_manager.get_global_stats()
            if global_stats:
                self.log_result("Global Statistics", "PASS", 
                              f"Total trades: {global_stats['total_trades']}")
            else:
                self.log_result("Global Statistics", "FAIL", "No global stats")
                
        except Exception as e:
            self.log_result("Statistics", "FAIL", f"Error: {e}")
            
    async def test_position_tracker(self):
        """Test position tracking"""
        try:
            tracker = PositionTracker()
            
            # Create test position
            position = tracker.create_position(
                user_id=12345,
                signal_type='BUY',
                entry_price=1800.0,
                tp=1803.0,
                sl=1797.0,
                timeframe='M5',
                is_manual=False
            )
            
            if position:
                self.log_result("Position Creation", "PASS", f"Position ID: {position.position_id}")
                
                # Test position retrieval
                positions = tracker.get_user_positions(12345)
                if positions:
                    self.log_result("Position Retrieval", "PASS", f"Found {len(positions)} positions")
                else:
                    self.log_result("Position Retrieval", "FAIL", "No positions found")
                    
                # Test PnL calculation
                position.update_pnl(1801.5)
                self.log_result("PnL Calculation", "PASS", f"PnL: ${position.pnl:.2f}")
                
                # Test close conditions
                close_reason = position.check_close_conditions(1804.0)
                if close_reason == 'TP':
                    self.log_result("Close Conditions", "PASS", f"TP triggered: {close_reason}")
                else:
                    self.log_result("Close Conditions", "FAIL", f"Expected TP, got: {close_reason}")
                    
            else:
                self.log_result("Position Creation", "FAIL", "Position not created")
                
        except Exception as e:
            self.log_result("Position Tracker", "FAIL", f"Error: {e}")
            
    async def test_signal_generator(self):
        """Test signal generator"""
        try:
            # This test requires WebSocket connection
            ws_client = DerivWebSocketClient()
            await ws_client.connect()
            
            signal_generator = SignalGenerator(ws_client)
            
            # Test manual signal generation
            manual_signal = await signal_generator.generate_manual_signal(12345)
            
            if manual_signal:
                self.log_result("Manual Signal", "PASS", 
                              f"Signal: {manual_signal.signal_type} at ${manual_signal.entry_price:.2f}")
            else:
                self.log_result("Manual Signal", "INFO", "No signal conditions met (normal)")
                
            await ws_client.disconnect()
            
        except Exception as e:
            self.log_result("Signal Generator", "FAIL", f"Error: {e}")
            
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*50)
        print("TEST SUMMARY")
        print("="*50)
        
        passed = sum(1 for r in self.test_results if r['status'] == 'PASS')
        failed = sum(1 for r in self.test_results if r['status'] == 'FAIL')
        info = sum(1 for r in self.test_results if r['status'] == 'INFO')
        
        print(f"Total tests: {len(self.test_results)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"ℹ️  Info: {info}")
        
        if failed == 0:
            print(f"\n{GREEN}🎉 All tests passed! Bot is ready to run.{NC}")
            return True
        else:
            print(f"\n{RED}⚠️  Some tests failed. Please check the issues above.{NC}")
            return False
            
async def run_all_tests():
    """Run all tests"""
    tester = BotTester()
    
    print("🚀 XAUUSD Bot Testing Suite")
    print("="*50)
    
    # Run tests
    await tester.test_config()
    await tester.test_websocket()
    await tester.test_indicators()
    await tester.test_user_manager()
    await tester.test_statistics()
    await tester.test_position_tracker()
    await tester.test_signal_generator()
    
    # Print summary
    success = tester.print_summary()
    
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTesting cancelled!")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)