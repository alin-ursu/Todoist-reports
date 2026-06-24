"""Todoist API client and Markdown report generation."""
import os
from collections import defaultdict
from datetime import date, datetime, time, timedelta, tzinfo
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
API_BASE = "https://api.todoist.com/api/v1"
DISPLAY_DATE_FORMAT = "%d-%m-%Y"
DISPLAY_DATE_FORMAT_HELP = "dd-mm-yyyy"
DISPLAY_DATETIME_FORMAT = "%d-%m-%Y %H:%M"


def format_display_date(value: date) -> str:
    """Format a calendar date for report titles, filenames, and timestamps."""
    return value.strftime(DISPLAY_DATE_FORMAT)


def get_timezone() -> tzinfo:
    """Return TZ from .env, or fall back to the system timezone."""
    tz_name = os.getenv("TZ")
    if tz_name:
        return ZoneInfo(tz_name)
    return datetime.now().astimezone().tzinfo or ZoneInfo("UTC")


_WEEKDAY_NAMES = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def get_week_start_weekday() -> int:
    """Return the weekday index (Monday=0) that starts a calendar week."""
    load_dotenv(PROJECT_ROOT / ".env")
    value = (os.getenv("WEEK_START_DAY") or "monday").strip().lower()
    if value not in _WEEKDAY_NAMES:
        valid = ", ".join(_WEEKDAY_NAMES)
        raise ValueError(
            f"Invalid WEEK_START_DAY {value!r}. Choose from: {valid}."
        )
    return _WEEKDAY_NAMES.index(value)


