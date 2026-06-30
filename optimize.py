#!/usr/bin/env python3
"""
XAUUSD Strategy Optimizer — Grid Search + Walk-Forward Validation
Teknik: grid search pada training set, validasi pada out-of-sample test set.
Fetch: Deriv WebSocket API (frxXAUUSD, M5, maks candle tersedia)
"""

import asyncio
import json
import sys
import os
import time
import itertools
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd
import websockets

sys.path.insert(0, os.path.dirname(__file__))
from config.config import Config

# ── Warna terminal ─────────────────────────────────────────────────────────────
G='\033[0;32m'; R='\033[0;31m'; Y='\033[0;33m'; B='\033[0;34m'
C='\033[0;36m'; W='\033[1;37m'; M='\033[0;35m'; NC='\033[0m'

WS_URL = "wss://ws.derivws.com/websockets/v3?app_id=1089"
SYMBOL = "frxXAUUSD"

# ── Grid Parameter ─────────────────────────────────────────────────────────────
GRID = {
    'adx_thresh':   [45, 50, 55, 60, 65, 70],
    'rsi_os':       [10, 15, 20, 25, 30],      # RSI exit oversold (buy zone)
    'rsi_ob':       [70, 75, 80, 85, 90],      # RSI exit overbought (sell zone)
    'tp_mult':      [1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
    'sl_mult':      [0.5, 0.75, 1.0, 1.5, 2.0],
}
# Total kombinasi: 6×5×5×6×5 = 4500

FIXED = {
    'ema_period':  Config.EMA_PERIOD,    # 50
    'rsi_period':  Config.RSI_PERIOD,    # 3
    'adx_period':  Config.ADX_PERIOD,    # 55
    'atr_period':  Config.ATR_PERIOD,    # 14
    'min_sl':      Config.MIN_SL,        # 1.0
    'max_sl':      Config.MAX_SL,        # 10.0
    'buffer':      100,
    'max_hold':    60,
}

TRAIN_RATIO = 0.70   # 70% data untuk training
MIN_TRADES  = 5      # minimum trade di training agar valid
TOP_N       = 20     # top N candidate untuk divalidasi

# ── Fetch Candles ───────────────────────────────────────────────────────────────

async def fetch_candles(gran: int = 300, count: int = 5000) -> List[Dict]:
    label = f"M{gran//60}"
    print(f"  {C}⚡ Fetching {count} candle {label} dari Deriv...{NC}")
    try:
        async with websockets.connect(WS_URL, ping_interval=30) as ws:
            await ws.send(json.dumps({
                "ticks_history": SYMBOL, "adjust_start_time": 1,
                "count": count, "end": "latest",
                "granularity": gran, "style": "candles"
            }))
            resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=45))
            if "error" in resp:
                print(f"  {R}❌ Error Deriv: {resp['error']['message']}{NC}")
                return []
            raw = resp.get("candles", [])
            candles = [{"time": c["epoch"], "open": float(c["open"]),
                        "high": float(c["high"]), "low": float(c["low"]),
                        "close": float(c["close"])} for c in raw]
            wib = timezone(timedelta(hours=7))
            t0 = datetime.fromtimestamp(candles[0]['time'],  tz=wib).strftime('%d %b %Y %H:%M WIB')
            t1 = datetime.fromtimestamp(candles[-1]['time'], tz=wib).strftime('%d %b %Y %H:%M WIB')
            days = len(candles) * gran / 86400
            print(f"  {G}✅ {len(candles)} candle {label} ({days:.1f} hari){NC}")
            print(f"     {t0}  →  {t1}")
            return candles
    except Exception as e:
        print(f"  {R}❌ Gagal fetch: {e}{NC}")
        return []


# ── Pre-compute Indicator Arrays ───────────────────────────────────────────────

