import datetime


def parse_datetime(value: str) -> datetime.datetime:
    """尝试多种常见格式解析时间字符串，返回 naive datetime（未设置 tz）。

    支持格式：日.月.年 和 月.日.年，以及常见 ISO 格式。
    如果不能解析，会尝试使用 dateutil.parser（若可用），否则抛出 ValueError。
    """
    fmts = [
        "%d.%m.%Y %H:%M:%S.%f",
        "%m.%d.%Y %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
    ]
    for fmt in fmts:
        try:
            return datetime.datetime.strptime(value, fmt)
        except Exception:
            continue
    try:
        from dateutil import parser

        return parser.parse(value)
    except Exception:
        raise ValueError(f"Unrecognized date format: {value}")
