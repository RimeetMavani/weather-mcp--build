"""
Run 5 live MCP tool calls against the weather server (stdio transport via in-process client).

For SSE/browser testing, use index.html instead.
Start server.py in a separate terminal first when testing via SSE manually.
"""

import asyncio

from fastmcp.client import Client
from fastmcp.client.transports import SSETransport

MCP_SSE_URL = "http://127.0.0.1:8000/sse"

TESTS = [
    ("weather_open_meteo", "London", "Open-Meteo"),
    ("weather_wttr", "Tokyo", "wttr.in"),
    ("weather_7timer", "Paris", "7Timer!"),
    ("weather_openweather", "New York", "OpenWeatherMap"),
    ("weather_weatherapi", "Sydney", "WeatherAPI.com"),
]


async def main() -> None:
    print("Connecting to MCP server at", MCP_SSE_URL)
    print("=" * 60)

    async with Client(SSETransport(MCP_SSE_URL)) as client:
        tools = await client.list_tools()
        print(f"Available tools ({len(tools)}):")
        for tool in tools:
            print(f"  - {tool.name}")
        print("=" * 60)

        for tool_name, city, label in TESTS:
            print(f"\n>> Test: {label} | tool={tool_name} | city={city}")
            try:
                result = await client.call_tool(tool_name, {"city": city})
                text = ""
                if hasattr(result, "content") and result.content:
                    for part in result.content:
                        if hasattr(part, "text"):
                            text = part.text
                            break
                if not text and hasattr(result, "data"):
                    text = str(result.data)
                preview = text[:200].replace("\n", " ")
                if len(text) > 200:
                    preview += "..."
                safe = preview.encode("ascii", errors="replace").decode("ascii")
                print(f"  OK Response preview: {safe}")
            except Exception as exc:
                print(f"  FAIL Error: {exc}")

    print("\n" + "=" * 60)
    print("All 5 tests complete. MCP connection closed.")


if __name__ == "__main__":
    asyncio.run(main())
