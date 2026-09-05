from __future__ import annotations

import queue
import json
import os
import re
import subprocess
import tempfile
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict


@dataclass(frozen=True, slots=True)
class VoiceIntent:
    transcript: str
    action: str
    arguments: Dict[str, Any]
    device: str = "television"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def friendly_voice_error(exc: Exception, *, action: str) -> str:
    detail = f"{type(exc).__name__}: {exc}".lower()
    unreachable_markers = (
        "handshake", "timed out", "timeout", "connection refused",
        "network is unreachable", "no route to host", "host is down",
    )
    if any(marker in detail for marker in unreachable_markers):
        if action in {"web_research", "live_fact_check", "live_explain"}:
            return (
                "I completed the research on the mother brain, but the television is not reachable. "
                "Switch the TV on and say Pilot show my results again."
            )
        return (
            "I can hear you, but the television is not reachable. "
            "Make sure it is switched on and connected to the same Wi-Fi, then ask me again."
        )
    return str(exc) or "I could not safely complete that command."


def parse_voice_intent(transcript: str) -> VoiceIntent | None:
    normalized = re.sub(r"[^a-z0-9 ]+", " ", transcript.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    # Local speech recognition frequently joins "air con" into "aircon" or
    # renders the spoken abbreviation as "AC"/"A C". Canonicalize only this
    # appliance noun so it cannot fall through into an open-ended plan.
    normalized = re.sub(r"\baircon\b|\bair conditioner\b|\ba c\b|\bac\b", "air con", normalized)
    # Bounded repairs for recurring local-ASR confusions around the product's
    # wake phrase and God View name. These only apply when the rest of the
    # utterance already names that surface, avoiding a general fuzzy wake-up.
    if re.match(r"^(?:file|pile)\s+(?:open|show|launch)\s+god\s+(?:wee|we|view)\b", normalized):
        normalized = re.sub(r"^(?:file|pile)\b", "pilot", normalized, count=1)
    normalized = re.sub(r"\bgod\s+(?:wee|we)\b", "god view", normalized)
    # Reject background dialogue that merely mentions Pilot mid-sentence.
    wake = re.match(r"^(?:(?:hey|hi|hello|ok|okay)\s+)?(?:pilot|pilate|pile it)\b", normalized)
    if not wake:
        return None
    command = normalized[wake.end() :].strip()
    if not command:
        return VoiceIntent(transcript, "wake_acknowledged", {})
    if command in {"sleep", "go to sleep", "stop listening", "microphone off", "turn off the microphone"}:
        return VoiceIntent(transcript, "voice_sleep", {})
    if command in {"emergency stop", "cancel all actions", "cancel", "never mind", "nevermind"}:
        return VoiceIntent(transcript, "emergency_stop", {})
    if command in {"confirm emergency alert", "confirm guardian alert", "yes send help", "send the help alert"}:
        return VoiceIntent(transcript, "guardian_confirm", {}, device="companion")
    if command in {"cancel emergency alert", "cancel guardian alert", "false alarm", "i am okay", "i m okay"}:
        return VoiceIntent(transcript, "guardian_cancel", {}, device="companion")
    if any(term in command for term in (
        "i fell over", "i have fallen over", "i ve fallen over", "help i fell",
        "call an ambulance", "get me help", "emergency help", "send help",
    )):
        return VoiceIntent(transcript, "guardian_help", {"trigger": command}, device="companion")
    if any(term in command for term in (
        "i feel lonely", "i am lonely", "i m lonely", "feeling lonely", "i feel alone", "i am alone",
        "talk to me", "i need company", "no one to talk to", "i can t breathe", "i cannot breathe", "severe chest pain", "i am in danger",
        "i want to hurt myself", "i want to kill myself", "end my life",
    )):
        return VoiceIntent(transcript, "contextual_companion", {"kind": "wellbeing"}, device="companion")
    climate_set = re.search(
        r"\b(?:set|put|cool|heat)(?: the)?(?: air con| air conditioning| room)?(?: to)?\s+(1[6-9]|2[0-9]|30)(?: degrees?)?\b",
        command,
    )
    if climate_set and any(term in command for term in ("air con", "air conditioning", "cool", "heat")):
        mode = "heat" if "heat" in command else "cool"
        return VoiceIntent(transcript, "climate_ir", {"preset": f"{mode}_{climate_set.group(1)}"}, device="air_conditioner")
    if any(term in command for term in ("turn off the air con", "turn off air con", "turn the air con off", "air con off", "turn off air conditioning")):
        return VoiceIntent(transcript, "climate_ir", {"preset": "off"}, device="air_conditioner")
    if any(term in command for term in ("turn on the air con", "turn on air con", "turn the air con on", "air con on", "turn on air conditioning")):
        return VoiceIntent(transcript, "climate_ir", {"preset": "last_active"}, device="air_conditioner")
    if command in {"pause this task", "pause the task", "save this for later", "put this aside"}:
        return VoiceIntent(transcript, "conversation_pause", {})
    if command in {"resume the previous task", "resume previous task", "continue the previous plan", "what were we doing"}:
        return VoiceIntent(transcript, "conversation_resume", {})
    if (
        command in {"stop", "stop it", "stop this", "exit", "exit it", "leave this"}
        or re.search(r"\b(?:exit|leave|stop)(?: the| this)? (?:film|movie|series|show|episode|crown)\b", command)
    ):
        return VoiceIntent(transcript, "exit_content", {"button": "BACK"})
    if (
        re.fullmatch(r"(?:take\s*over|acquire|control)(?: my| the)? (?:tv|television)", command)
        or re.fullmatch(r"(?:open|show|launch|put)(?: aion| pilot| the pilot)?(?: home| dashboard)?(?: on)?(?: my| the)? (?:tv|television)", command)
        or command in {
            "open pilot", "show pilot", "pilot home", "open pilot home", "show pilot home",
            "show my pilot home", "open my pilot home", "open dashboard", "open the dashboard",
            "show dashboard", "show the dashboard",
        }
    ):
        return VoiceIntent(transcript, "show_canvas", {"view": "home"})
    if any(term in command for term in ("open god view", "show god view", "launch god view", "open gods eye view")):
        return VoiceIntent(transcript, "show_canvas", {"view": "god_view"})
    god_fly = re.match(r"^(?:fly|flight|take me|go|move|zoom)(?: me)? to\s+(.+?)(?:\s+(?:in|on) god(?:s|')? view)?$", command)
    if god_fly:
        destination = god_fly.group(1).strip()
        if destination in {"iss", "the iss", "international space station", "the international space station"}:
            return VoiceIntent(transcript, "show_canvas", {"view": "god_view", "god_action": "iss_live"})
        return VoiceIntent(
            transcript,
            "show_canvas",
            {"view": "god_view", "god_action": "fly", "place": destination},
        )
    if any(term in command for term in ("track the iss", "track iss", "where is the iss", "where is iss", "show iss position")):
        return VoiceIntent(transcript, "show_canvas", {"view": "god_view", "god_action": "iss_track"})
    if any(term in command for term in ("iss view", "show the iss", "show iss", "international space station view", "iss live", "live view from space", "show the live view from space")):
        return VoiceIntent(transcript, "show_canvas", {"view": "god_view", "god_action": "iss_live"})
    if any(term in command for term in ("nasa earth", "satellite earth", "satellite view of earth", "show earth from space")):
        return VoiceIntent(transcript, "show_canvas", {"view": "god_view", "god_action": "nasa_earth"})
    if any(term in command for term in ("show the phone controller", "show phone controller", "connect my iphone", "connect my phone")):
        return VoiceIntent(transcript, "show_canvas", {"view": "companion"})
    if (
        re.fullmatch(
            r"(?:please )?(?:log ?out|log me out|sign ?out|sign me out)"
            r"(?: (?:of|from) (?:my |the )?(?:tv|television|shared screen))?",
            command,
        )
        or re.fullmatch(
            r"(?:please )?(?:release|lock)(?: my| the)? (?:tv|television|shared screen|tv workspace|workspace)",
            command,
        )
        or command in {"leave my workspace", "finish my session", "end my tv session"}
    ):
        return VoiceIntent(transcript, "identity_logout", {})
    workspace_open = re.fullmatch(
        r"(?:please )?(?:open|show|display|bring up|go to)(?: my| the)? (.+)",
        command,
    )
    workspace_target = workspace_open.group(1).strip() if workspace_open else ""
    if workspace_target in {
        "tasks", "task", "task list", "tasks list", "to do list", "todo list",
    }:
        return VoiceIntent(transcript, "show_canvas", {"view": "tasks"})
    if workspace_target in {"calendar", "schedule", "diary"}:
        return VoiceIntent(transcript, "show_canvas", {"view": "calendar"})
    if workspace_target in {
        "files", "documents", "assets", "saved files", "saved documents",
    }:
        return VoiceIntent(transcript, "show_canvas", {"view": "files"})
    if workspace_target in {
        "iot", "iot devices", "connected devices", "smart home", "smart home devices",
        "devices", "device controls", "home devices",
    }:
        return VoiceIntent(transcript, "show_canvas", {"view": "iot"})
    if workspace_target in {
        "work", "workspace", "work space", "personal work", "personal workspace",
        "research workspace", "work centre", "work center",
    }:
        return VoiceIntent(transcript, "show_canvas", {"view": "work"})
    if "mesh" in command:
        return VoiceIntent(transcript, "show_canvas", {"view": "mesh"})
    if any(term in command for term in ("boardroom", "board room", "bored room")):
        return VoiceIntent(transcript, "show_canvas", {"view": "boardroom"})
    if "briefing" in command or "brief me" in command:
        return VoiceIntent(transcript, "show_canvas", {"view": "briefing"})
    if any(term in command for term in ("start spanish lesson", "open learning centre", "open education", "learn spanish")):
        return VoiceIntent(transcript, "education_start", {"profile_id": "explorer_a"})
    if any(term in command for term in ("what is on my task list", "what s on my task list", "show my task list", "show my to do list", "tell me my tasks", "what are my tasks")):
        return VoiceIntent(transcript, "inbox_summary", {})
    add_task = re.match(
        r"^(?:add|put)\s+(.+?)\s+(?:to|on)\s+my\s+(?:tasks?|task list|text list|to do list|todo list)$",
        command,
    )
    if not add_task:
        add_task = re.match(r"^(?:make|create)\s+(?:a )?task(?: for me)?(?: to)?\s+(.+)$", command)
    if add_task:
        return VoiceIntent(transcript, "inbox_add_self", {"title": add_task.group(1).strip()})
    delegate_task = re.match(r"^(?:send|give|assign|delegate)\s+(.+?)\s+(?:a task|the task)\s+(?:to|that says)\s+(.+)$", command)
    if not delegate_task:
        delegate_task = re.match(r"^(?:ask|remind)\s+(.+?)\s+to\s+(.+)$", command)
    if not delegate_task:
        # Local speech models can render "send Becca a task" as
        # "s in back at a task".  Keep this repair narrowly bounded to an
        # explicit task-delivery grammar; recipient resolution later requires
        # one unique private contact and therefore never guesses an identity.
        delegate_task = re.match(
            r"^(?:send|sent|sin|s in|give|assign|delegate)\s+(.+?)\s+"
            r"(?:(?:a|at a|the)\s+)?task\s+(?:to|that says)\s+(.+)$",
            command,
        )
    if delegate_task:
        recipient_name = re.sub(r"\s+at$", "", delegate_task.group(1).strip())
        return VoiceIntent(transcript, "inbox_delegate_spoken", {"recipient_name": recipient_name, "title": delegate_task.group(2).strip()})
    pilot_message = re.match(r"^(?:send|tell)\s+(.+?)\s+(?:a message\s+)?(?:saying|that)\s+(.+)$", command)
    if pilot_message:
        return VoiceIntent(transcript, "inbox_message_spoken", {"recipient_name": pilot_message.group(1).strip(), "body": pilot_message.group(2).strip()})
    if any(term in command for term in ("continue last game", "continue my game", "resume last game", "resume my game")):
        return VoiceIntent(transcript, "game_continue", {})
    game_search = re.search(
        r"\b(?:find|search for|play)\s+(.+?)(?:\s+(?:on|in)\s+(?:geforce now|games?))?$",
        command,
    )
    if game_search and any(term in command for term in ("game", "geforce", "gaming")):
        query = re.sub(r"\b(?:a |the )?game\b|\bcalled\b", " ", game_search.group(1))
        query = re.sub(r"\s+", " ", query).strip()
        return VoiceIntent(transcript, "open_games", {"query": query})
    if any(
        term in command
        for term in ("open games", "open gaming", "open geforce now", "launch geforce now", "gaming mode")
    ):
        return VoiceIntent(transcript, "open_games", {})
    if any(term in command for term in ("movie mode", "cinema mode")):
        return VoiceIntent(transcript, "scene_movie", {"app_id": "netflix", "volume": 20})
    entertainment_memory = re.search(r"\b(?:remember (?:that )?we (?:watched|have seen)|we already (?:watched|saw))\s+(.+)", command)
    if entertainment_memory:
        return VoiceIntent(transcript, "entertainment_feedback", {"title": entertainment_memory.group(1).strip(), "outcome": "watched"})
    avoid_title = re.search(r"\b(?:don t recommend|avoid)\s+(.+)", command)
    if avoid_title:
        return VoiceIntent(transcript, "entertainment_feedback", {"title": avoid_title.group(1).strip(), "outcome": "avoid"})
    disliked_title = re.search(r"\bwe (?:didn t like|disliked)\s+(.+)", command)
    if disliked_title:
        return VoiceIntent(transcript, "entertainment_feedback", {"title": disliked_title.group(1).strip(), "outcome": "disliked"})
    liked_title = re.search(r"\bwe (?:really )?(?:liked|loved)\s+(.+)", command)
    if liked_title:
        return VoiceIntent(transcript, "entertainment_feedback", {"title": liked_title.group(1).strip(), "outcome": "liked"})
    availability = re.search(r"\bwhere can (?:we|i) watch\s+(.+)", command)
    if availability:
        return VoiceIntent(transcript, "entertainment_search", {"query": availability.group(1).strip()})
    cross_service = re.search(r"\b(?:search|find) (?:all |across )?(?:the )?streaming (?:apps|services)(?: for)?\s+(.+)", command)
    if cross_service:
        return VoiceIntent(transcript, "entertainment_search", {"query": cross_service.group(1).strip()})
    if (
        any(term in command for term in ("what should we watch", "recommend something", "find us something to watch", "show us something to watch"))
        or re.search(r"\bfind us (?:a|an|some) .*(?:film|movie|series|show)\b", command)
    ):
        duration = re.search(r"\b(?:under|about|around|within)\s+(\d{2,3})\s+minutes?\b", command)
        return VoiceIntent(
            transcript,
            "entertainment_recommend",
            {"query": command, **({"minutes": int(duration.group(1))} if duration else {})},
        )
    if any(term in command for term in ("continue what i was watching", "continue watching", "resume what i was watching")):
        return VoiceIntent(transcript, "continue_last", {})
    if any(term in command for term in ("make this comfortable for tonight", "comfortable for tonight", "evening mode")):
        return VoiceIntent(transcript, "scene_evening", {"volume": 18})
    if any(term in command for term in (
        "verify that product claim", "fact check that product", "is that product claim true",
        "check that advert claim", "fact check that advert",
    )):
        return VoiceIntent(transcript, "live_fact_check", {"kind": "product_claim"})
    if any(
        term in command
        for term in ("fact check that", "fact check this", "check if that is true", "is that true", "verify that claim")
    ):
        return VoiceIntent(transcript, "live_fact_check", {})
    if any(term in command for term in ("who disagrees", "who disagrees with that", "what sources disagree")):
        return VoiceIntent(transcript, "live_fact_followup", {"kind": "disagreement"})
    if any(term in command for term in ("explain the difference", "what is the difference", "why are they different")):
        return VoiceIntent(transcript, "live_fact_followup", {"kind": "difference"})
    if any(term in command for term in ("show me the evidence", "show the evidence", "what is the evidence")):
        return VoiceIntent(transcript, "live_fact_followup", {"kind": "evidence"})
    character = re.match(r"^who plays\s+(.+?)(?:\s+in (?:this|the show|the programme|the program))?$", command)
    if character:
        return VoiceIntent(
            transcript,
            "programme_cast",
            {"kind": "character", "character": character.group(1).strip()},
        )
    person_credits = re.match(r"^(?:what else (?:has|was)|what other (?:shows|programmes|programs|series) (?:has|was)|show me more with)\s+(.+?)(?:\s+(?:been in|in))?$", command)
    if person_credits:
        person = re.sub(r"\s+(?:been in|in)$", "", person_credits.group(1)).strip()
        return VoiceIntent(transcript, "programme_cast", {"kind": "credits", "person": person})
    if any(term in command for term in (
        "who is that actor", "who is this actor", "who is that actress", "who is this actress",
    )):
        return VoiceIntent(transcript, "programme_cast", {"kind": "visible_actor"})
    if any(term in command for term in (
        "who is in this", "who s in this", "who stars in this", "show me the cast",
        "show the cast", "who is in this programme", "who is in this show",
    )):
        return VoiceIntent(transcript, "programme_cast", {"kind": "cast"})
    if any(term in command for term in ("where was this filmed", "where did they film this", "show me the filming location")):
        return VoiceIntent(transcript, "programme_origin", {"kind": "filming_location"})
    if any(term in command for term in ("where is this set", "where does this take place", "what is the setting")):
        return VoiceIntent(transcript, "programme_origin", {"kind": "setting"})
    if any(term in command for term in (
        "what is this based on", "what was this based on", "is this based on a book",
        "what is the original source", "show me the original source",
    )):
        return VoiceIntent(transcript, "programme_origin", {"kind": "original_source"})
    learning = re.search(r"(?:teach|turn) (?:the )?(?:children|kids|child|this scene).*?\b(science|history|language)\b|\b(science|history|language) (?:lesson|activity) (?:from|about) this", command)
    if learning:
        subject = next(value for value in learning.groups() if value)
        return VoiceIntent(
            transcript,
            "live_explain",
            {"kind": "learning", "audience": "child", "detail_level": "simple", "learning_subject": subject},
        )
    if any(term in command for term in (
        "describe this scene", "describe what is happening", "what is happening visually",
        "audio describe this", "give me a scene description",
    )):
        return VoiceIntent(transcript, "live_explain", {"kind": "accessibility", "detail_level": "detailed"})
    if any(term in command for term in ("why is that funny", "explain that joke", "what was the joke", "why was that a joke")):
        return VoiceIntent(transcript, "live_explain", {"kind": "joke", "detail_level": "normal"})
    if any(term in command for term in (
        "explain that reference", "what does that reference mean", "what is that reference",
        "explain the cultural context", "what is the cultural context",
    )):
        kind = "cultural_context" if "cultural" in command else "reference"
        return VoiceIntent(transcript, "live_explain", {"kind": kind, "detail_level": "detailed"})
    if any(term in command for term in (
        "explain this to a child", "explain that to a child", "explain this for a child",
        "explain that for a child", "explain this to the kids", "explain that to the kids",
    )):
        return VoiceIntent(transcript, "live_explain", {"kind": "scene", "audience": "child", "detail_level": "simple"})
    if any(term in command for term in ("explain this simply", "explain that simply", "give me a simple explanation")):
        return VoiceIntent(transcript, "live_explain", {"kind": "scene", "detail_level": "simple"})
    if any(term in command for term in ("explain this in detail", "explain that in detail", "give me a detailed explanation")):
        return VoiceIntent(transcript, "live_explain", {"kind": "scene", "detail_level": "detailed"})
    if not any(term in command for term in ("referee", "foul", "penalty", "offside", "yellow card", "red card", "var")) and any(
        term in command
        for term in ("what just happened", "explain that", "what did they just say", "what was just said", "explain what just happened", "explain this scene", "explain without spoilers")
    ):
        kind = "dialogue" if any(term in command for term in ("what did they just say", "what was just said")) else "recap" if "what just happened" in command else "scene"
        return VoiceIntent(transcript, "live_explain", {"kind": kind, "spoiler_policy": "observed_evidence_only"})
    translation = re.search(r"\btranslate (?:that|this|what (?:they|he|she) (?:said|says)|the subtitle)(?: (?:into|to) (english|spanish|french|german|italian|portuguese))?\b", command)
    if translation or any(term in command for term in ("what does that mean in english", "say that in english")):
        target = translation.group(1) if translation and translation.group(1) else "english"
        source_kind = "subtitle" if "subtitle" in command else "dialogue"
        return VoiceIntent(transcript, "live_translate", {"target_language": target, "source_kind": source_kind})
    if any(term in command for term in ("why was that a foul", "why was that a penalty", "why was that offside", "explain that referee decision", "explain that decision", "what was that call", "why did the referee")):
        return VoiceIntent(transcript, "live_sports", {"kind": "decision", "question": command})
    if any(term in command for term in ("what is the score", "what s the score", "read the scoreboard", "who is winning", "who s winning")):
        kind = "leader" if "winning" in command else "score"
        return VoiceIntent(transcript, "live_event", {"kind": kind, "question": command})
    if any(term in command for term in ("who scored", "who scored the last goal", "who got the goal")):
        return VoiceIntent(transcript, "live_event", {"kind": "scorer", "question": command})
    if any(term in command for term in ("show the statistics", "show me the statistics", "show the stats", "match statistics", "player statistics")):
        return VoiceIntent(transcript, "live_event", {"kind": "statistics", "question": command})
    if any(term in command for term in ("show the incident timeline", "show match timeline", "what incidents happened", "show the match incidents")):
        return VoiceIntent(transcript, "live_event", {"kind": "timeline", "question": command})
    historical = re.search(r"\b(?:compare|show)(?: me)? (.+?) (?:statistics |stats )?(?:over|for|in) the last (\d{1,3}) days?\b", command)
    if historical:
        days = int(historical.group(2))
        return VoiceIntent(transcript, "live_event", {"kind": "historical_statistics", "question": command, "history_days": days})
    if any(term in command for term in ("show the fixtures", "what are the fixtures", "next fixtures", "upcoming matches")):
        return VoiceIntent(transcript, "live_event", {"kind": "fixtures", "question": command})
    close_watch = re.search(r"\bnotify me when (?:this|the) (?:match|game) (?:becomes|gets|is) (?:close|within (\d+) goals?)\b", command)
    if close_watch:
        return VoiceIntent(transcript, "live_engagement", {"kind": "close_watch", "margin": int(close_watch.group(1) or 1)})
    if any(term in command for term in ("show upcoming concerts", "find live events", "show upcoming events", "show awards events")):
        kind = "concerts" if "concert" in command else "awards" if "award" in command else "events"
        return VoiceIntent(transcript, "live_event", {"kind": kind, "question": command})
    private_save = re.search(r"\b(?:save|remember|keep|add) (?:this|that) (product|recipe|destination|place|song|music|idea|concept)(?: to my phone| for later)?\b", command)
    if private_save:
        category = {"place": "destination", "song": "music", "concept": "learning"}.get(private_save.group(1), private_save.group(1))
        return VoiceIntent(transcript, "private_save_prepare", {"category": category})
    if any(term in command for term in ("add this idea to my phone", "save this to my phone", "remember this for later")):
        return VoiceIntent(transcript, "private_save_prepare", {"category": "idea"})
    if any(term in command for term in ("what is on the screen", "what s on the screen", "understand this screen", "describe the screen")):
        return VoiceIntent(transcript, "screen_query", {"kind": "scene"})
    if any(term in command for term in ("what does the subtitle say", "read the subtitle", "translate that subtitle")):
        return VoiceIntent(transcript, "screen_query", {"kind": "subtitle"})
    if any(term in command for term in ("what product is that", "what is that product")):
        return VoiceIntent(transcript, "screen_query", {"kind": "product"})
    if any(term in command for term in ("what ingredients are they using", "what ingredients are being used", "what ingredients can you see")):
        return VoiceIntent(transcript, "screen_query", {"kind": "ingredients"})
    if any(term in command for term in ("what cooking technique is that", "what technique are they using", "how are they cooking that")):
        return VoiceIntent(transcript, "screen_query", {"kind": "technique"})
    if any(term in command for term in ("what objects can you see", "what objects are on screen", "identify the objects")):
        return VoiceIntent(transcript, "screen_query", {"kind": "objects"})
    moment = re.search(r"\b(?:clip|share|save|send)\b.*\b(?:that|this|it|scene|moment)\b", command)
    if moment:
        seconds = re.search(r"\b(\d{1,2})\s+seconds?\b", command)
        recipient = re.search(r"\bto (.+)$", command)
        return VoiceIntent(
            transcript,
            "share_moment",
            {
                "seconds": min(int(seconds.group(1)), 30) if seconds else 30,
                **({"recipient": recipient.group(1).strip()} if recipient else {}),
            },
        )
    if any(term in command for term in (
        "show my results again", "show the results again", "reopen my results",
        "show my search results again",
    )):
        return VoiceIntent(transcript, "show_research_results", {})
    result_words = {"first": 1, "one": 1, "1": 1, "second": 2, "two": 2, "2": 2, "third": 3, "three": 3, "3": 3, "fourth": 4, "four": 4, "4": 4, "fifth": 5, "five": 5, "5": 5}
    result_match = re.search(
        r"\bopen(?: the)? (first|one|1|second|two|2|third|three|3|fourth|four|4|fifth|five|5)(?:(?: result| one)\b|$)",
        command,
    )
    if result_match:
        return VoiceIntent(transcript, "open_research_result", {"result_index": result_words[result_match.group(1)]})
    if (
        "netflix" in command
        and any(term in command for term in ("search", "find", "play", "watch"))
        and "profile" not in command
        and "search google" not in command
        and "search the web" not in command
    ):
        query = re.sub(r"\b(?:search|find|play|watch|for|on|netflix|me|please)\b", " ", command)
        query = re.sub(r"\s+", " ", query).strip()
        if query:
            return VoiceIntent(transcript, "netflix_search", {"query": query})
    explicit_web_match = re.search(r"\b(?:search (?:google|the web) for)\s+(.+)", command)
    if explicit_web_match:
        return VoiceIntent(transcript, "web_research", {"query": explicit_web_match.group(1).strip(), "mode": "general"})
    contextual_search_match = re.search(r"\bsearch for\s+(.+)", command)
    if contextual_search_match:
        return VoiceIntent(transcript, "web_research", {"query": contextual_search_match.group(1).strip(), "mode": "contextual"})
    research_match = re.search(r"\b(?:find me|look for|research)\s+(.+)", command)
    if research_match:
        return VoiceIntent(transcript, "web_research", {"query": research_match.group(1).strip(), "mode": "general"})
    if "profile" in command and "netflix" in command and any(term in command for term in ("my profile", "my netflix profile", "saved profile", "remembered profile")):
        return VoiceIntent(transcript, "netflix_saved_profile", {})
    if command in {"open netflix profiles", "open netflix profile chooser", "show netflix profiles", "switch netflix profile"}:
        return VoiceIntent(transcript, "netflix_profile_menu", {})
    number_words = {"first": 1, "one": 1, "1": 1, "second": 2, "two": 2, "2": 2, "third": 3, "three": 3, "3": 3, "fourth": 4, "four": 4, "4": 4, "fifth": 5, "five": 5, "5": 5}
    visible_profile_match = re.search(
        r"\b(?:select|choose) visible (first|one|1|second|two|2|third|three|3|fourth|four|4|fifth|five|5)(?: netflix)? profile\b",
        command,
    )
    if visible_profile_match:
        return VoiceIntent(
            transcript,
            "netflix_profile",
            {
                "profile_index": number_words[visible_profile_match.group(1)],
                "remember": False,
                "chooser_visible": True,
            },
        )
    switch_profile_match = re.search(
        r"\b(?:switch|change|swap)(?: netflix)? profile(?: to)? (first|one|1|second|two|2|third|three|3|fourth|four|4|fifth|five|5)\b",
        command,
    )
    if switch_profile_match:
        return VoiceIntent(
            transcript,
            "netflix_profile",
            {"profile_index": number_words[switch_profile_match.group(1)], "remember": False},
        )
    profile_match = re.search(r"\b(first|one|1|second|two|2|third|three|3|fourth|four|4|fifth|five|5)\b(?: netflix)? profile", command)
    if profile_match and any(term in command for term in ("select", "choose", "use", "open", "remember", "default", "switch", "change", "swap")):
        return VoiceIntent(
            transcript,
            "netflix_profile",
            {
                "profile_index": number_words[profile_match.group(1)],
                "remember": "remember" in command or "default" in command,
            },
        )
    remote_buttons = {
        "go left": "LEFT", "move left": "LEFT",
        "go right": "RIGHT", "move right": "RIGHT",
        "go up": "UP", "move up": "UP",
        "go down": "DOWN", "move down": "DOWN",
        "select": "ENTER", "press ok": "ENTER", "click it": "ENTER",
        "go back": "BACK", "back": "BACK",
        "go home": "HOME", "home": "HOME", "home screen": "HOME", "show home screen": "HOME",
    }
    if command in {"accept", "accept cookies", "accept all", "accept the cookies", "accept google", "accept google cookies"}:
        return VoiceIntent(transcript, "google_consent_accept", {"button": "ENTER"})
    for phrase, button in remote_buttons.items():
        if command == phrase or command.startswith(f"{phrase} "):
            return VoiceIntent(transcript, "remote_button", {"button": button})
    volume_match = re.search(r"(?:set|put)(?: the)?(?: tv| television)? volume(?: to| at)? (\d{1,3})", command)
    if volume_match:
        return VoiceIntent(transcript, "set_volume", {"volume": int(volume_match.group(1))})
    if any(term in command for term in ("turn up", "volume up", "louder", "increase the volume")):
        return VoiceIntent(transcript, "change_volume", {"delta": 2})
    if any(term in command for term in ("turn down", "volume down", "quieter", "decrease the volume")):
        return VoiceIntent(transcript, "change_volume", {"delta": -2})
    if re.search(r"\bwhat(?: is|'s)?(?: the)?(?: tv| television)? volume\b", command):
        return VoiceIntent(transcript, "get_volume", {})
    if "unmute" in command:
        return VoiceIntent(transcript, "set_mute", {"muted": False})
    if re.search(r"\bmute\b", command):
        return VoiceIntent(transcript, "set_mute", {"muted": True})
    if re.search(r"\b(pause|hold)\b", command):
        return VoiceIntent(transcript, "media_pause", {})
    if re.search(r"\b(resume|play)\b", command):
        return VoiceIntent(transcript, "media_play", {})
    if "stop the tv" in command or "stop playback" in command or "stop playing" in command:
        return VoiceIntent(transcript, "media_stop", {})
    input_match = re.search(r"(?:switch|change|go)(?: the tv)? to hdmi ([1-4])", command)
    if input_match:
        return VoiceIntent(transcript, "switch_input", {"input_id": f"HDMI_{input_match.group(1)}"})
    if "netflix" in command and any(term in command for term in ("open", "launch", "put on", "start")):
        return VoiceIntent(transcript, "launch_app", {"app_id": "netflix"})
    if "youtube" in command and any(term in command for term in ("open", "launch", "put on", "start")):
        return VoiceIntent(transcript, "launch_app", {"app_id": "youtube.leanback.v4"})
    if re.match(r"^(?:what|who|where|when|why|how|which|tell me about|recommend)\b", command):
        return VoiceIntent(transcript, "web_research", {"query": command, "mode": "general"})
    if any(term in command for term in ("turn off", "power off", "switch off")):
        return VoiceIntent(transcript, "blocked_power", {})
    refinement = re.match(r"^(?:update|refine|change) the plan(?: with)?\s+(.+)", command)
    if refinement:
        return VoiceIntent(transcript, "agent_request", {"refinement": refinement.group(1).strip()})
    # Direct commands aimed at a known device or Pilot surface must never be
    # reinterpreted as open-ended planning.  If a deterministic adapter did not
    # match above, fail closed and explain that the control is not yet enabled.
    direct_verb = re.match(
        r"^(?:open|show|launch|start|stop|exit|close|take|acquire|control|turn|switch|change|set|select|choose|press|click|move|go|play|pause|resume|mute|unmute|connect|disconnect|lock|unlock|log|sign)\b",
        command,
    )
    direct_target = re.search(
        r"\b(?:tv|television|pilot|dashboard|home screen|netflix|youtube|profile|volume|hdmi|games?|gaming|geforce|board ?room|calendar|tasks?|to ?do|files?|documents?|iot|devices?|air con|air conditioning|god view|iss)\b",
        command,
    )
    if direct_verb and direct_target:
        return VoiceIntent(transcript, "unknown", {"deterministic_command": command})
    return VoiceIntent(transcript, "agent_request", {"request": command})


class VoiceControlService:
    """Local, ephemeral-audio voice node using the Mac microphone and cached Whisper."""

    def __init__(
        self,
        handler: Callable[[str], Dict[str, Any]],
        *,
        model_name: str | None = None,
        settings_path: str | Path | None = None,
    ) -> None:
        self.handler = handler
        self.model_name = model_name or os.getenv("AION_SPEECH_MODEL_PATH", "base")
        self.settings_path = Path(settings_path) if settings_path else None
        self._stop = threading.Event()
        self._sleep = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._follow_up: Dict[str, Any] | None = None
        self._follow_up_until = 0.0
        self._audio_ring: deque[Any] = deque(maxlen=300)
        self._activity_history: deque[Dict[str, Any]] = deque(maxlen=40)
        self._model: Any | None = None
        self._model_lock = threading.Lock()
        self._status: Dict[str, Any] = {
            "running": False,
            "ready": False,
            "privacy": "raw_audio_ephemeral_local_only",
            "wake_phrases": ["Pilot", "Hey Pilot"],
            "last_transcript": "",
            "last_heard_transcript": "",
            "last_result": "",
            "heard_utterances": 0,
            "wake_matches": 0,
            "audio_rms": 0.0,
            "speech_threshold": 0.012,
            "error": "",
            "recent_heard": [],
            "conversation": "idle",
            "sleeping": False,
            "microphone": "closed",
            "ephemeral_audio_buffer_seconds": 0.0,
            "raw_audio_retained": False,
            "activity_state": "off",
            "activity_history": [],
            "voice_name": "Daniel",
            "speech_rate": 185,
            "quiet_mode": False,
            "quiet_start": "",
            "quiet_end": "",
            "quiet_schedule_active": False,
        }
        if self.settings_path and self.settings_path.exists():
            try:
                saved = json.loads(self.settings_path.read_text(encoding="utf-8"))
                if isinstance(saved, dict):
                    self.set_preferences(
                        voice_name=saved.get("voice_name"),
                        speech_rate=saved.get("speech_rate"),
                        quiet_mode=saved.get("quiet_mode"),
                        quiet_start=saved.get("quiet_start"),
                        quiet_end=saved.get("quiet_end"),
                        persist=False,
                    )
            except (OSError, ValueError, json.JSONDecodeError):
                pass

    def _transition(self, state: str, *, outcome: str = "") -> None:
        """Publish a privacy-safe lifecycle event without transcript content."""
        state = str(state).strip().lower()
        if state not in {"off", "sleeping", "listening", "hearing", "thinking", "acting", "speaking", "completed", "cancelled", "error"}:
            raise ValueError("Unknown voice lifecycle state")
        with self._lock:
            if self._status.get("activity_state") != state or outcome:
                self._activity_history.append({
                    "state": state,
                    "at_unix": round(time.time(), 3),
                    "outcome": str(outcome)[:80],
                    "contains_transcript": False,
                    "contains_audio": False,
                })
            self._status["activity_state"] = state
            self._status["activity_history"] = list(self._activity_history)

    @staticmethod
    def _normalise_clock(value: str | None) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", text):
            raise ValueError("Quiet hours must use 24-hour HH:MM times")
        return text

    @staticmethod
    def _within_quiet_schedule(start: str, end: str, *, now_minutes: int) -> bool:
        if not start or not end or start == end:
            return False
        start_minutes = int(start[:2]) * 60 + int(start[3:])
        end_minutes = int(end[:2]) * 60 + int(end[3:])
        if start_minutes < end_minutes:
            return start_minutes <= now_minutes < end_minutes
        return now_minutes >= start_minutes or now_minutes < end_minutes

    def set_preferences(self, *, voice_name: str | None = None, speech_rate: int | None = None, quiet_mode: bool | None = None, quiet_start: str | None = None, quiet_end: str | None = None, persist: bool = True) -> Dict[str, Any]:
        allowed_voices = {"Daniel", "Samantha", "Karen", "Mónica", "Thomas", "Anna", "Alice", "Joana"}
        values: Dict[str, Any] = {}
        if voice_name is not None:
            if voice_name not in allowed_voices:
                raise ValueError("Unsupported local voice")
            values["voice_name"] = voice_name
        if speech_rate is not None:
            values["speech_rate"] = max(120, min(int(speech_rate), 240))
        if quiet_mode is not None:
            values["quiet_mode"] = bool(quiet_mode)
        current = self.status()
        if quiet_start is not None:
            values["quiet_start"] = self._normalise_clock(quiet_start)
        if quiet_end is not None:
            values["quiet_end"] = self._normalise_clock(quiet_end)
        effective_start = str(values.get("quiet_start", current.get("quiet_start") or ""))
        effective_end = str(values.get("quiet_end", current.get("quiet_end") or ""))
        values["quiet_schedule_active"] = bool(effective_start and effective_end and effective_start != effective_end)
        self._set_status(**values)
        if persist and self.settings_path:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.settings_path.with_suffix(".tmp")
            current = self.status()
            temporary.write_text(json.dumps({
                "voice_name": current["voice_name"],
                "speech_rate": current["speech_rate"],
                "quiet_mode": current["quiet_mode"],
                "quiet_start": current["quiet_start"],
                "quiet_end": current["quiet_end"],
            }, sort_keys=True), encoding="utf-8")
            os.replace(temporary, self.settings_path)
        return self.status()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._sleep.clear()
        self._set_status(sleeping=False, privacy="raw_audio_ephemeral_local_only")
        self._transition("listening")
        self._thread = threading.Thread(target=self._run, name="aion-local-voice", daemon=True)
        self._thread.start()

    def sleep(self) -> None:
        self._sleep.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=4)
        self._audio_ring.clear()
        self._set_status(
            running=False,
            ready=False,
            sleeping=True,
            microphone="closed",
            privacy="microphone_closed_no_audio_capture",
            conversation="sleeping",
            audio_rms=0.0,
            ephemeral_audio_buffer_seconds=0.0,
        )
        self._transition("sleeping")

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=4)
        self._audio_ring.clear()
        self._set_status(ephemeral_audio_buffer_seconds=0.0)

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._status)

    def recent_context(self, *, exclude_latest: bool = True) -> list[str]:
        """Return only recent local transcripts; raw audio never leaves the voice service."""
        recent = list(self.status().get("recent_heard", []))
        if exclude_latest and recent:
            recent.pop()
        return [str(item)[:320] for item in recent[-4:]]

    def _set_status(self, **values: Any) -> None:
        with self._lock:
            self._status.update(values)

    def _load_model(self) -> Any:
        with self._model_lock:
            if self._model is None:
                from faster_whisper import WhisperModel

                self._model = WhisperModel(
                    self.model_name,
                    device="cpu",
                    compute_type="int8",
                    local_files_only=True,
                )
            return self._model

    def transcribe_push_to_talk(self, payload: bytes, media_type: str) -> str:
        """Transcribe one explicitly captured phone utterance, then destroy the audio."""
        if not payload or len(payload) > 3 * 1024 * 1024:
            raise ValueError("Push-to-talk audio must contain 1 byte to 3 MiB")
        kind = media_type.split(";", 1)[0].strip().lower()
        suffix = {
            "audio/mp4": ".m4a", "audio/x-m4a": ".m4a", "audio/webm": ".webm",
            "audio/wav": ".wav", "audio/mpeg": ".mp3",
        }.get(kind)
        if suffix is None:
            raise ValueError("Unsupported push-to-talk audio format")
        temporary_path = ""
        try:
            with tempfile.NamedTemporaryFile(prefix="pilot-ptt-", suffix=suffix, delete=False) as temporary:
                temporary.write(payload)
                temporary.flush()
                os.fchmod(temporary.fileno(), 0o600)
                temporary_path = temporary.name
            model = self._load_model()
            with self._model_lock:
                segments, _ = model.transcribe(
                    temporary_path, language="en", beam_size=3, vad_filter=True,
                    condition_on_previous_text=False, initial_prompt="Pilot.",
                )
                transcript = " ".join(segment.text.strip() for segment in segments).strip()
            if not transcript:
                raise ValueError("No speech was detected")
            status = self.status()
            self._set_status(
                last_phone_transcript=transcript[:320],
                phone_push_to_talk_count=int(status.get("phone_push_to_talk_count", 0)) + 1,
            )
            return transcript[:320]
        finally:
            if temporary_path:
                try:
                    os.unlink(temporary_path)
                except FileNotFoundError:
                    pass

    def _speak(self, text: str, *, language: str = "en") -> None:
        voices = {"en": "Daniel", "es": "Mónica", "fr": "Thomas", "de": "Anna", "it": "Alice", "pt": "Joana"}
        status = self.status()
        now = datetime.now().astimezone()
        scheduled_quiet = self._within_quiet_schedule(
            str(status.get("quiet_start") or ""),
            str(status.get("quiet_end") or ""),
            now_minutes=now.hour * 60 + now.minute,
        )
        self._set_status(quiet_schedule_effective=scheduled_quiet)
        if status.get("quiet_mode") or scheduled_quiet:
            return
        selected_voice = str(status.get("voice_name") or voices.get(language) or "Daniel")
        command = ["/usr/bin/say"]
        command.extend(["-v", voices.get(language, selected_voice) if language != "en" else selected_voice])
        command.extend(["-r", str(int(status.get("speech_rate") or 185))])
        command.append(text[:300])
        subprocess.run(command, check=False, timeout=20)

    def _resolve_follow_up(self, transcript: str) -> str | None:
        if not self._follow_up or time.monotonic() > self._follow_up_until:
            self._follow_up = None
            return None
        normalized = re.sub(r"[^a-z0-9 ]+", " ", transcript.lower()).strip()
        normalized = re.sub(r"\s+", " ", normalized)
        if self._follow_up.get("kind") == "netflix_profile":
            positions = {
                "first": "first", "second": "second", "third": "third",
                "fourth": "fourth", "fifth": "fifth",
                "one": "first", "1": "first", "two": "second", "2": "second",
                "three": "third", "3": "third", "four": "fourth", "4": "fourth",
                "five": "fifth", "5": "fifth",
            }
            for word, ordinal in positions.items():
                if re.search(rf"\b{re.escape(word)}\b", normalized):
                    return f"Pilot select the {ordinal} Netflix profile"
        if self._follow_up.get("kind") == "research_result":
            positions = {
                "first": "first", "second": "second", "third": "third",
                "fourth": "fourth", "fifth": "fifth",
                "one": "first", "1": "first", "two": "second", "2": "second",
                "three": "third", "3": "third", "four": "fourth", "4": "fourth",
                "five": "fifth", "5": "fifth",
            }
            for word, ordinal in positions.items():
                if re.search(rf"\b{re.escape(word)}\b", normalized):
                    return f"Pilot open the {ordinal} result"
        god_view_candidate = parse_voice_intent(f"Pilot {normalized}")
        if (
            god_view_candidate is not None
            and god_view_candidate.action == "show_canvas"
            and god_view_candidate.arguments.get("view") == "god_view"
        ):
            return f"Pilot {normalized}"
        if self._follow_up.get("kind") == "agent_refinement" and self._plausible_agent_follow_up(normalized):
            return f"Pilot update the plan with {normalized}"
        return None

    @staticmethod
    def _plausible_agent_follow_up(normalized: str) -> bool:
        """Reject likely television/background dialogue during a brief reply window."""
        words = normalized.split()
        if not 1 <= len(words) <= 12:
            return False
        rejected_starts = (
            "wait", "okay", "ok ", "you know", "i will", "ill ", "want me",
            "what ", "who ", "where ", "why ", "how ", "go on", "come on",
        )
        rejected_fragments = (
            "welcome to", "subscribe", "channel", "episode", "commercial",
            "never going to", "thanks for watching",
        )
        if normalized in {"ok", "okay", "yes", "no", "yeah", "right"}:
            return False
        return not normalized.startswith(rejected_starts) and not any(item in normalized for item in rejected_fragments)

    def _run(self) -> None:
        try:
            import numpy as np
            import sounddevice as sd

            self._set_status(running=True, ready=False, error="loading local speech model")
            model = self._load_model()
            audio_queue: queue.Queue[Any] = queue.Queue(maxsize=200)

            def callback(indata, frames, time_info, status):  # type: ignore[no-untyped-def]
                if self._stop.is_set() or self._sleep.is_set():
                    return
                try:
                    block = indata[:, 0].copy()
                    self._audio_ring.append(block)
                    self._set_status(ephemeral_audio_buffer_seconds=round(len(self._audio_ring) / 10, 1))
                    audio_queue.put_nowait(block)
                except queue.Full:
                    pass

            samplerate = 16000
            self._set_status(ready=True, error="", microphone="default Mac input")
            with sd.InputStream(
                samplerate=samplerate,
                channels=1,
                dtype="float32",
                blocksize=1600,
                callback=callback,
            ):
                pre_roll: deque[Any] = deque(maxlen=4)
                utterance: list[Any] = []
                speaking = False
                silence_blocks = 0
                level_blocks = 0
                while not self._stop.is_set() and not self._sleep.is_set():
                    try:
                        block = audio_queue.get(timeout=0.5)
                    except queue.Empty:
                        continue
                    rms = float(np.sqrt(np.mean(np.square(block))))
                    level_blocks += 1
                    if level_blocks % 5 == 0:
                        self._set_status(audio_rms=round(rms, 6))
                    voiced = rms >= 0.012
                    if not speaking:
                        pre_roll.append(block)
                        if voiced:
                            self._transition("hearing")
                            speaking = True
                            utterance = list(pre_roll)
                            silence_blocks = 0
                    else:
                        utterance.append(block)
                        silence_blocks = 0 if voiced else silence_blocks + 1
                        duration = sum(len(item) for item in utterance) / samplerate
                        if silence_blocks < 8 and duration < 10:
                            continue
                        speaking = False
                        pre_roll.clear()
                        if duration < 0.45:
                            utterance = []
                            continue
                        audio = np.concatenate(utterance).astype(np.float32)
                        utterance = []
                        with self._model_lock:
                            segments, _ = model.transcribe(
                                audio,
                                language="en",
                                beam_size=3,
                                vad_filter=True,
                                condition_on_previous_text=False,
                                initial_prompt="Pilot.",
                                hotwords=(
                                    "Pilot hey Pilot television TV volume mute unmute Netflix HDMI play pause stop "
                                    "device mesh boardroom briefing movie mode take over profile select"
                                ),
                            )
                        transcript = " ".join(segment.text.strip() for segment in segments).strip()
                        if not transcript:
                            self._transition("listening")
                            continue
                        current_status = self.status()
                        recent = list(current_status.get("recent_heard", []))[-7:]
                        recent.append(transcript)
                        self._set_status(
                            last_heard_transcript=transcript,
                            heard_utterances=int(current_status.get("heard_utterances", 0)) + 1,
                            recent_heard=recent,
                        )
                        intent = parse_voice_intent(transcript)
                        effective_transcript = transcript
                        if intent is None:
                            resolved = self._resolve_follow_up(transcript)
                            if resolved:
                                effective_transcript = resolved
                                intent = parse_voice_intent(resolved)
                        if intent is None:
                            self._set_status(last_result="Ignored: Pilot wake phrase not detected")
                            self._transition("listening", outcome="background_rejected")
                            continue
                        current_status = self.status()
                        self._set_status(
                            last_transcript=transcript,
                            wake_matches=int(current_status.get("wake_matches", 0)) + 1,
                        )
                        try:
                            self._transition("thinking")
                            speech_language = "en"
                            if intent.action == "voice_sleep":
                                result = self.handler(effective_transcript)
                                spoken = str(result.get("spoken_response") or "Going to sleep. Microphone off.")
                                self._follow_up = None
                                self._follow_up_until = 0.0
                                self._set_status(last_result=spoken, conversation="sleeping")
                                self._speak(spoken)
                                self._sleep.set()
                                break
                            if intent.action == "agent_request":
                                self._transition("speaking")
                                self._speak("I am planning that now.")
                            self._transition("acting")
                            result = self.handler(effective_transcript)
                            spoken = str(result.get("spoken_response") or result.get("error") or "Done")
                            speech_language = str(result.get("speech_language") or "en")
                            follow_up = result.get("follow_up")
                            if isinstance(follow_up, dict):
                                self._follow_up = dict(follow_up)
                                self._follow_up_until = time.monotonic() + float(follow_up.get("expires_seconds", 30))
                                self._set_status(conversation=f"awaiting_{follow_up.get('kind', 'follow_up')}")
                            else:
                                self._follow_up = None
                                self._follow_up_until = 0.0
                                self._set_status(conversation="idle")
                        except Exception as exc:
                            spoken = friendly_voice_error(exc, action=intent.action)
                            self._transition("error", outcome=type(exc).__name__)
                        self._set_status(last_result=spoken)
                        while not audio_queue.empty():
                            try:
                                audio_queue.get_nowait()
                            except queue.Empty:
                                break
                        self._transition("speaking")
                        self._speak(spoken, language=speech_language)
                        self._transition("completed", outcome="command_completed")
                        while not audio_queue.empty():
                            try:
                                audio_queue.get_nowait()
                            except queue.Empty:
                                break
        except Exception as exc:
            self._set_status(running=False, ready=False, error=f"{type(exc).__name__}: {exc}")
        finally:
            self._audio_ring.clear()
            sleeping = self._sleep.is_set() and not self._stop.is_set()
            self._set_status(
                running=False,
                ready=False,
                sleeping=sleeping,
                microphone="closed",
                privacy="microphone_closed_no_audio_capture" if sleeping else "raw_audio_ephemeral_local_only",
                audio_rms=0.0,
                ephemeral_audio_buffer_seconds=0.0,
            )
            self._transition("sleeping" if sleeping else "off")
