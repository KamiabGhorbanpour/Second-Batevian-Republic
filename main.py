from __future__ import annotations

import html
import json
import os
from pathlib import Path
from typing import Any

from fastapi.responses import PlainTextResponse
from nicegui import app, ui

from game_store import (
    GameError,
    MINISTRIES,
    MINISTRY_MAP,
    ROUNDS,
    TOTAL_ROUNDS,
    create_room,
    get_snapshot,
    join_room,
    leave_room,
    submit_decision,
)


BASE_DIR = Path(__file__).resolve().parent
app.add_static_files("/scenes", BASE_DIR / "static" / "scenes")


@app.get("/health")
def healthcheck() -> PlainTextResponse:
    return PlainTextResponse("ok")


def ministry_name(ministry_id: str) -> str:
    return MINISTRY_MAP[ministry_id]["shortName"]


def delta_text(value: int) -> str:
    return f"+{value}" if value >= 0 else str(value)


@ui.page("/")
async def game_page() -> None:
    ui.add_css((BASE_DIR / "static" / "app.css").read_text(encoding="utf-8"))

    entry: dict[str, Any] = {
        "mode": "create",
        "name": "",
        "code": "",
        "ministry": "education",
    }
    state: dict[str, Any] = {
        "session": None,
        "error": "",
        "busy": False,
        "signature": "",
    }

    identity = app.storage.user.get("batavian_identity")
    if isinstance(identity, dict) and identity.get("code") and identity.get("token"):
        state["session"] = get_snapshot(identity["code"], identity["token"])
        if state["session"] is None:
            app.storage.user.pop("batavian_identity", None)
            identity = None
    else:
        identity = None

    def seen_round() -> int:
        if not identity:
            return 0
        return int(app.storage.user.get(f"batavian_seen_{identity['code']}", 0) or 0)

    async def enter_room() -> None:
        nonlocal identity
        state["busy"] = True
        state["error"] = ""
        render.refresh()
        try:
            if entry["mode"] == "create":
                new_identity = create_room(entry["name"], entry["ministry"])
            else:
                new_identity = join_room(entry["code"], entry["name"], entry["ministry"])
            identity = new_identity
            app.storage.user["batavian_identity"] = new_identity
            state["session"] = get_snapshot(new_identity["code"], new_identity["token"])
            state["signature"] = ""
        except GameError as error:
            state["error"] = str(error)
        finally:
            state["busy"] = False
            render.refresh()

    async def choose_ministry(ministry_id: str) -> None:
        entry["ministry"] = ministry_id
        render.refresh()

    async def set_mode(mode: str) -> None:
        entry["mode"] = mode
        state["error"] = ""
        render.refresh()

    async def submit(choice_index: int) -> None:
        if not identity or not state["session"]:
            return
        state["busy"] = True
        state["error"] = ""
        render.refresh()
        try:
            decision_index = len(state["session"]["my_decisions"])
            state["session"] = submit_decision(
                identity["code"],
                identity["token"],
                decision_index,
                choice_index,
            )
            state["signature"] = ""
        except GameError as error:
            state["error"] = str(error)
        finally:
            state["busy"] = False
            render.refresh()

    async def exit_room() -> None:
        nonlocal identity
        if identity and state["session"] and state["session"]["room"]["status"] == "lobby":
            leave_room(identity["code"], identity["token"])
        app.storage.user.pop("batavian_identity", None)
        identity = None
        state["session"] = None
        state["signature"] = ""
        state["error"] = ""
        render.refresh()

    async def acknowledge_result() -> None:
        if not identity or not state["session"] or not state["session"]["latest_result"]:
            return
        result_round = state["session"]["latest_result"]["round"]
        app.storage.user[f"batavian_seen_{identity['code']}"] = result_round
        render.refresh()

    def masthead(session: dict[str, Any] | None) -> None:
        with ui.element("header").classes("identity-header"):
            with ui.element("div").classes("government-lockup"):
                ui.label("II").classes("crest")
                with ui.element("div").classes("government-name"):
                    ui.label("The Second Batavian Republic").classes("government-title")
                    ui.label("Council of Ministers").classes("government-subtitle")
            if session:
                with ui.element("div").classes("room-chip"):
                    ui.label("Cabinet code")
                    ui.label(session["room"]["code"]).classes("room-chip-code")

    def title_band(session: dict[str, Any] | None) -> None:
        with ui.element("section").classes("title-band"):
            with ui.element("div").classes("band-inner"):
                ui.label("Home / Council simulation").classes("breadcrumb")
                title = ministry_name(session["me"]["ministry"]) if session else "The City We Inherit"
                ui.label(title).classes("band-title")
                if session:
                    ui.label(
                        f"Round {session['room']['current_round']} of {TOTAL_ROUNDS}"
                    ).classes("round-label")

    def error_message() -> None:
        if state["error"]:
            ui.label(state["error"]).classes("error").props('role="alert"')

    def ministry_cards() -> None:
        with ui.element("div").classes("ministry-grid"):
            for index, ministry in enumerate(MINISTRIES, start=1):
                selected = entry["ministry"] == ministry["id"]
                classes = "ministry-option selected" if selected else "ministry-option"
                with ui.button(
                    on_click=lambda ministry_id=ministry["id"]: choose_ministry(ministry_id)
                ).props("flat no-caps").classes(classes):
                    ui.label(f"0{index}").classes("ministry-number")
                    ui.label(ministry["shortName"]).classes("ministry-card-title")
                    ui.label(ministry["role"]).classes("ministry-card-role")

    def landing() -> None:
        with ui.element("section").classes("page-grid landing"):
            with ui.element("div").classes("intro-copy"):
                ui.label("Four players · four ministries · one republic").classes("eyebrow")
                ui.html("<h2>Govern together.<br>Compete for influence.</h2>")
                ui.label(
                    "Each player joins from a different computer and leads one ministry. "
                    "Make two private decisions per round. The council moves only when all eight decisions are in."
                ).classes("lead")
                with ui.element("div").classes("rule-list"):
                    with ui.element("div"):
                        ui.label("Shared stakes").classes("rule-title")
                        ui.label(
                            "Civil welfare, national resources, and public confidence rise or fall for everyone."
                        )
                    with ui.element("div"):
                        ui.label("Personal standing").classes("rule-title")
                        ui.label(
                            "Your choices also earn influence. The strongest minister may still preside over national failure."
                        )

            with ui.element("div").classes("entry-panel"):
                with ui.element("div").classes("tabs"):
                    for mode, label in (("create", "Create room"), ("join", "Join room")):
                        tab_class = "tab-button active" if entry["mode"] == mode else "tab-button"
                        ui.button(
                            label,
                            on_click=lambda selected_mode=mode: set_mode(selected_mode),
                        ).props("flat no-caps").classes(tab_class)
                ui.label(
                    "Form a new council" if entry["mode"] == "create" else "Take your council seat"
                ).classes("panel-title")
                if entry["mode"] == "join":
                    ui.label("Six-character room code").classes("field-label")
                    ui.input(
                        value=entry["code"],
                        placeholder="ABC123",
                        on_change=lambda event: entry.update(code=str(event.value).upper()[:6]),
                    ).props("outlined dense square maxlength=6 autocomplete=off").classes("official-input")
                ui.label("Your name").classes("field-label")
                ui.input(
                    value=entry["name"],
                    placeholder="Minister name",
                    on_change=lambda event: entry.update(name=str(event.value)[:28]),
                ).props("outlined dense square maxlength=28").classes("official-input")
                ui.label("Choose a ministry").classes("field-label ministry-label")
                ministry_cards()
                error_message()
                ui.button(
                    "Connecting…"
                    if state["busy"]
                    else "Create council room"
                    if entry["mode"] == "create"
                    else "Join council",
                    on_click=enter_room,
                ).props("unelevated no-caps").classes("primary").set_enabled(not state["busy"])

    def resource_strip(session: dict[str, Any]) -> None:
        labels = (
            ("Civil welfare", session["room"]["civilians"]),
            ("National resources", session["room"]["resources"]),
            ("Public confidence", session["room"]["popularity"]),
        )
        with ui.element("div").classes("resource-strip"):
            for label, value in labels:
                with ui.element("div").classes("resource-item"):
                    ui.label(label)
                    ui.label(str(value)).classes("resource-value")

    def seat_list(session: dict[str, Any], progress: bool = False) -> None:
        with ui.element("aside").classes("seat-list"):
            ui.label("Council seats").classes("eyebrow")
            ui.label(f"{len(session['players'])} / 4 ministers").classes("side-title")
            for ministry in MINISTRIES:
                player = next(
                    (person for person in session["players"] if person["ministry"] == ministry["id"]),
                    None,
                )
                with ui.element("div").classes("seat filled" if player else "seat"):
                    ui.label(ministry["shortName"])
                    if player and progress:
                        ui.label(f"{player['submitted']} / 2 submitted").classes("seat-value")
                    else:
                        ui.label(player["name"] if player else "Waiting…").classes("seat-value")

    def lobby(session: dict[str, Any]) -> None:
        with ui.element("section").classes("page-grid lobby-page"):
            with ui.element("div"):
                ui.label("Council assembly").classes("eyebrow")
                ui.html("<h2>Invite three other ministers.</h2>")
                ui.label(
                    "Share this code. Each player opens the game, chooses Join room, and claims one remaining ministry."
                ).classes("lead")
                ui.label(session["room"]["code"]).classes("large-code")
                ui.label("The first round starts automatically when all four seats are occupied.").classes("quiet")
                ui.button("Leave room", on_click=exit_room).props("flat no-caps").classes("text-button")
            seat_list(session)

    def waiting(session: dict[str, Any]) -> None:
        received = sum(player["submitted"] for player in session["players"])
        with ui.element("section").classes("page-grid waiting-page"):
            with ui.element("div"):
                ui.label("Your brief is complete").classes("eyebrow")
                ui.html("<h2>Waiting for the council.</h2>")
                ui.label(
                    "Your two decisions are locked. The round resolves once every ministry has submitted both choices."
                ).classes("lead")
                with ui.element("div").classes("progress-line"):
                    ui.element("span").style(f"width: {(received / 8) * 100:.0f}%")
                ui.label(f"{received} of 8 decisions received").classes("progress-copy")
            seat_list(session, progress=True)

    def decision_screen(session: dict[str, Any], decision: dict[str, Any], decision_index: int) -> None:
        ministry = MINISTRY_MAP[session["me"]["ministry"]]
        current_round = ROUNDS[session["room"]["current_round"] - 1]
        with ui.element("section").classes("decision-layout"):
            with ui.element("div").classes("editorial-image"):
                ui.html(
                    f'<img src="{html.escape(ministry["image"])}" '
                    f'alt="{html.escape(ministry["alt"])}">'
                )
            with ui.element("div").classes("decision-copy"):
                ui.label(
                    f"{current_round['title']} · Decision {decision_index + 1} of 2"
                ).classes("eyebrow")
                ui.html(f"<h2>{html.escape(decision['title'])}</h2>")
                ui.label(decision["brief"]).classes("brief")
                ui.label(decision["question"]).classes("decision-question")
                with ui.element("div").classes("choices"):
                    for index, choice in enumerate(decision["choices"], start=1):
                        choice_button = ui.button(
                            on_click=lambda choice_index=index - 1: submit(choice_index)
                        ).props("flat no-caps").classes("choice-button")
                        choice_button.set_enabled(not state["busy"])
                        with choice_button:
                            ui.label(f"0{index}").classes("choice-number")
                            with ui.element("div").classes("choice-copy"):
                                ui.label(choice["title"]).classes("choice-title")
                                ui.label(choice["detail"]).classes("choice-detail")
                            ui.label("Choose").classes("choice-action")
                error_message()
            with ui.element("aside").classes("minister-card"):
                ui.label("Your office").classes("minister-kicker")
                ui.label(session["me"]["name"]).classes("minister-name")
                ui.label(ministry["name"]).classes("minister-office")
                with ui.element("div").classes("influence-box"):
                    ui.label(str(session["me"]["influence"])).classes("influence-value")
                    ui.label("influence")
                ui.label("Your individual choices stay private until the round is resolved.").classes("minister-note")

    def result_screen(session: dict[str, Any], result: dict[str, Any]) -> None:
        current_round = ROUNDS[result["round"] - 1]
        resources = (
            ("Civil welfare", result["civilians_after"], result["civilians_delta"]),
            ("National resources", result["resources_after"], result["resources_delta"]),
            ("Public confidence", result["popularity_after"], result["popularity_delta"]),
        )
        with ui.element("section").classes("page-grid result-page"):
            with ui.element("div"):
                ui.label(f"Round {result['round']} complete").classes("eyebrow")
                ui.html(f"<h2>{html.escape(current_round['title'])}: council result</h2>")
                ui.label(
                    "All eight decisions have been combined. Shared resources show the cost of the council's collective direction."
                ).classes("lead")
                with ui.element("div").classes("result-resources"):
                    for label, value, change in resources:
                        with ui.element("article"):
                            ui.label(label)
                            ui.label(str(value)).classes("result-value")
                            change_class = "positive" if change >= 0 else "negative"
                            ui.label(delta_text(change)).classes(f"result-delta {change_class}")
                ui.button(
                    "See the final outcome" if session["room"]["status"] == "finished" else "Enter the next round",
                    on_click=acknowledge_result,
                ).props("unelevated no-caps").classes("primary")
            with ui.element("aside").classes("leaderboard"):
                ui.label("Ministerial influence").classes("eyebrow")
                ui.label("Council standings").classes("side-title")
                for index, standing in enumerate(result["standings"], start=1):
                    with ui.element("div").classes("standing"):
                        ui.label(str(index)).classes("standing-rank")
                        with ui.element("div"):
                            ui.label(standing["name"]).classes("standing-name")
                            ui.label(ministry_name(standing["ministry"])).classes("standing-office")
                        ui.label(str(standing["influence"])).classes("standing-score")

    def final_screen(session: dict[str, Any]) -> None:
        room = session["room"]
        values = [room["civilians"], room["resources"], room["popularity"]]
        success = all(value >= 35 for value in values) and sum(values) >= 250
        winner = max(session["players"], key=lambda player: player["influence"])
        with ui.element("section").classes("page-grid final-page"):
            with ui.element("div"):
                ui.label("Final national outcome").classes("eyebrow")
                ui.html(
                    "<h2>The republic endures.</h2>"
                    if success
                    else "<h2>The council loses the country.</h2>"
                )
                ui.label(
                    "The ministries protected enough public capacity to carry the republic through the crisis."
                    if success
                    else "Influence survived inside the council, but the shared foundations of government did not."
                ).classes("lead")
                with ui.element("div").classes("final-image"):
                    image_name = "good-ending.webp" if success else "bad-ending.webp"
                    ui.html(f'<img src="/scenes/{image_name}" alt="Final national outcome">')
                ui.button("Start another session", on_click=exit_room).props("unelevated no-caps").classes("primary")
            with ui.element("aside").classes("winner-panel"):
                ui.label("Highest influence").classes("eyebrow")
                ui.label(winner["name"]).classes("winner-name")
                ui.label(ministry_name(winner["ministry"])).classes("winner-office")
                with ui.element("div").classes("winner-score"):
                    ui.label(str(winner["influence"]))
                    ui.label("influence")
                ui.label(
                    "Ministerial victory and national success are measured separately."
                ).classes("quiet")

    @ui.refreshable
    def render() -> None:
        session = state["session"]
        with ui.element("main"):
            masthead(session)
            title_band(session)
            if not identity:
                landing()
                return
            if not session:
                with ui.element("section").classes("status-page"):
                    ui.spinner(size="42px", color="primary")
                    ui.label("Opening the council room…").classes("status-title")
                return

            result = session["latest_result"]
            unseen = result and result["round"] > seen_round()
            if unseen:
                result_screen(session, result)
            elif session["room"]["status"] == "lobby":
                lobby(session)
            elif session["room"]["status"] == "playing":
                resource_strip(session)
                decision_index = len(session["my_decisions"])
                if decision_index >= 2:
                    waiting(session)
                else:
                    round_data = ROUNDS[session["room"]["current_round"] - 1]
                    decision = round_data["decisions"][session["me"]["ministry"]][decision_index]
                    decision_screen(session, decision, decision_index)
            else:
                final_screen(session)

    async def poll() -> None:
        if not identity:
            return
        snapshot = get_snapshot(identity["code"], identity["token"])
        if snapshot is None:
            return
        signature = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
        if signature != state["signature"]:
            state["session"] = snapshot
            state["signature"] = signature
            render.refresh()

    render()
    if state["session"]:
        state["signature"] = json.dumps(state["session"], sort_keys=True, separators=(",", ":"))
    ui.timer(1.5, poll)


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="The Second Batavian Republic",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8080")),
        storage_secret=os.getenv("STORAGE_SECRET", "local-development-secret-change-me"),
        favicon="🏛️",
        reload=False,
        show=False,
    )
