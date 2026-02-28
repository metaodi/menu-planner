"""Google Sheets integration for the menu planner agent.

Uses gspread with a Google service account to read and write
the weekly menu plan in a Google Spreadsheet.

Expected sheet layout:
  Row 1: header row  → Day | Breakfast | Lunch | Dinner
  Rows 2–8: one row per day (Monday – Sunday)
"""

import os
import logging
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

_LOGGER = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MEAL_TYPES = ["Breakfast", "Lunch", "Dinner"]


def _get_client(credentials_file: str) -> gspread.Client:
    """Return an authenticated gspread client."""
    creds = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_worksheet(
    spreadsheet_id: str,
    worksheet_name: str,
    credentials_file: str,
) -> gspread.Worksheet:
    """Return the target worksheet, creating it if it doesn't exist."""
    client = _get_client(credentials_file)
    spreadsheet = client.open_by_key(spreadsheet_id)
    try:
        ws = spreadsheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=worksheet_name, rows=9, cols=4)
        _initialise_worksheet(ws)
    return ws


def _initialise_worksheet(ws: gspread.Worksheet) -> None:
    """Write the header row and day labels into a blank worksheet."""
    header = ["Day"] + MEAL_TYPES
    ws.update("A1:D1", [header])
    day_column = [[day] for day in DAYS]
    ws.update("A2:A8", day_column)


def get_weekly_menu(
    spreadsheet_id: str,
    worksheet_name: str = "Menu",
    credentials_file: str = "credentials.json",
) -> dict:
    """Return the full weekly menu as a nested dict.

    Returns
    -------
    dict
        ``{"Monday": {"Breakfast": "...", "Lunch": "...", "Dinner": "..."}, ...}``
    """
    ws = _get_worksheet(spreadsheet_id, worksheet_name, credentials_file)
    rows = ws.get_all_values()

    if not rows:
        return {}

    header = rows[0]
    menu: dict = {}
    for row in rows[1:]:
        if not row:
            continue
        day = row[0]
        if day not in DAYS:
            continue
        menu[day] = {}
        for col_idx, meal_type in enumerate(MEAL_TYPES, start=1):
            try:
                col_header = header[col_idx] if col_idx < len(header) else meal_type
                meal_value = row[col_idx] if col_idx < len(row) else ""
                menu[day][col_header] = meal_value
            except IndexError:
                menu[day][meal_type] = ""
    return menu


def update_meal(
    day: str,
    meal_type: str,
    meal_name: str,
    spreadsheet_id: str,
    worksheet_name: str = "Menu",
    credentials_file: str = "credentials.json",
) -> str:
    """Write a single meal entry into the spreadsheet.

    Parameters
    ----------
    day:
        Day of the week, e.g. ``"Monday"``.
    meal_type:
        One of ``"Breakfast"``, ``"Lunch"``, or ``"Dinner"``.
    meal_name:
        The name of the meal to write.

    Returns
    -------
    str
        A human-readable confirmation message.
    """
    day_title = day.strip().title()
    meal_title = meal_type.strip().title()

    if day_title not in DAYS:
        return f"Unknown day '{day}'. Please use one of: {', '.join(DAYS)}."
    if meal_title not in MEAL_TYPES:
        return f"Unknown meal type '{meal_type}'. Please use one of: {', '.join(MEAL_TYPES)}."

    ws = _get_worksheet(spreadsheet_id, worksheet_name, credentials_file)
    header = ws.row_values(1)

    try:
        col_idx = header.index(meal_title) + 1  # 1-based
    except ValueError:
        return f"Column '{meal_title}' not found in the spreadsheet header."

    row_idx = DAYS.index(day_title) + 2  # +1 for header, +1 for 1-based index

    ws.update_cell(row_idx, col_idx, meal_name)
    _LOGGER.info("Updated %s %s → %s", day_title, meal_title, meal_name)
    return f"Updated {day_title} {meal_title} to '{meal_name}'."
