from __future__ import annotations

import json
import os
import secrets
import sqlite3
import string
import threading
import time
import uuid
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
STORY = json.loads((BASE_DIR / "story.json").read_text(encoding="utf-8"))
INITIAL_RESOURCES = STORY["initial"]
RESOURCE_LABELS = STORY.get(
    "resource_labels",
    {"civilians": "NS", "resources": "Guilders", "popularity": "Popularity", "nr": "NR"},
)
MINISTRIES = STORY["ministries"]
MINISTRY_MAP = {ministry["id"]: ministry for ministry in MINISTRIES}
ROUNDS = STORY["rounds"]
TOTAL_ROUNDS = len(ROUNDS)

DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "game.db")))
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
DB_LOCK = threading.RLock()
ROOM_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class GameError(Exception):
    """A safe, player-facing game error."""


def _now() -> int:
    return int(time.time() * 1000)


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


def init_database() -> None:
    with DB_LOCK, _connect() as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS rooms (
                id TEXT PRIMARY KEY,
                code TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'lobby',
                current_round INTEGER NOT NULL DEFAULT 1,
                civilians INTEGER NOT NULL DEFAULT 130,
                resources INTEGER NOT NULL DEFAULT 120,
                popularity INTEGER NOT NULL DEFAULT 130,
                nr INTEGER NOT NULL DEFAULT 130,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS players (
                id TEXT PRIMARY KEY,
                token TEXT NOT NULL UNIQUE,
                room_id TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                ministry TEXT NOT NULL,
                influence INTEGER NOT NULL DEFAULT 0,
                joined_at INTEGER NOT NULL,
                UNIQUE(room_id, ministry)
            );

            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                player_id TEXT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
                ministry TEXT NOT NULL,
                round INTEGER NOT NULL,
                decision_index INTEGER NOT NULL,
                choice_index INTEGER NOT NULL,
                civilians_delta INTEGER NOT NULL,
                resources_delta INTEGER NOT NULL,
                popularity_delta INTEGER NOT NULL,
                nr_delta INTEGER NOT NULL DEFAULT 0,
                influence_delta INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                UNIQUE(player_id, round, decision_index)
            );

            CREATE TABLE IF NOT EXISTS round_results (
                id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                round INTEGER NOT NULL,
                civilians_delta INTEGER NOT NULL,
                resources_delta INTEGER NOT NULL,
                popularity_delta INTEGER NOT NULL,
                nr_delta INTEGER NOT NULL DEFAULT 0,
                civilians_after INTEGER NOT NULL,
                resources_after INTEGER NOT NULL,
                popularity_after INTEGER NOT NULL,
                nr_after INTEGER NOT NULL DEFAULT 130,
                standings_json TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                UNIQUE(room_id, round)
            );
            """
        )

        # Backward-compatible migration for deployments created before the
        # flowchart version introduced the fourth shared resource (NR).
        def ensure_column(table: str, column: str, declaration: str) -> None:
            columns = {
                row["name"]
                for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
            }
            if column not in columns:
                connection.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} {declaration}"
                )

        ensure_column("rooms", "nr", f"INTEGER NOT NULL DEFAULT {int(INITIAL_RESOURCES['nr'])}")
        ensure_column("decisions", "nr_delta", "INTEGER NOT NULL DEFAULT 0")
        ensure_column("round_results", "nr_delta", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(
            "round_results",
            "nr_after",
            f"INTEGER NOT NULL DEFAULT {int(INITIAL_RESOURCES['nr'])}",
        )


def clean_code(value: str | None) -> str:
    return "".join(character for character in (value or "").strip().upper() if character.isalnum())[:6]


def clean_name(value: str | None) -> str:
    return " ".join((value or "").strip().split())[:28]


def _make_code() -> str:
    return "".join(secrets.choice(ROOM_ALPHABET) for _ in range(6))


def _row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def _decision_count(round_number: int, ministry: str) -> int:
    try:
        return len(ROUNDS[round_number - 1]["decisions"][ministry])
    except (IndexError, KeyError, TypeError):
        return 0


def create_room(name: str, ministry: str) -> dict[str, str]:
    safe_name = clean_name(name)
    if not safe_name or ministry not in MINISTRY_MAP:
        raise GameError("Choose a name and ministry.")

    with DB_LOCK:
        connection = _connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            code = ""
            for _ in range(12):
                candidate = _make_code()
                exists = connection.execute("SELECT 1 FROM rooms WHERE code = ?", (candidate,)).fetchone()
                if not exists:
                    code = candidate
                    break
            if not code:
                raise GameError("A room code could not be created. Please try again.")

            room_id = str(uuid.uuid4())
            token = str(uuid.uuid4())
            timestamp = _now()
            connection.execute(
                """
                INSERT INTO rooms
                    (id, code, status, current_round, civilians, resources, popularity, nr, created_at, updated_at)
                VALUES (?, ?, 'lobby', 1, ?, ?, ?, ?, ?, ?)
                """,
                (
                    room_id,
                    code,
                    INITIAL_RESOURCES["civilians"],
                    INITIAL_RESOURCES["resources"],
                    INITIAL_RESOURCES["popularity"],
                    INITIAL_RESOURCES["nr"],
                    timestamp,
                    timestamp,
                ),
            )
            connection.execute(
                """
                INSERT INTO players (id, token, room_id, name, ministry, influence, joined_at)
                VALUES (?, ?, ?, ?, ?, 0, ?)
                """,
                (str(uuid.uuid4()), token, room_id, safe_name, ministry, timestamp),
            )
            connection.commit()
            return {"code": code, "token": token}
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


def join_room(code: str, name: str, ministry: str) -> dict[str, str]:
    safe_code = clean_code(code)
    safe_name = clean_name(name)
    if len(safe_code) != 6 or not safe_name or ministry not in MINISTRY_MAP:
        raise GameError("Enter a six-character room code, your name, and a ministry.")

    with DB_LOCK:
        connection = _connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            room = connection.execute("SELECT * FROM rooms WHERE code = ?", (safe_code,)).fetchone()
            if room is None:
                raise GameError("No room has that code.")
            if room["status"] != "lobby":
                raise GameError("This cabinet is already in session.")

            roster = connection.execute("SELECT * FROM players WHERE room_id = ?", (room["id"],)).fetchall()
            if len(roster) >= 4:
                raise GameError("This room is full.")
            if any(player["ministry"] == ministry for player in roster):
                raise GameError("That ministry has already been claimed.")

            token = str(uuid.uuid4())
            try:
                connection.execute(
                    """
                    INSERT INTO players (id, token, room_id, name, ministry, influence, joined_at)
                    VALUES (?, ?, ?, ?, ?, 0, ?)
                    """,
                    (str(uuid.uuid4()), token, room["id"], safe_name, ministry, _now()),
                )
            except sqlite3.IntegrityError as error:
                raise GameError("That ministry was just claimed. Choose another.") from error

            if len(roster) + 1 == 4:
                connection.execute(
                    "UPDATE rooms SET status = 'playing', updated_at = ? WHERE id = ?",
                    (_now(), room["id"]),
                )
            connection.commit()
            return {"code": safe_code, "token": token}
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


def leave_room(code: str, token: str) -> None:
    safe_code = clean_code(code)
    with DB_LOCK, _connect() as connection:
        room = connection.execute("SELECT * FROM rooms WHERE code = ?", (safe_code,)).fetchone()
        if room is None or room["status"] != "lobby":
            return
        connection.execute("DELETE FROM players WHERE room_id = ? AND token = ?", (room["id"], token))


def get_snapshot(code: str, token: str) -> dict[str, Any] | None:
    safe_code = clean_code(code)
    with DB_LOCK, _connect() as connection:
        room = connection.execute("SELECT * FROM rooms WHERE code = ?", (safe_code,)).fetchone()
        if room is None:
            return None
        roster = connection.execute("SELECT * FROM players WHERE room_id = ?", (room["id"],)).fetchall()
        me = next((player for player in roster if player["token"] == token), None)
        if me is None:
            return None

        current_decisions = connection.execute(
            "SELECT * FROM decisions WHERE room_id = ? AND round = ?",
            (room["id"], room["current_round"]),
        ).fetchall()
        my_decisions = sorted(
            (
                {"decision_index": decision["decision_index"], "choice_index": decision["choice_index"]}
                for decision in current_decisions
                if decision["player_id"] == me["id"]
            ),
            key=lambda decision: decision["decision_index"],
        )
        latest = connection.execute(
            "SELECT * FROM round_results WHERE room_id = ? ORDER BY round DESC LIMIT 1",
            (room["id"],),
        ).fetchone()

        players = []
        for player in roster:
            players.append(
                {
                    "name": player["name"],
                    "ministry": player["ministry"],
                    "influence": player["influence"],
                    "submitted": sum(1 for decision in current_decisions if decision["player_id"] == player["id"]),
                    "expected": _decision_count(room["current_round"], player["ministry"]),
                }
            )
        players.sort(key=lambda player: player["ministry"])

        latest_result = None
        if latest is not None:
            latest_result = {
                "round": latest["round"],
                "civilians_delta": latest["civilians_delta"],
                "resources_delta": latest["resources_delta"],
                "popularity_delta": latest["popularity_delta"],
                "civilians_after": latest["civilians_after"],
                "resources_after": latest["resources_after"],
                "popularity_after": latest["popularity_after"],
                "nr_delta": latest["nr_delta"],
                "nr_after": latest["nr_after"],
                "standings": json.loads(latest["standings_json"]),
            }

        decision_history: list[dict[str, Any]] = []
        if room["status"] == "finished":
            history_rows = connection.execute(
                """
                SELECT ministry, round, decision_index, choice_index
                FROM decisions
                WHERE room_id = ?
                ORDER BY round, ministry, decision_index
                """,
                (room["id"],),
            ).fetchall()
            decision_history = [
                {
                    "ministry": row["ministry"],
                    "round": row["round"],
                    "decision_index": row["decision_index"],
                    "choice_index": row["choice_index"],
                }
                for row in history_rows
            ]

        return {
            "room": {
                "code": room["code"],
                "status": room["status"],
                "current_round": room["current_round"],
                "civilians": room["civilians"],
                "resources": room["resources"],
                "popularity": room["popularity"],
                "nr": room["nr"],
            },
            "me": {"name": me["name"], "ministry": me["ministry"], "influence": me["influence"]},
            "players": players,
            "my_decisions": my_decisions,
            "latest_result": latest_result,
            "decision_history": decision_history,
        }


def _finalize_round(connection: sqlite3.Connection, room_id: str, round_number: int) -> None:
    room = connection.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
    if room is None or room["current_round"] != round_number or room["status"] != "playing":
        return

    roster_for_expected = connection.execute(
        "SELECT * FROM players WHERE room_id = ?", (room_id,)
    ).fetchall()
    expected = sum(
        _decision_count(round_number, player["ministry"])
        for player in roster_for_expected
    )
    all_decisions = connection.execute(
        "SELECT * FROM decisions WHERE room_id = ? AND round = ?",
        (room_id, round_number),
    ).fetchall()
    if expected <= 0 or len(all_decisions) != expected:
        return
    existing = connection.execute(
        "SELECT 1 FROM round_results WHERE room_id = ? AND round = ?",
        (room_id, round_number),
    ).fetchone()
    if existing:
        return

    delta = {
        "civilians": sum(decision["civilians_delta"] for decision in all_decisions),
        "resources": sum(decision["resources_delta"] for decision in all_decisions),
        "popularity": sum(decision["popularity_delta"] for decision in all_decisions),
        "nr": sum(decision["nr_delta"] for decision in all_decisions),
    }
    after = {
        key: max(0, room[key] + delta[key])
        for key in ("civilians", "resources", "popularity", "nr")
    }
    roster = connection.execute("SELECT * FROM players WHERE room_id = ?", (room_id,)).fetchall()
    standings = []
    for player in roster:
        influence_gain = sum(
            decision["influence_delta"]
            for decision in all_decisions
            if decision["player_id"] == player["id"]
        )
        standings.append(
            {
                "id": player["id"],
                "name": player["name"],
                "ministry": player["ministry"],
                "influence": player["influence"] + influence_gain,
            }
        )
    standings.sort(key=lambda standing: standing["influence"], reverse=True)

    public_standings = [
        {key: value for key, value in standing.items() if key != "id"}
        for standing in standings
    ]
    connection.execute(
        """
        INSERT INTO round_results
            (id, room_id, round, civilians_delta, resources_delta, popularity_delta, nr_delta,
             civilians_after, resources_after, popularity_after, nr_after, standings_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            room_id,
            round_number,
            delta["civilians"],
            delta["resources"],
            delta["popularity"],
            delta["nr"],
            after["civilians"],
            after["resources"],
            after["popularity"],
            after["nr"],
            json.dumps(public_standings),
            _now(),
        ),
    )
    for standing in standings:
        connection.execute(
            "UPDATE players SET influence = ? WHERE id = ?",
            (standing["influence"], standing["id"]),
        )

    finished = round_number >= TOTAL_ROUNDS
    connection.execute(
        """
        UPDATE rooms
        SET civilians = ?, resources = ?, popularity = ?, nr = ?, status = ?, current_round = ?, updated_at = ?
        WHERE id = ? AND current_round = ?
        """,
        (
            after["civilians"],
            after["resources"],
            after["popularity"],
            after["nr"],
            "finished" if finished else "playing",
            round_number if finished else round_number + 1,
            _now(),
            room_id,
            round_number,
        ),
    )


