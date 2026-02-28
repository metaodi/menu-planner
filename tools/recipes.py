"""Recipe search tool using the free TheMealDB API.

No API key is required for the public endpoints.
https://www.themealdb.com/api.php
"""

import logging
from typing import Optional

import requests

_LOGGER = logging.getLogger(__name__)

_BASE_URL = "https://www.themealdb.com/api/json/v1/1"


def search_recipes(query: str) -> list[dict]:
    """Search for recipes by name.

    Parameters
    ----------
    query:
        A meal name or keyword to search for.

    Returns
    -------
    list[dict]
        A list of matching recipes, each with ``id``, ``name``,
        ``category``, ``area``, and ``thumbnail`` keys.
        Returns an empty list when nothing is found.
    """
    url = f"{_BASE_URL}/search.php"
    try:
        resp = requests.get(url, params={"s": query}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        _LOGGER.error("Recipe search failed: %s", exc)
        return []

    meals = data.get("meals") or []
    return [
        {
            "id": meal["idMeal"],
            "name": meal["strMeal"],
            "category": meal.get("strCategory", ""),
            "area": meal.get("strArea", ""),
            "thumbnail": meal.get("strMealThumb", ""),
        }
        for meal in meals
    ]


def get_recipe_details(meal_id: str) -> Optional[dict]:
    """Fetch full details for a recipe, including ingredients.

    Parameters
    ----------
    meal_id:
        The numeric ID returned by :func:`search_recipes`.

    Returns
    -------
    dict or None
        A dict with ``name``, ``category``, ``area``, ``instructions``,
        ``ingredients`` (list of ``{"name": ..., "measure": ...}``),
        and ``source`` keys, or ``None`` when not found.
    """
    url = f"{_BASE_URL}/lookup.php"
    try:
        resp = requests.get(url, params={"i": meal_id}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        _LOGGER.error("Recipe details fetch failed for id=%s: %s", meal_id, exc)
        return None

    meals = data.get("meals")
    if not meals:
        return None

    meal = meals[0]

    # Collect ingredients and measures (TheMealDB uses up to 20 numbered pairs)
    ingredients = []
    for i in range(1, 21):
        name = (meal.get(f"strIngredient{i}") or "").strip()
        measure = (meal.get(f"strMeasure{i}") or "").strip()
        if name:
            ingredients.append({"name": name, "measure": measure})

    return {
        "id": meal["idMeal"],
        "name": meal["strMeal"],
        "category": meal.get("strCategory", ""),
        "area": meal.get("strArea", ""),
        "instructions": meal.get("strInstructions", ""),
        "ingredients": ingredients,
        "source": meal.get("strSource", ""),
        "thumbnail": meal.get("strMealThumb", ""),
    }


def get_random_recipe() -> Optional[dict]:
    """Return a random recipe from TheMealDB.

    Returns
    -------
    dict or None
        Same structure as :func:`get_recipe_details`, or ``None`` on failure.
    """
    url = f"{_BASE_URL}/random.php"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        _LOGGER.error("Random recipe fetch failed: %s", exc)
        return None

    meals = data.get("meals")
    if not meals:
        return None

    meal = meals[0]
    return get_recipe_details(meal["idMeal"])
