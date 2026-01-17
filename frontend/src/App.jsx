import React, { useEffect, useMemo, useRef, useState } from "react";
import { createChart } from "lightweight-charts";
import { fetchCacheStatus, fetchCandles, triggerDownload } from "./api.js";

const DEFAULT_INSTRUMENT = "XAU/USD";

function formatTimestamp(value) {
  if (!value) {
    return null;
  }
  if (typeof value === "number") {
    return value;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return Math.floor(parsed.getTime() / 1000);
}

export default function App() {
  const [instrument, setInstrument] = useState(DEFAULT_INSTRUMENT);
  const [cacheStatus, setCacheStatus] = useState([]);
  const [selectedTimeframe, setSelectedTimeframe] = useState("m1");
  const [candles, setCandles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [downloadStatus, setDownloadStatus] = useState("");
  const [autoDownloadStatus, setAutoDownloadStatus] = useState("");

  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);

  const timeframes = useMemo(() => ["m1", "m5", "H1"], []);
  const autoDownloadRef = useRef({ inFlight: false, lastKey: "" });
  const selectedCache = useMemo(
    () => cacheStatus.find((item) => item.timeframe === selectedTimeframe),
    [cacheStatus, selectedTimeframe],
  );

  useEffect(() => {
    async function loadCache() {
      try {
        setError("");
        const data = await fetchCacheStatus(instrument);
        setCacheStatus(data.timeframes ?? []);
        if (data.timeframes?.length) {
          setSelectedTimeframe((prev) =>
            prev && timeframes.includes(prev) ? prev : data.timeframes[0].timeframe,
          );
        }
      } catch (err) {
        setError(err.message);
      }
    }

    loadCache();
  }, [instrument, timeframes]);

  useEffect(() => {
    if (!chartContainerRef.current) {
      return;
    }
    if (!chartRef.current) {
      chartRef.current = createChart(chartContainerRef.current, {
        height: 420,
        layout: { background: { color: "#0b0f13" }, textColor: "#cbd5f5" },
        grid: { vertLines: { color: "#1c2533" }, horzLines: { color: "#1c2533" } },
        rightPriceScale: { borderColor: "#1f2a37" },
        timeScale: { borderColor: "#1f2a37", timeVisible: true, secondsVisible: true },
        crosshair: {
          vertLine: { color: "#38bdf8", style: 1, width: 1, labelBackgroundColor: "#0b0f13" },
          horzLine: { color: "#38bdf8", style: 1, width: 1, labelBackgroundColor: "#0b0f13" },
        },
      });
      seriesRef.current = chartRef.current.addCandlestickSeries({
        upColor: "#33d17a",
        downColor: "#ff6b6b",
        borderVisible: false,
        wickUpColor: "#33d17a",
        wickDownColor: "#ff6b6b",
      });
    }
    return () => {
      chartRef.current?.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    async function loadCandles() {
      if (!selectedTimeframe) {
        return;
      }
      if (!selectedCache?.cached) {
        setCandles([]);
        setLoading(false);
        setError("缓存未下载，请先下载后再预览。");
        return;
      }
      try {
        setLoading(true);
        setError("");
        const data = await fetchCandles(selectedTimeframe, instrument);
        const normalized = (data.candles ?? [])
          .map((item) => ({
            ...item,
            time: formatTimestamp(item.time) ?? item.time,
          }))
          .filter((item) => item.time);
        setCandles(normalized);
      } catch (err) {
        setError(err.message);
        setCandles([]);
      } finally {
        setLoading(false);
      }
    }

    loadCandles();
  }, [selectedTimeframe, instrument, selectedCache]);

  useEffect(() => {
    if (seriesRef.current) {
      seriesRef.current.setData(candles);
    }
  }, [candles]);

  const dataRange = useMemo(() => {
    if (!candles.length) {
      return null;
    }
    return candles.reduce(
      (acc, candle) => {
        const time = typeof candle.time === "number" ? candle.time : null;
        if (!time) {
          return acc;
        }
        if (!acc) {
          return { min: time, max: time };
        }
        return { min: Math.min(acc.min, time), max: Math.max(acc.max, time) };
      },
      null,
    );
  }, [candles]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) {
      return undefined;
    }
    const timeScale = chart.timeScale();
    const handleVisibleRangeChange = async (range) => {
      if (!range || !dataRange || !selectedTimeframe) {
        return;
      }
      const from = Math.floor(range.from ?? 0);
      const to = Math.ceil(range.to ?? 0);
      if (!from || !to) {
        return;
      }
      const missingStart = from < dataRange.min ? from : null;
      const missingEnd = to > dataRange.max ? to : null;
      if (missingStart === null && missingEnd === null) {
        return;
      }
      if (autoDownloadRef.current.inFlight) {
        return;
      }
      const startIso = missingStart ? new Date(missingStart * 1000).toISOString() : null;
      const endIso = missingEnd ? new Date(missingEnd * 1000).toISOString() : null;
      const key = `${selectedTimeframe}-${startIso ?? ""}-${endIso ?? ""}`;
      if (autoDownloadRef.current.lastKey === key) {
        return;
      }
      autoDownloadRef.current.inFlight = true;
      autoDownloadRef.current.lastKey = key;
      setAutoDownloadStatus("检测到可视范围超出缓存，正在自动补齐数据…");
      try {
        await triggerDownload({
          instrument,
          timeframes: [selectedTimeframe],
          start: startIso,
          end: endIso,
        });
        const fetchStart = new Date(Math.min(from, dataRange.min) * 1000).toISOString();
        const fetchEnd = new Date(Math.max(to, dataRange.max) * 1000).toISOString();
        const data = await fetchCandles(selectedTimeframe, instrument, {
          start: fetchStart,
          end: fetchEnd,
        });
        const normalized = (data.candles ?? [])
          .map((item) => ({
            ...item,
            time: formatTimestamp(item.time) ?? item.time,
          }))
          .filter((item) => item.time);
        setCandles(normalized);
        setAutoDownloadStatus("自动补齐完成，已更新图表。");
      } catch (err) {
        setError(err.message);
        setAutoDownloadStatus("");
      } finally {
        autoDownloadRef.current.inFlight = false;
      }
    };
    timeScale.subscribeVisibleTimeRangeChange(handleVisibleRangeChange);
    return () => {
      timeScale.unsubscribeVisibleTimeRangeChange(handleVisibleRangeChange);
    };
  }, [dataRange, instrument, selectedTimeframe]);

  async function handleDownload() {
    try {
      setDownloadStatus("");
      setError("");
      setAutoDownloadStatus("");
      const missingTimeframes = cacheStatus
        .filter((item) => !item.cached)
        .map((item) => item.timeframe);
      const timeframesToDownload =
        missingTimeframes.length > 0
          ? missingTimeframes
          : cacheStatus.length > 0
            ? []
            : [selectedTimeframe];
      const payload = {
        instrument,
        timeframes:
          timeframesToDownload.length > 0
            ? timeframesToDownload
            : timeframes.length > 0
              ? timeframes
              : [selectedTimeframe],
        start: start || null,
        end: end || null,
      };
      if (timeframesToDownload.length > 0) {
        await triggerDownload(payload);
        setDownloadStatus("已下载缺失缓存并刷新。");
        const data = await fetchCacheStatus(instrument);
        setCacheStatus(data.timeframes ?? []);
      } else {
        setDownloadStatus("缓存已存在，已直接预览。");
      }
      const data = await fetchCandles(selectedTimeframe, instrument, {
        start: start || null,
        end: end || null,
      });
      const normalized = (data.candles ?? [])
        .map((item) => ({
          ...item,
          time: formatTimestamp(item.time) ?? item.time,
        }))
        .filter((item) => item.time);
      setCandles(normalized);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="page">
      <header className="header">
        <div>
          <h1>MT4 风格黄金终端</h1>
          <p>支持 M1 / M5 / H1。数据按月分区存储，拖拽图表自动补齐缺失区间。</p>
        </div>
        <div className="instrument">
          <label>品种</label>
          <input value={instrument} onChange={(event) => setInstrument(event.target.value)} />
        </div>
      </header>

      <section className="panel toolbar">
        <div className="toolbar-left">
          <div className="timeframe-tabs">
            {timeframes.map((tf) => (
              <button
                key={tf}
                type="button"
                className={`tab ${selectedTimeframe === tf ? "active" : ""}`}
                onClick={() => setSelectedTimeframe(tf)}
              >
                {tf.toUpperCase()}
              </button>
            ))}
          </div>
          <div className="toolbar-note">手动选择预览时间范围后点击下载。</div>
        </div>
        <div className="controls">
          <label>
            开始时间
            <input
              type="datetime-local"
              step="1"
              value={start}
              onChange={(event) => setStart(event.target.value)}
            />
          </label>
          <label>
            结束时间
            <input
              type="datetime-local"
              step="1"
              value={end}
              onChange={(event) => setEnd(event.target.value)}
            />
          </label>
          <button type="button" className="primary" onClick={handleDownload}>
            下载并刷新缓存
          </button>
        </div>
      </section>

      <section className="panel">
        <h2>缓存状态</h2>
        <div className="cache-grid">
          {cacheStatus.map((item) => (
            <button
              key={item.timeframe}
              type="button"
              className={`cache-card ${selectedTimeframe === item.timeframe ? "active" : ""}`}
              onClick={() => setSelectedTimeframe(item.timeframe)}
            >
              <div className="cache-title">{item.timeframe.toUpperCase()}</div>
              <div className={`cache-badge ${item.cached ? "cached" : "missing"}`}>
                {item.cached ? "已缓存" : "未缓存"}
              </div>
              <div className="cache-meta">分区：{item.partitions ?? 0} 个月</div>
              <div className="cache-meta">行数：{item.rows}</div>
              <div className="cache-meta">更新：{item.last_modified ?? "-"}</div>
            </button>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>K线预览</h2>
          <div className="panel-status">
            {autoDownloadStatus && <span>{autoDownloadStatus}</span>}
          </div>
        </div>

        <div className="chart-card">
          {loading && <div className="status">正在加载 {selectedTimeframe} 数据…</div>}
          {!loading && candles.length === 0 && <div className="status">暂无K线数据。</div>}
          <div className="chart" ref={chartContainerRef} />
        </div>
      </section>

      {(error || downloadStatus) && (
        <section className="panel alerts">
          {error && <div className="alert error">{error}</div>}
          {downloadStatus && <div className="alert success">{downloadStatus}</div>}
        </section>
      )}
    </div>
  );
}