def precompute(candles: List[Dict]) -> Dict[str, np.ndarray]:
    """
    Pre-compute semua time series sekali saja — reusable untuk seluruh grid.
    Returns dict of numpy arrays, index sesuai posisi candle.
    """
    n = len(candles)
    closes = np.array([c['close'] for c in candles], dtype=np.float64)
    highs  = np.array([c['high']  for c in candles], dtype=np.float64)
    lows   = np.array([c['low']   for c in candles], dtype=np.float64)

    # EMA (fixed period 50)
    ema = pd.Series(closes).ewm(span=FIXED['ema_period'], adjust=False).mean().values

    # RSI (fixed period 3) — Cutler's method (SMA of gains/losses)
    diff  = np.diff(closes, prepend=closes[0])
    gains = np.where(diff > 0, diff, 0.0)
    loss_ = np.where(diff < 0, -diff, 0.0)
    rsi_arr = np.full(n, 50.0)
    ag = pd.Series(gains).rolling(FIXED['rsi_period']).mean().values
    al = pd.Series(loss_).rolling(FIXED['rsi_period']).mean().values
    with np.errstate(divide='ignore', invalid='ignore'):
        rs = np.where(al != 0, ag / al, np.inf)
        rsi_arr = np.where(al != 0, 100 - 100 / (1 + rs), 100.0)
    prev_rsi = np.roll(rsi_arr, 1); prev_rsi[0] = rsi_arr[0]

    # ADX (fixed period 55) — Wilder's EWM
    adx_arr = _calc_adx_series(highs, lows, closes, FIXED['adx_period'])

    # ATR (fixed period 14) — simple rolling mean of TR
    tr1 = highs[1:] - lows[1:]
    tr2 = np.abs(highs[1:] - closes[:-1])
    tr3 = np.abs(lows[1:]  - closes[:-1])
    tr  = np.maximum(np.maximum(tr1, tr2), tr3)
    tr_full = np.concatenate([[tr[0]], tr])
    atr_arr = pd.Series(tr_full).rolling(FIXED['atr_period']).mean().values

    return {
        'closes':   closes,
        'highs':    highs,
        'lows':     lows,
        'ema':      ema,
        'rsi':      rsi_arr,
        'prev_rsi': prev_rsi,
        'adx':      adx_arr,
        'atr':      atr_arr,
    }

def _calc_adx_series(highs, lows, closes, period) -> np.ndarray:
    n = len(highs)
    up   = highs[1:] - highs[:-1]
    down = lows[:-1] - lows[1:]
    tr1  = highs[1:] - lows[1:]
    tr2  = np.abs(highs[1:] - closes[:-1])
    tr3  = np.abs(lows[1:]  - closes[:-1])
    tr   = np.maximum(np.maximum(tr1, tr2), tr3)
    pdm  = np.where((up > down) & (up > 0), up, 0.0)
    mdm  = np.where((down > up) & (down > 0), down, 0.0)
    alpha = 1.0 / period
    tr_s  = pd.Series(tr).ewm(alpha=alpha, adjust=False).mean().values
    pdm_s = pd.Series(pdm).ewm(alpha=alpha, adjust=False).mean().values
    mdm_s = pd.Series(mdm).ewm(alpha=alpha, adjust=False).mean().values
    with np.errstate(divide='ignore', invalid='ignore'):
        pdi = np.where(tr_s != 0, 100 * pdm_s / tr_s, 0.0)
        mdi = np.where(tr_s != 0, 100 * mdm_s / tr_s, 0.0)
        ds  = pdi + mdi
        dx  = np.where(ds != 0, 100 * np.abs(pdi - mdi) / ds, 0.0)
    adx = pd.Series(dx).ewm(alpha=alpha, adjust=False).mean().values
    # pad satu di awal agar panjangnya = n
    return np.concatenate([[0.0], adx])


# ── Fast Backtest (vectorized signals, loop hanya untuk trade management) ──────

