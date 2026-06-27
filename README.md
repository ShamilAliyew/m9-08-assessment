![logo_ironhack_blue 7](https://user-images.githubusercontent.com/23629340/40541063-a07a0a8a-601a-11e8-91b5-2f13e4e6b441.png)

# Assessment | Ship a Multi-Tool Agent

## Overview

This is your chance to put the second half of the unit together. You'll build a small but genuinely useful **agent** that uses **three tools** to accomplish a real, multi-step goal — deciding its own steps, the way an agent should — and returns a **structured result**. Then you'll show you understand the grown-up parts: one reliability safeguard and one safety mitigation.

No RAG is required here. This is about **agents and tool use**: an agent that reasons, calls tools, and acts.

## What You'll Build

An agent (use **Google ADK**, or a hand-rolled loop if you prefer — your choice) that:

- has **three tools** it can call,
- is given a **multi-step goal** it can't satisfy with a single tool call,
- **decides for itself** which tools to use and in what order,
- returns a **structured final result** (e.g. a small JSON object or a clearly formatted report), and
- is **bounded** (a step limit) and **guarded** (one safety mitigation you implement and explain).

### Pick a scenario (or invent your own)

Choose one that interests you — these are starting points, not requirements:

- **Trip concierge** — tools: `search_flights`, `search_hotels`, `calculate`. Goal: "Plan a 3-day trip to Porto under €600 and give me the total." Output: a structured itinerary with a cost breakdown.
- **Order assistant** — tools: `lookup_order`, `check_warranty`, `calculate`. Goal: "I want two more of my last order — total cost, and is it still under warranty?" Output: a structured summary.
- **Study planner** — tools: `list_topics`, `estimate_effort`, `calculate`. Goal: "Build me a study plan for the exam with total hours." Output: a structured plan.

Your tools can use small local data files (like the `orders.json` you've seen) or return mock data — the focus is the **agent's behaviour**, not a real backend.

## Requirements

Your submission must include:

1. **A working agent** with three tools that solves the multi-step goal by its own tool choices (not a script you hardwired).
2. **A structured output** — the final answer in a parseable, well-shaped form, not just free text.
3. **A step limit** so the agent cannot loop forever, with a sensible cap.
4. **One safety mitigation** that you implement and can justify — for example, treating tool results as untrusted data, validating a tool's arguments before acting, or requiring confirmation before a "destructive" tool runs.
5. **A README** in your repo covering:
   - which scenario and three tools you chose, and why,
   - one **reliability** note (how your step limit / failure handling protects the run),
   - one **safety** note (the mitigation you added and what attack it defends against),
   - a captured run showing the agent's tool calls and structured result.

## Submission

Work on a branch, commit your code and README, open a Pull Request, and paste its link into the submission box.

**Deadline:** Sunday 28 June 2026, 23:59 local time. Late submissions are scored at 70% maximum.

## Grading Rubric (100 pts)

| Area | What we look for | Points |
|---|---|---|
| **Agent works** | Three tools; the multi-step goal is solved by the agent's own tool choices | 30 |
| **Structured output** | Final result is well-shaped and parseable, not free text | 15 |
| **Reliability** | A working step limit; graceful handling when a tool fails or the goal can't be met | 20 |
| **Safety** | A real mitigation, correctly implemented and clearly justified | 20 |
| **README & run** | Clear tool choices, reliability + safety notes, and a captured run | 15 |

## Quality Bar

- The agent **decides its own steps** — reviewers should see tool calls it chose, not a fixed script
- The output is genuinely **structured** and could be consumed by another program
- Both the **step limit** and the **safety mitigation** actually run, and you can explain what each protects against
- No API key is committed to the repo

---

## Solution

### Scenario: Trip Concierge

**Goal:** *"Plan a 3-day trip to Porto under €600 total. Find me a flight and hotel, then give me the total cost."*

The Trip Concierge scenario was chosen because it naturally requires three sequential, dependent steps that cannot be collapsed into one: you must find a flight before you know how much budget remains for a hotel, and you can only calculate the total once both prices are known. This makes it an honest test of agent reasoning — the agent cannot shortcut the problem.

### Three Tools

| Tool | Purpose |
|---|---|
| `search_flights(destination, budget_eur)` | Returns the cheapest flight to the destination within the given budget |
| `search_hotels(city, nights, budget_per_night_eur)` | Returns the best-rated hotel within the nightly budget |
| `calculate(items)` | Sums a list of EUR costs and returns the total |

Mock data lives in `data/mock_data.json`. The focus is agent behaviour, not a live API.

### Two Implementations

This submission includes two working agent implementations:

| File | Approach | Model |
|---|---|---|
| `agent.py` | Hand-rolled ReAct loop | `llama3.1:8b` via Ollama |
| `agent_adk.py` | Google ADK + LiteLLM | `qwen2.5:7b` via Ollama |

Both share the same `tools.py` and `data/mock_data.json`. Both produce a structured result and enforce a step limit.

### Stack

- **LLM:** Ollama (runs fully locally, no API key required)
- **Python:** 3.11+
- **Dependencies:** `requests`, `google-adk`, `litellm`

### How to Run

**Install dependencies:**
```bash
pip install requests google-adk litellm
```

**Pull models:**
```bash
ollama pull llama3.1:8b
ollama pull qwen2.5:7b
```

**Run hand-rolled version:**
```bash
python agent.py
```

**Run ADK version:**
```bash
python agent_adk.py
```

---

### Reliability

**Step limit:** Both implementations cap the agent at `MAX_STEPS = 10`.

- In `agent.py`, the hand-rolled loop exits after 10 iterations and returns a structured error object.
- In `agent_adk.py`, ADK's native `RunConfig(max_llm_calls=10)` is used — this is ADK's built-in mechanism for bounding agent execution.

If the step limit is reached, both agents return:
```json
{
  "error": "Agent reached maximum steps without completing the goal.",
  "max_steps": 10,
  "goal": "..."
}
```

**Tool failure handling:** Each tool returns an `{"error": "..."}` dict on invalid input rather than raising an exception. The agent receives the error as a tool result and can recover — for example, by correcting an argument or trying a different budget.

**What it protects against:** Without a step limit, a confused model can loop indefinitely — repeatedly calling the same tool or failing to emit a final answer. The cap ensures the process always terminates and the caller always receives a response.

---

### Safety

**Mitigation: Tool argument validation and sanitization** (implemented in `tools.py`)

Every tool validates and sanitizes its inputs before acting on them:

- **Type coercion:** `budget_eur` and `nights` auto-cast from string to the correct numeric type. Small models frequently emit `"600"` instead of `600`; rather than crashing, the tool corrects the type and continues.
- **Bounds checking:** `_validate_budget()` rejects values outside `(0, 100,000]`. `_validate_nights()` rejects values outside `[1, 30]`. This prevents runaway computation from absurd inputs like `nights=99999`.
- **String sanitization:** `_sanitize_string()` strips whitespace and rejects strings longer than 100 characters, preventing oversized or structurally malicious inputs from reaching downstream logic.
- **List parsing in `calculate`:** If the model passes `"[155, 330]"` as a string instead of a JSON array, the tool parses it safely via `json.loads`. Each item is then verified to be a non-negative number.

**What attack does this defend against?**

A prompt injection attack could cause the LLM to emit malicious tool arguments — for example `budget_eur: -1` to trigger unexpected behaviour, `nights: 99999` to cause runaway computation, or a crafted destination string containing markup intended to break downstream processing. By validating every argument at the tool boundary — treating the model's output as untrusted data — we ensure that even a compromised or manipulated model cannot cause the tools to act outside their intended contract.

---

### Captured Runs

#### Hand-rolled agent (`agent.py`)

```
==================================================
GOAL: Plan a 3-day trip to Porto under €600 total. Find me a flight and hotel, then give me the total cost.
==================================================

--- Step 1/10 ---
Tool call: search_flights({'destination': 'Porto', 'budget_eur': 400})
Tool result: {'flight_id': 'FL003', 'airline': 'Turkish Airlines', 'price_eur': 155, 'duration_hours': 8, 'destination': 'Porto'}

--- Step 2/10 ---
Tool call: search_hotels({'city': 'Porto', 'nights': 3, 'budget_per_night_eur': 150})
Tool result: {'hotel_id': 'HT002', 'name': 'Ribeira Boutique Hotel', 'stars': 4, 'price_per_night_eur': 110, 'nights': 3, 'total_hotel_cost_eur': 330, 'amenities': ['wifi', 'breakfast', 'pool']}

--- Step 3/10 ---
Tool call: calculate({'items': [155, 330]})
Tool result: {'items': [155.0, 330.0], 'total_eur': 485.0}

--- Step 4/10 ---
{"final_answer": {"flight": {"airline": "Turkish Airlines", "price_eur": 155, "duration_hours": 8}, "hotel": {"name": "Ribeira Boutique Hotel", "stars": 4, "price_per_night_eur": 110, "nights": 3, "total_hotel_cost_eur": 330}, "total_cost_eur": 485.0, "within_budget": true}}

==================================================
FINAL RESULT:
{
  "flight": {
    "airline": "Turkish Airlines",
    "price_eur": 155,
    "duration_hours": 8
  },
  "hotel": {
    "name": "Ribeira Boutique Hotel",
    "stars": 4,
    "price_per_night_eur": 110,
    "nights": 3,
    "total_hotel_cost_eur": 330
  },
  "total_cost_eur": 485.0,
  "within_budget": true
}
==================================================
```

#### ADK agent (`agent_adk.py`)

```
==================================================
GOAL: Plan a 3-day trip to Porto under €600 total. Find me a flight and hotel, then give me the total cost.
==================================================

--- Step 1/10 ---
Tool call: search_flights({'destination': 'Porto', 'budget_eur': 400})
Tool result: {'flight_id': 'FL003', 'airline': 'Turkish Airlines', 'price_eur': 155, 'duration_hours': 8, 'destination': 'Porto'}

--- Step 2/10 ---
Tool call: search_hotels({'city': 'Porto', 'nights': 3, 'budget_per_night_eur': 160})
Tool result: {'hotel_id': 'HT002', 'name': 'Ribeira Boutique Hotel', 'stars': 4, 'price_per_night_eur': 110, 'nights': 3, 'total_hotel_cost_eur': 330, 'amenities': ['wifi', 'breakfast', 'pool']}

--- Step 3/10 ---
Tool call: calculate({'items': [155, 330]})
Tool result: {'items': [155.0, 330.0], 'total_eur': 485.0}

==================================================
AGENT FINAL RESPONSE:
{"Flight": "Turkish Airlines €155", "Hotel": "Ribeira Boutique Hotel 3 nights €330", "Total": "€485", "Within budget": "Yes"}
==================================================
```

Both agents chose their own tool order and arguments at each step. No step sequence was hardcoded. The total of €485 is €115 under the €600 budget.