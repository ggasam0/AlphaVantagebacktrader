import React, { useEffect, useMemo, useRef, useState } from "react";
import { createChart } from "lightweight-charts";
import { fetchCacheStatus, fetchCandles, fetchWeeks, triggerDownload } from "./api.js";

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
  const [startWeek, setStartWeek] = useState("");
  const [endWeek, setEndWeek] = useState("");
  const [downloadStatus, setDownloadStatus] = useState("");
  const [weekList, setWeekList] = useState([]);
  const [selectedWeek, setSelectedWeek] = useState(null);

  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);

  const timeframes = useMemo(() => ["m5", "H1"], []);
  const selectedCache = useMemo(
    () => cacheStatus.find((item) => item.timeframe === selectedTimeframe),
    [cacheStatus, selectedTimeframe],
  );
  const weekOptions = useMemo(
    () =>
      weekList.map((week) => ({
        ...week,
        mondayLabel: week.start ? week.start.split("T")[0] : "",
      })),
    [weekList],
  );
  const startWeekLabel = useMemo(
    () => weekValueToRange(startWeek)?.mondayLabel ?? "",
    [startWeek],
  );
  const endWeekLabel = useMemo(() => weekValueToRange(endWeek)?.mondayLabel ?? "", [endWeek]);

  function weekValueToRange(weekValue) {
    if (!weekValue) {
      return null;
    }
    const [yearPart, weekPart] = weekValue.split("-W");
    const year = Number(yearPart);
    const week = Number(weekPart);
    if (!year || !week) {
      return null;
    }
    const jan4 = new Date(Date.UTC(year, 0, 4));
    const jan4Day = jan4.getUTCDay() || 7;
    const monday = new Date(jan4);
    monday.setUTCDate(jan4.getUTCDate() - (jan4Day - 1) + (week - 1) * 7);
    const endDate = new Date(monday);
    endDate.setUTCDate(monday.getUTCDate() + 6);
    endDate.setUTCHours(23, 59, 59, 0);
    return {
      startIso: monday.toISOString().slice(0, 19),
      endIso: endDate.toISOString().slice(0, 19),
      mondayLabel: monday.toISOString().slice(0, 10),
    };
  }

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
    setCandles([]);
    setSelectedWeek(null);
  }, [selectedTimeframe, instrument]);

  useEffect(() => {
    const startRange = weekValueToRange(startWeek);
    const endRange = weekValueToRange(endWeek);
    if (startRange && endRange) {
      setStart(startRange.startIso);
      setEnd(endRange.endIso);
    } else {
      setStart("");
      setEnd("");
    }
  }, [startWeek, endWeek]);

  useEffect(() => {
    if (seriesRef.current) {
      seriesRef.current.setData(candles);
    }
  }, [candles]);

  useEffect(() => {
    async function loadWeeks() {
      if (!selectedTimeframe) {
        return;
      }
      try {
        const data = await fetchWeeks(selectedTimeframe, instrument, {
          start: start || null,
          end: end || null,
        });
        setWeekList(data.weeks ?? []);
        if (selectedWeek) {
          const stillExists = data.weeks?.some((week) => week.key === selectedWeek.key);
          if (!stillExists) {
            setSelectedWeek(null);
          }
        }
      } catch (err) {
        setError(err.message);
        setWeekList([]);
      }
    }

    loadWeeks();
  }, [selectedTimeframe, instrument, start, end]);

  async function handleWeekDownload() {
    if (!selectedWeek) {
      setError("请先选择要下载的周区间。");
      return;
    }
    try {
      setDownloadStatus("");
      setError("");
      await triggerDownload({
        instrument,
        timeframes: [selectedTimeframe],
        start: selectedWeek.start,
        end: selectedWeek.end,
      });
      setDownloadStatus(`已下载 ${selectedWeek.key} 周数据。`);
      const data = await fetchCacheStatus(instrument);
      setCacheStatus(data.timeframes ?? []);
      const weeks = await fetchWeeks(selectedTimeframe, instrument, {
        start: start || null,
        end: end || null,
      });
      setWeekList(weeks.weeks ?? []);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleWeekPreview() {
    if (!selectedWeek) {
      setError("请先选择要预览的周区间。");
      return;
    }
    if (!selectedCache?.cached) {
      setError("缓存未下载，请先下载后再预览。");
      return;
    }
    try {
      setLoading(true);
      setError("");
      const data = await fetchCandles(selectedTimeframe, instrument, {
        start: selectedWeek.start,
        end: selectedWeek.end,
      });
      const normalized = (data.candles ?? [])
        .map((item) => ({
          ...item,
          time: formatTimestamp(item.time) ?? item.time,
        }))
        .filter((item) => item.time);
      setCandles(normalized);
      setDownloadStatus(`已预览 ${selectedWeek.key} 周数据。`);
    } catch (err) {
      setError(err.message);
      setCandles([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <header className="header">
        <div>
          <h1>MT4 风格黄金终端</h1>
          <p>支持 M5 / H1。数据按周分区存储，按周下载与预览。</p>
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
          <div className="toolbar-note">默认展示最近 8 周，可选择时间范围刷新列表。</div>
        </div>
        <div className="controls">
          <label>
            周列表开始周
            <input type="week" value={startWeek} onChange={(event) => setStartWeek(event.target.value)} />
            <span className="helper-text">
              {startWeekLabel ? `周一: ${startWeekLabel}` : "请选择开始周"}
            </span>
          </label>
          <label>
            周列表结束周
            <input type="week" value={endWeek} onChange={(event) => setEndWeek(event.target.value)} />
            <span className="helper-text">
              {endWeekLabel ? `周一: ${endWeekLabel}` : "请选择结束周"}
            </span>
          </label>
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
              <div className="cache-meta">分区：{item.partitions ?? 0} 周</div>
              <div className="cache-meta">行数：{item.rows}</div>
              <div className="cache-meta">更新：{item.last_modified ?? "-"}</div>
            </button>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>下载管理（周数据列表）</h2>
          <div className="panel-status">
            {selectedWeek ? (
              <span>
                已选择 {selectedWeek.key}（{selectedWeek.cached ? "已缓存" : "未缓存"}）
              </span>
            ) : (
              <span>请选择要操作的周区间。</span>
            )}
          </div>
        </div>
        <div className="week-select">
          <label>
            直接选择周（周一代表该周）
            <select
              value={selectedWeek?.key ?? ""}
              onChange={(event) => {
                const target = weekList.find((week) => week.key === event.target.value);
                setSelectedWeek(target ?? null);
              }}
            >
              <option value="">请选择周</option>
              {weekOptions.map((week) => (
                <option key={week.key} value={week.key}>
                  {week.key}（周一 {week.mondayLabel}）
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="week-grid">
          {weekList.length === 0 && <div className="empty-state">暂无周数据列表。</div>}
          {weekList.map((week) => (
            <button
              key={week.key}
              type="button"
              className={`week-card ${selectedWeek?.key === week.key ? "active" : ""}`}
              onClick={() => setSelectedWeek(week)}
            >
              <div className="week-title">{week.key}</div>
              <div className={`cache-badge ${week.cached ? "cached" : "missing"}`}>
                {week.cached ? "已下载" : "未下载"}
              </div>
              <div className="cache-meta">
                周一：{week.start?.split("T")[0]}｜{week.start} - {week.end}
              </div>
            </button>
          ))}
        </div>
        <div className="week-actions">
          <button type="button" className="primary" onClick={handleWeekDownload}>
            下载所选周
          </button>
          <button type="button" className="secondary" onClick={handleWeekPreview}>
            预览所选周
          </button>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>K线预览</h2>
          <div className="panel-status" />
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