@dataclass
class BacktestResult:
    params: Dict
    total:  int = 0
    wins:   int = 0
    losses: int = 0
    gross_profit: float = 0.0
    gross_loss:   float = 0.0
    max_dd:       float = 0.0

    @property
    def winrate(self): return self.wins / self.total * 100 if self.total else 0
    @property
    def net_pnl(self): return self.gross_profit - self.gross_loss
    @property
    def profit_factor(self):
        return self.gross_profit / self.gross_loss if self.gross_loss > 0 else (
            float('inf') if self.gross_profit > 0 else 0.0)
    @property
    def score(self):
        """Composite score: PF × sqrt(trades) × winrate_bonus — favors konsistensi"""
        if self.total < MIN_TRADES: return -1.0
        pf   = min(self.profit_factor, 10.0)        # cap PF agar tidak outlier
        wr   = self.winrate / 100
        trad = min(self.total, 100) ** 0.5           # sqrt(trades) — diminishing returns
        dd_pen = max(0, 1 - abs(self.max_dd) / max(abs(self.net_pnl), 1) * 0.5)
        return pf * trad * wr * dd_pen


def run_fast_backtest(ind: Dict[str, np.ndarray], params: Dict,
                      start_idx: int, end_idx: int) -> BacktestResult:
    closes   = ind['closes']
    highs    = ind['highs']
    lows     = ind['lows']
    ema      = ind['ema']
    rsi      = ind['rsi']
    prev_rsi = ind['prev_rsi']
    adx      = ind['adx']
    atr      = ind['atr']

    adx_t  = params['adx_thresh']
    rsi_os = params['rsi_os']
    rsi_ob = params['rsi_ob']
    tp_m   = params['tp_mult']
    sl_m   = params['sl_mult']
    min_sl = FIXED['min_sl']
    max_sl = FIXED['max_sl']
    mh     = FIXED['max_hold']

    res = BacktestResult(params=params)
    in_trade = False
    dir_ = 0; entry = tp_px = sl_px = 0.0; entry_i = 0
    equity = 0.0; peak = 0.0; dd = 0.0

    for i in range(start_idx, end_idx):
        if atr[i] is None or np.isnan(atr[i]) or atr[i] == 0: continue
        sl_dist = max(min_sl, min(max_sl, atr[i] * sl_m))
        tp_dist = max(min_sl, min(max_sl, atr[i] * tp_m))

        if in_trade:
            held = i - entry_i
            if dir_ == 1:  # BUY
                if highs[i] >= tp_px:
                    pnl = tp_dist; res.wins += 1; res.gross_profit += pnl
                    equity += pnl; in_trade = False
                elif lows[i] <= sl_px:
                    pnl = -sl_dist; res.losses += 1; res.gross_loss += sl_dist
                    equity += pnl; in_trade = False
                elif held >= mh:
                    pnl = closes[i] - entry; res.gross_profit += max(pnl,0); res.gross_loss += max(-pnl,0)
                    if pnl > 0: res.wins += 1
                    else: res.losses += 1
                    equity += pnl; in_trade = False
            else:  # SELL
                if lows[i] <= tp_px:
                    pnl = tp_dist; res.wins += 1; res.gross_profit += pnl
                    equity += pnl; in_trade = False
                elif highs[i] >= sl_px:
                    pnl = -sl_dist; res.losses += 1; res.gross_loss += sl_dist
                    equity += pnl; in_trade = False
                elif held >= mh:
                    pnl = entry - closes[i]; res.gross_profit += max(pnl,0); res.gross_loss += max(-pnl,0)
                    if pnl > 0: res.wins += 1
                    else: res.losses += 1
                    equity += pnl; in_trade = False
            if not in_trade:
                res.total += 1
                peak = max(peak, equity)
                dd   = min(dd, equity - peak)
                res.max_dd = min(res.max_dd, dd)
            continue

        # Entry check
        adx_ok = adx[i] > adx_t
        if not adx_ok: continue

        buy  = (closes[i] > ema[i] and prev_rsi[i] <= rsi_os and rsi[i] > rsi_os
                and rsi_os <= rsi[i] <= 50)
        sell = (closes[i] < ema[i] and prev_rsi[i] >= rsi_ob and rsi[i] < rsi_ob
                and 50 <= rsi[i] <= rsi_ob)

        if buy:
            entry = closes[i]; tp_px = entry + tp_dist; sl_px = entry - sl_dist
            dir_ = 1; in_trade = True; entry_i = i
        elif sell:
            entry = closes[i]; tp_px = entry - tp_dist; sl_px = entry + sl_dist
            dir_ = -1; in_trade = True; entry_i = i

    return res