def get_api_token() -> str:
    """Load and return the Todoist API token from .env."""
    load_dotenv(PROJECT_ROOT / ".env")
    token = os.getenv("TODOIST_API_TOKEN") or os.getenv("TODOIST_TOKEN")
    if not token:
        raise ValueError(
            "Missing Todoist API token. Set TODOIST_API_TOKEN in your .env file."
        )
    return token


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def fetch_projects(token: str) -> dict[str, str]:
    """Return a mapping of project ID to project name."""
    params: dict[str, str | int] = {"limit": 200}
    project_names: dict[str, str] = {}

    # Paginate until all projects are fetched
    while True:
        response = requests.get(
            f"{API_BASE}/projects",
            headers=_auth_headers(token),
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        for project in data.get("results", []):
            project_names[project["id"]] = project["name"]

        next_cursor = data.get("next_cursor")
        if not next_cursor:
            break
        params["cursor"] = next_cursor

    return project_names


def fetch_completed_tasks(
    token: str,
    since: datetime,
    until: datetime,
) -> list[dict]:
    """Fetch all tasks completed between since (inclusive) and until (exclusive)."""
    params: dict[str, str | int] = {
        "since": since.isoformat(),
        "until": until.isoformat(),
        "limit": 200,
    }
    items: list[dict] = []

    # Todoist returns results in pages; follow next_cursor until exhausted
    while True:
        response = requests.get(
            f"{API_BASE}/tasks/completed/by_completion_date",
            headers=_auth_headers(token),
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        items.extend(data.get("items", []))

        next_cursor = data.get("next_cursor")
        if not next_cursor:
            break
        params["cursor"] = next_cursor

    return items


def fetch_task(token: str, task_id: str) -> dict | None:
    """Fetch a single active task by ID. Returns None if not found."""
    response = requests.get(
        f"{API_BASE}/tasks/{task_id}",
        headers=_auth_headers(token),
        timeout=30,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def is_subtask(task: dict) -> bool:
    """Return True when the task is a subtask rather than a top-level task."""
    parent_id = task.get("parent_id")
    task_id = task.get("id")
    return bool(parent_id) and parent_id != task_id


def resolve_parent_titles(token: str, tasks: list[dict]) -> dict[str, str]:
    """Fetch titles for incomplete parents referenced by completed subtasks."""
    completed_by_id = {task["id"]: task for task in tasks}
    parent_titles: dict[str, str] = {}

    missing_parent_ids = {
        task["parent_id"]
        for task in tasks
        if is_subtask(task) and task["parent_id"] not in completed_by_id
    }

    for parent_id in missing_parent_ids:
        active_parent = fetch_task(token, parent_id)
        if active_parent:
            parent_titles[parent_id] = active_parent.get("content", f"Parent task {parent_id}")
        else:
            parent_titles[parent_id] = f"Parent task {parent_id}"

    return parent_titles


def day_bounds(target_day: date, tz: tzinfo) -> tuple[datetime, datetime]:
    """Return (since, until) datetimes spanning one calendar day in the given timezone."""
    start = datetime.combine(target_day, time.min, tzinfo=tz)
    end = start + timedelta(days=1)
    return start, end


def last_week_bounds(today: date, tz: tzinfo) -> tuple[datetime, datetime, date, date]:
    """Return API bounds and display dates for the previous calendar week.

    The week start day is configured via WEEK_START_DAY in .env (default: monday).
    """
    week_start_weekday = get_week_start_weekday()
    days_since_start = (today.weekday() - week_start_weekday) % 7
    this_week_start = today - timedelta(days=days_since_start)
    last_week_start = this_week_start - timedelta(days=7)
    last_week_end = this_week_start - timedelta(days=1)

    since = datetime.combine(last_week_start, time.min, tzinfo=tz)
    # until is exclusive: current week's start 00:00 includes all of last week's final day
    until = datetime.combine(this_week_start, time.min, tzinfo=tz)
    return since, until, last_week_start, last_week_end


def format_completed_at(value: str, tz: tzinfo) -> str:
    """Convert an API timestamp to a local time string for the report."""
    completed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return completed.astimezone(tz).strftime(DISPLAY_DATETIME_FORMAT)


def _format_task_line(task: dict, tz: tzinfo, indent: int = 0) -> str:
    prefix = "  " * indent
    completed_at = format_completed_at(task["completed_at"], tz)
    content = task.get("content", "(no title)")
    return f"{prefix}- [{completed_at}] {content}"


def _completion_sort_key(value: str) -> str:
    return value or ""


def group_tasks_for_report(
    project_tasks: list[dict],
    parent_titles: dict[str, str],
) -> list[dict[str, Any]]:
    """Group completed project tasks into standalone items and parent/subtask groups."""
    completed_by_id = {task["id"]: task for task in project_tasks}
    subtasks = [task for task in project_tasks if is_subtask(task)]
    top_level = [task for task in project_tasks if not is_subtask(task)]

    children_by_parent: dict[str, list[dict]] = defaultdict(list)
    for subtask in subtasks:
        children_by_parent[subtask["parent_id"]].append(subtask)

    parent_ids_with_children = set(children_by_parent)
    groups: list[dict[str, Any]] = []

    for task in top_level:
        if task["id"] not in parent_ids_with_children:
            groups.append({"type": "standalone", "task": task})

    for parent_id in parent_ids_with_children:
        parent_task = completed_by_id.get(parent_id)
        children = sorted(
            children_by_parent[parent_id],
            key=lambda item: _completion_sort_key(item.get("completed_at", "")),
        )

        if parent_task:
            title = parent_task.get("content", f"Parent task {parent_id}")
        else:
            title = parent_titles.get(parent_id, f"Parent task {parent_id}")

        groups.append(
            {
                "type": "parent",
                "parent_id": parent_id,
                "title": title,
                "is_open": parent_task is None,
                "parent_task": parent_task,
                "children": children,
            }
        )

    def group_sort_key(group: dict[str, Any]) -> str:
        if group["type"] == "standalone":
            return _completion_sort_key(group["task"].get("completed_at", ""))

        completion_times = [
            _completion_sort_key(child.get("completed_at", "")) for child in group["children"]
        ]
        if group["parent_task"]:
            completion_times.append(
                _completion_sort_key(group["parent_task"].get("completed_at", ""))
            )
        return min(completion_times)

    standalone_groups = sorted(
        [group for group in groups if group["type"] == "standalone"],
        key=group_sort_key,
    )
    parent_groups = sorted(
        [group for group in groups if group["type"] == "parent"],
        key=group_sort_key,
    )
    return standalone_groups + parent_groups


def _render_project_groups(groups: list[dict[str, Any]], tz: tzinfo) -> list[str]:
    lines: list[str] = []

    for group in groups:
        if group["type"] == "standalone":
            lines.append(_format_task_line(group["task"], tz))
            continue

        heading = f"### {group['title']}"
        if group["is_open"]:
            heading += " (open)"
        lines.append(heading)
        lines.append("")

        child_indent = 0 if group["is_open"] else 1
        if group["parent_task"]:
            lines.append(_format_task_line(group["parent_task"], tz))

        for child in group["children"]:
            lines.append(_format_task_line(child, tz, indent=child_indent))

        lines.append("")

    return lines


def build_report(
    title: str,
    tasks: list[dict],
    project_names: dict[str, str],
    tz: tzinfo,
    parent_titles: dict[str, str] | None = None,
) -> str:
    """Format tasks into a Markdown report grouped by project and parent task."""
    lines = [f"# {title}", ""]

    if not tasks:
        lines.append("No completed tasks found for this period.")
        return "\n".join(lines)

    lines.append(f"**Total completed:** {len(tasks)}")
    lines.append("")

    parent_titles = parent_titles or {}
    tasks_by_project: dict[str, list[dict]] = {}
    for task in tasks:
        project_id = task.get("project_id", "unknown")
        project_name = project_names.get(project_id, f"Project {project_id}")
        tasks_by_project.setdefault(project_name, []).append(task)

    for project_name in sorted(tasks_by_project):
        lines.append(f"## {project_name}")
        lines.append("")
        groups = group_tasks_for_report(tasks_by_project[project_name], parent_titles)
        project_lines = _render_project_groups(groups, tz)
        if project_lines and project_lines[-1] == "":
            project_lines = project_lines[:-1]
        lines.extend(project_lines)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def save_report(filename: str, content: str) -> Path:
    """Write report content to the reports/ directory."""
    REPORTS_DIR.mkdir(exist_ok=True)
    output_path = REPORTS_DIR / filename
    output_path.write_text(content, encoding="utf-8")
    return output_path


def generate_report(title: str, since: datetime, until: datetime, filename: str) -> Path:
    """Fetch data from Todoist, build the report, print it, and save to disk."""
    token = get_api_token()
    tz = get_timezone()
    project_names = fetch_projects(token)
    tasks = fetch_completed_tasks(token, since, until)
    parent_titles = resolve_parent_titles(token, tasks)
    report = build_report(title, tasks, project_names, tz, parent_titles)
    output_path = save_report(filename, report)
    print(report)
    print(f"\nReport saved to: {output_path}")
    return output_path
