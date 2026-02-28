"""Bring shopping list integration.

Uses the python-bring-api library to interact with the Bring! app.
"""

import logging
from typing import Optional

from python_bring_api.bring import Bring
from python_bring_api.exceptions import BringAuthException, BringRequestException

_LOGGER = logging.getLogger(__name__)


def _get_client(email: str, password: str) -> Bring:
    """Authenticate and return a Bring client."""
    client = Bring(email, password)
    client.login()
    return client


def _find_list_uuid(client: Bring, list_name: Optional[str] = None) -> Optional[str]:
    """Return the UUID of the named list, or the first list if no name given."""
    response = client.loadLists()
    lists = response.get("lists", [])
    if not lists:
        return None
    if list_name:
        for lst in lists:
            if lst["name"].lower() == list_name.lower():
                return lst["listUuid"]
        _LOGGER.warning("List '%s' not found; using first list.", list_name)
    return lists[0]["listUuid"]


def get_shopping_lists(email: str, password: str) -> list[dict]:
    """Return all Bring shopping lists for this account.

    Parameters
    ----------
    email:
        Bring account e-mail.
    password:
        Bring account password.

    Returns
    -------
    list[dict]
        Each dict has ``listUuid``, ``name``, and ``theme`` keys.
    """
    try:
        client = _get_client(email, password)
        response = client.loadLists()
        return response.get("lists", [])
    except (BringAuthException, BringRequestException) as exc:
        _LOGGER.error("Failed to load Bring lists: %s", exc)
        return []


def get_list_items(
    email: str,
    password: str,
    list_name: Optional[str] = None,
) -> list[dict]:
    """Return the current items on a Bring shopping list.

    Parameters
    ----------
    email:
        Bring account e-mail.
    password:
        Bring account password.
    list_name:
        Name of the list to query. Uses the first list when omitted.

    Returns
    -------
    list[dict]
        Each dict has ``name`` and ``specification`` keys.
    """
    try:
        client = _get_client(email, password)
        list_uuid = _find_list_uuid(client, list_name)
        if not list_uuid:
            return []
        response = client.getItems(list_uuid)
        return response.get("purchase", [])
    except (BringAuthException, BringRequestException) as exc:
        _LOGGER.error("Failed to get Bring list items: %s", exc)
        return []


def add_item(
    item_name: str,
    specification: str = "",
    email: str = "",
    password: str = "",
    list_name: Optional[str] = None,
) -> str:
    """Add an item to a Bring shopping list.

    Parameters
    ----------
    item_name:
        Name of the ingredient or product to add.
    specification:
        Optional detail such as quantity or brand (e.g. ``"2 kg"``).
    email:
        Bring account e-mail.
    password:
        Bring account password.
    list_name:
        Name of the target list. Uses the first list when omitted.

    Returns
    -------
    str
        A human-readable confirmation or error message.
    """
    try:
        client = _get_client(email, password)
        list_uuid = _find_list_uuid(client, list_name)
        if not list_uuid:
            return "No shopping list found in your Bring account."
        client.saveItem(list_uuid, item_name, specification)
        msg = f"Added '{item_name}'"
        if specification:
            msg += f" ({specification})"
        msg += " to your Bring shopping list."
        _LOGGER.info(msg)
        return msg
    except (BringAuthException, BringRequestException) as exc:
        _LOGGER.error("Failed to add item to Bring: %s", exc)
        return f"Failed to add '{item_name}' to Bring: {exc}"


def remove_item(
    item_name: str,
    email: str = "",
    password: str = "",
    list_name: Optional[str] = None,
) -> str:
    """Remove an item from a Bring shopping list.

    Parameters
    ----------
    item_name:
        Name of the item to remove.
    email:
        Bring account e-mail.
    password:
        Bring account password.
    list_name:
        Name of the target list. Uses the first list when omitted.

    Returns
    -------
    str
        A human-readable confirmation or error message.
    """
    try:
        client = _get_client(email, password)
        list_uuid = _find_list_uuid(client, list_name)
        if not list_uuid:
            return "No shopping list found in your Bring account."
        client.removeItem(list_uuid, item_name)
        msg = f"Removed '{item_name}' from your Bring shopping list."
        _LOGGER.info(msg)
        return msg
    except (BringAuthException, BringRequestException) as exc:
        _LOGGER.error("Failed to remove item from Bring: %s", exc)
        return f"Failed to remove '{item_name}' from Bring: {exc}"
