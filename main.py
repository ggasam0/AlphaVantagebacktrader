
import datetime
import os
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
SUPPORTED_TIMEFRAMES = ["m5", "H1"]
DEFAULT_INSTRUMENT = "XAU/USD"


def get_credentials() -> tuple[str | None, str | None]:
    """从环境变量读取用户名和密码。"""
    load_dotenv()
    user = os.getenv('user_name')
    pwd = os.getenv('password')
    return user, pwd


def fetch_history(
    fx,
    instrument: str,
    timeframe: str,
    start: datetime.datetime,
    end: datetime.datetime,
):
    """调用 ForexConnect 获取历史数据并返回列表（每项为 dict）。"""
    return fx.get_history(instrument, timeframe, start, end)


def save_history_to_csv(history, filepath: str):
    """将 history（可转为 DataFrame）保存为 CSV。"""
    try:
        df = pd.DataFrame(history)
        # 确保 Date 列为可读的字符串格式
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%m.%d.%Y %H:%M:%S.%f')
        df.to_csv(filepath, index=False)
    except Exception:
        # 退回到简单的 numpy 保存（保留原有行为的容错）
        np.savetxt(filepath, history, delimiter=',', fmt='%s')


def print_history(history):
    print("Date, Bid, Ask")
    for row in history:
        print("{0:s}, {1:,.5f}, {2:,.5f}".format(
            pd.to_datetime(str(row.get('Date'))).strftime('%m.%d.%Y %H:%M:%S.%f'), row.get('Bid'), row.get('Ask')))


def process_timeframe(
    fx,
    instrument: str,
    timeframe: str,
    start: datetime.datetime,
    end: datetime.datetime,
    out_dir: str = ".",
):
    """为单个时间级别获取黄金数据并保存到文件，返回文件路径。"""
    history = fetch_history(fx, instrument, timeframe, start, end)
    filename = f"{instrument.replace('/','')}_{timeframe}.csv"
    filepath = os.path.join(out_dir, filename)
    save_history_to_csv(history, filepath)
    return filepath


def parse_datetime(s: str) -> datetime.datetime:
    """尝试多种常见格式解析时间字符串，返回 naive datetime（未设置 tz）。

    支持格式：日.月.年 和 月.日.年，以及常见 ISO 格式。
    如果不能解析，会尝试使用 dateutil.parser（若可用），否则抛出 ValueError。
    """
    fmts = [
        '%d.%m.%Y %H:%M:%S.%f',
        '%m.%d.%Y %H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S',
    ]
    for fmt in fmts:
        try:
            return datetime.datetime.strptime(s, fmt)
        except Exception:
            continue
    try:
        from dateutil import parser
        return parser.parse(s)
    except Exception:
        raise ValueError(f"Unrecognized date format: {s}")


def ensure_data_dir() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR


def cached_file_path(instrument: str, timeframe: str) -> Path:
    safe_instrument = instrument.replace("/", "")
    return ensure_data_dir() / f"{safe_instrument}_{timeframe}.csv"


def load_history(filepath: Path) -> pd.DataFrame:
    if not filepath.exists():
        raise FileNotFoundError(str(filepath))
    df = pd.read_csv(filepath)
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df


def normalize_candles(df: pd.DataFrame) -> list[dict]:
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


def cache_summary(instrument: str, timeframes: Iterable[str]) -> list[dict]:
    summary = []
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


class DownloadRequest(BaseModel):
    instrument: str = Field(default=DEFAULT_INSTRUMENT)
    timeframes: list[str] = Field(default_factory=lambda: SUPPORTED_TIMEFRAMES.copy())
    start: Optional[str] = None
    end: Optional[str] = None


class DownloadResponse(BaseModel):
    saved: list[dict]


app = FastAPI(title="Gold Data Cache API")


@app.get("/api/cache")
def api_cache(instrument: str = DEFAULT_INSTRUMENT):
    return {"instrument": instrument, "timeframes": cache_summary(instrument, SUPPORTED_TIMEFRAMES)}


@app.get("/api/data/{timeframe}")
def api_data(timeframe: str, instrument: str = DEFAULT_INSTRUMENT):
    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise HTTPException(status_code=400, detail="Unsupported timeframe")
    filepath = cached_file_path(instrument, timeframe)
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Cache not found")
    df = load_history(filepath)
    candles = normalize_candles(df)
    return {"instrument": instrument, "timeframe": timeframe, "candles": candles}


@app.post("/api/download", response_model=DownloadResponse)
def api_download(payload: DownloadRequest):
    user_name, password = get_credentials()
    if not user_name or not password:
        raise HTTPException(status_code=400, detail="Missing credentials")
    start = (
        parse_datetime(payload.start).replace(tzinfo=datetime.timezone.utc)
        if payload.start
        else datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=3)
    )
    end = (
        parse_datetime(payload.end).replace(tzinfo=datetime.timezone.utc)
        if payload.end
        else datetime.datetime.now(tz=datetime.timezone.utc)
    )
    saved = []
    from forexconnect import ForexConnect

    with ForexConnect() as fx:
        fx.login(
            user_name,
            password,
            "fxcorporate.com/Hosts.jsp",
            "Real",
            session_status_callback=session_status_changed,
        )
        for tf in payload.timeframes:
            if tf not in SUPPORTED_TIMEFRAMES:
                continue
            path = process_timeframe(fx, payload.instrument, tf, start, end, out_dir=str(ensure_data_dir()))
            saved.append({"timeframe": tf, "path": path})
        fx.logout()
    return DownloadResponse(saved=saved)


def session_status_changed(session, status):
    print("Trading session status: " + str(status))


def main():
    # 获取凭据
    user_name, password = get_credentials()

    # 可配置项：品种与时间段（默认取示例中的 2020-06-08 17:51:21 到 18:00:21 UTC）
    instrument = DEFAULT_INSTRUMENT  # 黄金（以 XAU/USD 为例）
    timeframes = SUPPORTED_TIMEFRAMES.copy()
    
    # 使用 parse_datetime 来兼容日.月.年 与 月.日.年 两种常见表示
    start = parse_datetime("13.01.2026 17:51:21.000").replace(tzinfo=datetime.timezone.utc)
    end = parse_datetime("14.01.2026 18:00:21.000").replace(tzinfo=datetime.timezone.utc)

    from forexconnect import ForexConnect

    with ForexConnect() as fx:
        try:
            fx.login(user_name, password, "fxcorporate.com/Hosts.jsp",
                     "Real", session_status_callback=session_status_changed)

            # 按时间级别处理并保存到不同文件
            for tf in timeframes:
                try:
                    out_file = process_timeframe(fx, instrument, tf, start, end, out_dir=str(ensure_data_dir()))
                    print(f"Saved {instrument} {tf} data to: {out_file}")
                except Exception as e:
                    print(f"Failed to process {tf}: {e}")

        except Exception as e:
            print("Exception: " + str(e))
        try:
            fx.logout()
        except Exception as e:
            print("Exception: " + str(e))

if __name__ == "__main__":
    main()
