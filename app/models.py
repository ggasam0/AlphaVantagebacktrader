from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field

from app.config import DEFAULT_INSTRUMENT, SUPPORTED_TIMEFRAMES


class DownloadRequest(BaseModel):
    instrument: str = Field(default=DEFAULT_INSTRUMENT)
    timeframes: List[str] = Field(default_factory=lambda: SUPPORTED_TIMEFRAMES.copy())
    start: Optional[str] = None
    end: Optional[str] = None


class DownloadResponse(BaseModel):
    saved: List[Dict[str, Any]]
