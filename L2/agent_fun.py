import asyncio
import sys
from typing import Dict, Any, List
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SYSTEM = (
    "You are a cheerful weekend helper. "
    "You can call MCP tools."
)

def llm_json(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    last = messages[-1]["content"].lower()

    if "weather" in last:
        return {
            "action": "get_weather",
            "args": {
                "latitude": 28.6139,   # Delhi
                "longitude": 77.2090
            }
        }

    if "book" in last:
        topic = last.replace("books", "").replace("book", "").strip() or "technology"
        return {
            "action": "book_recs",
            "args": {
                "topic": topic,
                "limit": 3
            }
        }

    if "joke" in last:
        return {"action": "random_joke", "args": {}}

    if "dog" in last:
        return {"action": "random_dog", "args": {}}

    if "trivia" in last:
        return {"action": "trivia", "args": {}}

    if "movie" in last or "movies" in last or "film" in last or "series" in last or "show" in last:
        topic = (
            last.replace("movies", "")
                .replace("movie", "")
                .replace("film", "")
                .replace("series", "")
                .replace("show", "")
                .strip()
            or "drama"
        )
        return {
            "action": "movie_recs",
            "args": {
                "topic": topic,
                "limit": 3
            }
        }

    return {
        "action": "final",
        "answer": "Try: weather, books, joke, dog, movies trivia 🙂"
    }

async def main():
    server_path = sys.argv[1] if len(sys.argv) > 1 else "server_fun.py"

    exit_stack = AsyncExitStack()
    stdio = await exit_stack.enter_async_context(
        stdio_client(
            StdioServerParameters(command="python", args=[server_path])
        )
    )

    r_in, w_out = stdio
    session = await exit_stack.enter_async_context(
        ClientSession(r_in, w_out)
    )
    await session.initialize()

    tools = (await session.list_tools()).tools
    tool_index = {t.name: t for t in tools}
    print("Connected tools:", list(tool_index.keys()))

    try:
        while True:
            user = input("\nYou: ").strip()
            if not user or user.lower() in {"exit", "quit"}:
                break

            decision = llm_json([{"role": "user", "content": user}])

            # Final answer (no tool)
            if decision["action"] == "final":
                print("\nAgent:", decision["answer"])
                continue

            # Tool call
            tname = decision["action"]
            args = decision.get("args", {})

            result = await session.call_tool(tname, args)

            # 🔑 PRINT TOOL RESULT DIRECTLY
            if result.content:
                print("\nAgent:", result.content[0].text)
            else:
                print("\nAgent:", result.model_dump_json())

    finally:
        await exit_stack.aclose()

if __name__ == "__main__":
    asyncio.run(main())
