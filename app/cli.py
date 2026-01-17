import datetime

from app.config import DEFAULT_INSTRUMENT, SUPPORTED_TIMEFRAMES
from app.forex import forexconnect_session
from app.storage import ensure_data_dir, process_timeframe
from app.time_utils import parse_datetime


def main() -> None:
    instrument = DEFAULT_INSTRUMENT
    timeframes = SUPPORTED_TIMEFRAMES.copy()

    start = parse_datetime("13.01.2026 17:51:21.000").replace(tzinfo=datetime.timezone.utc)
    end = parse_datetime("14.01.2026 18:00:21.000").replace(tzinfo=datetime.timezone.utc)

    with forexconnect_session() as fx:
        for tf in timeframes:
            try:
                out_file = process_timeframe(fx, instrument, tf, start, end, out_dir=str(ensure_data_dir()))
                print(f"Saved {instrument} {tf} data to: {out_file}")
            except Exception as exc:
                print(f"Failed to process {tf}: {exc}")


if __name__ == "__main__":
    main()
