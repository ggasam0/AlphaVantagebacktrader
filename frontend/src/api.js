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

export async function fetchCandles(timeframe, instrument) {
  const url = new URL(`/api/data/${timeframe}`, window.location.origin);
  if (instrument) {
    url.searchParams.set("instrument", instrument);
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error("无法获取K线数据");
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
