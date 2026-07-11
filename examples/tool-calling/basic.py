"""
Basic Tool Calling (Function Calling) — Raw HTTP
==================================================

Sends a chat message with tool/function definitions via a plain HTTP POST
and prints the model's response — no OpenAI client library needed.

llama-server natively supports the ``tools`` and ``tool_choice`` parameters
in the standard ``/v1/chat/completions`` endpoint.

Usage:
    uv run python examples/tool-calling/basic.py

Prerequisites:
    - A tool-calling model installed (e.g. functiongemma-270m-it-GGUF)
    - A container started for "tool-calling" capability:
        curl -X POST http://localhost:6060/api/v1/containers \
          -H 'Content-Type: application/json' \
          -d '{"capability":"tool-calling","model_id":"<model-id>"}'

    Change ``URL`` below to match your setup:
      - Direct llama-server:  http://localhost:8080/v1/chat/completions
      - Via Nginx:            http://localhost:6060/v1/chat/completions
"""

import json
import httpx

# ── Config ──────────────────────────────────────────────────────────
URL = "http://localhost:8080/v1/chat/completions"
# ────────────────────────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a city",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name, e.g. Paris",
                    }
                },
                "required": ["location"],
            },
        },
    }
]


def main() -> None:
    payload = {
        "model": "functiongemma",
        "messages": [
            {"role": "user", "content": "What's the weather in Paris?"},
        ],
        "tools": TOOLS,
        "tool_choice": "auto",
        "stream": False,
    }

    with httpx.Client() as client:
        resp = client.post(URL, json=payload)
        resp.raise_for_status()
        data = resp.json()

    message = data["choices"][0]["message"]
    tool_calls = message.get("tool_calls")

    if tool_calls:
        for tc in tool_calls:
            print(f"Tool call: {tc['function']['name']}")
            print(f"Arguments: {tc['function']['arguments']}")
    else:
        print(f"Answer: {message['content']}")


if __name__ == "__main__":
    main()