# ── Grid Search ────────────────────────────────────────────────────────────────

def grid_search(ind: Dict, start: int, end: int,
                label: str = "") -> List[BacktestResult]:
    keys   = list(GRID.keys())
    values = list(GRID.values())
    combos = list(itertools.product(*values))
    total  = len(combos)

    results = []
    t0 = time.time()

    for idx, combo in enumerate(combos):
        params = dict(zip(keys, combo))
        r = run_fast_backtest(ind, params, start, end)
        if r.total >= MIN_TRADES:
            results.append(r)

        if (idx + 1) % 500 == 0 or idx + 1 == total:
            pct  = (idx + 1) / total * 100
            elapsed = time.time() - t0
            eta = elapsed / (idx + 1) * (total - idx - 1)
            bar = '█' * int(pct / 5) + '░' * (20 - int(pct / 5))
            print(f"  {C}[{bar}] {pct:5.1f}%  {idx+1}/{total}  "
                  f"valid={len(results)}  ETA={eta:.0f}s{NC}", end='\r', flush=True)

    print()
    results.sort(key=lambda r: r.score, reverse=True)
    return results


# ── Print Results ───────────────────────────────────────────────────────────────

def print_top(results: List[BacktestResult], label: str, n: int = 10,
              show_score: bool = True):
    print(f"\n{W}  {'─'*82}{NC}")
    print(f"  {W}TOP {n} — {label}{NC}")
    print(f"  {'─'*82}{NC}")
    header = (f"  {'#':>2}  {'ADX':>4} {'OS':>3} {'OB':>3} "
              f"{'TP×':>4} {'SL×':>4}  "
              f"{'Trades':>6} {'Win%':>5} {'PF':>5} {'NetPnL':>8}")
    if show_score: header += f"  {'Score':>7}"
    print(header)
    print(f"  {'─'*82}{NC}")
    for i, r in enumerate(results[:n]):
        p = r.params
        pf_col = G if r.profit_factor >= 2 else (Y if r.profit_factor >= 1.5 else R)
        wr_col = G if r.winrate >= 55 else (Y if r.winrate >= 45 else R)
        pnl_col = G if r.net_pnl > 0 else R
        line = (f"  {i+1:>2}  {p['adx_thresh']:>4} {p['rsi_os']:>3} {p['rsi_ob']:>3} "
                f"{p['tp_mult']:>4.1f} {p['sl_mult']:>4.2f}  "
                f"{r.total:>6} {wr_col}{r.winrate:>4.0f}%{NC} "
                f"{pf_col}{r.profit_factor:>5.2f}{NC} {pnl_col}{r.net_pnl:>+8.2f}{NC}")
        if show_score: line += f"  {C}{r.score:>7.3f}{NC}"
        print(line)


