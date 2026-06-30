"""
Chart generator for XAUUSD signal visualization.
Generates candlestick chart with EMA50, RSI3, ADX55 panels
and TP/SL/Entry horizontal lines.
"""
import io
import logging
from typing import List, Dict

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

logger = logging.getLogger(__name__)

# ─── Colour palette (dark theme) ────────────────────────────────────────────
BG_COLOR     = '#0d1117'
PANEL_COLOR  = '#161b22'
GRID_COLOR   = '#21262d'
TEXT_COLOR   = '#e6edf3'
BULL_COLOR   = '#26a69a'
BEAR_COLOR   = '#ef5350'
EMA_COLOR    = '#ffd700'
ENTRY_COLOR  = '#58a6ff'
TP_COLOR     = '#3fb950'
SL_COLOR     = '#f85149'
RSI_COLOR    = '#a5d6ff'
ADX_COLOR    = '#d2a8ff'
SPINE_COLOR  = '#30363d'


# ─── Series indicator helpers ────────────────────────────────────────────────

def _ema_series(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _rsi_series(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_g = gain.rolling(window=period, min_periods=period).mean()
    avg_l = loss.rolling(window=period, min_periods=period).mean()
    # Seed with rolling mean then apply Wilder smoothing
    for i in range(period, len(avg_g)):
        avg_g.iloc[i] = (avg_g.iloc[i - 1] * (period - 1) + gain.iloc[i]) / period
        avg_l.iloc[i] = (avg_l.iloc[i - 1] * (period - 1) + loss.iloc[i]) / period
    # RSI = 100 when no losses, 0 when no gains (avoid NaN for zero-denominator)
    rsi = pd.Series(np.where(avg_l == 0, 100.0,
                    np.where(avg_g == 0, 0.0,
                    100 - (100 / (1 + avg_g / avg_l)))),
                    index=close.index)
    rsi[avg_g.isna()] = np.nan   # keep NaN for warm-up period
    return rsi


def _adx_series(df: pd.DataFrame, period: int) -> pd.Series:
    high  = df['high']
    low   = df['low']
    close = df['close']

    prev_high  = high.shift(1)
    prev_low   = low.shift(1)
    prev_close = close.shift(1)

    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs()
    ], axis=1).max(axis=1)

    up   = high - prev_high
    down = prev_low - low

    plus_dm  = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)

    plus_dm_s  = pd.Series(plus_dm,  index=df.index, dtype=float)
    minus_dm_s = pd.Series(minus_dm, index=df.index, dtype=float)

    atr      = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_di  = 100 * plus_dm_s.ewm(alpha=1 / period, adjust=False).mean() / atr
    minus_di = 100 * minus_dm_s.ewm(alpha=1 / period, adjust=False).mean() / atr

    denom = (plus_di + minus_di).replace(0, np.nan)
    dx    = 100 * (plus_di - minus_di).abs() / denom
    adx   = dx.ewm(alpha=1 / period, adjust=False).mean()
    return adx


# ─── Candlestick drawing ─────────────────────────────────────────────────────

def _draw_candles(ax, df_view: pd.DataFrame):
    """Draw OHLC candlestick bars on ax."""
    bar_width = 0.6
    for idx, (_, row) in enumerate(df_view.iterrows()):
        is_bull = row['close'] >= row['open']
        color   = BULL_COLOR if is_bull else BEAR_COLOR
        body_lo = min(row['open'], row['close'])
        body_hi = max(row['open'], row['close'])
        body_h  = max(body_hi - body_lo, 0.01)   # minimum visible body

        # Wick
        ax.plot([idx, idx], [row['low'], row['high']],
                color=color, linewidth=0.8, zorder=2)
        # Body
        rect = mpatches.FancyBboxPatch(
            (idx - bar_width / 2, body_lo),
            bar_width, body_h,
            boxstyle='square,pad=0',
            facecolor=color, edgecolor=color, linewidth=0.5,
            zorder=3
        )
        ax.add_patch(rect)


# ─── Public API ─────────────────────────────────────────────────────────────

