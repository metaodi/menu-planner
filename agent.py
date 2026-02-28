#!/usr/bin/env python3
"""AI agent for weekly menu planning.

This agent can:
- Read and update a weekly menu plan stored in a Google Sheet
- Search for new recipes via TheMealDB
- Add ingredients and items to the Bring! shopping list app

Usage
-----
Run interactively::

    python agent.py

Or pass a one-shot prompt::

    python agent.py "Plan dinners for this week and add ingredients to Bring"

Configuration
-------------
Copy ``.env.example`` to ``.env`` and fill in your credentials before running.
"""

import json
import logging
import os
import sys
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from tools import bring as bring_tool
from tools import google_sheets as sheets_tool
from tools import recipes as recipe_tool

load_dotenv()

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _sheets_kwargs() -> dict:
    return {
        "spreadsheet_id": _env("GOOGLE_SPREADSHEET_ID"),
        "worksheet_name": _env("GOOGLE_WORKSHEET_NAME", "Menu"),
        "credentials_file": _env("GOOGLE_CREDENTIALS_FILE", "credentials.json"),
    }


def _bring_kwargs() -> dict:
    return {
        "email": _env("BRING_EMAIL"),
        "password": _env("BRING_PASSWORD"),
        "list_name": _env("BRING_LIST_NAME") or None,
    }


# ---------------------------------------------------------------------------
# Tool definitions (sent to OpenAI)
# ---------------------------------------------------------------------------

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_weekly_menu",
            "description": (
                "Read the current weekly menu plan from the Google Sheet. "
                "Returns a JSON object mapping each day of the week to its "
                "Breakfast, Lunch, and Dinner entries."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_meal",
            "description": (
                "Write a single meal into the Google Sheet. "
                "Call this once per meal slot you want to fill."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "day": {
                        "type": "string",
                        "description": "Day of the week, e.g. 'Monday'.",
                        "enum": [
                            "Monday",
                            "Tuesday",
                            "Wednesday",
                            "Thursday",
                            "Friday",
                            "Saturday",
                            "Sunday",
                        ],
                    },
                    "meal_type": {
                        "type": "string",
                        "description": "Meal slot: 'Breakfast', 'Lunch', or 'Dinner'.",
                        "enum": ["Breakfast", "Lunch", "Dinner"],
                    },
                    "meal_name": {
                        "type": "string",
                        "description": "Name of the meal to put in this slot.",
                    },
                },
                "required": ["day", "meal_type", "meal_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_recipes",
            "description": (
                "Search TheMealDB for recipes matching a name or keyword. "
                "Returns a list of matching meals with their IDs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Recipe name or keyword to search for.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recipe_details",
            "description": (
                "Fetch full details for a recipe by its TheMealDB ID, "
                "including the complete ingredients list."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "meal_id": {
                        "type": "string",
                        "description": "The numeric meal ID from search_recipes.",
                    }
                },
                "required": ["meal_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_random_recipe",
            "description": "Return a random recipe suggestion with full details.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_shopping_lists",
            "description": "List all Bring! shopping lists in the user's account.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_list_items",
            "description": "Return the items currently on the Bring! shopping list.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_item_to_bring",
            "description": (
                "Add a single ingredient or product to the Bring! shopping list."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {
                        "type": "string",
                        "description": "Name of the ingredient or product.",
                    },
                    "specification": {
                        "type": "string",
                        "description": "Optional quantity or brand detail, e.g. '500g'.",
                    },
                },
                "required": ["item_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_item_from_bring",
            "description": "Remove an item from the Bring! shopping list.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {
                        "type": "string",
                        "description": "Name of the item to remove.",
                    }
                },
                "required": ["item_name"],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------

def _dispatch(name: str, args: dict[str, Any]) -> str:
    """Call the named tool function and return a JSON-serialisable string."""
    try:
        if name == "get_weekly_menu":
            result = sheets_tool.get_weekly_menu(**_sheets_kwargs())
        elif name == "update_meal":
            result = sheets_tool.update_meal(**args, **_sheets_kwargs())
        elif name == "search_recipes":
            result = recipe_tool.search_recipes(args["query"])
        elif name == "get_recipe_details":
            result = recipe_tool.get_recipe_details(args["meal_id"])
        elif name == "get_random_recipe":
            result = recipe_tool.get_random_recipe()
        elif name == "get_shopping_lists":
            result = bring_tool.get_shopping_lists(**_bring_kwargs())
        elif name == "get_list_items":
            result = bring_tool.get_list_items(**_bring_kwargs())
        elif name == "add_item_to_bring":
            result = bring_tool.add_item(
                item_name=args["item_name"],
                specification=args.get("specification", ""),
                **_bring_kwargs(),
            )
        elif name == "remove_item_from_bring":
            result = bring_tool.remove_item(
                item_name=args["item_name"],
                **_bring_kwargs(),
            )
        else:
            result = f"Unknown tool: {name}"
    except Exception as exc:  # noqa: BLE001
        result = f"Tool '{name}' raised an error: {exc}"

    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a helpful meal-planning assistant.

You have access to tools that let you:
1. Read and update a weekly menu plan stored in a Google Sheet.
2. Search for recipes and get full ingredient lists via TheMealDB.
3. Add items to and manage the user's Bring! shopping list.

When the user asks you to plan meals, search for relevant recipes first,
then fill in the menu sheet for each requested day and meal type,
and finally add the required ingredients to Bring!.

Be concise and confirm each action you take.
"""


def run_agent(user_message: str, model: str = "") -> None:
    """Run the agent for a single user message."""
    client = OpenAI(api_key=_env("OPENAI_API_KEY"))
    model = model or _env("OPENAI_MODEL", "gpt-4o")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    print(f"\nUser: {user_message}\n")

    while True:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        choice = response.choices[0]
        message = choice.message

        # Append the assistant turn (may contain tool_calls)
        messages.append(message)

        if choice.finish_reason == "tool_calls":
            for tool_call in message.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                print(f"[tool] {name}({json.dumps(args, ensure_ascii=False)})")
                result = _dispatch(name, args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )
        else:
            # Final answer
            print(f"\nAssistant: {message.content}\n")
            break


def run_interactive() -> None:
    """Start an interactive REPL session with the agent."""
    print("Menu Planner Agent")
    print("Type your request and press Enter. Use Ctrl+C or Ctrl+D to quit.\n")
    model = _env("OPENAI_MODEL", "gpt-4o")
    client = OpenAI(api_key=_env("OPENAI_API_KEY"))

    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        while True:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
            choice = response.choices[0]
            message = choice.message
            messages.append(message)

            if choice.finish_reason == "tool_calls":
                for tool_call in message.tool_calls:
                    name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    print(f"  [tool] {name}({json.dumps(args, ensure_ascii=False)})")
                    result = _dispatch(name, args)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result,
                        }
                    )
            else:
                print(f"\nAssistant: {message.content}\n")
                break


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_agent(" ".join(sys.argv[1:]))
    else:
        run_interactive()
