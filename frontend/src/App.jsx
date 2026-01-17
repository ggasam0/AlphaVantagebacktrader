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
  const [selectedTimeframe, setSelectedTimeframe] = useState("m5");
  const [candles, setCandles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [downloadStatus, setDownloadStatus] = useState("");

  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);

  const timeframes = useMemo(() => cacheStatus.map((item) => item.timeframe), [cacheStatus]);

  useEffect(() => {
    async function loadCache() {
      try {
        setError("");
        const data = await fetchCacheStatus(instrument);
        setCacheStatus(data.timeframes ?? []);
        if (data.timeframes?.length) {
          setSelectedTimeframe((prev) => prev || data.timeframes[0].timeframe);
        }
      } catch (err) {
        setError(err.message);
      }
    }

    loadCache();
  }, [instrument]);

  useEffect(() => {
    if (!chartContainerRef.current) {
      return;
    }
    if (!chartRef.current) {
      chartRef.current = createChart(chartContainerRef.current, {
        height: 420,
        layout: { background: { color: "#0f172a" }, textColor: "#e2e8f0" },
        grid: { vertLines: { color: "#1e293b" }, horzLines: { color: "#1e293b" } },
        rightPriceScale: { borderColor: "#334155" },
        timeScale: { borderColor: "#334155" },
      });
      seriesRef.current = chartRef.current.addCandlestickSeries({
        upColor: "#22c55e",
        downColor: "#ef4444",
        borderVisible: false,
        wickUpColor: "#22c55e",
        wickDownColor: "#ef4444",
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
  }, [selectedTimeframe, instrument]);

  useEffect(() => {
    if (seriesRef.current) {
      seriesRef.current.setData(candles);
    }
  }, [candles]);

  async function handleDownload() {
    try {
      setDownloadStatus("");
      setError("");
      const payload = {
        instrument,
        timeframes: timeframes.length ? timeframes : [selectedTimeframe],
        start: start || null,
        end: end || null,
      };
      await triggerDownload(payload);
      setDownloadStatus("下载完成，缓存已更新。");
      const data = await fetchCacheStatus(instrument);
      setCacheStatus(data.timeframes ?? []);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="page">
      <header className="header">
        <div>
          <h1>黄金数据缓存管理</h1>
          <p>管理 m5 / H1 的缓存数据，并预览不同周期的K线图。</p>
        </div>
        <div className="instrument">
          <label>品种</label>
          <input value={instrument} onChange={(event) => setInstrument(event.target.value)} />
        </div>
      </header>

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
              <div className="cache-title">{item.timeframe}</div>
              <div className={`cache-badge ${item.cached ? "cached" : "missing"}`}>
                {item.cached ? "已缓存" : "未缓存"}
              </div>
              <div className="cache-meta">行数：{item.rows}</div>
              <div className="cache-meta">更新：{item.last_modified ?? "-"}</div>
            </button>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>K线预览</h2>
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
