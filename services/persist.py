"""CSV persistence layer for telemetry runs with a stable schema contract.

This module is responsible for writing and reading run telemetry in
``data/runs.csv``. The header order defined in :data:`CSV_HEADERS` must remain
stable because external analytics tooling relies on that schema.
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime
from loguru import logger
from pathlib import Path
from typing import Any, cast, Literal

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


def append_run(record: RunRecord, correlation_id: str | None = None) -> None:
    """Append a run record to the CSV file"""

    logger_bound = logger.bind(correlation_id=correlation_id) if correlation_id else logger

    init_csv()
    row = record.model_dump()
    row["ts"] = record.ts.isoformat()

    serialised_row = {header: row.get(header, "") for header in CSV_HEADERS}

    try:
        with CSV_PATH.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_HEADERS)
            writer.writerow(serialised_row)
        logger_bound.info("Run record appended to CSV", extra={"record_id": str(record.ts)})
    except OSError as exc:  # pragma: no cover - filesystem failure paths
        logger_bound.error("Failed to append run record", extra={"error": str(exc)})
        raise RuntimeError(f"Failed to append run record: {exc}") from exc


def _coerce_int_robust(value: str) -> int:
    """
    Robust integer coercion with proper error handling.
    """
    if not value or value.strip() == "":
        return 0

    try:
        # Strip whitespace
        cleaned = value.strip()
        # Handle potential float strings
        if '.' in cleaned:
            return int(float(cleaned))
        return int(cleaned)
    except (ValueError, OverflowError):
        logger.warning(f"Failed to coerce '{value}' to int, defaulting to 0")
        return 0


def _coerce_float_robust(value: str) -> float:
    """
    Robust float coercion with proper error handling.
    """
    if not value or value.strip() == "":
        return 0.0

    try:
        cleaned = value.strip()
        return float(cleaned)
    except (ValueError, OverflowError):
        logger.warning(f"Failed to coerce '{value}' to float, defaulting to 0.0")
        return 0.0


def _coerce_bool_robust(value: str) -> bool:
    """
    Robust boolean coercion with comprehensive truthy/falsy handling.
    """
    if not value:
        return False

    cleaned = value.strip().lower()

    # Truthy values
    if cleaned in ('1', 'true', 'yes', 'y'):
        return True

    # Falsy values
    if cleaned in ('false', '0', 'no', 'off', 'disabled', '', 'n', 'f'):
        return False

    # Default to False for unrecognized values
    logger.warning(f"Unrecognized boolean value '{value}', defaulting to False")
    return False


# Backward compatibility aliases
def _coerce_bool(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return _coerce_bool_robust(value)
    return False


def _coerce_int(value: Any) -> int:
    if isinstance(value, str):
        return _coerce_int_robust(value)
    if value in ("", None):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _coerce_float(value: Any) -> float:
    if isinstance(value, str):
        return _coerce_float_robust(value)
    if value in ("", None):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def load_recent_runs(limit: int = 10) -> list[RunRecord]:
    """Load the N most recent runs from CSV with robust parsing"""

    if not CSV_PATH.exists():
        return []

    records: list[RunRecord] = []
    try:
        with CSV_PATH.open("r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Use robust parsing that handles errors gracefully
                record = _parse_row_robust(row)
                if record is not None:
                    records.append(record)
    except OSError as exc:  # pragma: no cover - filesystem failure paths
        raise RuntimeError(f"Failed to read CSV at {CSV_PATH}: {exc}") from exc

    return records[-limit:]


def _parse_row_robust(row: dict[str, str]) -> RunRecord | None:
    """
    Robust row parsing with comprehensive error handling.
    """
    try:
        # Required fields validation
        ts_str = row.get('ts', '').strip()
        if not ts_str:
            logger.warning("Missing timestamp in row, skipping")
            return None

        try:
            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except ValueError:
            logger.warning(f"Invalid timestamp format '{ts_str}', skipping")
            return None

        # Extract and coerce all fields
        agent_name = row.get('agent_name', '').strip()
        model = row.get('model', '').strip()

        # All numeric fields with robust coercion
        prompt_tokens = _coerce_int_robust(row.get('prompt_tokens', '0'))
        completion_tokens = _coerce_int_robust(row.get('completion_tokens', '0'))
        total_tokens = _coerce_int_robust(row.get('total_tokens', '0'))
        latency_ms = _coerce_int_robust(row.get('latency_ms', '0'))
        cost_usd = _coerce_float_robust(row.get('cost_usd', '0.0'))

        # String fields with defaults
        experiment_id = row.get('experiment_id', '').strip()
        task_label = row.get('task_label', '').strip()
        run_notes = row.get('run_notes', '').strip()
        model_list_source = row.get('model_list_source', 'unknown').strip()
        web_status = row.get('web_status', 'off').strip()

        # Boolean fields
        streaming = _coerce_bool_robust(row.get('streaming', 'false'))
        tool_web_enabled = _coerce_bool_robust(row.get('tool_web_enabled', 'false'))
        aborted = _coerce_bool_robust(row.get('aborted', 'false'))

        return RunRecord(
            ts=ts,
            agent_name=agent_name,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            experiment_id=experiment_id,
            task_label=task_label,
            run_notes=run_notes,
            streaming=streaming,
            model_list_source=cast(Literal["dynamic", "fallback"], model_list_source if model_list_source in ["dynamic", "fallback"] else "fallback"),
            tool_web_enabled=tool_web_enabled,
            web_status=cast(Literal["off", "ok", "blocked"], web_status if web_status in ["off", "ok", "blocked"] else "off"),
            aborted=aborted
        )

    except Exception as e:
        logger.error(f"Failed to parse row: {e}", extra={"row": row})
        return None


def _parse_row(row: dict[str, Any]) -> dict[str, Any]:
    """Legacy _parse_row for backward compatibility."""
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


def load_session(session_path: Path | str) -> Session:
    """Load a session from disk by path."""
    if isinstance(session_path, str):
        session_path = Path(session_path)
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