def print_comparison(train: BacktestResult, test: BacktestResult, rank: int):
    p = train.params
    ok = (test.profit_factor >= 1.2 and test.total >= MIN_TRADES
          and test.net_pnl > 0)
    verdict = f"{G}✅ VALID OOS{NC}" if ok else f"{R}❌ OVERFIT{NC}"
    pf_oos = f"{G}{test.profit_factor:.2f}{NC}" if test.profit_factor >= 1.5 else f"{R}{test.profit_factor:.2f}{NC}"
    print(f"  {rank:>2}  ADX>{p['adx_thresh']} OS={p['rsi_os']} OB={p['rsi_ob']} "
          f"TP×{p['tp_mult']} SL×{p['sl_mult']}  "
          f"IS: {train.total}t {train.winrate:.0f}% PF{train.profit_factor:.2f} "
          f"→ OOS: {test.total}t {test.winrate:.0f}% PF{pf_oos}  {verdict}")


# ── Apply Config ────────────────────────────────────────────────────────────────

def apply_to_config(params: Dict):
    cfg_path = os.path.join(os.path.dirname(__file__), 'config', 'config.py')
    with open(cfg_path) as f:
        src = f.read()

    replacements = {
        'ADX_THRESHOLD':       (r"ADX_THRESHOLD\s*=\s*int\(os\.getenv\('ADX_THRESHOLD',\s*\d+\)\)",
                                f"ADX_THRESHOLD = int(os.getenv('ADX_THRESHOLD', {int(params['adx_thresh'])}))"
                                f"  # [optimized]"),
        'ATR_TP_MULT':         (r"ATR_TP_MULT\s*=\s*float\(os\.getenv\('ATR_TP_MULT',\s*[\d.]+\)\)[^\n]*",
                                f"ATR_TP_MULT    = float(os.getenv('ATR_TP_MULT', {params['tp_mult']}))"
                                f"  # TP = ATR × {params['tp_mult']}  [optimized]"),
        'ATR_SL_MULT':         (r"ATR_SL_MULT\s*=\s*float\(os\.getenv\('ATR_SL_MULT',\s*[\d.]+\)\)[^\n]*",
                                f"ATR_SL_MULT    = float(os.getenv('ATR_SL_MULT', {params['sl_mult']}))"
                                f"  # SL = ATR × {params['sl_mult']}  [optimized]"),
        'RSI_EXIT_OVERSOLD':   (r"RSI_EXIT_OVERSOLD\s*=\s*\d+[^\n]*",
                                f"RSI_EXIT_OVERSOLD = {int(params['rsi_os'])}   # [optimized]"),
        'RSI_EXIT_OVERBOUGHT': (r"RSI_EXIT_OVERBOUGHT\s*=\s*\d+[^\n]*",
                                f"RSI_EXIT_OVERBOUGHT = {int(params['rsi_ob'])}  # [optimized]"),
    }

    import re
    for key, (pattern, replacement) in replacements.items():
        src = re.sub(pattern, replacement, src)

    with open(cfg_path, 'w') as f:
        f.write(src)
    print(f"  {G}✅ config/config.py diperbarui.{NC}")


# ── Main ────────────────────────────────────────────────────────────────────────

