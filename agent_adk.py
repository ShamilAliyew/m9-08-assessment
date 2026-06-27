"""
Trip Concierge Agent — Google ADK version
Uses qwen2.5:7b via Ollama through LiteLLM.
"""

import asyncio

from google.adk import Agent, Runner
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService
from google.adk.runners import RunConfig
from google.genai import types

from tools import search_flights, search_hotels, calculate

# --- Config ---
MAX_STEPS = 10
MODEL = "ollama/qwen2.5:7b"

INSTRUCTION = """You are a trip planning assistant.
Use the provided tools to answer the user's travel planning request.

Step order:
1. Call search_flights to find a flight
2. Call search_hotels to find a hotel
3. Call calculate with [flight_price, hotel_total] to get the grand total
4. STOP calling tools and write your final answer as plain text

IMPORTANT: After you have all three tool results, do NOT call any more tools.
Write a summary like:
"Flight: Turkish Airlines €155. Hotel: Ribeira Boutique Hotel 3 nights €330. Total: €485. Within budget: Yes."

Never invent data. Use exact city names like "Porto".
"""


def create_agent() -> Agent:
    return Agent(
        name="trip_concierge",
        model=LiteLlm(model=MODEL),
        instruction=INSTRUCTION,
        tools=[search_flights, search_hotels, calculate],
    )


async def run_agent(goal: str) -> dict:
    agent = create_agent()
    session_service = InMemorySessionService()

    runner = Runner(
        agent=agent,
        app_name="trip_concierge",
        session_service=session_service,
        auto_create_session=True,
    )

    run_config = RunConfig(max_llm_calls=MAX_STEPS)

    print(f"\n{'='*50}")
    print(f"GOAL: {goal}")
    print(f"{'='*50}\n")

    user_message = types.Content(
        role="user",
        parts=[types.Part(text=goal)],
    )

    step = 0
    final_text = ""

    async for event in runner.run_async(
        user_id="user_1",
        session_id="session_1",
        new_message=user_message,
        run_config=run_config,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    step += 1
                    fn = part.function_call
                    print(f"--- Step {step}/{MAX_STEPS} ---")
                    print(f"Tool call: {fn.name}({dict(fn.args)})")

                elif hasattr(part, "function_response") and part.function_response:
                    fn = part.function_response
                    print(f"Tool result: {dict(fn.response)}\n")

                elif hasattr(part, "text") and part.text:
                    final_text = part.text

    if not final_text:
        print(f"\nStep limit ({MAX_STEPS}) reached without a final answer.")
        return {
            "error": "Agent reached maximum steps without completing the goal.",
            "max_steps": MAX_STEPS,
            "goal": goal,
        }

    print(f"\n{'='*50}")
    print("AGENT FINAL RESPONSE:")
    print(final_text)
    print(f"{'='*50}\n")

    return {"response": final_text}


if __name__ == "__main__":
    asyncio.run(
        run_agent(
            "Plan a 3-day trip to Porto under €600 total. "
            "Find me a flight and hotel, then give me the total cost."
        )
    )