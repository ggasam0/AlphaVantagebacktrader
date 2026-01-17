import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException

from app.config import DEFAULT_INSTRUMENT, SUPPORTED_TIMEFRAMES
from app.forex import forexconnect_session
from app.models import DownloadRequest, DownloadResponse
from app.storage import (
    cache_summary,
    cached_file_path,
    filter_history,
    load_history,
    normalize_candles,
    process_timeframe,
    ensure_data_dir,
)
from app.time_utils import parse_datetime

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


@app.get("/api/preview/{timeframe}")
def api_preview(
    timeframe: str,
    instrument: str = DEFAULT_INSTRUMENT,
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise HTTPException(status_code=400, detail="Unsupported timeframe")
    filepath = cached_file_path(instrument, timeframe)
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Cache not found")
    df = load_history(filepath)
    df = filter_history(df, start, end)
    candles = normalize_candles(df)
    return {"instrument": instrument, "timeframe": timeframe, "candles": candles}


@app.post("/api/download", response_model=DownloadResponse)
def api_download(payload: DownloadRequest):
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
    try:
        with forexconnect_session() as fx:
            for tf in payload.timeframes:
                if tf not in SUPPORTED_TIMEFRAMES:
                    continue
                path = process_timeframe(
                    fx,
                    payload.instrument,
                    tf,
                    start,
                    end,
                    out_dir=str(ensure_data_dir()),
                )
                saved.append({"timeframe": tf, "path": path})
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return DownloadResponse(saved=saved)
