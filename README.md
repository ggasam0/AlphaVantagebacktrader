# AlphaVantagebacktrader

Alpha Vantage 外汇数据拉取 + 本地缓存 + backtrader 回测示例模板。

## 安装依赖

```bash
pip install backtrader alpha_vantage pandas pyarrow
```

> `pyarrow` 用于写入 Parquet；如不想安装，请自行改为 CSV 缓存。

## 项目结构

```text
.
├── cache/
├── data.py
├── main.py
└── strategy.py
```

## 核心功能

- **优先读缓存**：回测时先读本地缓存，避免反复触发限流。
- **自动限流**：免费版 5 次/分钟，示例中保守 `sleep(15s)`。
- **Parquet 缓存**：速度快、体积小，按 `pair + interval + outputsize` 区分文件。

## 运行方式

编辑 `main.py` 中的 `API_KEY`，然后执行：

```bash
python main.py
```

首次运行会调用 Alpha Vantage API 并写入：

```
cache/EUR_USD__60min__full.parquet
```

后续回测会直接读缓存。

## 策略说明（RSI + EMA）

- 趋势过滤：快 EMA > 慢 EMA 做多；快 EMA < 慢 EMA 做空。
- 触发信号：
  - 做多：趋势多头 + RSI 上穿 30。
  - 做空：趋势空头 + RSI 下穿 70。
- 出场：反向信号或固定止损止盈。
