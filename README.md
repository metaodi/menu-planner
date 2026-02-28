# menu-planner

An AI agent that helps you fill out your weekly menu plan in a Google Sheet,
find new recipes, and add ingredients to your [Bring!](https://www.getbring.com/)
shopping list.

## Features

- **Weekly menu planning** – reads and writes a Google Sheet with a
  Monday–Sunday × Breakfast/Lunch/Dinner grid.
- **Recipe search** – searches [TheMealDB](https://www.themealdb.com/) (free,
  no API key) for recipes by name or keyword, and retrieves full ingredient
  lists.
- **Bring! shopping list** – adds or removes items in your Bring! account via
  the unofficial Bring API.
- **Conversational AI agent** – powered by OpenAI GPT-4o; understands natural
  language requests such as:
  - *"Plan dinners for this week with Italian recipes"*
  - *"Add all ingredients for Monday's dinner to Bring"*
  - *"What's a good vegetarian lunch I can make on Wednesday?"*

## Project structure

```
menu-planner/
├── agent.py               # Main entry point – interactive or one-shot mode
├── tools/
│   ├── __init__.py
│   ├── google_sheets.py   # Google Sheets read/write
│   ├── recipes.py         # TheMealDB recipe search
│   └── bring.py           # Bring! shopping list
├── tests.py               # Unit tests (no live credentials needed)
├── requirements.txt
└── .env.example           # Copy to .env and fill in your credentials
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | Your [OpenAI API key](https://platform.openai.com/api-keys) |
| `OPENAI_MODEL` | Model to use (default: `gpt-4o`) |
| `GOOGLE_SPREADSHEET_ID` | ID from the Google Sheet URL |
| `GOOGLE_CREDENTIALS_FILE` | Path to your service account JSON file |
| `GOOGLE_WORKSHEET_NAME` | Sheet tab name (default: `Menu`) |
| `BRING_EMAIL` | E-mail for your Bring! account |
| `BRING_PASSWORD` | Password for your Bring! account |
| `BRING_LIST_NAME` | Name of the Bring! list to use (uses first list if empty) |

### 3. Set up Google Sheets access

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project and enable the **Google Sheets API**.
3. Create a **Service Account** and download the JSON credentials file.
4. Set `GOOGLE_CREDENTIALS_FILE` in `.env` to the path of that file.
5. Share your Google Sheet with the service account's e-mail address
   (give it *Editor* access).

The sheet should have (or will be auto-created with) the following layout:

| Day | Breakfast | Lunch | Dinner |
|---|---|---|---|
| Monday | | | |
| Tuesday | | | |
| … | | | |
| Sunday | | | |

## Usage

### Interactive mode

```bash
python agent.py
```

Type requests in plain English:

```
You: Plan dinners for this week with Italian recipes
You: Add all ingredients for Monday's dinner to my Bring list
You: What's a quick breakfast for Saturday?
```

### One-shot mode

```bash
python agent.py "Suggest a healthy dinner for Thursday and add it to the menu"
```

## Running tests

```bash
python -m pytest tests.py -v
```

All tests use mocks – no live API credentials are required.
