"""
Multi-Tool Calling — Full Conversation Loop
=============================================

Demonstrates a more realistic tool-calling interaction with the OpenAI
client, including:

- Multiple tool definitions (weather, time, calculator)
- Automatic execution of tool calls with simulated results
- Multi-turn conversation — feeding tool results back to the model
- Streaming response support
- Graceful error handling for unexpected responses

Usage:
    uv run --with openai python examples/tool-calling/multi_tool.py

Prerequisites:
    - A container running a model that supports tool/function calling
      (e.g. functiongemma-270m-it with ``--jinja`` flag).
"""

from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

# ── Config ──────────────────────────────────────────────────────────
CLIENT = OpenAI(
    base_url="http://localhost:6060/v1",
    api_key="not-needed",
)
MODEL = "base-model"
# ────────────────────────────────────────────────────────────────────

# ── Tool Definitions ────────────────────────────────────────────────

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name, e.g. Paris, Tokyo",
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Temperature unit",
                    },
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get the current time in a timezone",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "Timezone name, e.g. Europe/Paris, Asia/Tokyo",
                    },
                },
                "required": ["timezone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a mathematical expression",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Math expression to evaluate, e.g. 2 + 2 * 5",
                    },
                },
                "required": ["expression"],
            },
        },
    },
]

# ── Simulated Tool Implementations ─────────────────────────────────

# Rough temperature data for demonstration
_WEATHER_DATA: dict[str, dict[str, Any]] = {
    "paris": {"temp": 22, "condition": "Sunny", "humidity": 45},
    "tokyo": {"temp": 28, "condition": "Humid", "humidity": 75},
    "london": {"temp": 15, "condition": "Cloudy", "humidity": 60},
    "new york": {"temp": 25, "condition": "Clear", "humidity": 50},
    "sydney": {"temp": 18, "condition": "Rainy", "humidity": 80},
}


def _execute_tool(name: str, args: dict[str, Any]) -> str:
    """Simulate executing a tool and return a result string."""
    if name == "get_weather":
        location = args.get("location", "unknown").lower()
        unit = args.get("unit", "celsius")
        data = _WEATHER_DATA.get(
            location,
            {"temp": 20, "condition": "Unknown", "humidity": 50},
        )
        temp = data["temp"]
        if unit == "fahrenheit":
            temp = round(temp * 9 / 5 + 32)
            unit_label = "°F"
        else:
            unit_label = "°C"
        return json.dumps({
            "location": args["location"],
            "temperature": f"{temp}{unit_label}",
            "condition": data["condition"],
            "humidity": f"{data['humidity']}%",
        })

    if name == "get_time":
        importzone = args.get("timezone", "UTC")
        # Simulated — in reality you'd use pytz / zoneinfo
        time_map = {
            "europe/paris": "14:30 CEST",
            "asia/tokyo": "21:30 JST",
            "america/new_york": "08:30 EDT",
            "europe/london": "13:30 BST",
            "australia/sydney": "22:30 AEST",
        }
        time_str = time_map.get(
            importzone.lower(),
            "12:00 UTC",
        )
        return json.dumps({
            "timezone": args["timezone"],
            "current_time": time_str,
        })

    if name == "calculate":
        expr = args.get("expression", "0")
        # Safe eval — only allow basic arithmetic
        safe_pattern = re.compile(r"^[\d\s+\-*/().]+$")
        if not safe_pattern.match(expr):
            return json.dumps({"error": "Invalid expression", "expression": expr})
        try:
            result = eval(expr, {"__builtins__": {}}, {})  # noqa: S307
            return json.dumps({
                "expression": expr,
                "result": result,
            })
        except Exception as e:
            return json.dumps({
                "expression": expr,
                "error": str(e),
            })

    return json.dumps({"error": f"Unknown tool: {name}"})


# ── Main Conversation Loop ─────────────────────────────────────────

def run_conversation(user_input: str, *, stream: bool = False) -> None:
    """Run a multi-turn conversation with tool execution loop."""
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": user_input},
    ]

    max_turns = 5
    for turn in range(max_turns):
        print(f"\n─── Turn {turn + 1} ───")

        # ── Request ────────────────────────────────────────────────
        response = CLIENT.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,  # type: ignore[arg-type]
            tool_choice="auto",
            stream=stream,
        )

        if stream:
            # Streaming: collect the full message
            collected_content: str | None = ""
            collected_tool_calls: list[tuple[int, str, str, str]] = []
            for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue

                if delta.content:
                    collected_content = (collected_content or "") + delta.content

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index if tc.index is not None else 0
                        # Accumulate by index
                        while len(collected_tool_calls) <= idx:
                            collected_tool_calls.append((idx, "", "", ""))
                        curr_id, curr_name, curr_args = collected_tool_calls[idx]
                        collected_tool_calls[idx] = (
                            tc.id or curr_id,
                            tc.function.name or curr_name,
                            (curr_args + (tc.function.arguments or "")),
                        )

            content = collected_content or None
            tool_calls_raw = [
                type("ToolCall", (), {
                    "id": cid,
                    "function": type("Func", (), {"name": cname, "arguments": cargs})(),
                })()
                for cid, cname, cargs in collected_tool_calls
                if cname
            ]
        else:
            choice = response.choices[0]
            message = choice.message
            content = message.content
            tool_calls_raw = message.tool_calls or []

        # ── Handle response ────────────────────────────────────────
        if content:
            print(f"Assistant: {content}")

        if not tool_calls_raw:
            print("\n✓ Conversation complete — no more tool calls.")
            break

        # ── Execute tool calls ─────────────────────────────────────
        for tc in tool_calls_raw:
            try:
                raw_args = tc.function.arguments
                parsed_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                parsed_args = {"raw": raw_args}

            print(f"\n  ▶ Tool call: {tc.function.name}({json.dumps(parsed_args)})")
            result = _execute_tool(tc.function.name, parsed_args)
            print(f"  ◀ Result: {result}")

            # Feed the result back to the model
            messages.append({
                "role": "assistant",
                "content": content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": raw_args,
                        },
                    }
                ],
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })
    else:
        print(f"\n⚠ Reached max {max_turns} turns — stopping.")


# ── Entry Point ────────────────────────────────────────────────────

def main() -> None:
    print("═" * 55)
    print("  Multi-Tool Calling — Demo")
    print("═" * 55)
    print("\nTools available: get_weather, get_time, calculate")
    print()

    # --- Example 1: single question, multi-tool ---
    print("▸ Example 1: Compare weather & time across cities")
    run_conversation(
        "What's the weather in Paris and Tokyo? "
        "Also what time is it in each city?",
        stream=False,
    )

    print("\n" + "─" * 55)

    # --- Example 2: calculation + weather ---
    print("\n▸ Example 2: Calculation combined with weather")
    run_conversation(
        "What is (15 + 27) * 3? Also is it warm enough to "
        "swim in Sydney right now?",
        stream=False,
    )

    print("\n" + "─" * 55)

    # --- Example 3: streaming ---
    print("\n▸ Example 3: Same query with streaming enabled")
    run_conversation(
        "What's the weather in London in fahrenheit?",
        stream=True,
    )


if __name__ == "__main__":
    main()