async def main():
    print()
    print(f"{W}{'='*65}{NC}")
    print(f"{W}  🔬 XAUUSD STRATEGY OPTIMIZER — GRID SEARCH + WALK-FORWARD{NC}")
    print(f"{W}{'='*65}{NC}")
    print(f"  Fixed  : EMA{FIXED['ema_period']} / RSI{FIXED['rsi_period']} / "
          f"ADX-period={FIXED['adx_period']} / ATR{FIXED['atr_period']}")
    total_combos = 1
    for v in GRID.values(): total_combos *= len(v)
    print(f"  Grid   : {' × '.join(str(len(v)) for v in GRID.values())} = "
          f"{total_combos:,} kombinasi")
    print(f"  Split  : {int(TRAIN_RATIO*100)}% train / {int((1-TRAIN_RATIO)*100)}% test (walk-forward)")
    print(f"{W}{'='*65}{NC}\n")

    # ── 1. Fetch Data ───────────────────────────────────────────────────────────
    print(f"{W}[1/4] Mengambil data historis...{NC}")
    candles_m5 = await fetch_candles(gran=300, count=5000)
    if len(candles_m5) < 200:
        print(f"{R}Data tidak cukup. Periksa koneksi.{NC}")
        return

    # ── 2. Pre-compute Indicators ───────────────────────────────────────────────
    print(f"\n{W}[2/4] Pre-compute indikator...{NC}")
    t0 = time.time()
    ind_m5 = precompute(candles_m5)
    warmup = max(FIXED['ema_period'], FIXED['adx_period']) + FIXED['atr_period'] + 10
    total_n   = len(candles_m5)
    train_end = warmup + int((total_n - warmup) * TRAIN_RATIO)
    test_start = train_end
    test_end   = total_n

    wib = timezone(timedelta(hours=7))
    def fmt(idx): return datetime.fromtimestamp(
        candles_m5[idx]['time'], tz=wib).strftime('%d %b %Y %H:%M WIB')

    print(f"  Warmup    : {warmup} candle (indikator settling)")
    print(f"  Training  : idx {warmup}–{train_end}  "
          f"({fmt(warmup)} → {fmt(train_end-1)})")
    print(f"  Testing   : idx {test_start}–{test_end-1}  "
          f"({fmt(test_start)} → {fmt(test_end-1)})")
    print(f"  Pre-compute selesai: {time.time()-t0:.1f}s")

    # ── 3. Grid Search (Training Set) ───────────────────────────────────────────
    print(f"\n{W}[3/4] Grid search pada training set ({total_combos:,} kombinasi)...{NC}")
    t1 = time.time()
    train_results = grid_search(ind_m5, warmup, train_end, label="M5 TRAIN")
    elapsed = time.time() - t1
    print(f"  Selesai: {elapsed:.1f}s  |  Valid kombinasi: {len(train_results)}")
    print_top(train_results, f"IN-SAMPLE (M5 Training {fmt(warmup)} → {fmt(train_end-1)})",
              n=10, show_score=True)

    # ── 4. Walk-Forward Validation (Test Set) ───────────────────────────────────
    print(f"\n{W}[4/4] Walk-forward validation pada test set (top {TOP_N} kandidat)...{NC}")
    print(f"  {'#':>2}  {'Params':^45}  {'IN-SAMPLE':^25}  {'OUT-OF-SAMPLE':^28}  Verdict")
    print(f"  {'─'*120}")

    validated = []
    for rank, tr in enumerate(train_results[:TOP_N], 1):
        te = run_fast_backtest(ind_m5, tr.params, test_start, test_end)
        ok = (te.profit_factor >= 1.2 and te.total >= MIN_TRADES and te.net_pnl > 0)
        print_comparison(tr, te, rank)
        if ok:
            validated.append((tr, te))

    # ── 5. Pilih Parameter Terbaik ──────────────────────────────────────────────
    print(f"\n{W}{'='*65}{NC}")
    print(f"{W}  📊 HASIL WALK-FORWARD VALIDATION{NC}")
    print(f"{W}{'='*65}{NC}")

    if not validated:
        print(f"  {R}❌ Tidak ada kombinasi yang lolos validasi OOS.{NC}")
        print(f"  {Y}   Kemungkinan market conditions berubah drastis.{NC}")
        print(f"  {Y}   Parameter saat ini tetap dipertahankan.{NC}")
        print(f"\n  {Y}Rekomendasi: jalankan ulang optimizer dengan data lebih panjang.{NC}")
        return

    # Ranking ulang berdasarkan geometric mean IS × OOS score
    def combined_score(tr, te):
        s_is  = tr.score
        s_oos = te.score if te.total >= MIN_TRADES else 0.0
        pf_penalty = max(0, 1 - abs(tr.profit_factor - te.profit_factor) / tr.profit_factor * 0.5)
        return (s_is * s_oos) ** 0.5 * pf_penalty  # geometric mean × consistency penalty

    validated.sort(key=lambda x: combined_score(*x), reverse=True)
    best_tr, best_te = validated[0]
    bp = best_tr.params

    print(f"  {G}✅ {len(validated)} dari {TOP_N} kandidat lolos out-of-sample.{NC}\n")
    print(f"  {W}═══ PARAMETER TERBAIK ═══{NC}")
    print(f"  ADX Threshold    : {W}{int(bp['adx_thresh'])}{NC}")
    print(f"  RSI Exit Oversold: {W}{int(bp['rsi_os'])}{NC}  (BUY zone)")
    print(f"  RSI Exit Overbought: {W}{int(bp['rsi_ob'])}{NC}  (SELL zone)")
    print(f"  TP Multiplier    : {W}{bp['tp_mult']}×{NC} ATR")
    print(f"  SL Multiplier    : {W}{bp['sl_mult']}×{NC} ATR")
    print(f"  Risk:Reward      : {W}1:{bp['tp_mult']/bp['sl_mult']:.1f}{NC}")
    print()
    print(f"  {'Metrik':<22} {'In-Sample':>12} {'Out-of-Sample':>14}")
    print(f"  {'─'*50}")
    def show(label, is_val, oos_val, fmt='.2f', good_fn=None):
        is_s  = f"{is_val:{fmt}}"
        oos_s = f"{oos_val:{fmt}}"
        col   = G if (good_fn and good_fn(oos_val)) else NC
        print(f"  {label:<22} {is_s:>12} {col}{oos_s:>14}{NC}")
    show("Total Trades",       best_tr.total,         best_te.total,          fmt='d')
    show("Win Rate",           f"{best_tr.winrate:.1f}%", f"{best_te.winrate:.1f}%",
         fmt='s', good_fn=lambda x: float(x.strip('%')) >= 50)
    show("Profit Factor",      best_tr.profit_factor, best_te.profit_factor,
         good_fn=lambda x: x >= 1.5)
    show("Net PnL (poin)",     f"{best_tr.net_pnl:+.2f}", f"{best_te.net_pnl:+.2f}",
         fmt='s', good_fn=lambda x: float(x.replace('+','')) > 0)
    show("Max Drawdown",       f"{best_tr.max_dd:.2f}", f"{best_te.max_dd:.2f}", fmt='s')

    print(f"\n{W}{'='*65}{NC}")

    # ── 6. Terapkan ke Config ────────────────────────────────────────────────────
    print()
    print(f"  Parameter di atas akan diterapkan ke {W}config/config.py{NC}")

    # Bandingkan dengan config saat ini
    current = {
        'adx_thresh': Config.ADX_THRESHOLD,
        'rsi_os':     Config.RSI_EXIT_OVERSOLD,
        'rsi_ob':     Config.RSI_EXIT_OVERBOUGHT,
        'tp_mult':    Config.ATR_TP_MULT,
        'sl_mult':    Config.ATR_SL_MULT,
    }
    changed = {k for k in current if current[k] != bp[k]}
    if not changed:
        print(f"  {G}✅ Config sudah optimal — tidak ada yang perlu diubah.{NC}")
        return

    print(f"\n  Perubahan yang akan diterapkan:")
    labels = {'adx_thresh':'ADX_THRESHOLD','rsi_os':'RSI_EXIT_OVERSOLD',
              'rsi_ob':'RSI_EXIT_OVERBOUGHT','tp_mult':'ATR_TP_MULT','sl_mult':'ATR_SL_MULT'}
    for k in changed:
        print(f"    {labels[k]:<22}: {Y}{current[k]}{NC} → {G}{bp[k]}{NC}")

    apply_to_config(bp)
    print(f"\n  {Y}⚠️  Restart bot agar perubahan aktif.{NC}")
    print(f"  {Y}   Backtest tidak termasuk spread/slippage Deriv.{NC}")
    print(f"  {Y}   Selalu pantau performa live setelah parameter diubah.{NC}")


if __name__ == "__main__":
    asyncio.run(main())
