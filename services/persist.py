"""CSV persistence layer for telemetry runs with a stable schema contract.

This module is responsible for writing and reading run telemetry in
``data/runs.csv``. The header order defined in :data:`CSV_HEADERS` must remain
stable because external analytics tooling relies on that schema.
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from agents.models import RunRecord, Session

CSV_PATH = Path("data/runs.csv")
SESSIONS_DIR = Path("data/sessions")
CSV_HEADERS = [
    "ts",
    "agent_name",
    "model",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "latency_ms",
    "cost_usd",
    "experiment_id",
    "task_label",
    "run_notes",
    "streaming",
    "model_list_source",
    "tool_web_enabled",
    "web_status",
    "aborted",
]

_INT_FIELDS = {"prompt_tokens", "completion_tokens", "total_tokens", "latency_ms"}
_FLOAT_FIELDS = {"cost_usd"}
_BOOL_FIELDS = {"streaming", "tool_web_enabled", "aborted"}


def init_csv() -> None:
    """Initialize CSV file with headers if it doesn't exist"""

    if CSV_PATH.exists():
        return

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with CSV_PATH.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_HEADERS)
            writer.writeheader()
    except OSError as exc:  # pragma: no cover - filesystem failure paths
        raise RuntimeError(f"Failed to initialize CSV at {CSV_PATH}: {exc}") from exc


def append_run(record: RunRecord) -> None:
    """Append a run record to the CSV file"""

    init_csv()
    row = record.model_dump()
    row["ts"] = record.ts.isoformat()

    serialised_row = {header: row.get(header, "") for header in CSV_HEADERS}

    try:
        with CSV_PATH.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_HEADERS)
            writer.writerow(serialised_row)
    except OSError as exc:  # pragma: no cover - filesystem failure paths
        raise RuntimeError(f"Failed to append run record: {exc}") from exc


def _coerce_bool(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _coerce_int(value: Any) -> int:
    if value in ("", None):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _coerce_float(value: Any) -> float:
    if value in ("", None):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def load_recent_runs(limit: int = 10) -> list[RunRecord]:
    """Load the N most recent runs from CSV"""

    if not CSV_PATH.exists():
        return []

    records: list[RunRecord] = []
    try:
        with CSV_PATH.open("r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    parsed = _parse_row(row)
                except ValueError:
                    # Skip rows that cannot be parsed into a valid RunRecord
                    continue
                records.append(RunRecord(**parsed))
    except OSError as exc:  # pragma: no cover - filesystem failure paths
        raise RuntimeError(f"Failed to read CSV at {CSV_PATH}: {exc}") from exc

    return records[-limit:]


def _parse_row(row: dict[str, Any]) -> dict[str, Any]:
    parsed: dict[str, Any] = {key: row.get(key, "") for key in CSV_HEADERS}

    ts_value = parsed.get("ts", "")
    if ts_value in (None, ""):
        raise ValueError("Missing timestamp in CSV row")
    try:
        parsed["ts"] = datetime.fromisoformat(ts_value)
    except ValueError as exc:
        raise ValueError("Invalid timestamp format") from exc

    for field in _INT_FIELDS:
        parsed[field] = _coerce_int(parsed.get(field))

    for field in _FLOAT_FIELDS:
        parsed[field] = _coerce_float(parsed.get(field))

    for field in _BOOL_FIELDS:
        parsed[field] = _coerce_bool(parsed.get(field))

    # Normalise optional string fields to empty string when missing.
    for field in {"experiment_id", "task_label", "run_notes", "model_list_source", "web_status", "agent_name", "model"}:
        parsed[field] = (parsed.get(field) or "").strip()

    return parsed


def save_session(session: Session) -> Path:
    """Save a session to disk with unique ID-based filename."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    session_path = SESSIONS_DIR / f"{session.id}.json"

    try:
        with session_path.open("w", encoding="utf-8") as file:
            import json
            json.dump(session.model_dump(), file, indent=2, default=str)
    except OSError as exc:
        raise RuntimeError(f"Failed to save session to {session_path}: {exc}") from exc

    return session_path


def load_session(session_path: Path) -> Session:
    """Load a session from disk by path."""
    try:
        with session_path.open("r", encoding="utf-8") as file:
            import json
            data = json.load(file)
    except OSError as exc:
        raise RuntimeError(f"Failed to load session from {session_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in session file {session_path}: {exc}") from exc

    return dict_to_session(data)


def list_sessions() -> list[tuple[str, Path]]:
    """List all saved sessions with their paths, sorted by creation time."""
    if not SESSIONS_DIR.exists():
        return []

    sessions = []
    try:
        for session_file in SESSIONS_DIR.glob("*.json"):
            try:
                session = load_session(session_file)
                sessions.append((session.notes or f"Session {session.id[:8]}", session_file))
            except Exception:
                # Skip corrupted session files
                continue
    except OSError:
        return []

    # Sort by creation time (newest first)
    sessions.sort(key=lambda x: load_session(x[1]).created_at, reverse=True)
    return sessions


def session_to_dict(session: Session) -> dict:
    """Convert Session object to dictionary for JSON serialization."""
    return session.model_dump()


def dict_to_session(data: dict) -> Session:
    """Convert dictionary to Session object, handling datetime parsing."""
    # Handle datetime parsing for created_at
    if isinstance(data.get("created_at"), str):
        from datetime import datetime
        data["created_at"] = datetime.fromisoformat(data["created_at"])

    return Session(**data)


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    record = RunRecord(
        ts=datetime.now(),
        agent_name="TestAgent",
        model="openai/gpt-3.5-turbo",
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
        latency_ms=1500,
        cost_usd=0.001,
        streaming=True,
        model_list_source="fallback",
    )

    init_csv()
    append_run(record)
    print(f"✅ Record written to {CSV_PATH}")

    recent = load_recent_runs(limit=5)
    print(f"✅ Loaded {len(recent)} recent runs")

    if CSV_PATH.exists():
        print(f"✅ CSV exists at: {CSV_PATH.absolute()}")
