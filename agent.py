import json
import re
import requests

from tools import search_flights, search_hotels, calculate

# --- Config ---
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.1:8b"
MAX_STEPS = 10

# --- Tool registry ---
TOOLS = {
    "search_flights": search_flights,
    "search_hotels": search_hotels,
    "calculate": calculate,
}

SYSTEM_PROMPT = """You are a trip planning assistant. Use the provided tools to answer the user's request.

## Available Tools

Call a tool by responding with ONLY this JSON (no other text):
{"tool": "<tool_name>", "args": {<arguments>}}

### search_flights
Find the cheapest flight to a destination within a budget.
Arguments:
  - destination (string): city name only, e.g. "Porto"
  - budget_eur (number): max price in EUR, e.g. 400

### search_hotels
Find the best hotel in a city within a nightly budget.
Arguments:
  - city (string): city name only, e.g. "Porto"
  - nights (integer): number of nights, e.g. 3
  - budget_per_night_eur (number): max price per night, e.g. 150

### calculate
Sum a list of EUR costs.
Arguments:
  - items (array of numbers): e.g. [155, 330]

## Returning the Final Answer

Once you have results from all three tools, respond with ONLY this JSON:
{"final_answer": {"flight": {"airline": "...", "price_eur": 0, "duration_hours": 0}, "hotel": {"name": "...", "stars": 0, "price_per_night_eur": 0, "nights": 0, "total_hotel_cost_eur": 0}, "total_cost_eur": 0, "within_budget": true}}

Use the EXACT values returned by the tools, not summaries or strings.

## Rules
- Call ONE tool per message. Never call two tools at once.
- Use EXACT city names like "Porto", never "Porto, Portugal".
- Numbers must be actual numbers: 3 not "3", 400 not "400".
- items must be a JSON array: [155, 330] not "[155, 330]".
- Never guess or invent data. Only use what the tools return.
- Do NOT use {"tool": "final_answer", ...}. The final answer format is {"final_answer": {...}}.
- Follow this order: search_flights → search_hotels → calculate → final_answer
"""


def call_ollama(messages: list) -> str:
    response = requests.post(
        OLLAMA_URL,
        json={"model": MODEL, "messages": messages, "stream": False},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def extract_json(text: str) -> dict | None:
    """Extract the first valid JSON object containing 'tool' or 'final_answer'."""
    # Try to find all {...} blocks, largest first
    candidates = list(re.finditer(r'\{.*?\}', text, re.DOTALL))
    candidates += list(re.finditer(r'\{.*\}', text, re.DOTALL))

    seen = set()
    for match in candidates:
        s = match.group()
        if s in seen:
            continue
        seen.add(s)
        try:
            obj = json.loads(s)
            if "tool" in obj or "final_answer" in obj:
                return obj
        except json.JSONDecodeError:
            continue

    try:
        obj = json.loads(text.strip())
        if "tool" in obj or "final_answer" in obj:
            return obj
    except json.JSONDecodeError:
        pass

    return None


def run_agent(goal: str) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": goal},
    ]

    print(f"\n{'='*50}")
    print(f"GOAL: {goal}")
    print(f"{'='*50}\n")

    for step in range(1, MAX_STEPS + 1):
        print(f"--- Step {step}/{MAX_STEPS} ---")

        raw = call_ollama(messages)
        print(f"Model output:\n{raw}\n")

        messages.append({"role": "assistant", "content": raw})

        parsed = extract_json(raw)

        if parsed is None:
            messages.append({
                "role": "user",
                "content": 'Respond with ONLY a JSON object. Either {"tool": ..., "args": ...} or {"final_answer": ...}. No other text.'
            })
            continue

        # Final answer — correct format
        if "final_answer" in parsed:
            result = parsed["final_answer"]
            print(f"\n{'='*50}")
            print("FINAL RESULT:")
            print(json.dumps(result, indent=2))
            print(f"{'='*50}\n")
            return result

        if "tool" in parsed:
            tool_name = parsed.get("tool")
            tool_args = parsed.get("args", {})

            # Catch common mistake: model uses {"tool": "final_answer", ...}
            if tool_name == "final_answer":
                result = tool_args
                print(f"\n{'='*50}")
                print("FINAL RESULT:")
                print(json.dumps(result, indent=2))
                print(f"{'='*50}\n")
                return result

            if tool_name not in TOOLS:
                messages.append({
                    "role": "user",
                    "content": f"Unknown tool '{tool_name}'. Available tools: search_flights, search_hotels, calculate."
                })
                continue

            print(f"Calling tool: {tool_name}({tool_args})")
            try:
                tool_result = TOOLS[tool_name](**tool_args)
            except TypeError as e:
                tool_result = {"error": f"Invalid arguments: {e}"}

            print(f"Tool result: {tool_result}\n")

            messages.append({
                "role": "user",
                "content": f"Tool '{tool_name}' returned: {json.dumps(tool_result)}. Continue to the next step."
            })
            continue

        messages.append({
            "role": "user",
            "content": 'Your JSON must have either "tool" or "final_answer" as a top-level key.'
        })

    print(f"Step limit ({MAX_STEPS}) reached without a final answer.")
    return {
        "error": "Agent reached maximum steps without completing the goal.",
        "max_steps": MAX_STEPS,
        "goal": goal
    }


if __name__ == "__main__":
    result = run_agent(
        "Plan a 3-day trip to Porto under €600 total. "
        "Find me a flight and hotel, then give me the total cost."
    )