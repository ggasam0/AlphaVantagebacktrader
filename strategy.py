import backtrader as bt


class RsiEmaStrategy(bt.Strategy):
    params = dict(
        rsi_period=14,
        ema_fast=20,
        ema_slow=50,
        rsi_low=30,
        rsi_high=70,
        stop_loss=0.01,
        take_profit=0.02,
    )

    def __init__(self):
        self.ema_fast = bt.ind.EMA(self.data.close, period=self.p.ema_fast)
        self.ema_slow = bt.ind.EMA(self.data.close, period=self.p.ema_slow)
        self.rsi = bt.ind.RSI(self.data.close, period=self.p.rsi_period)

        self.order = None
        self.entry_price = None

    def _trend_long(self) -> bool:
        return self.ema_fast[0] > self.ema_slow[0]

    def _trend_short(self) -> bool:
        return self.ema_fast[0] < self.ema_slow[0]

    def next(self):
        if self.order:
            return

        price = self.data.close[0]

        if self.position:
            if self.position.size > 0:
                if price <= self.entry_price * (1 - self.p.stop_loss):
                    self.order = self.close()
                    return
                if price >= self.entry_price * (1 + self.p.take_profit):
                    self.order = self.close()
                    return
            else:
                if price >= self.entry_price * (1 + self.p.stop_loss):
                    self.order = self.close()
                    return
                if price <= self.entry_price * (1 - self.p.take_profit):
                    self.order = self.close()
                    return

        if not self.position:
            if self._trend_long() and self.rsi[-1] < self.p.rsi_low and self.rsi[0] >= self.p.rsi_low:
                self.order = self.buy()
                self.entry_price = price
                return

            if self._trend_short() and self.rsi[-1] > self.p.rsi_high and self.rsi[0] <= self.p.rsi_high:
                self.order = self.sell()
                self.entry_price = price
                return

    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            self.order = None
