"""Tests for the menu planner tools.

These tests use unittest.mock to avoid requiring live credentials.
Run with:  python -m pytest tests.py -v
"""

import json
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Recipe tool tests
# ---------------------------------------------------------------------------


class TestSearchRecipes(unittest.TestCase):
    @patch("tools.recipes.requests.get")
    def test_returns_list_of_recipes(self, mock_get):
        mock_get.return_value.json.return_value = {
            "meals": [
                {
                    "idMeal": "52772",
                    "strMeal": "Teriyaki Chicken Casserole",
                    "strCategory": "Chicken",
                    "strArea": "Japanese",
                    "strMealThumb": "https://example.com/thumb.jpg",
                }
            ]
        }
        mock_get.return_value.raise_for_status = MagicMock()

        from tools.recipes import search_recipes

        results = search_recipes("teriyaki")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "52772")
        self.assertEqual(results[0]["name"], "Teriyaki Chicken Casserole")

    @patch("tools.recipes.requests.get")
    def test_returns_empty_list_when_no_meals(self, mock_get):
        mock_get.return_value.json.return_value = {"meals": None}
        mock_get.return_value.raise_for_status = MagicMock()

        from tools.recipes import search_recipes

        results = search_recipes("xyznotarecipe")
        self.assertEqual(results, [])

    @patch("tools.recipes.requests.get")
    def test_returns_empty_list_on_network_error(self, mock_get):
        import requests as req

        mock_get.side_effect = req.RequestException("timeout")

        from tools.recipes import search_recipes

        results = search_recipes("pasta")
        self.assertEqual(results, [])


class TestGetRecipeDetails(unittest.TestCase):
    def _meal_payload(self):
        meal = {
            "idMeal": "52772",
            "strMeal": "Teriyaki Chicken",
            "strCategory": "Chicken",
            "strArea": "Japanese",
            "strInstructions": "Cook it.",
            "strSource": "",
            "strMealThumb": "",
        }
        for i in range(1, 21):
            meal[f"strIngredient{i}"] = ""
            meal[f"strMeasure{i}"] = ""
        meal["strIngredient1"] = "Chicken"
        meal["strMeasure1"] = "500g"
        meal["strIngredient2"] = "Soy Sauce"
        meal["strMeasure2"] = "3 tbsp"
        return meal

    @patch("tools.recipes.requests.get")
    def test_returns_ingredients(self, mock_get):
        mock_get.return_value.json.return_value = {"meals": [self._meal_payload()]}
        mock_get.return_value.raise_for_status = MagicMock()

        from tools.recipes import get_recipe_details

        details = get_recipe_details("52772")
        self.assertIsNotNone(details)
        self.assertEqual(details["name"], "Teriyaki Chicken")
        self.assertEqual(len(details["ingredients"]), 2)
        self.assertEqual(details["ingredients"][0]["name"], "Chicken")
        self.assertEqual(details["ingredients"][0]["measure"], "500g")

    @patch("tools.recipes.requests.get")
    def test_returns_none_when_not_found(self, mock_get):
        mock_get.return_value.json.return_value = {"meals": None}
        mock_get.return_value.raise_for_status = MagicMock()

        from tools.recipes import get_recipe_details

        self.assertIsNone(get_recipe_details("99999"))


class TestGetRandomRecipe(unittest.TestCase):
    @patch("tools.recipes.get_recipe_details")
    @patch("tools.recipes.requests.get")
    def test_returns_recipe(self, mock_get, mock_details):
        mock_get.return_value.json.return_value = {
            "meals": [{"idMeal": "52772", "strMeal": "Teriyaki Chicken"}]
        }
        mock_get.return_value.raise_for_status = MagicMock()
        mock_details.return_value = {"id": "52772", "name": "Teriyaki Chicken"}

        from tools.recipes import get_random_recipe

        result = get_random_recipe()
        self.assertIsNotNone(result)
        mock_details.assert_called_once_with("52772")


# ---------------------------------------------------------------------------
# Bring tool tests
# ---------------------------------------------------------------------------


