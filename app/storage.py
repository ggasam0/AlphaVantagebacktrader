import datetime
from pathlib import Path
from typing import Iterable, Optional, List, Dict, Any

import numpy as np
import pandas as pd

from app.config import DATA_DIR
from app.time_utils import parse_datetime


def ensure_data_dir() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR


def timeframe_dir(instrument: str, timeframe: str) -> Path:
    safe_instrument = instrument.replace("/", "")
    return ensure_data_dir() / safe_instrument / timeframe


def list_partition_files(instrument: str, timeframe: str) -> List[Path]:
    directory = timeframe_dir(instrument, timeframe)
    if not directory.exists():
        return []
    return sorted(directory.glob("*.csv"))


def _normalize_date_column(df: pd.DataFrame) -> pd.DataFrame:
    if "Date" in df.columns:
        df = df.copy()
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df


def _format_date_column(df: pd.DataFrame) -> pd.DataFrame:
    if "Date" in df.columns:
        df = df.copy()
        df["Date"] = df["Date"].dt.strftime("%m.%d.%Y %H:%M:%S.%f")
    return df


def _merge_existing(filepath: Path, df_new: pd.DataFrame) -> pd.DataFrame:
    if filepath.exists():
        df_old = pd.read_csv(filepath)
        df_old = _normalize_date_column(df_old)
        df = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df = df_new
    if "Date" in df.columns:
        df = df.dropna(subset=["Date"]).drop_duplicates(subset=["Date"]).sort_values("Date")
    return df


def _week_start(dt: datetime.datetime) -> datetime.datetime:
    start = dt - datetime.timedelta(days=dt.weekday())
    return start.replace(hour=0, minute=0, second=0, microsecond=0)


def _week_key(dt: datetime.datetime) -> str:
    iso = dt.isocalendar()
    try:
        year = iso.year
        week = iso.week
    except AttributeError:
        year, week = iso[0], iso[1]
    return f"{year:04d}-W{week:02d}"


def _fromisocalendar(year: int, week: int, day: int) -> datetime.date:
    try:
        return datetime.date.fromisocalendar(year, week, day)
    except AttributeError:
        jan4 = datetime.date(year, 1, 4)
        start = jan4 - datetime.timedelta(days=jan4.isoweekday() - 1)
        return start + datetime.timedelta(weeks=week - 1, days=day - 1)


def save_history_to_partitions(history, instrument: str, timeframe: str) -> List[str]:
    """将历史数据按周分区保存为 CSV，保留历史数据并避免覆盖。"""
    target_dir = timeframe_dir(instrument, timeframe)
    target_dir.mkdir(parents=True, exist_ok=True)
    saved: List[str] = []
    try:
        df_new = pd.DataFrame(history)
        df_new = _normalize_date_column(df_new)
        if "Date" in df_new.columns and df_new["Date"].notna().any():
            df_new = df_new.dropna(subset=["Date"])
            df_new["Partition"] = df_new["Date"].apply(_week_key)
            for week_key, group in df_new.groupby("Partition"):
                filename = f"{week_key}.csv"
                filepath = target_dir / filename
                df = _merge_existing(filepath, group.drop(columns=["Partition"]))
                df = _format_date_column(df)
                df.to_csv(filepath, index=False)
                saved.append(str(filepath))
        else:
            filepath = target_dir / "undated.csv"
            df = _merge_existing(filepath, df_new)
            df = _format_date_column(df)
            df.to_csv(filepath, index=False)
            saved.append(str(filepath))
    except Exception:
        fallback_path = target_dir / "undated.csv"
        np.savetxt(fallback_path, history, delimiter=",", fmt="%s")
        saved.append(str(fallback_path))
    return saved


def process_timeframe(
    fx,
    instrument: str,
    timeframe: str,
    start: datetime.datetime,
    end: datetime.datetime,
    out_dir: str = ".",
) -> List[str]:
    """为单个时间级别获取黄金数据并保存到按周分区的文件。"""
    history = fx.get_history(instrument, timeframe, start, end)
    return save_history_to_partitions(history, instrument, timeframe)


