import os
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
SUPPORTED_TIMEFRAMES = ["m5", "H1"]
DEFAULT_INSTRUMENT = "XAU/USD"
