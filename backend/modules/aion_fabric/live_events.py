from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso


class LiveEventIntelligence:
    """Authenticated live-feed retrieval fused with separately labelled local evidence."""

    FOOTBALL_HOST = "api.football-data.org"
    TICKETMASTER_HOST = "app.ticketmaster.com"
    MAX_RESPONSE_BYTES = 512_000

    def __init__(
        self,
        runtime_dir: str | Path,
        *,
        urlopen: Callable[..., Any] | None = None,
        secret_resolver: Callable[[str], str] | None = None,
    ) -> None:
        self.root = Path(runtime_dir) / "live_events"
        self.latest_path = self.root / "latest.json"
        self.cache_path = self.root / "provider_cache.json"
        self.root.mkdir(parents=True, exist_ok=True)
        self.urlopen = urlopen or urllib.request.urlopen
        self.secret_resolver = secret_resolver or self._environment_secret

    @staticmethod
    def _environment_secret(provider: str) -> str:
        names = {
            "football_data": "PILOT_FOOTBALL_DATA_TOKEN",
            "ticketmaster": "PILOT_TICKETMASTER_API_KEY",
        }
        return str(os.getenv(names.get(provider, ""), "")).strip()

    @staticmethod
    def _read(path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value
        except (OSError, json.JSONDecodeError):
            return default

    @staticmethod
    def _write(path: Path, value: Any) -> None:
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(value))
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)

    @classmethod
    def _read_json_response(cls, response: Any) -> Dict[str, Any]:
        body = response.read(cls.MAX_RESPONSE_BYTES + 1)
        if len(body) > cls.MAX_RESPONSE_BYTES:
            raise RuntimeError("Live-event provider response exceeded its safety limit")
        value = json.loads(body)
        if not isinstance(value, dict):
            raise RuntimeError("Live-event provider returned an invalid response")
        return value

    @staticmethod
    def _token_set(value: str) -> set[str]:
        return {part for part in re.findall(r"[a-z0-9]+", value.lower()) if len(part) > 1}

    @classmethod
    def _match_score(cls, home: str, away: str, observed: Dict[str, Any] | None) -> float:
        if not observed:
            return 0.0
        left = cls._token_set(str(observed.get("left") or ""))
        right = cls._token_set(str(observed.get("right") or ""))
        provider_home, provider_away = cls._token_set(home), cls._token_set(away)
        direct = len(left & provider_home) + len(right & provider_away)
        reverse = len(left & provider_away) + len(right & provider_home)
        denominator = max(1, len(left) + len(right))
        return round(max(direct, reverse) / denominator, 3)

    @staticmethod
    def _score_pair(score: Dict[str, Any]) -> tuple[int | None, int | None]:
        for key in ("fullTime", "regularTime", "halfTime"):
            value = dict(score.get(key) or {})
            home, away = value.get("home"), value.get("away")
            if isinstance(home, int) and isinstance(away, int):
                return home, away
        return None, None

    @classmethod
    def _normalise_match(cls, raw: Dict[str, Any]) -> Dict[str, Any]:
        home = str((raw.get("homeTeam") or {}).get("name") or "Home")[:160]
        away = str((raw.get("awayTeam") or {}).get("name") or "Away")[:160]
        home_score, away_score = cls._score_pair(dict(raw.get("score") or {}))
        goals = []
        for goal in list(raw.get("goals") or [])[-20:]:
            if not isinstance(goal, dict):
                continue
            scorer = str((goal.get("scorer") or {}).get("name") or "")[:160]
            team = str((goal.get("team") or {}).get("name") or "")[:160]
            goals.append(
                {
                    "minute": goal.get("minute"),
                    "injury_time": goal.get("injuryTime"),
                    "scorer": scorer,
                    "team": team,
                    "score": dict(goal.get("score") or {}),
                }
            )
        bookings = []
        for booking in list(raw.get("bookings") or [])[-30:]:
            if not isinstance(booking, dict):
                continue
            bookings.append(
                {
                    "minute": booking.get("minute"),
                    "injury_time": booking.get("injuryTime"),
                    "player": str((booking.get("player") or {}).get("name") or "")[:160],
                    "team": str((booking.get("team") or {}).get("name") or "")[:160],
                    "card": str(booking.get("card") or "")[:40],
                }
            )
        substitutions = []
        for substitution in list(raw.get("substitutions") or [])[-30:]:
            if not isinstance(substitution, dict):
                continue
            substitutions.append(
                {
                    "minute": substitution.get("minute"),
                    "injury_time": substitution.get("injuryTime"),
                    "team": str((substitution.get("team") or {}).get("name") or "")[:160],
                    "player_out": str((substitution.get("playerOut") or {}).get("name") or "")[:160],
                    "player_in": str((substitution.get("playerIn") or {}).get("name") or "")[:160],
                }
            )
        lineups = {}
        for side, key in (("home", "homeTeam"), ("away", "awayTeam")):
            team = dict(raw.get(key) or {})
            lineup = []
            for player in list(team.get("lineup") or [])[:30]:
                if not isinstance(player, dict):
                    continue
                lineup.append({
                    "name": str(player.get("name") or "")[:160],
                    "position": str(player.get("position") or "")[:80],
                    "shirt_number": player.get("shirtNumber"),
                })
            if lineup:
                lineups[side] = lineup
        return {
            "provider_match_id": str(raw.get("id") or "")[:100],
            "competition": str((raw.get("competition") or {}).get("name") or "")[:160],
            "home": home,
            "away": away,
            "home_score": home_score,
            "away_score": away_score,
            "status": str(raw.get("status") or "UNKNOWN")[:40],
            "minute": raw.get("minute"),
            "injury_time": raw.get("injuryTime"),
            "utc_date": str(raw.get("utcDate") or "")[:80],
            "last_updated": str(raw.get("lastUpdated") or "")[:80],
            "goals": goals,
            "bookings": bookings,
            "substitutions": substitutions,
            "lineups": lineups,
        }

    def _football_matches(self, *, include_upcoming: bool, history_days: int | None = None) -> tuple[list[Dict[str, Any]], Dict[str, Any]]:
        token = self.secret_resolver("football_data")
        if len(token) < 8 or any(character.isspace() for character in token):
            return [], {"provider": "football-data.org", "connected": False, "reason": "owner API token not configured"}
        today = datetime.now(timezone.utc).date()
        if history_days is not None:
            bounded_days = max(1, min(int(history_days), 365))
            query = {"dateFrom": (today - timedelta(days=bounded_days)).isoformat(), "dateTo": today.isoformat()}
        else:
            query = {
                "dateFrom": (today - timedelta(days=1)).isoformat(),
                "dateTo": (today + timedelta(days=7 if include_upcoming else 1)).isoformat(),
            }
        url = f"https://{self.FOOTBALL_HOST}/v4/matches?{urllib.parse.urlencode(query)}"
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "Pilot-Fabric/0.47.0 live-event-intelligence",
                "X-Auth-Token": token,
                "X-Unfold-Goals": "true",
            },
        )
        try:
            with self.urlopen(request, timeout=12) as response:
                payload = self._read_json_response(response)
            matches = [self._normalise_match(item) for item in list(payload.get("matches") or [])[:100] if isinstance(item, dict)]
            return matches, {
                "provider": "football-data.org",
                "connected": True,
                "authenticated": True,
                "retrieved_at": utc_now_iso(),
                "request_url": url,
                "raw_response_retained": False,
            }
        except urllib.error.HTTPError as exc:
            reason = f"provider HTTP {exc.code}"
        except (urllib.error.URLError, OSError, json.JSONDecodeError, RuntimeError) as exc:
            reason = str(exc)[:180] or "provider unavailable"
        return [], {"provider": "football-data.org", "connected": True, "authenticated": True, "reason": reason}

    def _ticketmaster_events(self, question: str) -> tuple[list[Dict[str, Any]], Dict[str, Any]]:
        key = self.secret_resolver("ticketmaster")
        if len(key) < 8 or any(character.isspace() for character in key):
            return [], {"provider": "ticketmaster", "connected": False, "reason": "owner API key not configured"}
        keyword = re.sub(r"\b(show|find|upcoming|events?|concerts?|awards?|near me|pilot)\b", " ", question, flags=re.I)
        keyword = " ".join(keyword.split())[:100] or "live"
        query = urllib.parse.urlencode({"keyword": keyword, "countryCode": "ES", "size": 10, "apikey": key})
        url = f"https://{self.TICKETMASTER_HOST}/discovery/v2/events.json?{query}"
        safe_url = f"https://{self.TICKETMASTER_HOST}/discovery/v2/events.json?keyword={urllib.parse.quote(keyword)}&countryCode=ES&size=10"
        request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "Pilot-Fabric/0.47.0 live-event-intelligence"})
        try:
            with self.urlopen(request, timeout=12) as response:
                payload = self._read_json_response(response)
            raw_events = list(((payload.get("_embedded") or {}).get("events") or []))[:10]
            events = []
            for raw in raw_events:
                if not isinstance(raw, dict):
                    continue
                venue = ((raw.get("_embedded") or {}).get("venues") or [{}])[0]
                events.append({
                    "provider_event_id": str(raw.get("id") or "")[:100],
                    "name": str(raw.get("name") or "Event")[:200],
                    "date": str(((raw.get("dates") or {}).get("start") or {}).get("dateTime") or ((raw.get("dates") or {}).get("start") or {}).get("localDate") or "")[:80],
                    "status": str(((raw.get("dates") or {}).get("status") or {}).get("code") or "unknown")[:40],
                    "venue": str((venue or {}).get("name") or "")[:200],
                    "official_url": str(raw.get("url") or "")[:1000] if str(raw.get("url") or "").startswith("https://") else "",
                })
            return events, {"provider": "ticketmaster", "connected": True, "authenticated": True, "retrieved_at": utc_now_iso(), "request_url": safe_url, "raw_response_retained": False}
        except urllib.error.HTTPError as exc:
            reason = f"provider HTTP {exc.code}"
        except (urllib.error.URLError, OSError, json.JSONDecodeError, RuntimeError) as exc:
            reason = str(exc)[:180] or "provider unavailable"
        return [], {"provider": "ticketmaster", "connected": True, "authenticated": True, "reason": reason}

    @staticmethod
    def _provider_score_answer(match: Dict[str, Any]) -> str:
        if match.get("home_score") is None or match.get("away_score") is None:
            return f"The authenticated feed identifies {match['home']} against {match['away']}, but has not supplied a score."
        minute = f" after {match['minute']} minutes" if isinstance(match.get("minute"), int) else ""
        return f"The authenticated feed shows {match['home']} {match['home_score']}, {match['away']} {match['away_score']}{minute}."

    @staticmethod
    def _incident_timeline(match: Dict[str, Any]) -> list[Dict[str, Any]]:
        incidents = []
        for goal in list(match.get("goals") or []):
            incidents.append({"kind": "goal", **goal})
        for booking in list(match.get("bookings") or []):
            incidents.append({"kind": "booking", **booking})
        for substitution in list(match.get("substitutions") or []):
            incidents.append({"kind": "substitution", **substitution})
        return sorted(incidents, key=lambda item: (item.get("minute") if isinstance(item.get("minute"), int) else 999, item.get("injury_time") or 0))[:80]

    @classmethod
    def _historical_summary(cls, matches: list[Dict[str, Any]], question: str, days: int) -> tuple[str, Dict[str, Any] | None]:
        stop = {"pilot", "compare", "show", "statistics", "stats", "history", "historical", "over", "the", "last", "days", "day", "for"}
        requested = cls._token_set(question) - stop - {str(days)}
        candidates: Dict[str, Dict[str, Any]] = {}
        for match in matches:
            for side in ("home", "away"):
                name = str(match.get(side) or "")
                tokens = cls._token_set(name)
                overlap = len(tokens & requested)
                if requested and overlap:
                    entry = candidates.setdefault(name, {"overlap": overlap, "tokens": tokens, "matches": []})
                    entry["overlap"] = max(entry["overlap"], overlap)
                    entry["matches"].append(match)
        if not candidates:
            return "I could not identify one team in the authenticated results for that explicit time range.", None
        ranked = sorted(candidates.items(), key=lambda item: (item[1]["overlap"], len(item[1]["tokens"] & requested)), reverse=True)
        name, selected = ranked[0]
        if len(ranked) > 1 and ranked[1][1]["overlap"] == selected["overlap"] and ranked[1][0] != name:
            return "The requested team is ambiguous in the authenticated results, so I will not merge their statistics.", None
        played = wins = draws = losses = goals_for = goals_against = 0
        for match in selected["matches"]:
            home_score, away_score = match.get("home_score"), match.get("away_score")
            if not isinstance(home_score, int) or not isinstance(away_score, int):
                continue
            is_home = match.get("home") == name
            own, other = (home_score, away_score) if is_home else (away_score, home_score)
            played += 1
            goals_for += own
            goals_against += other
            if own > other:
                wins += 1
            elif own == other:
                draws += 1
            else:
                losses += 1
        summary = {"team": name, "range_days": days, "played": played, "wins": wins, "draws": draws, "losses": losses, "goals_for": goals_for, "goals_against": goals_against}
        if not played:
            return f"The feed found {name}, but no completed scored matches in the selected {days}-day range.", summary
        return f"Across the explicitly selected last {days} days, the authenticated feed records {name}: {played} played, {wins} won, {draws} drawn, {losses} lost, {goals_for} goals for and {goals_against} against.", summary

    def query(
        self,
        *,
        question_kind: str,
        question: str,
        local_interpretation: Dict[str, Any] | None,
        history_days: int | None = None,
    ) -> Dict[str, Any]:
        local = dict(local_interpretation or {})
        observed = dict((local.get("scoreboard") or {}).get("structured") or {})
        is_discovery = question_kind in {"events", "concerts", "awards"}
        matches: list[Dict[str, Any]] = []
        events: list[Dict[str, Any]] = []
        is_history = question_kind == "historical_statistics"
        if is_discovery:
            events, provider = self._ticketmaster_events(question)
        else:
            matches, provider = self._football_matches(include_upcoming=question_kind == "fixtures", history_days=history_days if is_history else None)
        selected = None
        match_confidence = 0.0
        if matches:
            ranked = sorted(
                ((self._match_score(item["home"], item["away"], observed), item) for item in matches),
                key=lambda pair: pair[0],
                reverse=True,
            )
            match_confidence, selected = ranked[0]
            if observed and match_confidence == 0:
                selected = None

        reconciliation = "provider_unavailable"
        if selected and observed:
            left = self._token_set(str(observed.get("left") or ""))
            right = self._token_set(str(observed.get("right") or ""))
            home = self._token_set(str(selected.get("home") or ""))
            away = self._token_set(str(selected.get("away") or ""))
            direct = len(left & home) + len(right & away)
            reverse = len(left & away) + len(right & home)
            provider_pair = (
                (selected.get("home_score"), selected.get("away_score"))
                if direct >= reverse
                else (selected.get("away_score"), selected.get("home_score"))
            )
            observed_pair = (observed.get("left_score"), observed.get("right_score"))
            reconciliation = "screen_and_provider_agree" if provider_pair == observed_pair else "screen_provider_conflict"
        elif selected:
            reconciliation = "provider_only"
        elif observed:
            reconciliation = "screen_only"

        historical_summary = None
        if is_history:
            if history_days is None or not 1 <= int(history_days) <= 365:
                answer = "Choose an explicit historical range between 1 and 365 days so I do not imply an undefined comparison."
                confidence = 0.0
            elif matches:
                answer, historical_summary = self._historical_summary(matches, question, int(history_days))
                confidence = 0.9 if historical_summary and historical_summary.get("played") else 0.35
            else:
                answer = f"I could not retrieve verified historical matches. {provider.get('reason', 'No matches were returned')}."
                confidence = 0.0
        elif is_discovery:
            if events:
                names = "; ".join(f"{item['name']} on {item['date'] or 'date unavailable'}" for item in events[:3])
                answer = f"The authenticated event feed found: {names}."
                confidence = 0.9
            else:
                answer = f"I could not verify matching events. {provider.get('reason', 'The provider returned no results')}."
                confidence = 0.0
        elif question_kind == "fixtures":
            if matches:
                answer = "The authenticated feed lists: " + "; ".join(f"{item['home']} versus {item['away']} at {item['utc_date']}" for item in matches[:3]) + "."
                confidence = 0.88
            else:
                answer = f"I could not retrieve verified fixtures. {provider.get('reason', 'No matches were returned')}."
                confidence = 0.0
        elif selected and question_kind == "scorer":
            goals = list(selected.get("goals") or [])
            if goals and goals[-1].get("scorer"):
                goal = goals[-1]
                answer = f"The authenticated feed attributes the latest recorded goal to {goal['scorer']} for {goal.get('team') or 'the scoring team'}"
                if goal.get("minute") is not None:
                    answer += f" in minute {goal['minute']}"
                answer += "."
                confidence = 0.93
            else:
                answer = "The match is identified, but this provider tier did not return verified scorer data. I will not guess from the picture."
                confidence = 0.45
        elif selected and question_kind == "statistics":
            lineups = dict(selected.get("lineups") or {})
            lineup_count = len(lineups.get("home") or []) + len(lineups.get("away") or [])
            answer = self._provider_score_answer(selected)
            answer += f" The authenticated response includes {lineup_count} lineup entries." if lineup_count else " This provider response does not include verified player statistics for the match."
            confidence = 0.78 if lineup_count else 0.72
        elif selected and question_kind == "timeline":
            timeline = self._incident_timeline(selected)
            if timeline:
                labels = []
                for item in timeline[-8:]:
                    minute = f"{item.get('minute')}' " if item.get("minute") is not None else ""
                    if item["kind"] == "goal":
                        labels.append(f"{minute}goal by {item.get('scorer') or 'unlisted scorer'}")
                    elif item["kind"] == "booking":
                        labels.append(f"{minute}{item.get('card') or 'card'} for {item.get('player') or 'unlisted player'}")
                    else:
                        labels.append(f"{minute}{item.get('player_in') or 'player'} replaced {item.get('player_out') or 'player'}")
                answer = "The authenticated incident timeline records: " + "; ".join(labels) + "."
                confidence = 0.9
            else:
                answer = "The match is identified, but this authenticated response contains no incident timeline."
                confidence = 0.4
        elif selected:
            answer = self._provider_score_answer(selected)
            confidence = 0.92
        else:
            answer = str(local.get("answer") or "I do not have enough current event evidence.")
            if not provider.get("connected"):
                answer += " No authenticated live-event provider is connected to this mother brain."
            confidence = float(local.get("confidence") or 0)

        record: Dict[str, Any] = {
            "schema_version": "pilot.live-event.v1",
            "event_query_id": f"event_{uuid4().hex}",
            "created_at": utc_now_iso(),
            "question_kind": question_kind,
            "question": " ".join(question.split())[:300],
            "answer": answer[:1200],
            "authenticated_provider_fact": selected or (events[:3] if events else None),
            "historical_statistics": historical_summary,
            "screen_observation": (local.get("scoreboard") or None),
            "pilot_interpretation": {
                "rule_key": local.get("rule_key"),
                "rule_explanation": local.get("rule_explanation"),
            },
            "provider": provider,
            "reconciliation": reconciliation,
            "match_confidence": match_confidence,
            "confidence": round(max(0.0, min(float(confidence), 1.0)), 3),
            "provenance": {
                "provider_fact_label": "authenticated provider" if provider.get("authenticated") else "none",
                "screen_fact_label": "owner-captured screen" if local.get("scoreboard") else "none",
                "interpretation_label": "Pilot interpretation" if local.get("rule_explanation") else "none",
                "raw_provider_response_retained": False,
                "provider_secret_projected_to_tv_or_phone": False,
                "paid_ai_used": False,
            },
            "presentation": {"playback_preserved": True, "private_phone_detail": True},
        }
        record["evidence_hash"] = canonical_hash(
            {"provider_fact": record["authenticated_provider_fact"], "screen": record["screen_observation"], "interpretation": record["pilot_interpretation"]}
        )
        record["record_hash"] = canonical_hash(record)
        self._write(self.latest_path, record)
        return record

    def latest(self) -> Dict[str, Any] | None:
        value = self._read(self.latest_path, None)
        return value if isinstance(value, dict) else None

    def status(self) -> Dict[str, Any]:
        return {
            "football_data": {"connected": bool(self.secret_resolver("football_data")), "secret_exposed": False},
            "ticketmaster": {"connected": bool(self.secret_resolver("ticketmaster")), "secret_exposed": False},
            "latest": self.latest(),
        }
