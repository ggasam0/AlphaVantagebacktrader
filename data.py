import os
import time
from typing import Tuple

import pandas as pd
from alpha_vantage.foreignexchange import ForeignExchange

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_path(pair: str, interval: str, outputsize: str) -> str:
    safe = pair.replace("/", "_")
    return os.path.join(CACHE_DIR, f"{safe}__{interval}__{outputsize}.parquet")


def _normalize_fx_frame(df: pd.DataFrame) -> pd.DataFrame:
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    df.columns = [column.lower() for column in df.columns]
    return df


def _fetch_intraday_fx(
    api_key: str, pair: str, interval: str, outputsize: str
) -> Tuple[pd.DataFrame, dict]:
    from_ccy, to_ccy = pair.split("/")
    fx = ForeignExchange(key=api_key, output_format="pandas")
    return fx.get_currency_exchange_intraday(
        from_symbol=from_ccy,
        to_symbol=to_ccy,
        interval=interval,
        outputsize=outputsize,
    )


def load_fx_from_cache_or_api(
    api_key: str,
    pair: str = "EUR/USD",
    interval: str = "60min",
    outputsize: str = "full",
    force_refresh: bool = False,
    throttle_seconds: int = 15,
) -> pd.DataFrame:
    """
    Return a DataFrame with DatetimeIndex and columns: open/high/low/close.
    """
    path = _cache_path(pair, interval, outputsize)

    if (not force_refresh) and os.path.exists(path):
        df = pd.read_parquet(path)
        return _normalize_fx_frame(df)

    time.sleep(throttle_seconds)
    df, _meta = _fetch_intraday_fx(api_key, pair, interval, outputsize)
    df = _normalize_fx_frame(df)
    df.to_parquet(path)
    return df
