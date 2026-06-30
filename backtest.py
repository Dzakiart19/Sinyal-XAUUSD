#!/usr/bin/env python3
"""
XAUUSD Backtest — Strategi EMA50 / RSI3 / ADX55
Data: Deriv WebSocket API (frxXAUUSD, M1 candles, 24 jam terakhir)
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple

import websockets
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from config.config import Config

# ─── Konstanta Strategi ────────────────────────────────────────────────────────
EMA_PERIOD    = Config.EMA_PERIOD      # 50
RSI_PERIOD    = Config.RSI_PERIOD      # 3
ADX_PERIOD    = Config.ADX_PERIOD      # 55
ADX_THRESH    = Config.ADX_THRESHOLD   # 50 (diubah dari 30 — hasil backtest)
ATR_PERIOD    = Config.ATR_PERIOD      # 14
ATR_TP_MULT   = Config.ATR_TP_MULT     # 1.5
ATR_SL_MULT   = Config.ATR_SL_MULT     # 1.5
MIN_SL        = Config.MIN_SL          # 1.0
MAX_SL        = Config.MAX_SL          # 10.0
RSI_EXIT_OB   = Config.RSI_EXIT_OVERBOUGHT   # 75
RSI_EXIT_OS   = Config.RSI_EXIT_OVERSOLD     # 25

WS_URL = "wss://ws.derivws.com/websockets/v3?app_id=1089"
SYMBOL = "frxXAUUSD"

# Warna terminal
G = '\033[0;32m'
R = '\033[0;31m'
Y = '\033[0;33m'
B = '\033[0;34m'
C = '\033[0;36m'
W = '\033[1;37m'
NC = '\033[0m'


# ─── Fetch Candles dari Deriv ──────────────────────────────────────────────────

async def fetch_candles(granularity: int = 60, count: int = 1500) -> List[Dict]:
    """Ambil candle XAUUSD dari Deriv WebSocket API"""
    print(f"{C}⚡ Menghubungkan ke Deriv API...{NC}")
    candles = []
    try:
        async with websockets.connect(WS_URL, ping_interval=30) as ws:
            req = {
                "ticks_history": SYMBOL,
                "adjust_start_time": 1,
                "count": count,
                "end": "latest",
                "granularity": granularity,
                "style": "candles"
            }
            await ws.send(json.dumps(req))
            resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))

            if "error" in resp:
                print(f"{R}❌ Error dari Deriv: {resp['error']['message']}{NC}")
                return []

            raw = resp.get("candles", [])
            for c in raw:
                candles.append({
                    "time":  c["epoch"],
                    "open":  float(c["open"]),
                    "high":  float(c["high"]),
                    "low":   float(c["low"]),
                    "close": float(c["close"]),
                })
            print(f"{G}✅ {len(candles)} candle M1 berhasil diambil{NC}")
    except Exception as e:
        print(f"{R}❌ Gagal fetch candle: {e}{NC}")
    return candles


# ─── Indikator (identik dengan src/indicators.py) ──────────────────────────────

def calc_ema(prices: List[float], period: int) -> Optional[float]:
    if len(prices) < period:
        return None
    return float(pd.Series(prices, dtype=float).ewm(span=period, adjust=False).mean().iloc[-1])

def calc_rsi(prices: List[float], period: int = 3) -> Optional[float]:
    if len(prices) < period + 1:
        return None
    delta      = np.diff(np.array(prices, dtype=float))
    gains      = np.where(delta > 0, delta, 0.0)
    losses     = np.where(delta < 0, -delta, 0.0)
    avg_gain   = pd.Series(gains).rolling(period).mean().iloc[-1]
    avg_loss   = pd.Series(losses).rolling(period).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    return float(100 - 100 / (1 + avg_gain / avg_loss))

def calc_adx(candles: List[Dict], period: int = 55) -> Optional[float]:
    if len(candles) < period + 1:
        return None
    highs  = np.array([c['high']  for c in candles], dtype=float)
    lows   = np.array([c['low']   for c in candles], dtype=float)
    closes = np.array([c['close'] for c in candles], dtype=float)
    tr1 = highs[1:] - lows[1:]
    tr2 = np.abs(highs[1:] - closes[:-1])
    tr3 = np.abs(lows[1:]  - closes[:-1])
    tr  = np.maximum(np.maximum(tr1, tr2), tr3)
    up   = highs[1:] - highs[:-1]
    down = lows[:-1] - lows[1:]
    pdm  = np.where((up > down) & (up > 0), up, 0.0)
    mdm  = np.where((down > up) & (down > 0), down, 0.0)
    alpha = 1.0 / period
    tr_s  = pd.Series(tr).ewm(alpha=alpha, adjust=False).mean().values
    pdm_s = pd.Series(pdm).ewm(alpha=alpha, adjust=False).mean().values
    mdm_s = pd.Series(mdm).ewm(alpha=alpha, adjust=False).mean().values
    with np.errstate(divide='ignore', invalid='ignore'):
        pdi = np.where(tr_s != 0, 100 * pdm_s / tr_s, 0.0)
        mdi = np.where(tr_s != 0, 100 * mdm_s / tr_s, 0.0)
        di_sum  = pdi + mdi
        dx = np.where(di_sum != 0, 100 * np.abs(pdi - mdi) / di_sum, 0.0)
    return float(pd.Series(dx).ewm(alpha=alpha, adjust=False).mean().iloc[-1])

def calc_atr(candles: List[Dict], period: int = 14) -> Optional[float]:
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        tr = max(
            candles[i]['high']  - candles[i]['low'],
            abs(candles[i]['high']  - candles[i-1]['close']),
            abs(candles[i]['low']   - candles[i-1]['close']),
        )
        trs.append(tr)
    return float(np.mean(trs[-period:]))


# ─── Signal Check (identik dengan indicators.py) ───────────────────────────────

def check_buy(closes: List[float], candles: List[Dict]) -> Tuple[bool, Dict]:
    ind = {}
    ind['ema']  = calc_ema(closes, EMA_PERIOD)
    ind['rsi']  = calc_rsi(closes, RSI_PERIOD)
    ind['prsi'] = calc_rsi(closes[:-1], RSI_PERIOD)
    ind['adx']  = calc_adx(candles, ADX_PERIOD)
    if any(v is None for v in ind.values()):
        return False, ind
    price_above_ema      = closes[-1] > ind['ema']
    rsi_exiting_oversold = ind['prsi'] <= RSI_EXIT_OS and ind['rsi'] > RSI_EXIT_OS
    adx_ok               = ind['adx'] > ADX_THRESH
    rsi_range            = RSI_EXIT_OS <= ind['rsi'] <= 50
    return (price_above_ema and rsi_exiting_oversold and adx_ok and rsi_range), ind

def check_sell(closes: List[float], candles: List[Dict]) -> Tuple[bool, Dict]:
    ind = {}
    ind['ema']  = calc_ema(closes, EMA_PERIOD)
    ind['rsi']  = calc_rsi(closes, RSI_PERIOD)
    ind['prsi'] = calc_rsi(closes[:-1], RSI_PERIOD)
    ind['adx']  = calc_adx(candles, ADX_PERIOD)
    if any(v is None for v in ind.values()):
        return False, ind
    price_below_ema        = closes[-1] < ind['ema']
    rsi_exiting_overbought = ind['prsi'] >= RSI_EXIT_OB and ind['rsi'] < RSI_EXIT_OB
    adx_ok                 = ind['adx'] > ADX_THRESH
    rsi_range              = 50 <= ind['rsi'] <= RSI_EXIT_OB
    return (price_below_ema and rsi_exiting_overbought and adx_ok and rsi_range), ind


# ─── Backtest Engine ───────────────────────────────────────────────────────────

def run_backtest(candles: List[Dict], label: str = "M1") -> Dict:
    """
    Simulasi trading:
    - Entry  : close candle sinyal (candle ke-i)
    - TP/SL  : ATR × multiplier, dicheck pada candle-candle berikutnya
    - Max hold: 60 candle (1 jam untuk M1)
    - Skip   : sinyal baru jika posisi sedang aktif
    """
    MIN_CANDLES = max(EMA_PERIOD, ADX_PERIOD) + ATR_PERIOD + RSI_PERIOD + 10

    trades   : List[Dict] = []
    in_trade  = False
    trade_dir = None
    entry_px  = tp = sl = 0.0
    entry_idx = 0
    MAX_HOLD  = 60  # candle

    for i in range(MIN_CANDLES, len(candles)):
        window   = candles[:i+1]
        closes   = [c['close'] for c in window]
        cur      = candles[i]

        # Jika sedang dalam posisi, cek TP/SL
        if in_trade:
            held = i - entry_idx
            if trade_dir == 'BUY':
                if cur['high'] >= tp:
                    trades.append({'dir': 'BUY', 'result': 'WIN',
                                   'entry': entry_px, 'exit': tp,
                                   'pnl': tp - entry_px, 'held': held,
                                   'time': datetime.fromtimestamp(cur['time'], tz=timezone.utc)})
                    in_trade = False
                elif cur['low'] <= sl:
                    trades.append({'dir': 'BUY', 'result': 'LOSS',
                                   'entry': entry_px, 'exit': sl,
                                   'pnl': sl - entry_px, 'held': held,
                                   'time': datetime.fromtimestamp(cur['time'], tz=timezone.utc)})
                    in_trade = False
                elif held >= MAX_HOLD:
                    # Time-exit di close
                    trades.append({'dir': 'BUY', 'result': 'EXPIRED',
                                   'entry': entry_px, 'exit': cur['close'],
                                   'pnl': cur['close'] - entry_px, 'held': held,
                                   'time': datetime.fromtimestamp(cur['time'], tz=timezone.utc)})
                    in_trade = False
            else:  # SELL
                if cur['low'] <= tp:
                    trades.append({'dir': 'SELL', 'result': 'WIN',
                                   'entry': entry_px, 'exit': tp,
                                   'pnl': entry_px - tp, 'held': held,
                                   'time': datetime.fromtimestamp(cur['time'], tz=timezone.utc)})
                    in_trade = False
                elif cur['high'] >= sl:
                    trades.append({'dir': 'SELL', 'result': 'LOSS',
                                   'entry': entry_px, 'exit': sl,
                                   'pnl': entry_px - sl, 'held': held,
                                   'time': datetime.fromtimestamp(cur['time'], tz=timezone.utc)})
                    in_trade = False
                elif held >= MAX_HOLD:
                    trades.append({'dir': 'SELL', 'result': 'EXPIRED',
                                   'entry': entry_px, 'exit': cur['close'],
                                   'pnl': entry_px - cur['close'], 'held': held,
                                   'time': datetime.fromtimestamp(cur['time'], tz=timezone.utc)})
                    in_trade = False
            continue

        # Cek sinyal baru
        atr = calc_atr(window, ATR_PERIOD)
        if atr is None:
            continue

        raw_sl = atr * ATR_SL_MULT
        raw_tp = atr * ATR_TP_MULT
        sl_dist = max(MIN_SL, min(MAX_SL, raw_sl))
        tp_dist = max(MIN_SL, min(MAX_SL, raw_tp))

        buy_sig, _ = check_buy(closes, window)
        if buy_sig:
            entry_px  = cur['close']
            tp        = entry_px + tp_dist
            sl        = entry_px - sl_dist
            trade_dir = 'BUY'
            in_trade  = True
            entry_idx = i
            continue

        sell_sig, _ = check_sell(closes, window)
        if sell_sig:
            entry_px  = cur['close']
            tp        = entry_px - tp_dist
            sl        = entry_px + sl_dist
            trade_dir = 'SELL'
            in_trade  = True
            entry_idx = i

    return {
        'label':  label,
        'trades': trades,
        'total_candles': len(candles),
    }


# ─── Cetak Hasil ───────────────────────────────────────────────────────────────

def print_results(result: Dict, period_hours: int = 24):
    trades = result['trades']
    label  = result['label']
    total  = len(trades)

    if total == 0:
        print(f"\n{Y}⚠️  Tidak ada sinyal yang tergenerate dalam periode ini.{NC}")
        print(f"   (Strategi RSI3 crossover + ADX55 + EMA50 memang selektif){NC}")
        return

    wins    = [t for t in trades if t['result'] == 'WIN']
    losses  = [t for t in trades if t['result'] == 'LOSS']
    expired = [t for t in trades if t['result'] == 'EXPIRED']

    win_pnl  = sum(t['pnl'] for t in wins)
    loss_pnl = abs(sum(t['pnl'] for t in losses))
    exp_pnl  = sum(t['pnl'] for t in expired)
    total_pnl = sum(t['pnl'] for t in trades)

    winrate  = len(wins) / total * 100
    pf       = win_pnl / loss_pnl if loss_pnl > 0 else float('inf')
    avg_hold = sum(t['held'] for t in trades) / total

    buys  = [t for t in trades if t['dir'] == 'BUY']
    sells = [t for t in trades if t['dir'] == 'SELL']
    buy_wr  = len([t for t in buys  if t['result'] == 'WIN']) / len(buys)  * 100 if buys  else 0
    sell_wr = len([t for t in sells if t['result'] == 'WIN']) / len(sells) * 100 if sells else 0

    first_t = datetime.fromtimestamp(0, tz=timezone.utc)
    last_t  = datetime.fromtimestamp(0, tz=timezone.utc)
    if trades:
        first_t = trades[0]['time']
        last_t  = trades[-1]['time']

    # Ubah ke WIB
    wib = timezone(timedelta(hours=7))
    first_wib = first_t.astimezone(wib).strftime('%d %b %Y %H:%M WIB')
    last_wib  = last_t.astimezone(wib).strftime('%d %b %Y %H:%M WIB')

    print()
    print(f"{W}{'='*58}{NC}")
    print(f"{W}  📊 HASIL BACKTEST XAUUSD — {label} ({period_hours} JAM TERAKHIR){NC}")
    print(f"{W}{'='*58}{NC}")
    print(f"  Periode data : {first_wib}")
    print(f"               s/d {last_wib}")
    print(f"  Total candle : {result['total_candles']} candle M1")
    print()

    wr_color = G if winrate >= 55 else (Y if winrate >= 45 else R)
    print(f"  {W}── RINGKASAN TRADE ──────────────────────────────{NC}")
    print(f"  Total Sinyal   : {W}{total}{NC}")
    print(f"  ✅ WIN         : {G}{len(wins)}{NC}")
    print(f"  ❌ LOSS        : {R}{len(losses)}{NC}")
    print(f"  ⏱️  EXPIRED     : {Y}{len(expired)}{NC}  (keluar di close setelah 60 candle)")
    print()
    print(f"  {W}── WINRATE & STATISTIK ─────────────────────────{NC}")
    print(f"  Winrate Overall : {wr_color}{W}{winrate:.1f}%{NC}")
    print(f"  BUY  winrate   : {G}{buy_wr:.1f}%{NC}  ({len(buys)} sinyal)")
    print(f"  SELL winrate   : {G}{sell_wr:.1f}%{NC}  ({len(sells)} sinyal)")
    print(f"  Profit Factor  : {C}{pf:.2f}{NC}  (>1.5 bagus, >2 excellent)")
    print(f"  Rata-rata hold : {avg_hold:.0f} candle M1 (~{avg_hold:.0f} menit)")
    print()
    print(f"  {W}── PnL (dalam poin/pip XAUUSD) ─────────────────{NC}")
    pnl_color = G if total_pnl > 0 else R
    print(f"  Gross Profit   : +{win_pnl:.2f}")
    print(f"  Gross Loss     : -{loss_pnl:.2f}")
    print(f"  Expired PnL    : {'+' if exp_pnl >= 0 else ''}{exp_pnl:.2f}")
    print(f"  Net PnL Total  : {pnl_color}{W}{'+' if total_pnl >= 0 else ''}{total_pnl:.2f} poin{NC}")
    print()

    # Detail setiap trade
    print(f"  {W}── DETAIL TRADE (chronological) ─────────────────{NC}")
    print(f"  {'No':>3}  {'Arah':<5}  {'Entry':>8}  {'Exit':>8}  {'PnL':>7}  {'Hasil':<8}  {'Hold':>5}")
    print(f"  {'-'*55}")
    for i, t in enumerate(trades, 1):
        pnl_s   = f"{'+' if t['pnl'] >= 0 else ''}{t['pnl']:.2f}"
        col     = G if t['result'] == 'WIN' else (R if t['result'] == 'LOSS' else Y)
        hasil   = f"{col}{t['result']:<8}{NC}"
        print(f"  {i:>3}  {t['dir']:<5}  {t['entry']:>8.2f}  {t['exit']:>8.2f}  {pnl_s:>7}  {hasil}  {t['held']:>3}m")

    print(f"{W}{'='*58}{NC}")

    # Kesimpulan
    print()
    if winrate >= 60:
        verdict = f"{G}✅ STRATEGI PERFORMANYA BAGUS di periode ini{NC}"
    elif winrate >= 50:
        verdict = f"{Y}⚠️  STRATEGI CUKUP, borderline profitable{NC}"
    else:
        verdict = f"{R}❌ STRATEGI KURANG OPTIMAL di periode ini{NC}"

    print(f"  {verdict}")
    print(f"  {Y}⚠️  Catatan: Backtest tidak menjamin hasil live trading.{NC}")
    print(f"  {Y}   Deriv spread, slippage, dan sentimen news tidak diperhitungkan.{NC}")
    print()


# ─── Main ──────────────────────────────────────────────────────────────────────

async def main():
    print()
    print(f"{W}{'='*58}{NC}")
    print(f"{W}  🔬 BACKTEST ENGINE — XAUUSD SCALPING BOT{NC}")
    print(f"{W}  Strategi : EMA{EMA_PERIOD} / RSI{RSI_PERIOD} / ADX{ADX_PERIOD}{NC}")
    print(f"{W}  TP/SL    : ATR×{ATR_TP_MULT} / ATR×{ATR_SL_MULT}  (RR 1:1){NC}")
    print(f"{W}  Sumber   : Deriv WebSocket API (frxXAUUSD){NC}")
    print(f"{W}{'='*58}{NC}")
    print()

    # Ambil ~1500 candle M1 = ~25 jam (buffer extra untuk indikator hangat)
    candles = await fetch_candles(granularity=60, count=1500)
    if not candles:
        print(f"{R}Gagal mendapatkan data. Periksa koneksi internet.{NC}")
        return

    # Gunakan 1440 candle terakhir = tepat 24 jam
    candles_24h = candles[-1440:]
    total_hours = len(candles_24h) / 60

    print(f"{C}🔄 Menjalankan backtest pada {len(candles_24h)} candle M1 (~{total_hours:.1f} jam)...{NC}")
    print(f"   Butuh beberapa detik untuk kalkulasi indikator...\n")

    result = run_backtest(candles, label="M1")  # pakai semua candle (biar indikator warm-up)
    # Filter hanya trade yang terjadi dalam 24 jam terakhir
    cutoff = datetime.fromtimestamp(candles_24h[0]['time'], tz=timezone.utc)
    result['trades'] = [t for t in result['trades'] if t['time'] >= cutoff]

    print_results(result, period_hours=24)


if __name__ == "__main__":
    asyncio.run(main())
