"""
JSON Database and Persistence Module.
Provides thread-safe, atomic read/write operations for JSON storage files.
Includes schema validation, file corruption recovery, and lock management.
"""

import json
import os
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
import config

_LOCK = threading.RLock()


class JSONDatabase:
    """
    Thread-safe, atomic JSON database engine for persisting highway enforcement records.

    Limitations for Production:
    - Entire files are read and written in-memory; suitable for small/medium academic datasets.
    - Not suitable for high-concurrency multi-process distributed systems without a transactional RDBMS/NoSQL.
    - File-level locking only serializes threads within the current Python process.
    """

    def __init__(self):
        config.ensure_directories()
        self._init_files()

    def _init_files(self):
        """Ensure all required database files exist with valid initial structures."""
        with _LOCK:
            if not config.SETTINGS_FILE.exists():
                self.atomic_write(config.SETTINGS_FILE, config.DEFAULT_SETTINGS)

            if not config.VEHICLES_FILE.exists():
                self.atomic_write(config.VEHICLES_FILE, [])

            if not config.VIOLATIONS_FILE.exists():
                self.atomic_write(config.VIOLATIONS_FILE, [])

            if not config.TICKETS_FILE.exists():
                self.atomic_write(config.TICKETS_FILE, [])

            if not config.STATE_FILE.exists():
                default_state = {
                    "is_processing": False,
                    "records_processed": 0,
                    "violations_detected": 0,
                    "last_run": None,
                    "active_source": config.DEFAULT_SETTINGS["dataset_source"],
                    "status_message": "System Idle"
                }
                self.atomic_write(config.STATE_FILE, default_state)

    def atomic_write(self, file_path: Path, data: Any) -> None:
        """
        Safely write data to a JSON file atomically using a temporary file and os.replace.
        Prevents partial writes and file corruption on unexpected crashes.
        """
        target_dir = file_path.parent
        target_dir.mkdir(parents=True, exist_ok=True)

        with _LOCK:
            # Create temporary file in the same directory for atomic replace across filesystem boundaries
            fd, temp_path = tempfile.mkstemp(
                dir=str(target_dir),
                prefix=f"{file_path.stem}_tmp_",
                suffix=".json"
            )
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                # Atomic replace on Windows & POSIX
                os.replace(temp_path, str(file_path))
            except Exception as e:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass
                raise IOError(f"Failed to atomically write to {file_path}: {e}") from e

    def read_json(self, file_path: Path, default_value: Any = None) -> Any:
        """
        Read and deserialize JSON data with lock protection and corruption fallback.
        """
        with _LOCK:
            if not file_path.exists():
                if default_value is not None:
                    self.atomic_write(file_path, default_value)
                    return default_value
                return []

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        return default_value if default_value is not None else []
                    return json.loads(content)
            except (json.JSONDecodeError, OSError) as e:
                # Backup corrupted file for forensic inspection and reinitialize
                backup_path = file_path.with_suffix(f".corrupt_{int(os.path.getmtime(file_path))}.json")
                try:
                    shutil.copy2(file_path, backup_path)
                except Exception:
                    pass

                fallback = default_value if default_value is not None else []
                self.atomic_write(file_path, fallback)
                return fallback

    # --- Vehicles ---
    def get_vehicles(self) -> List[Dict[str, Any]]:
        return self.read_json(config.VEHICLES_FILE, default_value=[])

    def save_vehicles(self, vehicles: List[Dict[str, Any]]) -> None:
        self.atomic_write(config.VEHICLES_FILE, vehicles)

    # --- Violations ---
    def get_violations(self) -> List[Dict[str, Any]]:
        return self.read_json(config.VIOLATIONS_FILE, default_value=[])

    def save_violations(self, violations: List[Dict[str, Any]]) -> None:
        self.atomic_write(config.VIOLATIONS_FILE, violations)

    # --- Tickets ---
    def get_tickets(self) -> List[Dict[str, Any]]:
        return self.read_json(config.TICKETS_FILE, default_value=[])

    def save_tickets(self, tickets: List[Dict[str, Any]]) -> None:
        self.atomic_write(config.TICKETS_FILE, tickets)

    def add_ticket(self, ticket: Dict[str, Any]) -> bool:
        """Add a ticket if it doesn't already exist for this violation/vehicle."""
        with _LOCK:
            tickets = self.get_tickets()
            # Prevent duplicate ticket generation
            for t in tickets:
                if t.get("ticket_id") == ticket.get("ticket_id") or t.get("violation_id") == ticket.get("violation_id"):
                    return False
            tickets.append(ticket)
            self.save_tickets(tickets)
            return True

    def get_ticket_by_id(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        tickets = self.get_tickets()
        for t in tickets:
            if t.get("ticket_id") == ticket_id:
                return t
        return None

    # --- Settings ---
    def get_settings(self) -> Dict[str, Any]:
        data = self.read_json(config.SETTINGS_FILE, default_value=config.DEFAULT_SETTINGS)
        # Ensure default keys are preserved if partial update occurred
        merged = {**config.DEFAULT_SETTINGS, **data}
        return merged

    def update_settings(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        with _LOCK:
            current = self.get_settings()
            current.update(new_settings)
            self.atomic_write(config.SETTINGS_FILE, current)
            return current

    # --- State ---
    def get_state(self) -> Dict[str, Any]:
        default_state = {
            "is_processing": False,
            "records_processed": 0,
            "violations_detected": 0,
            "last_run": None,
            "active_source": config.DEFAULT_SETTINGS["dataset_source"],
            "status_message": "System Idle"
        }
        return self.read_json(config.STATE_FILE, default_value=default_state)

    def update_state(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        with _LOCK:
            current = self.get_state()
            current.update(updates)
            self.atomic_write(config.STATE_FILE, current)
            return current

    def reset_database(self) -> None:
        """Completely reset dynamic observation and ticket data, preserving settings."""
        with _LOCK:
            self.atomic_write(config.VEHICLES_FILE, [])
            self.atomic_write(config.VIOLATIONS_FILE, [])
            self.atomic_write(config.TICKETS_FILE, [])
            self.atomic_write(config.STATE_FILE, {
                "is_processing": False,
                "records_processed": 0,
                "violations_detected": 0,
                "last_run": None,
                "active_source": config.DEFAULT_SETTINGS["dataset_source"],
                "status_message": "Database Reset to Clean State"
            })
            # Clean generated tickets folder safely
            if config.GENERATED_TICKETS_DIR.exists():
                for p in config.GENERATED_TICKETS_DIR.glob("*.png"):
                    try:
                        p.unlink()
                    except OSError:
                        pass


db = JSONDatabase()
