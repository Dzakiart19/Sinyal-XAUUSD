"""
Chart generator for XAUUSD signal visualization.
Generates candlestick chart with EMA50, RSI3, ADX55 panels
and TP/SL/Entry horizontal lines.
"""
import io
import datetime
import logging
from typing import List, Dict, Optional

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

logger = logging.getLogger(__name__)

# ─── Colour palette (dark theme) ────────────────────────────────────────────
BG_COLOR    = '#0d1117'
PANEL_COLOR = '#161b22'
GRID_COLOR  = '#21262d'
TEXT_COLOR  = '#e6edf3'
BULL_COLOR  = '#26a69a'
BEAR_COLOR  = '#ef5350'
EMA_COLOR   = '#ffd700'
ENTRY_COLOR = '#58a6ff'
TP_COLOR    = '#3fb950'
SL_COLOR    = '#f85149'
RSI_COLOR   = '#a5d6ff'
ADX_COLOR   = '#d2a8ff'
SPINE_COLOR = '#30363d'


# ─── Indicator series helpers ────────────────────────────────────────────────

def _ema_series(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _rsi_series(close: pd.Series, period: int) -> pd.Series:
    """RSI series using simple rolling mean — matches indicators.py exactly."""
    delta  = close.diff()
    gains  = delta.clip(lower=0)
    losses = (-delta).clip(lower=0)
    avg_g  = gains.rolling(window=period, min_periods=period).mean()
    avg_l  = losses.rolling(window=period, min_periods=period).mean()
    rsi = np.where(
        avg_l == 0,  100.0,
        np.where(avg_g == 0, 0.0,
                 100.0 - (100.0 / (1.0 + avg_g / avg_l)))
    )
    result = pd.Series(rsi, index=close.index, dtype=float)
    result[avg_g.isna()] = np.nan
    return result


def _adx_series(df: pd.DataFrame, period: int) -> pd.Series:
    """
    ADX series that EXACTLY mirrors TechnicalIndicators.calculate_adx()
    in indicators.py — uses Wilder EWM (alpha=1/period, adjust=False).
    First row is NaN (no previous data).
    """
    highs  = df['high'].values.astype(float)
    lows   = df['low'].values.astype(float)
    closes = df['close'].values.astype(float)

    # Work on rows 1..N (need previous bar)
    tr1 = highs[1:] - lows[1:]
    tr2 = np.abs(highs[1:] - closes[:-1])
    tr3 = np.abs(lows[1:]  - closes[:-1])
    tr  = np.maximum(np.maximum(tr1, tr2), tr3)

    up_move   = highs[1:] - highs[:-1]
    down_move = lows[:-1]  - lows[1:]
    plus_dm   = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm  = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    alpha = 1.0 / period
    tr_s  = pd.Series(tr).ewm(alpha=alpha, adjust=False).mean().values
    pdm_s = pd.Series(plus_dm).ewm(alpha=alpha, adjust=False).mean().values
    mdm_s = pd.Series(minus_dm).ewm(alpha=alpha, adjust=False).mean().values

    with np.errstate(divide='ignore', invalid='ignore'):
        plus_di  = np.where(tr_s != 0, 100.0 * pdm_s / tr_s, 0.0)
        minus_di = np.where(tr_s != 0, 100.0 * mdm_s / tr_s, 0.0)
        di_sum   = plus_di + minus_di
        di_diff  = np.abs(plus_di - minus_di)
        dx = np.where(di_sum != 0, 100.0 * di_diff / di_sum, 0.0)

    adx_vals = pd.Series(dx).ewm(alpha=alpha, adjust=False).mean().values

    # Prepend NaN for the first row that had no previous bar
    full = np.empty(len(df))
    full[0]  = np.nan
    full[1:] = adx_vals
    return pd.Series(full, index=df.index)


# ─── Candlestick drawing ─────────────────────────────────────────────────────

def _draw_candles(ax, df_view: pd.DataFrame, bar_width: float = 0.6):
    for idx, (_, row) in enumerate(df_view.iterrows()):
        is_bull = row['close'] >= row['open']
        color   = BULL_COLOR if is_bull else BEAR_COLOR
        body_lo = min(row['open'], row['close'])
        body_hi = max(row['open'], row['close'])
        body_h  = max(body_hi - body_lo, 1e-6)

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


def _style_axes(axes):
    for ax in axes:
        ax.set_facecolor(PANEL_COLOR)
        ax.tick_params(colors=TEXT_COLOR, labelsize=7)
        for spine in ax.spines.values():
            spine.set_edgecolor(SPINE_COLOR)
        ax.grid(color=GRID_COLOR, linewidth=0.4, linestyle='--', alpha=0.5)


def _hline(ax, price: float, color: str, label: str, x_end: int):
    """Draw labelled horizontal dashed line."""
    ax.axhline(price, color=color, linewidth=0.9, linestyle='--', alpha=0.9, zorder=5)
    ax.text(
        x_end - 0.5, price, f' {label}',
        fontsize=6.5, color=color,
        ha='right', va='bottom',
        bbox=dict(facecolor=PANEL_COLOR, alpha=0.5, edgecolor='none', pad=1)
    )


# ─── Public API ─────────────────────────────────────────────────────────────

def generate_signal_chart(
    candles: List[Dict],
    signal_type: str,          # 'BUY' or 'SELL'
    entry_price: float,
    tp: float,
    sl: float,
    timeframe: str,
    signal_label: str = 'AUTO',
    ema_period: int = 50,
    rsi_period: int = 3,
    adx_period: int = 55,
    adx_threshold: int = 65,
    actual_rsi: Optional[float] = None,   # from Signal object — for annotation
    actual_adx: Optional[float] = None,   # from Signal object — for annotation
    display_candles: int = 40,
) -> bytes:
    """Generate a PNG chart and return raw bytes. Run in a thread pool."""
    if len(candles) < 5:
        raise ValueError("Not enough candle data to plot")

    # ── Build & sort DataFrame ───────────────────────────────────────────────
    df = pd.DataFrame(candles)[['epoch', 'open', 'high', 'low', 'close']].copy()
    df = df.astype({'open': float, 'high': float, 'low': float, 'close': float})
    df = df.sort_values('epoch').reset_index(drop=True)

    # ── Compute indicator series from ALL available candles for accuracy ─────
    df['ema'] = _ema_series(df['close'], ema_period)
    df['rsi'] = _rsi_series(df['close'], rsi_period)
    df['adx'] = _adx_series(df, adx_period)

    # ── Trim to display window ───────────────────────────────────────────────
    df_view = df.tail(display_candles).reset_index(drop=True)
    n = len(df_view)
    x = np.arange(n)

    # ── Figure layout ────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(12, 7.5), dpi=120, facecolor=BG_COLOR)
    gs  = GridSpec(3, 1, figure=fig,
                   height_ratios=[3, 1, 1], hspace=0.06,
                   left=0.07, right=0.97, top=0.91, bottom=0.07)

    ax_main = fig.add_subplot(gs[0])
    ax_rsi  = fig.add_subplot(gs[1], sharex=ax_main)
    ax_adx  = fig.add_subplot(gs[2], sharex=ax_main)

    _style_axes([ax_main, ax_rsi, ax_adx])

    # ────────────────────── Main panel ──────────────────────────────────────
    _draw_candles(ax_main, df_view)

    # EMA line
    ema_vals = df_view['ema'].values
    ax_main.plot(x, ema_vals, color=EMA_COLOR, linewidth=1.5,
                 label=f'EMA {ema_period}: ${ema_vals[-1]:.2f}', zorder=4)

    # TP / SL / Entry horizontal lines
    _hline(ax_main, tp,          TP_COLOR,    f'TP  ${tp:.2f}',       n)
    _hline(ax_main, entry_price, ENTRY_COLOR, f'Entry  ${entry_price:.2f}', n)
    _hline(ax_main, sl,          SL_COLOR,    f'SL  ${sl:.2f}',       n)

    # Signal arrow on last candle
    last_row = df_view.iloc[-1]
    if signal_type == 'BUY':
        arrow_y = last_row['low']  - (last_row['high'] - last_row['low']) * 0.3
        ax_main.annotate('▲ BUY', xy=(n - 1, last_row['low']),
                         xytext=(n - 1, arrow_y),
                         fontsize=9, color=BULL_COLOR, ha='center', fontweight='bold',
                         arrowprops=dict(arrowstyle='->', color=BULL_COLOR, lw=1.2),
                         zorder=7)
    else:
        arrow_y = last_row['high'] + (last_row['high'] - last_row['low']) * 0.3
        ax_main.annotate('▼ SELL', xy=(n - 1, last_row['high']),
                         xytext=(n - 1, arrow_y),
                         fontsize=9, color=BEAR_COLOR, ha='center', fontweight='bold',
                         arrowprops=dict(arrowstyle='->', color=BEAR_COLOR, lw=1.2),
                         zorder=7)

    # Y range with padding
    prices = df_view[['low', 'high']].values.flatten()
    ylo = min(prices.min(), sl,          tp) * 0.9995
    yhi = max(prices.max(), sl,          tp) * 1.0005
    ax_main.set_ylim(ylo, yhi)
    ax_main.set_xlim(-0.5, n - 0.5)

    ax_main.legend(loc='upper left', fontsize=7, framealpha=0.35,
                   labelcolor=TEXT_COLOR, facecolor=PANEL_COLOR, edgecolor=SPINE_COLOR)

    # ────────────────────── RSI panel ───────────────────────────────────────
    rsi_vals = df_view['rsi'].values
    ax_rsi.plot(x, rsi_vals, color=RSI_COLOR, linewidth=1.1)
    ax_rsi.axhline(80, color=BEAR_COLOR, linewidth=0.7, linestyle='--', alpha=0.8)
    ax_rsi.axhline(50, color=TEXT_COLOR,  linewidth=0.5, linestyle='--', alpha=0.35)
    ax_rsi.axhline(20, color=BULL_COLOR,  linewidth=0.7, linestyle='--', alpha=0.8)
    ax_rsi.fill_between(x, rsi_vals, 80, where=(np.nan_to_num(rsi_vals) >= 80),
                        alpha=0.15, color=BEAR_COLOR, interpolate=True)
    ax_rsi.fill_between(x, rsi_vals, 20, where=(np.nan_to_num(rsi_vals) <= 20),
                        alpha=0.15, color=BULL_COLOR, interpolate=True)
    ax_rsi.set_ylim(0, 100)

    # Annotate — prefer actual signal value for accuracy
    rsi_display = actual_rsi if actual_rsi is not None else (
        rsi_vals[-1] if not np.isnan(rsi_vals[-1]) else 0.0
    )
    ax_rsi.set_ylabel(f'RSI {rsi_period}  [{rsi_display:.1f}]',
                      fontsize=7, color=RSI_COLOR)
    ax_rsi.yaxis.set_label_position('right')
    ax_rsi.yaxis.tick_right()
    ax_rsi.tick_params(labelbottom=False)
    ax_rsi.set_yticks([20, 50, 80])

    # ────────────────────── ADX panel ───────────────────────────────────────
    adx_vals = df_view['adx'].values
    ax_adx.plot(x, adx_vals, color=ADX_COLOR, linewidth=1.1)
    ax_adx.axhline(adx_threshold, color=EMA_COLOR, linewidth=0.8,
                   linestyle='--', alpha=0.9)

    # Dynamic y-range: show both series values and actual ADX value
    adx_display = actual_adx if actual_adx is not None else (
        adx_vals[~np.isnan(adx_vals)][-1] if len(adx_vals[~np.isnan(adx_vals)]) > 0 else 0.0
    )
    y_adx_max = max(100.0, adx_display * 1.15, float(np.nanmax(adx_vals)) * 1.1)
    ax_adx.set_ylim(0, y_adx_max)

    # Mark actual signal ADX with a horizontal reference line
    if actual_adx is not None:
        ax_adx.axhline(actual_adx, color=ADX_COLOR, linewidth=0.6,
                       linestyle=':', alpha=0.7)

    ax_adx.set_ylabel(f'ADX {adx_period}  [{adx_display:.1f}]',
                      fontsize=7, color=ADX_COLOR)
    ax_adx.yaxis.set_label_position('right')
    ax_adx.yaxis.tick_right()
    ax_adx.text(n - 0.5, adx_threshold + 1.5, f' >{adx_threshold}',
                fontsize=6, color=EMA_COLOR, ha='right')

    # Fill above threshold
    adx_safe = np.nan_to_num(adx_vals)
    ax_adx.fill_between(x, adx_safe, adx_threshold,
                        where=(adx_safe >= adx_threshold),
                        alpha=0.12, color=ADX_COLOR, interpolate=True)

    # ────────────────────── X-axis time labels ──────────────────────────────
    tick_step = max(1, n // 8)
    tick_pos  = list(range(0, n, tick_step))
    tick_lbs  = []
    for i in tick_pos:
        epoch = int(df_view.iloc[i]['epoch'])
        dt = datetime.datetime.utcfromtimestamp(epoch)
        tick_lbs.append(dt.strftime('%H:%M'))
    ax_adx.set_xticks(tick_pos)
    ax_adx.set_xticklabels(tick_lbs, fontsize=6.5, color=TEXT_COLOR)

    plt.setp(ax_main.get_xticklabels(), visible=False)
    plt.setp(ax_rsi.get_xticklabels(),  visible=False)

    # ────────────────────── Title (ASCII — no emoji font needed) ────────────
    direction  = 'BUY  >>>' if signal_type == 'BUY' else '<<<  SELL'
    label_text = 'SINYAL OTOMATIS' if signal_label == 'AUTO' else 'SINYAL MANUAL'
    title_color = BULL_COLOR if signal_type == 'BUY' else BEAR_COLOR
    fig.text(0.5, 0.955,
             f'XAUUSD / {timeframe}  —  {direction}  |  {label_text}',
             ha='center', va='top',
             color=title_color, fontsize=11, fontweight='bold')

    # ────────────────────── Export ──────────────────────────────────────────
    buf = io.BytesIO()
    try:
        fig.savefig(buf, format='png', dpi=120, facecolor=BG_COLOR)
    finally:
        plt.close(fig)
    buf.seek(0)
    return buf.read()
