
import pandas as pd
import datetime
import csv
import numpy as np
from forexconnect import fxcorepy, ForexConnect
from dotenv import load_dotenv
import os


def get_credentials():
    """从环境变量读取用户名和密码。"""
    load_dotenv()
    user = os.getenv('user_name')
    pwd = os.getenv('password')
    return user, pwd


def fetch_history(fx, instrument: str, timeframe: str, start: datetime.datetime, end: datetime.datetime):
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


def process_timeframe(fx, instrument: str, timeframe: str, start: datetime.datetime, end: datetime.datetime, out_dir: str = '.'):
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


def session_status_changed(session: fxcorepy.O2GSession,
                           status: fxcorepy.AO2GSessionStatus.O2GSessionStatus):
    print("Trading session status: " + str(status))


def main():
    # 获取凭据
    user_name, password = get_credentials()

    # 可配置项：品种与时间段（默认取示例中的 2020-06-08 17:51:21 到 18:00:21 UTC）
    instrument = 'XAU/USD'  # 黄金（以 XAU/USD 为例）
    timeframes = ['m5', 'H1'] # 支持的时间级别列表't1', 'm1', 'm5', 'H1', 'H4','D1'
    
    # 使用 parse_datetime 来兼容日.月.年 与 月.日.年 两种常见表示
    start = parse_datetime("13.01.2026 17:51:21.000").replace(tzinfo=datetime.timezone.utc)
    end = parse_datetime("14.01.2026 18:00:21.000").replace(tzinfo=datetime.timezone.utc)

    with ForexConnect() as fx:
        try:
            fx.login(user_name, password, "fxcorporate.com/Hosts.jsp",
                     "Real", session_status_callback=session_status_changed)

            # 按时间级别处理并保存到不同文件
            for tf in timeframes:
                try:
                    out_file = process_timeframe(fx, instrument, tf, start, end, out_dir='.')
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