def submit_decision(code: str, token: str, decision_index: int, choice_index: int) -> dict[str, Any]:
    safe_code = clean_code(code)
    if not isinstance(decision_index, int) or not isinstance(choice_index, int):
        raise GameError("Incomplete decision.")

    with DB_LOCK:
        connection = _connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            room = connection.execute("SELECT * FROM rooms WHERE code = ?", (safe_code,)).fetchone()
            if room is None or room["status"] != "playing":
                raise GameError("This cabinet is not accepting decisions.")
            player = connection.execute(
                "SELECT * FROM players WHERE room_id = ? AND token = ?",
                (room["id"], token),
            ).fetchone()
            if player is None or player["ministry"] not in MINISTRY_MAP:
                raise GameError("Player not found.")

            expected_for_player = _decision_count(
                room["current_round"], player["ministry"]
            )
            if decision_index < 0 or decision_index >= expected_for_player:
                raise GameError("That decision is unavailable.")

            mine = connection.execute(
                "SELECT * FROM decisions WHERE player_id = ? AND round = ? ORDER BY decision_index",
                (player["id"], room["current_round"]),
            ).fetchall()
            if decision_index != len(mine):
                raise GameError("Decisions must be submitted in order.")

            try:
                decision = ROUNDS[room["current_round"] - 1]["decisions"][player["ministry"]][decision_index]
                choice = decision["choices"][choice_index]
            except (IndexError, KeyError, TypeError) as error:
                raise GameError("That choice is unavailable.") from error
            effects = choice["effects"]

            try:
                connection.execute(
                    """
                    INSERT INTO decisions
                        (id, room_id, player_id, ministry, round, decision_index, choice_index,
                         civilians_delta, resources_delta, popularity_delta, nr_delta, influence_delta, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        room["id"],
                        player["id"],
                        player["ministry"],
                        room["current_round"],
                        decision_index,
                        choice_index,
                        effects["civilians"],
                        effects["resources"],
                        effects["popularity"],
                        effects.get("nr", 0),
                        effects["influence"],
                        _now(),
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise GameError("This decision has already been submitted.") from error

            _finalize_round(connection, room["id"], room["current_round"])
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    state = get_snapshot(safe_code, token)
    if state is None:
        raise GameError("This session could not be found.")
    return state


init_database()