def _week_keys_between(start_dt: datetime.datetime, end_dt: datetime.datetime) -> List[str]:
    start_week = _week_start(start_dt)
    end_week = _week_start(end_dt)
    keys: List[str] = []
    current = start_week
    while current <= end_week:
        keys.append(_week_key(current))
        current = current + datetime.timedelta(days=7)
    return keys


def list_week_options(weeks: int = 60) -> List[Dict[str, str]]:
    if weeks < 1:
        weeks = 1
    end_dt = datetime.datetime.now()
    start_dt = end_dt - datetime.timedelta(weeks=weeks)
    week_keys = _week_keys_between(start_dt, end_dt)
    options: List[Dict[str, str]] = []
    for key in week_keys:
        year, week = key.split("-W")
        monday = _fromisocalendar(int(year), int(week), 1)
        options.append(
            {
                "key": key,
                "value": f"{year}-W{int(week):02d}",
                "monday": monday.isoformat(),
            }
        )
    return options


def select_partition_files(
    instrument: str, timeframe: str, start: Optional[str], end: Optional[str]
) -> List[Path]:
    files = list_partition_files(instrument, timeframe)
    if not files or start is None or end is None:
        return files
    start_dt = parse_datetime(start)
    end_dt = parse_datetime(end)
    week_keys = set(_week_keys_between(start_dt, end_dt))
    selected: List[Path] = []
    for filepath in files:
        if filepath.stem in week_keys:
            selected.append(filepath)
    return selected


def list_week_partitions(
    instrument: str,
    timeframe: str,
    start: Optional[str],
    end: Optional[str],
    weeks: int = 8,
) -> List[Dict[str, Any]]:
    files = list_partition_files(instrument, timeframe)
    existing = {path.stem for path in files}
    if start and end:
        start_dt = parse_datetime(start)
        end_dt = parse_datetime(end)
        if end_dt < start_dt:
            start_dt, end_dt = end_dt, start_dt
    else:
        end_dt = datetime.datetime.now()
        start_dt = end_dt - datetime.timedelta(weeks=weeks)
    week_keys = _week_keys_between(start_dt, end_dt)
    partitions: List[Dict[str, Any]] = []
    for key in week_keys:
        year, week = key.split("-W")
        monday = _fromisocalendar(int(year), int(week), 1)
        start_week = datetime.datetime.combine(monday, datetime.time.min)
        end_week = start_week + datetime.timedelta(days=7) - datetime.timedelta(seconds=1)
        partitions.append(
            {
                "key": key,
                "start": start_week.isoformat(),
                "end": end_week.isoformat(),
                "cached": key in existing,
            }
        )
    return partitions


def load_history(paths: Iterable[Path]) -> pd.DataFrame:
    paths = list(paths)
    if not paths:
        raise FileNotFoundError("No cache files found")
    frames = []
    for filepath in paths:
        df = pd.read_csv(filepath)
        df = _normalize_date_column(df)
        frames.append(df)
    combined = pd.concat(frames, ignore_index=True)
    if "Date" in combined.columns:
        combined = combined.dropna(subset=["Date"]).drop_duplicates(subset=["Date"]).sort_values("Date")
    return combined


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
        files = list_partition_files(instrument, timeframe)
        if files:
            df = load_history(files)
            last_modified = max(
                datetime.datetime.fromtimestamp(path.stat().st_mtime, tz=datetime.timezone.utc)
                for path in files
            )
            summary.append(
                {
                    "timeframe": timeframe,
                    "cached": True,
                    "rows": int(len(df)),
                    "last_modified": last_modified.isoformat(),
                    "partitions": len(files),
                    "path": str(timeframe_dir(instrument, timeframe)),
                }
            )
        else:
            summary.append(
                {
                    "timeframe": timeframe,
                    "cached": False,
                    "rows": 0,
                    "last_modified": None,
                    "partitions": 0,
                    "path": str(timeframe_dir(instrument, timeframe)),
                }
            )
    return summary
