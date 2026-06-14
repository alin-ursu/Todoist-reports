# Todoist Reports

Python scripts that fetch your completed tasks from Todoist and generate Markdown reports grouped by project.

Useful when you want a quick answer to: *"What did I actually finish today, yesterday, or last week?"*

## Features

- Report completed tasks for **today**, **yesterday**, or the **previous calendar week** (Monday–Sunday)
- Group tasks by project with human-readable names
- Nest completed subtasks under their parent task, even when the parent is still open
- Show completion timestamps in your local timezone using **dd-mm-yyyy** dates
- Print reports to the terminal and save them as Markdown files
- Keep API credentials out of source code via `.env`

## Requirements

- Python 3.9+
- A [Todoist API token](https://todoist.com/prefs/integrations)

## Quick start

1. Clone the repository and enter the project directory.

2. Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

3. Create your environment file:

```bash
cp .env.example .env
```

4. Add your Todoist API token to `.env`:

```
TODOIST_API_TOKEN=your_todoist_api_token_here
```

5. Run a report from the project root:

```bash
python scripts/report.py --period yesterday
```

## Usage

Use the unified CLI with a `--period` flag, or pass a custom date range with `--from` and `--to` in **dd-mm-yyyy** format:

| Period | Command | Example output file |
|--------|---------|---------------------|
| `today` | `python scripts/report.py --period today` | `reports/today_06-06-2026.md` |
| `yesterday` | `python scripts/report.py --period yesterday` | `reports/yesterday_05-06-2026.md` |
| `last-week` | `python scripts/report.py --period last-week` | `reports/last_week_25-05-2026_to_31-05-2026.md` |
| custom range | `python scripts/report.py --from 01-05-2026 --to 31-05-2026` | `reports/custom_01-05-2026_to_31-05-2026.md` |

```bash
python scripts/report.py --period today
python scripts/report.py --period yesterday
python scripts/report.py -p last-week
python scripts/report.py --from 01-05-2026 --to 31-05-2026
python scripts/report.py --help
```

Custom ranges are inclusive of both start and end dates. You cannot combine `--period` with `--from` / `--to`.

Each command prints the report to the terminal and saves a Markdown file in the `reports/` directory.

The older single-purpose scripts (`report_today.py`, `report_yesterday.py`, `report_last_week.py`) still work and call the same logic.

## Configuration

Environment variables are loaded from `.env` in the project root.

| Variable | Required | Description |
|----------|----------|-------------|
| `TODOIST_API_TOKEN` | Yes | Your Todoist API token. `TODOIST_TOKEN` is also accepted as an alias. |
| `TZ` | No | Timezone for date boundaries and displayed timestamps (e.g. `America/New_York`). Defaults to your system timezone. |

**Getting your API token:** open [Todoist → Settings → Integrations](https://todoist.com/prefs/integrations), find the API token section, and copy your token into `.env`.

Never commit `.env` to version control. It is listed in `.gitignore`.

## Report format

Reports are grouped by project. Completed subtasks appear under a `###` parent heading, even if the parent task itself was not completed in that period. All dates in report titles, filenames, and task timestamps use **dd-mm-yyyy**.

```markdown
# Todoist Report: Yesterday (05-06-2026)

**Total completed:** 4

## Work

- [05-06-2026 14:30] Finish quarterly review

### Plan party (open)

- [05-06-2026 11:06] Buy decorations
- [05-06-2026 11:07] Send invites

### Quarterly review

- [05-06-2026 09:00] Parent also completed today
  - [05-06-2026 09:15] Draft outline
```

- **Standalone tasks** appear as normal bullets with timestamps.
- **Open parents** (not completed in the period) are shown as `### Parent name (open)` with their completed subtasks listed below.
- **Completed parents** show the parent bullet first, with subtasks indented underneath.
- **`Total completed`** counts only completed tasks; open parents are labels, not counted.

If no tasks were completed in the selected period, the report will say:

```
No completed tasks found for this period.
```

## How it works

```
scripts/report.py
        │
        ▼
  todoist_reports/periods.py
        │
        ▼
  todoist_reports/client.py
        │
        ├── Load token from .env
        ├── Fetch project names (Todoist API)
        ├── Fetch completed tasks for date range (Todoist API)
        ├── Build Markdown report
        └── Save to reports/
```

1. `scripts/report.py` parses the `--period` flag and resolves the date range.
2. `run_period_report()` in `todoist_reports/periods.py` maps the period to `since`/`until` bounds.
3. `generate_report()` in `todoist_reports/client.py` loads your API token and timezone.
4. Incomplete parent titles are fetched from the active-tasks API when subtasks were completed.
5. The client fetches all projects to map project IDs to names.
6. The client fetches completed tasks within the date range, handling API pagination automatically.
7. Tasks are grouped by project and parent, formatted as Markdown, printed, and saved to `reports/`.

### Date ranges

- **Today / yesterday:** midnight to midnight in your configured timezone.
- **Last week:** the previous Monday 00:00 through the following Sunday 23:59 (implemented as Monday 00:00 of the current week as the exclusive end boundary).

The Todoist API treats the `until` parameter as **exclusive**, so a full day is requested as `since=2026-06-05T00:00:00` and `until=2026-06-06T00:00:00`.

### API endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/projects` | Resolve project IDs to names |
| `GET /api/v1/tasks/{task_id}` | Resolve incomplete parent task titles for subtask grouping |
| `GET /api/v1/tasks/completed/by_completion_date` | Fetch completed tasks in a date range |

Both endpoints use Bearer token authentication. See the [Todoist API documentation](https://developer.todoist.com/api/v1/) for details.

## Project structure

```
Todoist-reports/
├── todoist_reports/          # Core library
│   ├── __init__.py           # Public exports
│   └── client.py             # API client, date logic, report generation
├── scripts/                  # Runnable entry points
│   ├── _bootstrap.py         # Adds project root to Python path
│   ├── report.py             # Unified CLI (--period flag)
│   ├── report_today.py       # Convenience wrapper
│   ├── report_yesterday.py   # Convenience wrapper
│   └── report_last_week.py   # Convenience wrapper
├── reports/                  # Generated Markdown reports (gitignored)
├── .env.example              # Template for environment variables
├── requirements.txt
└── README.md
```

### Library API

The `todoist_reports` package exposes these functions for reuse or extension:

| Function | Description |
|----------|-------------|
| `get_timezone()` | Returns the configured or system timezone |
| `day_bounds(day, tz)` | Returns `(since, until)` datetimes for a single calendar day |
| `last_week_bounds(today, tz)` | Returns `(since, until, week_start, week_end)` for the previous week |
| `run_period_report(period)` | Generate a report for `today`, `yesterday`, or `last-week` |
| `resolve_period(period, tz)` | Return `(title, since, until, filename)` for a named period |
| `generate_report(title, since, until, filename)` | Fetches data, builds the report, saves and prints it |

## Troubleshooting

**`Missing Todoist API token`**
- Ensure `.env` exists in the project root (not inside `scripts/`).
- Check that `TODOIST_API_TOKEN` is set and has no extra quotes or spaces.

**`401 Unauthorized`**
- Your API token may be invalid or revoked. Generate a new one in Todoist settings.

**Empty report but tasks were completed**
- Verify your `TZ` setting matches when you completed the tasks.
- Remember that date ranges are timezone-aware; a task completed late at night may fall on a different day in UTC.

**`ModuleNotFoundError: No module named 'todoist_reports'`**
- Run scripts from the project root, not from inside `scripts/`.
- Ensure your virtual environment is activated and dependencies are installed.

## Development

### Dependencies

- [requests](https://pypi.org/project/requests/) — HTTP calls to the Todoist API
- [python-dotenv](https://pypi.org/project/python-dotenv/) — load environment variables from `.env`

### Adding a new report period

1. Add the period to `PERIODS` and handle it in `todoist_reports/periods.py`.
2. Export any new helpers from `todoist_reports/__init__.py` if needed.
3. The new period is automatically available via `python scripts/report.py --period <name>`.

### Planned improvements

- CSV export alongside Markdown
- Simple chart of tasks completed per day
- Automated weekly email report via cron or Task Scheduler

## License

This project is for personal use. Add a license file if you plan to share or open-source it.
