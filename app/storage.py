import datetime
import os
from pathlib import Path
from typing import Iterable, Optional, List, Dict, Any

import numpy as np
import pandas as pd

from app.config import DATA_DIR
from app.time_utils import parse_datetime


def ensure_data_dir() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR


def cached_file_path(instrument: str, timeframe: str) -> Path:
    safe_instrument = instrument.replace("/", "")
    return ensure_data_dir() / f"{safe_instrument}_{timeframe}.csv"


def save_history_to_csv(history, filepath: str) -> None:
    """将 history（可转为 DataFrame）保存为 CSV，保留历史数据并避免覆盖。"""
    try:
        df_new = pd.DataFrame(history)
        if "Date" in df_new.columns:
            df_new["Date"] = pd.to_datetime(df_new["Date"], errors="coerce")
        filepath_obj = Path(filepath)
        if filepath_obj.exists():
            df_old = pd.read_csv(filepath_obj)
            if "Date" in df_old.columns:
                df_old["Date"] = pd.to_datetime(df_old["Date"], errors="coerce")
            df = pd.concat([df_old, df_new], ignore_index=True)
            if "Date" in df.columns:
                df = df.drop_duplicates(subset=["Date"]).sort_values("Date")
        else:
            df = df_new
        if "Date" in df.columns:
            df["Date"] = df["Date"].dt.strftime("%m.%d.%Y %H:%M:%S.%f")
        df.to_csv(filepath_obj, index=False)
    except Exception:
        # 退回到简单的 numpy 保存（保留原有行为的容错）
        np.savetxt(filepath, history, delimiter=",", fmt="%s")


def process_timeframe(
    fx,
    instrument: str,
    timeframe: str,
    start: datetime.datetime,
    end: datetime.datetime,
    out_dir: str = ".",
) -> str:
    """为单个时间级别获取黄金数据并保存到文件，返回文件路径。"""
    history = fx.get_history(instrument, timeframe, start, end)
    filename = f"{instrument.replace('/','')}_{timeframe}.csv"
    filepath = os.path.join(out_dir, filename)
    save_history_to_csv(history, filepath)
    return filepath


def load_history(filepath: Path) -> pd.DataFrame:
    if not filepath.exists():
        raise FileNotFoundError(str(filepath))
    df = pd.read_csv(filepath)
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df


def filter_history(df: pd.DataFrame, start: Optional[str], end: Optional[str]) -> pd.DataFrame:
    if "Date" not in df.columns or (start is None and end is None):
        return df
    start_dt = parse_datetime(start) if start else None
    end_dt = parse_datetime(end) if end else None
    filtered = df
    if start_dt is not None:
        filtered = filtered[filtered["Date"] >= start_dt]
    if end_dt is not None:
        filtered = filtered[filtered["Date"] <= end_dt]
    return filtered


def normalize_candles(df: pd.DataFrame) -> List[Dict[str, Any]]:
    candidates = [
        ("BidOpen", "BidHigh", "BidLow", "BidClose"),
        ("Open", "High", "Low", "Close"),
    ]
    date_series = df["Date"] if "Date" in df.columns else None
    for open_col, high_col, low_col, close_col in candidates:
        if all(col in df.columns for col in (open_col, high_col, low_col, close_col)):
            return [
                {
                    "time": (
                        date_series.iloc[idx].isoformat()
                        if date_series is not None and not pd.isna(date_series.iloc[idx])
                        else str(idx)
                    ),
                    "open": float(row[open_col]),
                    "high": float(row[high_col]),
                    "low": float(row[low_col]),
                    "close": float(row[close_col]),
                }
                for idx, row in df.iterrows()
            ]
    if "Bid" in df.columns:
        return [
            {
                "time": (
                    date_series.iloc[idx].isoformat()
                    if date_series is not None and not pd.isna(date_series.iloc[idx])
                    else str(idx)
                ),
                "open": float(row["Bid"]),
                "high": float(row["Bid"]),
                "low": float(row["Bid"]),
                "close": float(row["Bid"]),
            }
            for idx, row in df.iterrows()
        ]
    return []


def cache_summary(instrument: str, timeframes: Iterable[str]) -> List[Dict[str, Any]]:
    summary: List[Dict[str, Any]] = []
    for timeframe in timeframes:
        filepath = cached_file_path(instrument, timeframe)
        if filepath.exists():
            df = load_history(filepath)
            summary.append(
                {
                    "timeframe": timeframe,
                    "cached": True,
                    "rows": int(len(df)),
                    "last_modified": datetime.datetime.fromtimestamp(
                        filepath.stat().st_mtime, tz=datetime.timezone.utc
                    ).isoformat(),
                    "path": str(filepath),
                }
            )
        else:
            summary.append(
                {
                    "timeframe": timeframe,
                    "cached": False,
                    "rows": 0,
                    "last_modified": None,
                    "path": str(filepath),
                }
            )
    return summary
