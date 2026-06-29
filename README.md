# Weather MCP Server

A simple **Model Context Protocol (MCP)** server built with [fastmcp](https://gofastmcp.com) that exposes **exactly 5 weather tools**, each calling a different **live public weather API**. Includes a browser-based test UI that connects over **SSE** transport.

---

## Architecture Diagram

```mermaid
flowchart TB
    subgraph Browser["Browser (port 8080)"]
        UI[index.html]
        SDK[MCP JavaScript SDK]
        UI --> SDK
    end

    subgraph MCP["MCP Server (port 8000)"]
        SSE[SSE Endpoint /sse]
        MSG[Messages /messages/]
        T1[weather_open_meteo]
        T2[weather_wttr]
        T3[weather_7timer]
        T4[weather_openweather]
        T5[weather_weatherapi]
        SSE --> T1 & T2 & T3 & T4 & T5
        MSG --> SSE
    end

    subgraph APIs["Live Weather APIs"]
        A1[Open-Meteo\nno key]
        A2[wttr.in\nno key]
        A3[7Timer!\nno key]
        A4[OpenWeatherMap\nfree key]
        A5[WeatherAPI.com\nfree key]
    end

    SDK -->|SSE GET /sse| SSE
    SDK -->|POST /messages/| MSG
    T1 --> A1
    T2 --> A2
    T3 --> A3
    T4 --> A4
    T5 --> A5
    T1 & T2 & T3 & T4 & T5 -->|HTML response| SDK
    SDK --> UI
```

---

## The 5 Tools & APIs

| # | MCP Tool | Weather API | API Key Required? |
|---|----------|-------------|-------------------|
| 1 | `weather_open_meteo` | [Open-Meteo](https://open-meteo.com/) | No |
| 2 | `weather_wttr` | [wttr.in](https://wttr.in/) | No |
| 3 | `weather_7timer` | [7Timer!](https://www.7timer.info/) | No |
| 4 | `weather_openweather` | [OpenWeatherMap](https://openweathermap.org/api) | Yes (free tier) |
| 5 | `weather_weatherapi` | [WeatherAPI.com](https://www.weatherapi.com/) | Yes (free tier) |

### Free API Keys (optional)

Tools 1–3 work immediately with no setup. For tools 4–5:

1. Copy `.env.example` to `.env`
2. Register for free keys:
   - **OpenWeatherMap**: https://openweathermap.org/api (1,000 calls/day)
   - **WeatherAPI.com**: https://www.weatherapi.com/signup.aspx (1M calls/month)
3. Paste keys into `.env`

---

## Quick Start

### 1. Install dependencies

```bash
git clone https://github.com/RimeetMavani/weather-mcp--build.git
cd weather-mcp--build
pip install -r requirements.txt
```

### 2. Configure API keys

```bash
copy .env.example .env
# Edit .env — add GROQ_API_KEY (free tier, required for LLM inbox)
# Optionally add free weather API keys for tools 4–5
```

### 3. Start the MCP server (SSE on port 8000)

```bash
python server.py
```

You should see output like:

```
Starting MCP server 'Weather MCP Server' with transport 'sse' on http://127.0.0.1:8000/sse
```

**Keep this terminal open.**

### 4. Start the LLM agent (port 8001)

Open a **second terminal**:

```bash
python agent.py
```

The agent lists MCP tools, lets the LLM pick one for your question, calls the tool, and returns an HTML answer.

### 5. Serve the HTML inbox UI (port 8080)

Open a **third terminal**:

```bash
python -m http.server 8080
```

### 6. Open the browser UI

Go to: **http://localhost:8080/index.html**

1. Wait for status dots to turn green (agent, MCP, LLM)
2. Type a weather question in the **inbox** (no tool dropdown — the LLM chooses)
3. View the **HTML-formatted** LLM response

---

## 5 Suggested Test Prompts

| Prompt | Tool | City |
|--------|------|------|
| London weather via Open-Meteo | `weather_open_meteo` | London |
| Tokyo temperature via wttr.in | `weather_wttr` | Tokyo |
| Paris astronomical forecast via 7Timer! | `weather_7timer` | Paris |
| New York weather via OpenWeatherMap | `weather_openweather` | New York |
| Sydney weather via WeatherAPI.com | `weather_weatherapi` | Sydney |

---

## CLI Test (all 5 tools)

With `server.py` running in another terminal:

```bash
python test_client.py
```

This connects via SSE, lists tools, calls all 5 with live data, prints previews, then closes the connection.

---

## Project Files

| File | Purpose |
|------|---------|
| `server.py` | MCP server — 5 weather tools, SSE transport |
| `agent.py` | LLM agent — picks MCP tool, returns HTML answer |
| `index.html` | Inbox UI — ask weather questions, no manual tool select |
| `test_client.py` | Python script to test all 5 tools from the terminal |
| `requirements.txt` | Python dependencies |
| `.env.example` | Template for API keys (Groq + optional weather keys) |

---

## End Testing

1. Close the browser tab
2. Stop the HTML server: `Ctrl+C` in the http.server terminal
3. Stop the MCP server: `Ctrl+C` in the server.py terminal
