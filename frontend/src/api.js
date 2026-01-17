export async function fetchCacheStatus(instrument) {
  const url = new URL("/api/cache", window.location.origin);
  if (instrument) {
    url.searchParams.set("instrument", instrument);
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error("无法获取缓存状态");
  }
  return response.json();
}

export async function fetchCandles(timeframe, instrument, { start, end } = {}) {
  const url = new URL(`/api/preview/${timeframe}`, window.location.origin);
  if (instrument) {
    url.searchParams.set("instrument", instrument);
  }
  if (start) {
    url.searchParams.set("start", start);
  }
  if (end) {
    url.searchParams.set("end", end);
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error("无法获取K线预览数据");
  }
  return response.json();
}

export async function fetchWeeks(timeframe, instrument, { start, end } = {}) {
  const url = new URL(`/api/weeks/${timeframe}`, window.location.origin);
  if (instrument) {
    url.searchParams.set("instrument", instrument);
  }
  if (start) {
    url.searchParams.set("start", start);
  }
  if (end) {
    url.searchParams.set("end", end);
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error("无法获取周分区状态");
  }
  return response.json();
}

export async function triggerDownload(payload) {
  const response = await fetch("/api/download", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail?.detail ?? "下载失败");
  }
  return response.json();
}
