import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.error import TelegramError

from .websocket_client import DerivWebSocketClient
from .signal_generator import SignalGenerator, Signal
from .position_tracker import PositionTracker
from .user_manager import UserManager
from .statistics import StatisticsManager
from config.config import Config

# logging.basicConfig is already configured in main.py
logger = logging.getLogger(__name__)

class XAUUSDBot:
    """XAUUSD Scalping Signal Telegram Bot"""
    
    def __init__(self):
        self.app = Application.builder().token(Config.BOT_TOKEN).build()
        self.ws_client = DerivWebSocketClient()
        self.signal_generator = SignalGenerator(self.ws_client)
        self.position_tracker = PositionTracker()
        self.user_manager = UserManager()
        self.stats_manager = StatisticsManager()
        
        # Track active dashboard messages
        self.dashboard_messages = {}  # user_id -> message_id
        self.dashboard_tasks = {}     # user_id -> task
        
        # Register signal callback
        self.signal_generator.register_signal_callback(self._on_new_signal)
        
    async def start(self):
        """Start the bot"""
        try:
            # Initialize WebSocket connection
            await self.ws_client.connect()
            
            # Wait for WebSocket to be ready
            while not self.ws_client.is_ready():
                logger.info("Waiting for WebSocket to be ready...")
                await asyncio.sleep(2)
                
            # Start signal generator
            await self.signal_generator.start()
            
            # Set up command handlers
            self._setup_handlers()
            
            # Start the bot
            await self.app.initialize()
            await self.app.start()
            
            logger.info("Bot started successfully!")
            
            # Keep running
            await self.app.updater.start_polling()
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise
            
    async def stop(self):
        """Stop the bot"""
        try:
            # Stop all tasks
            for task in self.dashboard_tasks.values():
                task.cancel()
                
            # Stop components
            await self.signal_generator.stop()
            await self.ws_client.disconnect()
            
            # Stop bot
            await self.app.stop()
            
            logger.info("Bot stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
            
    def _setup_handlers(self):
        """Set up command handlers"""
        self.app.add_handler(CommandHandler('start', self.cmd_start))
        self.app.add_handler(CommandHandler('dashboard', self.cmd_dashboard))
        self.app.add_handler(CommandHandler('stats', self.cmd_stats))
        self.app.add_handler(CommandHandler('getsignal', self.cmd_getsignal))
        self.app.add_handler(CommandHandler('info', self.cmd_info))
        self.app.add_handler(CommandHandler('riset', self.cmd_riset))
        self.app.add_handler(CommandHandler('help', self.cmd_help))
        self.app.add_handler(CommandHandler('stop', self.cmd_stop_dashboard))
        
        # Callback query handler
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        user_id = user.id
        
        # Add user to active users
        self.user_manager.add_user(user_id, user.username or user.first_name)
        
        welcome_message = f"""
🤖 *XAUUSD SCALPING BOT*

Halo {user.first_name}! 👋

Bot sinyal scalping XAUUSD kini *AKTIF* dan siap beroperasi 24/7!

📊 *Strategi:*
• EMA 50, RSI 3, ADX 55
• Timeframe: M1 & M5
• Risk:Reward = 1:1 (TP: ${Config.DEFAULT_TP}, SL: ${Config.DEFAULT_SL})

📱 *Perintah yang tersedia:*
/dashboard - Lihat posisi aktif + live price
/stats - Statistik trading
/getsignal - Sinyal manual khusus Anda
/info - Info sistem & strategi
/riset - Reset data historis
/help - Bantuan

Bot akan otomatis mengirim sinyal saat kondisi terpenuhi. 🎯

⚠️ *Disclaimer:* Trading berisiko. Gunakan dengan bijak.
        """
        
        keyboard = [
            [InlineKeyboardButton("📊 Dashboard", callback_data='dashboard')],
            [InlineKeyboardButton("📈 Statistik", callback_data='stats')],
            [InlineKeyboardButton("🎯 Sinyal Manual", callback_data='getsignal')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_message, 
                                      parse_mode='Markdown',
                                      reply_markup=reply_markup)
        
        # Auto-start dashboard for new users
        await self._start_dashboard(update, context)
        
    async def cmd_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /dashboard command"""
        await self._start_dashboard(update, context)
        
    async def _start_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start live dashboard"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Check if dashboard is already running
        if user_id in self.dashboard_tasks and not self.dashboard_tasks[user_id].done():
            await update.message.reply_text("Dashboard sudah aktif! Ketik /stop untuk menghentikan.")
            return
            
        # Send initial dashboard message
        dashboard_msg = await update.message.reply_text("🔄 Memulai dashboard...")
        self.dashboard_messages[user_id] = dashboard_msg.message_id
        
        # Start dashboard update task
        task = asyncio.create_task(self._update_dashboard(user_id, chat_id))
        self.dashboard_tasks[user_id] = task
        
    async def _update_dashboard(self, user_id: int, chat_id: int):
        """Update dashboard every 5 seconds"""
        try:
            while True:
                # Get current data
                latest_price = self.ws_client.get_latest_price()
                active_positions = self.position_tracker.get_user_positions(user_id)
                
                # Format dashboard message
                if latest_price:
                    price_text = f"${latest_price:.2f}"
                else:
                    price_text = "Connecting..."
                    
                dashboard_text = f"""
📊 *XAUUSD DASHBOARD*

💰 *Harga Live:* `{price_text}`
⏰ *Update:* {datetime.now().strftime('%H:%M:%S')}

📈 *Posisi Aktif:* {len(active_positions)}
                """
                
                if active_positions:
                    for i, position in enumerate(active_positions[:3], 1):
                        status = "🟢 BUY" if position['signal_type'] == 'BUY' else "🔴 SELL"
                        pnl = position.get('pnl', 0)
                        pnl_text = f"{pnl:+.2f}" if pnl != 0 else "Menunggu..."
                        
                        dashboard_text += f"""
*{i}. {status}*
Entry: ${position['entry_price']:.2f}
TP: ${position['tp']:.2f} | SL: ${position['sl']:.2f}
PnL: `{pnl_text}`
                        """
                else:
                    dashboard_text += "\n_Tidak ada posisi aktif_"
                    
                dashboard_text += f"""

🤖 *Status Bot:* {"🟢 Aktif" if self.ws_client.is_connected else "🔴 Terputus"}
📡 *WebSocket:* {"✅ Terhubung" if self.ws_client.is_ready() else "🔄 Menghubungkan..."}
                """
                
                # Update message
                try:
                    message_id = self.dashboard_messages.get(user_id)
                    if message_id:
                        await self.app.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=message_id,
                            text=dashboard_text,
                            parse_mode='Markdown'
                        )
                except TelegramError as e:
                    if "message to edit not found" in str(e).lower():
                        # Dashboard message was deleted, stop updates
                        break
                        
                await asyncio.sleep(Config.DASHBOARD_UPDATE_INTERVAL)
                
        except asyncio.CancelledError:
            logger.info(f"Dashboard task cancelled for user {user_id}")
        except Exception as e:
            logger.error(f"Error updating dashboard for user {user_id}: {e}")
            
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        user_id = update.effective_user.id
        
        # Get user statistics
        stats = self.stats_manager.get_user_stats(user_id)
        
        stats_text = f"""
📈 *STATISTIK TRADING*

📊 *Total Signal:* {stats['total_signals']}
✅ *Win:* {stats['win_count']}
❌ *Loss:* {stats['loss_count']}
🎯 *Winrate:* {stats['winrate']:.2f}%

💰 *Total PnL:* ${stats['total_pnl']:.2f}
📊 *Rata-rata PnL per trade:* ${stats['avg_pnl']:.2f}

⏰ *Periode:* {stats['period_days']} hari terakhir
🔄 *Signal terakhir:* {stats['last_signal'] or 'Belum ada'}
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Reset Statistik", callback_data='reset_stats')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(stats_text, 
                                      parse_mode='Markdown',
                                      reply_markup=reply_markup)
        
    async def cmd_getsignal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /getsignal command - Generate manual signal"""
        user_id = update.effective_user.id
        
        # Check if user already has an active position
        active_positions = self.position_tracker.get_user_positions(user_id)
        if len(active_positions) > 0:
            await update.message.reply_text("⚠️ Anda sudah memiliki posisi aktif. Selesaikan posisi tersebut sebelum meminta sinyal baru.")
            return

        # Send waiting message
        wait_msg = await update.message.reply_text("🔄 Mencari sinyal untuk Anda...")
        
        # Generate manual signal
        signal = await self.signal_generator.generate_manual_signal(user_id)
        
        if signal:
            # Create position for tracking
            position = self.position_tracker.create_position(
                user_id=user_id,
                signal_type=signal.signal_type,
                entry_price=signal.entry_price,
                tp=signal.tp,
                sl=signal.sl,
                timeframe=signal.timeframe,
                is_manual=True
            )
            
            # Format signal message
            signal_text = f"""
🎯 *SINYAL MANUAL*

{'🟢 BUY' if signal.signal_type == 'BUY' else '🔴 SELL'} *XAUUSD*

💰 *Entry:* ${signal.entry_price:.2f}
🎯 *TP:* ${signal.tp:.2f}
🛑 *SL:* ${signal.sl:.2f}

📊 *Indikator:*
• EMA 50: ${signal.ema_50:.2f}
• RSI 3: {signal.rsi:.2f}
• ADX 55: {signal.adx:.2f}

⏰ *Timeframe:* {signal.timeframe}
🕐 *Waktu:* {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

⚠️ *Risk Management:*
Risk:Reward = 1:1
Stop Loss: ${Config.DEFAULT_SL}
Take Profit: ${Config.DEFAULT_TP}

🔄 *Status:* Akan dipantau otomatis...
            """
            
            keyboard = [
                [InlineKeyboardButton("📊 Lihat Posisi", callback_data='view_position')],
                [InlineKeyboardButton("🗑️ Hapus Sinyal", callback_data='delete_signal')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await wait_msg.edit_text(signal_text, 
                                   parse_mode='Markdown',
                                   reply_markup=reply_markup)
            
        else:
            await wait_msg.edit_text("""
❌ *TIDAK ADA SINYAL*

Saat ini tidak ada kondisi yang memenuhi kriteria sinyal.

Kondisi yang dicari:
• Harga di atas/bawah EMA 50
• RSI keluar dari zona overbought/oversold
• ADX > 30 (trend cukup kuat)

Silakan coba lagi nanti atau tunggu sinyal otomatis dari bot.
            """, parse_mode='Markdown')
            
    async def cmd_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /info command"""
        info_text = f"""
🤖 *INFO SISTEM*

📊 *Strategi Trading:*
• EMA 50: Trend direction
• RSI 3: Momentum entry/exit
• ADX 55: Filter kekuatan trend

🎯 *Logika Sinyal:*

🟢 *BUY:*
1. Harga di atas EMA 50
2. RSI keluar dari oversold (±20-25)
3. ADX > 30 (trend cukup kuat)

🔴 *SELL:*
1. Harga di bawah EMA 50
2. RSI keluar dari overbought (±75-80)
3. ADX > 30 (trend cukup kuat)

⚙️ *Pengaturan:*
• Timeframe: M1 & M5
• Risk:Reward = 1:1
• TP: ${Config.DEFAULT_TP}
• SL: ${Config.DEFAULT_SL}
• Filter ADX: > {Config.ADX_THRESHOLD}

🔄 *Operasional:*
• Bot berjalan 24/7 nonstop
• Sinyal otomatis + manual
• Tracking posisi real-time
• Dashboard update 5 detik

⚠️ *Disclaimer:*
Bot ini hanya untuk analisis dan sinyal trading. 
Tidak melakukan eksekusi order otomatis.
Selalu gunakan risk management yang tepat.
Trading forex dan emas melibatkan risiko kehilangan modal.
        """
        
        await update.message.reply_text(info_text, parse_mode='Markdown')
        
    async def cmd_riset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /riset command - Reset user statistics"""
        user_id = update.effective_user.id
        
        # Confirm reset
        keyboard = [
            [
                InlineKeyboardButton("✅ Ya, Reset", callback_data=f'confirm_reset_{user_id}'),
                InlineKeyboardButton("❌ Batal", callback_data='cancel_reset')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⚠️ *RESET DATA TRADING*\n\nAnda yakin ingin mereset semua data trading?\n"
            "Data yang akan dihapus:\n"
            "• Riwayat posisi\n"
            "• Statistik trading\n"
            "• Data tidak dapat dikembalikan",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = f"""
🆘 *BANTUAN*

📱 *Perintah Utama:*

/start - Aktifkan bot & mulai sinyal
/dashboard - Dashboard live (update 5 detik)
/stats - Lihat statistik trading
/getsignal - Sinyal manual khusus Anda
/info - Info sistem & strategi bot
/riset - Reset data historis trading
/help - Tampilkan bantuan ini
/stop - Hentikan dashboard

🔧 *Cara Menggunakan:*

1. *Start Bot:*
   Ketik /start untuk mengaktifkan bot
   Bot otomatis mencari sinyal 24/7

2. *Dashboard:*
   Ketik /dashboard untuk melihat:
   • Harga XAUUSD live
   • Posisi aktif Anda
   • Status bot & koneksi

3. *Sinyal Otomatis:*
   Bot kirim sinyal ketika kondisi terpenuhi
   Sinyal langsung dipantau hingga TP/SL

4. *Sinyal Manual:*
   Ketik /getsignal untuk minta sinyal
   Setiap user punya sinyal terpisah

5. *Statistik:*
   Ketik /stats untuk lihat:
   • Win/Loss rate
   • Total PnL
   • History trading

⚠️ *Penting:*
• Sinyal tidak auto-eksekusi
• Gunakan di broker Anda sendiri
• Selalu pakai stop loss
• Jangan risk lebih dari 2% per trade

🆘 *Butuh Bantuan?*
Hubungi admin jika ada masalah.
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
        
    async def cmd_stop_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command - Stop dashboard updates"""
        user_id = update.effective_user.id
        
        if user_id in self.dashboard_tasks:
            self.dashboard_tasks[user_id].cancel()
            del self.dashboard_tasks[user_id]
            
            await update.message.reply_text("✅ Dashboard dihentikan.")
        else:
            await update.message.reply_text("ℹ️ Dashboard tidak aktif.")
            
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = update.effective_user.id
        
        if data == 'dashboard':
            await self.cmd_dashboard(update, context)
        elif data == 'stats':
            await self.cmd_stats(update, context)
        elif data == 'getsignal':
            await self.cmd_getsignal(update, context)
        elif data == 'view_position':
            await self.cmd_dashboard(update, context)
        elif data.startswith('confirm_reset_'):
            target_user_id = int(data.split('_')[-1])
            if user_id == target_user_id:
                self.stats_manager.reset_user_stats(user_id)
                self.position_tracker.reset_user_positions(user_id)
                await query.edit_message_text("✅ Data berhasil direset!")
            else:
                await query.edit_message_text("❌ Anda tidak bisa mereset data user lain!")
        elif data == 'cancel_reset':
            await query.edit_message_text("❌ Reset dibatalkan.")
            
    async def _on_new_signal(self, signal: Signal):
        """Handle new signals from generator"""
        try:
            # Format signal message
            signal_text = f"""
🤖 *SINYAL OTOMATIS*

{'🟢 BUY' if signal.signal_type == 'BUY' else '🔴 SELL'} *XAUUSD*

💰 *Entry:* ${signal.entry_price:.2f}
🎯 *TP:* ${signal.tp:.2f}
🛑 *SL:* ${signal.sl:.2f}

📊 *Indikator:*
• EMA 50: ${signal.ema_50:.2f}
• RSI 3: {signal.rsi:.2f}
• ADX 55: {signal.adx:.2f}

⏰ *Timeframe:* {signal.timeframe}
🕐 *Waktu:* {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

⚠️ *Risk Management:*
Risk:Reward = 1:1
Stop Loss: ${Config.DEFAULT_SL}
Take Profit: ${Config.DEFAULT_TP}

🔄 *Status:* Akan dipantau otomatis...
            """
            
            # Send to all active users
            active_users = self.user_manager.get_active_users()
            
            for user_id in active_users:
                try:
                    # Check if user already has an active position
                    active_positions = self.position_tracker.get_user_positions(user_id)
                    if len(active_positions) > 0:
                        logger.info(f"Skipping signal for user {user_id} - already has {len(active_positions)} active positions")
                        continue

                    # Create position for tracking
                    self.position_tracker.create_position(
                        user_id=user_id,
                        signal_type=signal.signal_type,
                        entry_price=signal.entry_price,
                        tp=signal.tp,
                        sl=signal.sl,
                        timeframe=signal.timeframe,
                        is_manual=False
                    )
                    
                    # Send signal
                    await self.app.bot.send_message(
                        chat_id=user_id,
                        text=signal_text,
                        parse_mode='Markdown'
                    )
                    
                except TelegramError as e:
                    logger.error(f"Failed to send signal to user {user_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error handling new signal: {e}")
            
    async def run(self):
        """Run the bot (blocking)"""
        try:
            await self.start()
            
            # Keep running indefinitely
            while True:
                await asyncio.sleep(3600)  # Sleep for 1 hour
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            await self.stop()