def generate_signal_chart(
    candles: List[Dict],
    signal_type: str,
    entry_price: float,
    tp: float,
    sl: float,
    timeframe: str,
    signal_label: str = 'AUTO',   # 'AUTO' or 'MANUAL'
    ema_period: int = 50,
    rsi_period: int = 3,
    adx_period: int = 55,
    adx_threshold: int = 65,
    display_candles: int = 60,
) -> bytes:
    """
    Generate a PNG chart and return raw bytes.
    Run in a thread pool (blocking matplotlib call).
    """
    if len(candles) < 2:
        raise ValueError("Not enough candle data to plot")

    # ── Build DataFrame ──────────────────────────────────────────────────────
    df = pd.DataFrame(candles)[['epoch', 'open', 'high', 'low', 'close']].copy()
    df = df.astype({'open': float, 'high': float, 'low': float, 'close': float})
    df = df.sort_values('epoch').reset_index(drop=True)

    # ── Compute full-series indicators (use all candles for accuracy) ────────
    df['ema']  = _ema_series(df['close'], ema_period)
    df['rsi']  = _rsi_series(df['close'], rsi_period)
    df['adx']  = _adx_series(df, adx_period)

    # ── Trim to display window ───────────────────────────────────────────────
    df_view = df.tail(display_candles).reset_index(drop=True)
    n = len(df_view)
    x = np.arange(n)

    # ── Layout ───────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(12, 8), dpi=120, facecolor=BG_COLOR)
    gs  = GridSpec(
        3, 1,
        figure=fig,
        height_ratios=[3, 1, 1],
        hspace=0.04,
        left=0.07, right=0.97, top=0.91, bottom=0.06
    )

    ax_main = fig.add_subplot(gs[0])
    ax_rsi  = fig.add_subplot(gs[1], sharex=ax_main)
    ax_adx  = fig.add_subplot(gs[2], sharex=ax_main)

    for ax in (ax_main, ax_rsi, ax_adx):
        ax.set_facecolor(PANEL_COLOR)
        ax.tick_params(colors=TEXT_COLOR, labelsize=7)
        ax.yaxis.label.set_color(TEXT_COLOR)
        for spine in ax.spines.values():
            spine.set_edgecolor(SPINE_COLOR)
        ax.grid(color=GRID_COLOR, linewidth=0.5, linestyle='--', alpha=0.6)

    # ── Main panel: candles + EMA + levels ───────────────────────────────────
    _draw_candles(ax_main, df_view)

    # EMA line
    ema_vals = df_view['ema'].values
    ax_main.plot(x, ema_vals, color=EMA_COLOR, linewidth=1.4,
                 label=f'EMA {ema_period}', zorder=4)

    # Horizontal levels
    _hline(ax_main, entry_price, ENTRY_COLOR, f'Entry  ${entry_price:.2f}', n)
    _hline(ax_main, tp,          TP_COLOR,    f'TP  ${tp:.2f}',            n)
    _hline(ax_main, sl,          SL_COLOR,    f'SL  ${sl:.2f}',            n)

    # Signal marker on last candle
    last_idx = n - 1
    last_row = df_view.iloc[last_idx]
    arrow_y  = last_row['low'] * 0.9997 if signal_type == 'BUY' else last_row['high'] * 1.0003
    marker   = '▲' if signal_type == 'BUY' else '▼'
    mcolor   = BULL_COLOR if signal_type == 'BUY' else BEAR_COLOR
    ax_main.annotate(
        marker,
        xy=(last_idx, arrow_y),
        fontsize=14, color=mcolor, ha='center', va='center', zorder=6
    )

    # Y-axis range: show entry + TP + SL with some padding
    prices = df_view[['low', 'high']].values.flatten()
    price_min = min(prices.min(), sl) * 0.9997
    price_max = max(prices.max(), tp) * 1.0003
    ax_main.set_ylim(price_min, price_max)
    ax_main.set_xlim(-1, n)

    # Legend
    ax_main.legend(loc='upper left', fontsize=7, framealpha=0.3,
                   labelcolor=TEXT_COLOR, facecolor=PANEL_COLOR, edgecolor=SPINE_COLOR)

    # ── RSI panel ────────────────────────────────────────────────────────────
    rsi_vals = df_view['rsi'].values
    ax_rsi.plot(x, rsi_vals, color=RSI_COLOR, linewidth=1.0)
    ax_rsi.axhline(80, color=BEAR_COLOR, linewidth=0.7, linestyle='--', alpha=0.8)
    ax_rsi.axhline(50, color=TEXT_COLOR,  linewidth=0.5, linestyle='--', alpha=0.4)
    ax_rsi.axhline(20, color=BULL_COLOR,  linewidth=0.7, linestyle='--', alpha=0.8)
    ax_rsi.fill_between(x, rsi_vals, 80,
                        where=(rsi_vals >= 80), alpha=0.15, color=BEAR_COLOR)
    ax_rsi.fill_between(x, rsi_vals, 20,
                        where=(rsi_vals <= 20), alpha=0.15, color=BULL_COLOR)
    ax_rsi.set_ylim(0, 100)
    ax_rsi.set_ylabel(f'RSI {rsi_period}', fontsize=7, color=TEXT_COLOR)
    ax_rsi.yaxis.set_label_position('right')
    ax_rsi.yaxis.tick_right()
    ax_rsi.tick_params(labelbottom=False)
    # Annotate current RSI
    last_rsi = rsi_vals[-1] if not np.isnan(rsi_vals[-1]) else 0
    ax_rsi.annotate(f'{last_rsi:.1f}', xy=(last_idx, last_rsi),
                    xytext=(last_idx - 3, last_rsi + 8 if last_rsi < 50 else last_rsi - 8),
                    fontsize=7, color=RSI_COLOR)

    # ── ADX panel ────────────────────────────────────────────────────────────
    adx_vals = df_view['adx'].values
    ax_adx.plot(x, adx_vals, color=ADX_COLOR, linewidth=1.0)
    ax_adx.axhline(adx_threshold, color=EMA_COLOR, linewidth=0.7,
                   linestyle='--', alpha=0.8,
                   label=f'Threshold {adx_threshold}')
    ax_adx.fill_between(x, adx_vals, adx_threshold,
                        where=(adx_vals >= adx_threshold),
                        alpha=0.12, color=ADX_COLOR)
    ax_adx.set_ylim(0, max(100, float(np.nanmax(adx_vals)) * 1.1))
    ax_adx.set_ylabel(f'ADX {adx_period}', fontsize=7, color=TEXT_COLOR)
    ax_adx.yaxis.set_label_position('right')
    ax_adx.yaxis.tick_right()
    ax_adx.legend(loc='upper left', fontsize=6, framealpha=0.3,
                  labelcolor=TEXT_COLOR, facecolor=PANEL_COLOR, edgecolor=SPINE_COLOR)
    # Annotate current ADX
    last_adx = adx_vals[-1] if not np.isnan(adx_vals[-1]) else 0
    ax_adx.annotate(f'{last_adx:.1f}', xy=(last_idx, last_adx),
                    fontsize=7, color=ADX_COLOR)

    # X axis labels — show epoch as HH:MM
    tick_step = max(1, n // 10)
    tick_pos  = list(range(0, n, tick_step))
    tick_lbs  = []
    for i in tick_pos:
        epoch = int(df_view.iloc[i]['epoch'])
        import datetime
        dt = datetime.datetime.utcfromtimestamp(epoch)
        tick_lbs.append(dt.strftime('%H:%M'))
    ax_adx.set_xticks(tick_pos)
    ax_adx.set_xticklabels(tick_lbs, fontsize=6, color=TEXT_COLOR)

    plt.setp(ax_main.get_xticklabels(), visible=False)
    plt.setp(ax_rsi.get_xticklabels(),  visible=False)

    # ── Title ────────────────────────────────────────────────────────────────
    emoji = '🟢 BUY' if signal_type == 'BUY' else '🔴 SELL'
    label = 'SINYAL OTOMATIS' if signal_label == 'AUTO' else 'SINYAL MANUAL'
    fig.suptitle(
        f'XAUUSD / {timeframe}  —  {emoji}  |  {label}',
        color=TEXT_COLOR, fontsize=11, fontweight='bold', y=0.97
    )

    # ── Export ───────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    try:
        fig.savefig(buf, format='png', dpi=120, facecolor=BG_COLOR)
    finally:
        plt.close(fig)   # always release figure memory, even if savefig raises
    buf.seek(0)
    return buf.read()


def _hline(ax, price: float, color: str, label: str, n: int):
    """Draw a labelled horizontal dashed line."""
    ax.axhline(price, color=color, linewidth=0.9, linestyle='--', alpha=0.9, zorder=5)
    ax.annotate(
        label,
        xy=(n - 1, price),
        xytext=(-4, 2),
        textcoords='offset points',
        fontsize=6.5, color=color,
        ha='right', va='bottom'
    )
