import backtrader as bt

from data import load_fx_from_cache_or_api
from strategy import RsiEmaStrategy


class PandasFXData(bt.feeds.PandasData):
    params = (
        ("datetime", None),
        ("open", "open"),
        ("high", "high"),
        ("low", "low"),
        ("close", "close"),
        ("volume", -1),
        ("openinterest", -1),
    )


def run_backtest(
    api_key: str,
    pair: str = "EUR/USD",
    interval: str = "60min",
    outputsize: str = "full",
) -> None:
    df = load_fx_from_cache_or_api(
        api_key=api_key,
        pair=pair,
        interval=interval,
        outputsize=outputsize,
        force_refresh=False,
        throttle_seconds=15,
    )
    df = df.sort_index()

    cerebro = bt.Cerebro()
    cerebro.addstrategy(RsiEmaStrategy)

    datafeed = PandasFXData(dataname=df)
    cerebro.adddata(datafeed)

    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.0002)

    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", timeframe=bt.TimeFrame.Days)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="dd")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

    print("Starting Portfolio Value:", cerebro.broker.getvalue())
    results = cerebro.run()
    strat = results[0]
    print("Final Portfolio Value:", cerebro.broker.getvalue())

    print("Sharpe:", strat.analyzers.sharpe.get_analysis())
    print("DrawDown:", strat.analyzers.dd.get_analysis())
    print("Trades:", strat.analyzers.trades.get_analysis())

    # cerebro.plot()


if __name__ == "__main__":
    API_KEY = "YOUR_ALPHA_VANTAGE_KEY"
    run_backtest(API_KEY, pair="EUR/USD", interval="60min", outputsize="full")
