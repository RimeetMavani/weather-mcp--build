# Weather MCP Server

A **Model Context Protocol (MCP)** server built with [fastmcp](https://gofastmcp.com) that exposes **exactly 5 weather tools** from **one API provider** ([Open-Meteo](https://open-meteo.com/)) — each tool calls a **different endpoint** on that provider.

Includes a **Groq-powered LLM agent** and a browser **inbox UI**. You ask a weather question in plain English; the LLM picks the right Open-Meteo endpoint tool, calls it, and returns an HTML answer. The UI shows **which MCP tool was actually called** for each query.

---

## Architecture Diagram

```mermaid
<<<<<<< HEAD
flowchart LR
    classDef browser fill:#e0f2fe,stroke:#0284c7,color:#0f172a,stroke-width:1.5px;
    classDef agent fill:#ede9fe,stroke:#7c3aed,color:#0f172a,stroke-width:1.5px;
    classDef mcp fill:#dcfce7,stroke:#16a34a,color:#0f172a,stroke-width:1.5px;
    classDef api fill:#fef3c7,stroke:#d97706,color:#0f172a,stroke-width:1.5px;
    classDef store fill:#f8fafc,stroke:#64748b,color:#0f172a,stroke-width:1px;

    subgraph Browser["Browser UI - index.html :8080"]
        Q["User asks weather question"]:::browser
        H["GET /health"]:::browser
        C["POST /chat { question }"]:::browser
        R["Render tool_used + HTML answer"]:::browser
    end

    subgraph Agent["Groq Agent - agent.py :8001"]
        A1["FastAPI routes"]:::agent
        A2["MCP SSE client"]:::agent
        A3["Groq call #1<br/>pick best tool + extract city"]:::agent
        A4["Groq call #2<br/>format final HTML answer"]:::agent
    end

    subgraph MCP["Weather MCP Server - server.py :8000"]
        M0["SSE endpoint /sse"]:::mcp
        M1["open_meteo_geocode"]:::mcp
        M2["open_meteo_current"]:::mcp
        M3["open_meteo_forecast"]:::mcp
        M4["open_meteo_air_quality"]:::mcp
        M5["open_meteo_historical"]:::mcp
    end

    subgraph OpenMeteo["Open-Meteo provider"]
        E1["/v1/search"]:::api
        E2["/v1/forecast<br/>current weather"]:::api
        E3["/v1/forecast<br/>5-day forecast"]:::api
        E4["/v1/air-quality"]:::api
        E5["/v1/archive"]:::api
    end

    K[".env<br/>GROQ_API_KEY<br/>MCP_SSE_URL"]:::store

    Q --> C
    H --> A1
    C --> A1
    A1 --> A2
    A1 --> A3
    A3 -->|"tool choice + city"| A2
    A2 -->|"list_tools() + call_tool()"| M0
    M0 --> M1
    M0 --> M2
    M0 --> M3
    M0 --> M4
    M0 --> M5
    M1 --> E1
    M2 --> E2
    M3 --> E3
    M4 --> E4
    M5 --> E5
    M0 -->|"HTML tool result"| A4
    A4 -->|"tool_used + html"| R
    K --> A1
=======
flowchart TB
    subgraph Browser["Browser — index.html (port 8080)"]
        UI[Weather Inbox]
        Status[System Status\nagent · MCP · LLM]
        ToolBar["Tool Called Bar\n(open_meteo_*)"]
        Answer[HTML Answer Card]
        UI --> Status
        UI --> ToolBar
        UI --> Answer
    end

    subgraph Agent["LLM Agent — agent.py (port 8001)"]
        Health["GET /health"]
        Chat["POST /chat"]
        GROQ[Groq LLM]
        MCPClient[MCP Client]
        Chat --> GROQ
        Chat --> MCPClient
        GROQ -->|"1. pick tool"| MCPClient
        MCPClient -->|"2. tool HTML"| GROQ
        GROQ -->|"3. format answer"| Chat
    end

    subgraph MCP["MCP Server — server.py (port 8000)"]
        SSE["SSE /sse"]
        T1[open_meteo_geocode]
        T2[open_meteo_current]
        T3[open_meteo_forecast]
        T4[open_meteo_air_quality]
        T5[open_meteo_historical]
        SSE --> T1 & T2 & T3 & T4 & T5
    end

    subgraph OpenMeteo["Open-Meteo — one provider, five endpoints"]
        E1["geocoding-api…/v1/search"]
        E2["api…/v1/forecast — current"]
        E3["api…/v1/forecast — daily"]
        E4["air-quality-api…/v1/air-quality"]
        E5["archive-api…/v1/archive"]
    end

    UI -->|"POST /chat { question }"| Chat
    UI -->|"GET /health"| Health
    MCPClient -->|SSE| SSE
    T1 --> E1
    T2 --> E2
    T3 --> E3
    T4 --> E4
    T5 --> E5
    Chat -->|"{ tool_used, html }"| ToolBar
    Chat --> Answer
>>>>>>> 0ba0528254102c38fa5a69efe8c4d7417de8fcf5
```

---

## Query Flow

```mermaid
sequenceDiagram
<<<<<<< HEAD
    autonumber
    participant U as Browser UI
    participant AG as agent.py
    participant G as Groq
    participant M as server.py
    participant O as Open-Meteo

    U->>AG: GET /health
    AG->>M: list_tools() over SSE
    M-->>AG: 5 available open_meteo_* tools
    AG-->>U: agent ok, MCP status, Groq configured

    U->>AG: POST /chat {question}
    AG->>M: list_tools() over SSE
    M-->>AG: tool schemas
    AG->>G: Question + tool schemas
    G-->>AG: Selected tool + city args
    AG->>M: call_tool(tool_name, {city})
    M->>O: HTTP GET to chosen endpoint
    O-->>M: live JSON weather data
    M-->>AG: HTML tool result
    AG->>G: User question + tool name + tool HTML
    G-->>AG: final HTML answer
    AG-->>U: { tool_used, html }
    U->>U: Show tool bar and answer card
```

---

=======
    participant U as User (Browser)
    participant A as Agent (Groq)
    participant M as MCP Server
    participant O as Open-Meteo API

    U->>A: POST /chat — weather question
    A->>M: list_tools (SSE)
    M-->>A: 5 open_meteo_* tools
    A->>A: Groq picks best tool + city
    A->>M: call_tool(open_meteo_*, city)
    M->>O: HTTP GET (one endpoint)
    O-->>M: live JSON data
    M-->>A: HTML tool result
    A->>A: Groq formats final HTML
    A-->>U: tool_used + html
    U->>U: Show tool name bar + answer
```

---

>>>>>>> 0ba0528254102c38fa5a69efe8c4d7417de8fcf5
## The 5 Tools — One Provider, Five Endpoints

| # | MCP Tool | Open-Meteo Endpoint | What it returns |
|---|----------|---------------------|-----------------|
| 1 | `open_meteo_geocode` | `geocoding-api.open-meteo.com/v1/search` | Coordinates, timezone, region |
| 2 | `open_meteo_current` | `api.open-meteo.com/v1/forecast` | Current temp, humidity, wind, conditions |
| 3 | `open_meteo_forecast` | `api.open-meteo.com/v1/forecast` | 5-day daily high/low, rain |
| 4 | `open_meteo_air_quality` | `air-quality-api.open-meteo.com/v1/air-quality` | AQI, PM2.5, PM10, ozone |
| 5 | `open_meteo_historical` | `archive-api.open-meteo.com/v1/archive` | Yesterday's min/max temp, conditions |

All 5 tools use **Open-Meteo only** — free, no weather API key required.

### API Keys

| Key | Required for | Sign up |
|-----|--------------|---------|
| `GROQ_API_KEY` | LLM inbox UI (`agent.py`) | https://console.groq.com/keys (free tier) |

Weather tools need **no API key**. Only Groq is required for the inbox UI.

```bash
copy .env.example .env
# Edit .env — add GROQ_API_KEY
```

---

## Quick Start

### 1. Install dependencies

```bash
git clone https://github.com/RimeetMavani/weather-mcp--build.git
cd weather-mcp--build
pip install -r requirements.txt
```

### 2. Configure Groq API key

```bash
copy .env.example .env
# Edit .env — add GROQ_API_KEY (required for LLM inbox)
```

### 3. Start the MCP server (SSE on port 8000)

```bash
python server.py
```

You should see:

```
Starting MCP server 'Weather MCP Server' with transport 'sse' on http://127.0.0.1:8000/sse
```

**Keep this terminal open.**

### 4. Start the LLM agent (port 8001)

Open a **second terminal**:

```bash
python agent.py
```

### 5. Serve the HTML inbox UI (port 8080)

Open a **third terminal**:

```bash
python -m http.server 8080
```

### 6. Open the browser UI

Go to: **http://localhost:8080/index.html**

1. Wait for status dots to turn green (agent, MCP, LLM)
2. Type a weather question or click a suggested question
3. After each query, the **MCP tool called** bar shows the exact tool the LLM picked (e.g. `open_meteo_forecast`) and its endpoint
4. View the **HTML-formatted** answer below

---

## Inbox UI — Dynamic Tool Display

The UI does **not** show a fixed tool name before you ask. After each query:

| UI element | What it shows |
|------------|---------------|
| **Tool called bar** | Exact MCP tool name + Open-Meteo endpoint used for *this* query |
| **HTML answer card** | Groq-formatted weather answer (badge shows the specific tool name) |
| **Suggested questions** | Plain questions only — no pre-assigned tool labels |

Example after asking *"Give me the 5-day forecast for Tokyo"*:

```
MCP tool called:  open_meteo_forecast  →  api.open-meteo.com/v1/forecast
```

---

## 5 Suggested Inbox Questions

| Question | Tool the LLM typically picks |
|----------|------------------------------|
| What's the weather in London right now? | `open_meteo_current` |
| Give me the 5-day forecast for Tokyo | `open_meteo_forecast` |
| What's the air quality in Paris? | `open_meteo_air_quality` |
| What were the coordinates and timezone for New York? | `open_meteo_geocode` |
| How was the weather in Sydney yesterday? | `open_meteo_historical` |

The actual tool chosen is shown in the UI after each query — the LLM may pick a different tool if it fits the question better.

---

## CLI Test (all 5 tools)

With `server.py` running in another terminal:

```bash
python test_client.py
```

Connects via SSE, lists all 5 tools, calls each with a live city, and prints a pass/fail summary. No Groq agent needed for this test.

---

## Project Files

| File | Purpose |
|------|---------|
| `server.py` | MCP server — 5 Open-Meteo endpoint tools, SSE transport |
| `agent.py` | Groq LLM agent — picks MCP tool, returns `tool_used` + HTML |
| `index.html` | Inbox UI — status panel, dynamic tool bar, HTML answers |
| `test_client.py` | Terminal script to test all 5 MCP tools directly |
| `requirements.txt` | Python dependencies |
| `.env.example` | Template for Groq API key |

---

## Ports Summary

| Port | Service | Command |
|------|---------|---------|
| 8000 | MCP server (SSE) | `python server.py` |
| 8001 | Groq LLM agent | `python agent.py` |
| 8080 | Browser UI | `python -m http.server 8080` |

---

## End Testing

1. Close the browser tab
2. Stop the HTML server: `Ctrl+C`
3. Stop the agent: `Ctrl+C`
4. Stop the MCP server: `Ctrl+C`
