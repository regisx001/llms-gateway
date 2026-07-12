"""
Tool Calling via OpenAI Client — /v1/chat/completions
=======================================================

Uses the standard ``openai`` Python client to send a chat request
with tool/function definitions to a local llama-server instance
(via the Nginx reverse proxy).

llama-server natively supports the ``tools`` and ``tool_choice``
parameters in the ``/v1/chat/completions`` endpoint, so the OpenAI
client works out of the box with a custom ``base_url``.

Usage:
    uv run --with openai python examples/tool-calling/openai_client.py

Prerequisites:
    - An LLM container running on ``modelctl-chat`` (or any
      container that serves ``/v1/chat/completions``).
    - The container's model must support tool / function calling
      (e.g. functiongemma-270m-it).
"""

from openai import OpenAI

# ── Config ──────────────────────────────────────────────────────────
CLIENT = OpenAI(
    base_url="http://localhost:6060/v1",
    api_key="not-needed",  # llama-server doesn't require an API key
)
MODEL = "base-model"
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
    response = CLIENT.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "What's the weather in Paris?"},
        ],
        tools=TOOLS,  # type: ignore[arg-type]
        tool_choice="auto",
        stream=False,
    )

    message = response.choices[0].message

    if message.tool_calls:
        for tc in message.tool_calls:
            print(f"Tool call: {tc.function.name}")
            print(f"Arguments: {tc.function.arguments}")
    else:
        print(f"Answer: {message.content}")


if __name__ == "__main__":
    main()
