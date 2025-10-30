# AI Lead Generation Agent

A Streamlit app that finds potential leads from Quora posts using Firecrawl and formats them into a simple, downloadable dataset.

This fork removes Google Sheets/Composio integrations and focuses on CSV/JSON exports. You can also save the CSV to disk directly from the app.

## Features
- Extracts Quora links relevant to your product/service using Firecrawl
- Scrapes and structures user interactions (username, bio, post type, timestamp, upvotes, links)
- Previews results in a table
- Download as CSV/JSON
- Save CSV to disk (configurable filename in sidebar)

## Tech Stack
- Streamlit
- Firecrawl (API)
- Gemini (Google Generative AI)
- Python 3.10+

## Project Structure
```
Lead_Generation_agent-main/
├─ app.py                           # Streamlit app entry point (flattened)
├─ requirements.txt                  # Dependencies for entire project
├─ README.md
└─ Notes.txt                         # (Optional) Misc notes
```
Note: The app entry has been flattened to `app.py` at the repo root for simpler usage.

## Setup
1. Create and activate a Python virtual environment (recommended).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Required API Keys
- Firecrawl API Key
  - Get from: https://www.firecrawl.dev/app/api-keys
- Gemini API Key
  - Get from: https://aistudio.google.com/app/apikey

You will paste these keys into the Streamlit sidebar when running the app.

## Run the App
From the repo root:
```bash
streamlit run app.py
```

## Saving CSV to Disk
- In the sidebar, set "Output CSV filename". Examples:
  - `leads.csv` (saves to current working directory)
  - `C:\\Users\\you\\Documents\\leads.csv` (absolute Windows path)
- After generation, the app will write the CSV to that file and display a success message.

## Notes on Removed Integrations
- Google Sheets via Composio and Service Account integrations were removed to simplify setup.
- Exports are CSV/JSON only.

## Development
- Python version: 3.10+ recommended
- Lint/format: optional (e.g., black, ruff)

## License
MIT (see LICENSE)
