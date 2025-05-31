#!/usr/bin/env python3
"""
generate_candlestick.py

This script uses pandas + mplfinance to build a dummy 30-day candlestick chart
and saves it as "candlestick.png" in this same folder.
"""

import os
# ── Force our working directory to the folder containing this script.
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Now import pandas/numpy/mplfinance
import pandas as pd
import numpy as np
import mplfinance as mpf
from datetime import datetime, timedelta

# 1) Build a date index for the last 30 days
end_date   = datetime.now()
start_date = end_date - timedelta(days=29)
dates      = pd.date_range(start=start_date, end=end_date, freq='D')

# 2) Create dummy “close” prices and derive OHLC
np.random.seed(42)
base_price = 100.0
price      = np.cumsum(np.random.randn(len(dates)) * 2) + base_price

df            = pd.DataFrame(index=dates)
df['close']   = price
df['open']    = df['close'].shift(1).fillna(df['close'].iloc[0])
df['high']    = df[['open','close']].max(axis=1) + np.random.rand(len(dates)) * 2
df['low']     = df[['open','close']].min(axis=1) - np.random.rand(len(dates)) * 2
df            = df[['open','high','low','close']]

# 3) Choose an mplfinance style
mpf_style = mpf.make_mpf_style(base_mpf_style='classic')

# 4) Plot & save to "candlestick.png" inside this folder
mpf.plot(
    df,
    type='candle',
    style=mpf_style,
    title='Dummy Candlestick (Last 30 Days)',
    ylabel='Price',
    figsize=(8, 4),
    savefig='candlestick.png'
)

print("✅ Saved candlestick.png")