class TestBringTool(unittest.TestCase):
    def _mock_bring(self):
        mock = MagicMock()
        mock.loadLists.return_value = {
            "lists": [{"listUuid": "uuid-1", "name": "Weekly", "theme": ""}]
        }
        return mock

    @patch("tools.bring.Bring")
    def test_get_shopping_lists(self, MockBring):
        MockBring.return_value = self._mock_bring()

        from tools.bring import get_shopping_lists

        lists = get_shopping_lists("a@b.com", "pass")
        self.assertEqual(len(lists), 1)
        self.assertEqual(lists[0]["name"], "Weekly")

    @patch("tools.bring.Bring")
    def test_add_item_success(self, MockBring):
        mock_client = self._mock_bring()
        mock_client.saveItem.return_value = None
        MockBring.return_value = mock_client

        from tools.bring import add_item

        result = add_item("Milk", "1L", email="a@b.com", password="pass")
        self.assertIn("Milk", result)
        self.assertIn("1L", result)
        mock_client.saveItem.assert_called_once_with("uuid-1", "Milk", "1L")

    @patch("tools.bring.Bring")
    def test_add_item_finds_named_list(self, MockBring):
        mock_client = MagicMock()
        mock_client.loadLists.return_value = {
            "lists": [
                {"listUuid": "uuid-1", "name": "Groceries", "theme": ""},
                {"listUuid": "uuid-2", "name": "Weekly", "theme": ""},
            ]
        }
        mock_client.saveItem.return_value = None
        MockBring.return_value = mock_client

        from tools.bring import add_item

        add_item("Eggs", email="a@b.com", password="pass", list_name="Weekly")
        mock_client.saveItem.assert_called_once_with("uuid-2", "Eggs", "")

    @patch("tools.bring.Bring")
    def test_remove_item_success(self, MockBring):
        mock_client = self._mock_bring()
        mock_client.removeItem.return_value = None
        MockBring.return_value = mock_client

        from tools.bring import remove_item

        result = remove_item("Milk", email="a@b.com", password="pass")
        self.assertIn("Milk", result)
        mock_client.removeItem.assert_called_once_with("uuid-1", "Milk")

    @patch("tools.bring.Bring")
    def test_get_list_items(self, MockBring):
        mock_client = self._mock_bring()
        mock_client.getItems.return_value = {
            "purchase": [{"name": "Apples", "specification": ""}]
        }
        MockBring.return_value = mock_client

        from tools.bring import get_list_items

        items = get_list_items("a@b.com", "pass")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["name"], "Apples")

    @patch("tools.bring.Bring")
    def test_returns_empty_on_auth_error(self, MockBring):
        from python_bring_api.exceptions import BringAuthException

        MockBring.return_value.login.side_effect = BringAuthException("bad creds")

        from tools.bring import get_shopping_lists

        result = get_shopping_lists("bad@email.com", "wrong")
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# Google Sheets tool tests
# ---------------------------------------------------------------------------


class TestGoogleSheetsGetMenu(unittest.TestCase):
    @patch("tools.google_sheets._get_worksheet")
    def test_parses_full_menu(self, mock_ws):
        worksheet = MagicMock()
        worksheet.get_all_values.return_value = [
            ["Day", "Breakfast", "Lunch", "Dinner"],
            ["Monday", "Oats", "Salad", "Pasta"],
            ["Tuesday", "Toast", "Soup", "Steak"],
        ]
        mock_ws.return_value = worksheet

        from tools.google_sheets import get_weekly_menu

        menu = get_weekly_menu("sheet-id")
        self.assertIn("Monday", menu)
        self.assertEqual(menu["Monday"]["Dinner"], "Pasta")
        self.assertIn("Tuesday", menu)
        self.assertEqual(menu["Tuesday"]["Breakfast"], "Toast")

    @patch("tools.google_sheets._get_worksheet")
    def test_returns_empty_on_blank_sheet(self, mock_ws):
        worksheet = MagicMock()
        worksheet.get_all_values.return_value = []
        mock_ws.return_value = worksheet

        from tools.google_sheets import get_weekly_menu

        self.assertEqual(get_weekly_menu("sheet-id"), {})


class TestGoogleSheetsUpdateMeal(unittest.TestCase):
    @patch("tools.google_sheets._get_worksheet")
    def test_updates_cell(self, mock_ws):
        worksheet = MagicMock()
        worksheet.row_values.return_value = ["Day", "Breakfast", "Lunch", "Dinner"]
        mock_ws.return_value = worksheet

        from tools.google_sheets import update_meal

        result = update_meal("Monday", "Dinner", "Spaghetti", spreadsheet_id="id")
        self.assertIn("Spaghetti", result)
        # Monday is row 2, Dinner is column 4
        worksheet.update_cell.assert_called_once_with(2, 4, "Spaghetti")

    @patch("tools.google_sheets._get_worksheet")
    def test_rejects_invalid_day(self, mock_ws):
        from tools.google_sheets import update_meal

        result = update_meal("Funday", "Dinner", "Pizza", spreadsheet_id="id")
        self.assertIn("Unknown day", result)

    @patch("tools.google_sheets._get_worksheet")
    def test_rejects_invalid_meal_type(self, mock_ws):
        from tools.google_sheets import update_meal

        result = update_meal("Monday", "Snack", "Crackers", spreadsheet_id="id")
        self.assertIn("Unknown meal type", result)


if __name__ == "__main__":
    unittest.main()
