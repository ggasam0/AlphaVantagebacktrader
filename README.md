# AlphaVantagebacktrader

## 项目简介

本项目提供一个用于获取并缓存外汇/贵金属历史行情数据的服务端程序，并通过 FastAPI 暴露数据下载与查询接口。服务会将指定品种与时间级别的历史行情写入本地 CSV 缓存，以便后续快速读取，同时支持直接从缓存返回标准化 K 线数据供前端或策略系统使用。

核心能力包括：

- 调用 ForexConnect 拉取历史行情并写入 CSV 缓存。
- 提供缓存概览与数据查询 API。
- 支持多时间级别（如 m5、H1）与自定义品种。

## 目录结构

- `main.py`：后端 FastAPI 服务与数据下载逻辑。
- `data/`：默认缓存目录（运行后自动创建）。
- `frontend/`：可选前端项目（Vite）。

## 部署与运行

### 1. 准备环境

- Python 3.10+（建议）
- ForexConnect SDK（需按供应商指引安装）

安装依赖：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

在项目根目录创建 `.env` 或导出环境变量：

```bash
export user_name="<你的账号>"
export password="<你的密码>"
```

可选配置：

- `DATA_DIR`：自定义缓存目录（默认为 `data/`）。

### 3. 启动 API 服务

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

常用接口示例：

- 缓存概览：`GET /api/cache`
- 查询缓存数据：`GET /api/data/{timeframe}`
- 触发下载：`POST /api/download`

示例下载请求：

```bash
curl -X POST "http://localhost:8000/api/download" \
  -H "Content-Type: application/json" \
  -d '{
    "instrument": "XAU/USD",
    "timeframes": ["m5", "H1"],
    "start": "2024-01-01 00:00:00",
    "end": "2024-01-02 00:00:00"
  }'
```

### 4. 运行一次性脚本（可选）

如果只想通过脚本下载数据而不启动服务：

```bash
python main.py
```

### 5. 前端（可选）

如果需要本地启动前端项目：

```bash
cd frontend
npm install
npm run dev
```

前端默认通过 Vite 启动，请根据实际需求配置 API 代理或请求地址。
