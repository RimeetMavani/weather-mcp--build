"""
Weather Agent — LLM picks an MCP tool, runs it, and returns an HTML answer.

Flow:
  1. List tools from the MCP server
  2. Send user question + tools to the LLM → LLM chooses a tool
  3. Call that tool via MCP
  4. Send tool output back to the LLM → HTML response for the UI
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from pydantic import BaseModel, Field

from fastmcp.client import Client
from fastmcp.client.transports import SSETransport

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

MCP_SSE_URL = os.getenv("MCP_SSE_URL", "http://127.0.0.1:8000/sse").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
AGENT_HOST = os.getenv("AGENT_HOST", "127.0.0.1").strip()
AGENT_PORT = int(os.getenv("AGENT_PORT", "8001"))

TOOL_SELECT_SYSTEM = """You are a weather assistant with access to MCP weather tools.
Choose the best tool for the user's question and call it with the correct city argument.

Tool guide:
- General current weather → weather_open_meteo or weather_wttr (no API key)
- Feels-like, wind, description → weather_wttr
- Stargazing / cloud cover / astronomical → weather_7timer
- OpenWeatherMap data → weather_openweather
- WeatherAPI.com data → weather_weatherapi

Extract the city or location from the question. If the user did not name a place,
reply in plain text asking which city they mean — do not call a tool."""

HTML_SYSTEM = """You format weather answers as HTML for a dark-themed web UI.
Return ONLY valid HTML (no markdown code fences, no ``` blocks).

Prefer this structure:

<div class="weather-card ok">
  <div class="card-header">
    <h3>Short title</h3>
    <span class="badge">API or tool name</span>
  </div>
  <p class="city">City, Country</p>
  <p>Clear natural-language answer to the user's question.</p>
  <table>
    <tr><th>Metric</th><td>Value</td></tr>
  </table>
</div>

Use class="weather-card error" for errors. Mention which tool was used.
Be concise, accurate, and friendly."""

app = FastAPI(title="Weather MCP Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    html: str
    tool_used: str | None = None


def _error_html(title: str, message: str) -> str:
    return f"""<div class="weather-card error">
  <div class="card-header"><h3>{title}</h3></div>
  <p>{message}</p>
</div>"""


def _strip_html_fences(text: str) -> str:
    cleaned = text.strip()
    match = re.match(r"^```(?:html)?\s*\n?(.*?)\n?```\s*$", cleaned, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return cleaned


def _extract_tool_text(result) -> str:
    if hasattr(result, "content") and result.content:
        for part in result.content:
            if hasattr(part, "text") and part.text:
                return part.text
    if hasattr(result, "data") and result.data is not None:
        return str(result.data)
    return str(result)


def _mcp_tools_to_llm(tools) -> list[dict]:
    llm_tools = []
    for tool in tools:
        schema = getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", None)
        if not schema:
            schema = {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}
        llm_tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or f"Weather tool: {tool.name}",
                    "parameters": schema,
                },
            }
        )
    return llm_tools


def _format_as_html(client: Groq, question: str, tool_name: str | None, tool_output: str) -> str:
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": HTML_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"User question: {question}\n\n"
                    f"Tool used: {tool_name or 'none'}\n\n"
                    f"Tool output:\n{tool_output}"
                ),
            },
        ],
    )
    return _strip_html_fences(response.choices[0].message.content or "")


async def _run_agent(question: str) -> ChatResponse:
    if not GROQ_API_KEY:
        return ChatResponse(
            html=_error_html(
                "Missing API Key",
                "Set GROQ_API_KEY in your .env file. Get a free key at https://console.groq.com/keys",
            ),
        )

    client = Groq(api_key=GROQ_API_KEY)

    try:
        async with Client(SSETransport(MCP_SSE_URL)) as mcp:
            mcp_tools = await mcp.list_tools()
            llm_tools = _mcp_tools_to_llm(mcp_tools)

            pick = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": TOOL_SELECT_SYSTEM},
                    {"role": "user", "content": question},
                ],
                tools=llm_tools,
                tool_choice="auto",
            )
            message = pick.choices[0].message

            if not message.tool_calls:
                direct = message.content or "Please specify a city for the weather lookup."
                html = _format_as_html(client, question, None, direct)
                return ChatResponse(html=html)

            tool_call = message.tool_calls[0]
            tool_name = tool_call.function.name
            try:
                arguments = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                arguments = {"city": question}

            result = await mcp.call_tool(tool_name, arguments)
            tool_text = _extract_tool_text(result)
            html = _format_as_html(client, question, tool_name, tool_text)
            return ChatResponse(html=html, tool_used=tool_name)

    except Exception as exc:
        return ChatResponse(html=_error_html("Agent Error", str(exc)))


@app.get("/health")
async def health():
    mcp_ok = False
    mcp_tools = 0
    try:
        async with Client(SSETransport(MCP_SSE_URL)) as mcp:
            tools = await mcp.list_tools()
            mcp_ok = True
            mcp_tools = len(tools)
    except Exception:
        pass

    return {
        "agent": "ok",
        "llm_provider": "groq",
        "llm_configured": bool(GROQ_API_KEY),
        "model": GROQ_MODEL,
        "mcp_connected": mcp_ok,
        "mcp_tools": mcp_tools,
        "mcp_url": MCP_SSE_URL,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    return await _run_agent(body.question.strip())


if __name__ == "__main__":
    uvicorn.run(app, host=AGENT_HOST, port=AGENT_PORT)
