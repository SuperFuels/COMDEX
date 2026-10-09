"""Read-only API and visual panel for AION native English learning."""
from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
import threading
import time

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from backend.modules.aion_cognition.native_english_conversation import NativeEnglishConversation
from backend.modules.aion_cognition.native_english_games import FAMILIES, NativeEnglishGames
from backend.modules.aion_cognition.native_english_transfer import NativeEnglishTransfer
from backend.modules.aion_cognition.native_english_coverage import NativeEnglishCoverage
from backend.modules.aion_cognition.native_english_progress import collect_native_english_progress
from backend.modules.aion_cognition.native_english_practice_gym import NativeEnglishPracticeGym
from backend.modules.aion_cognition.native_semantic_spider import NativeSemanticSpider
from backend.modules.aion_cognition.native_semantic_transfer_academy import NativeSemanticTransferAcademy
from backend.modules.aion_cognition.native_language_workshop import NativeLanguageWorkshop
from backend.modules.aion_cognition.native_reading_academy import NativeReadingAcademy


router = APIRouter(prefix="/api/aion/english-intelligence", tags=["AION English Intelligence"])

_PROGRESS_CACHE_SECONDS = 12.0
_progress_cache: dict = {}
_progress_cache_epoch = 0.0
_progress_lock = threading.Lock()


class NativeQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(default="panel", min_length=1, max_length=120)


class NewGameRequest(BaseModel):
    family: str = Field(default="mixed", max_length=60)
    difficulty: int = Field(default=1, ge=1, le=5)


class GameAnswerRequest(BaseModel):
    answer: str = Field(default="", max_length=4000)
    player: str = Field(default="human", pattern="^(human|aion)$")


class GameCorrectionRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=4000)
    reason: str = Field(default="", max_length=4000)


class ConversationCorrectionRequest(BaseModel):
    proposed_answer: str = Field(min_length=1, max_length=4000)
    reason: str = Field(default="", max_length=4000)
    source_ref: str = Field(default="", max_length=2000)


class TransferChallengeRequest(BaseModel):
    kind: str = Field(default="sentence_qa", pattern="^(sentence_qa|word_order)$")
    material: str = Field(min_length=1, max_length=4000)
    question: str = Field(default="", max_length=2000)
    expected_answer: str = Field(default="", max_length=2000)
    answer_reason: str = Field(default="", max_length=4000)


class SemanticSpiderStartRequest(BaseModel):
    seed: str = Field(default="language", min_length=1, max_length=120)


class ReadingSourceRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=20, max_length=5_000_000)
    author: str = Field(default="Unknown", max_length=300)
    subject: str = Field(default="general", max_length=120)
    license: str = Field(default="owner-provided", max_length=120)
    source_ref: str = Field(default="owner-provided text", max_length=1200)


class ReadingURLRequest(BaseModel):
    url: str = Field(min_length=8, max_length=4000)
    title: str = Field(default="Online reading", max_length=300)
    author: str = Field(default="Unknown", max_length=300)
    subject: str = Field(default="general", max_length=120)


def _repo_root() -> Path:
    return Path(os.getenv("AION_REPO_ROOT") or Path(__file__).resolve().parents[2]).resolve()


@lru_cache(maxsize=1)
def _conversation() -> NativeEnglishConversation:
    return NativeEnglishConversation(repo_root=_repo_root())


@lru_cache(maxsize=1)
def _games() -> NativeEnglishGames:
    return NativeEnglishGames(repo_root=_repo_root())


@lru_cache(maxsize=1)
def _transfer() -> NativeEnglishTransfer:
    return NativeEnglishTransfer(repo_root=_repo_root())


@lru_cache(maxsize=1)
def _coverage() -> NativeEnglishCoverage:
    return NativeEnglishCoverage(repo_root=_repo_root())


@lru_cache(maxsize=1)
def _semantic_spider() -> NativeSemanticSpider:
    return NativeSemanticSpider(repo_root=_repo_root())


@lru_cache(maxsize=1)
def _semantic_academy() -> NativeSemanticTransferAcademy:
    return NativeSemanticTransferAcademy(repo_root=_repo_root())


@lru_cache(maxsize=1)
def _practice_gym() -> NativeEnglishPracticeGym:
    return NativeEnglishPracticeGym(repo_root=_repo_root())


@lru_cache(maxsize=1)
def _language_workshop() -> NativeLanguageWorkshop:
    return NativeLanguageWorkshop(repo_root=_repo_root())


@lru_cache(maxsize=1)
def _reading_academy() -> NativeReadingAcademy:
    return NativeReadingAcademy(repo_root=_repo_root())


@router.get("/progress")
def progress() -> dict:
    global _progress_cache, _progress_cache_epoch
    now = time.monotonic()
    if _progress_cache and now - _progress_cache_epoch < _PROGRESS_CACHE_SECONDS:
        return _progress_cache
    # Multiple panel tabs must not pile identical SD-card scans on top of the
    # teacher and spider writers.  A concurrent caller receives the last
    # coherent snapshot while one request refreshes it.
    if not _progress_lock.acquire(blocking=False):
        if _progress_cache:
            return _progress_cache
        _progress_lock.acquire()
        _progress_lock.release()
        return _progress_cache
    try:
        payload = collect_native_english_progress(_repo_root())
        payload["conversation"] = _conversation().metrics()
        payload["games"] = _games().metrics()
        payload["transfer"] = _transfer().metrics()
        payload["coverage"] = _coverage().metrics()
        payload["semantic_spider"] = _semantic_spider().status()
        payload["semantic_transfer_academy"] = _semantic_academy().metrics()
        payload["practice_gym"] = _practice_gym().metrics()
        payload["language_workshop"] = _language_workshop().metrics()
        payload["reading_academy"] = _reading_academy().metrics()
        _progress_cache = payload
        _progress_cache_epoch = time.monotonic()
        return payload
    finally:
        _progress_lock.release()


@router.post("/conversation/ask")
def ask_native_english(payload: NativeQuestion) -> dict:
    return _conversation().ask(
        payload.question, session_id=payload.session_id,
    )


@router.post("/conversation/improve")
def run_native_improvement() -> dict:
    return _conversation().self_improvement_cycle()


@router.post("/conversation/{turn_id}/correction")
def correct_native_english(turn_id: str, payload: ConversationCorrectionRequest) -> dict:
    return _conversation().correct(
        turn_id=turn_id, proposed_answer=payload.proposed_answer,
        reason=payload.reason, source_ref=payload.source_ref,
    )


@router.get("/games/families")
def game_families() -> dict:
    return {"families": list(FAMILIES), "difficulties": [1, 2, 3, 4, 5]}


@router.post("/games/new")
def new_game(payload: NewGameRequest) -> dict:
    return _games().new_game(
        family=payload.family, difficulty=payload.difficulty,
    )


@router.post("/games/{game_id}/answer")
def answer_game(game_id: str, payload: GameAnswerRequest) -> dict:
    return _games().submit(
        game_id=game_id, answer=payload.answer, player=payload.player,
    )


@router.post("/games/{game_id}/correction")
def correct_game(game_id: str, payload: GameCorrectionRequest) -> dict:
    return _games().propose_correction(
        game_id=game_id, answer=payload.answer, reason=payload.reason,
    )


@router.post("/transfer/challenge")
def run_transfer_challenge(payload: TransferChallengeRequest) -> dict:
    transfer = _transfer()
    challenge = transfer.create_challenge(
        kind=payload.kind, material=payload.material, question=payload.question,
        expected_answer=payload.expected_answer, answer_reason=payload.answer_reason,
    )
    return {"challenge": challenge, "attempt": transfer.attempt(challenge["challenge_id"])}


@router.get("/semantic-spider")
def semantic_spider_status() -> dict:
    return _semantic_spider().status()


@router.get("/reading-academy")
def reading_academy_status() -> dict:
    return _reading_academy().metrics()


@router.post("/reading-academy/ingest")
def ingest_reading_source(payload: ReadingSourceRequest) -> dict:
    return _reading_academy().ingest_text(
        title=payload.title, text=payload.text, author=payload.author,
        subject=payload.subject, license_name=payload.license,
        source_ref=payload.source_ref,
    )


@router.post("/reading-academy/run")
def run_reading_academy() -> dict:
    return _reading_academy().run_cycle(
        limit=max(1, min(500, int(os.getenv("AION_READING_ACADEMY_BATCH", "200"))))
    )


@router.post("/reading-academy/ingest-url")
def ingest_online_reading_source(payload: ReadingURLRequest) -> dict:
    return _reading_academy().online.ingest_url(
        payload.url, title=payload.title, author=payload.author, subject=payload.subject,
    )


@router.post("/semantic-spider/start")
def start_semantic_spider(payload: SemanticSpiderStartRequest) -> dict:
    return _semantic_spider().start(payload.seed)


@router.post("/semantic-spider/step")
def step_semantic_spider() -> dict:
    return _semantic_spider().step()


@router.post("/semantic-spider/pause")
def pause_semantic_spider() -> dict:
    return _semantic_spider().pause()


@router.get("/panel", response_class=HTMLResponse)
def panel() -> HTMLResponse:
    return HTMLResponse(_PANEL_HTML)


_PANEL_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AION English Intelligence</title>
<style>
:root{color-scheme:dark;--bg:#071019;--panel:#0d1924;--line:#1d3447;--text:#eef8ff;--muted:#87a0b4;--cyan:#29d9ff;--blue:#5685ff;--green:#4be3a1;--amber:#ffc85c;--red:#ff6b7a}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 78% 0,#132b45 0,transparent 38%),var(--bg);color:var(--text);font:14px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,sans-serif}
.wrap{max-width:1280px;margin:auto;padding:30px}.top{display:flex;gap:20px;align-items:flex-start;justify-content:space-between;margin-bottom:22px}.eyebrow{color:var(--cyan);font-size:12px;font-weight:800;letter-spacing:.16em;text-transform:uppercase}.title{font-size:34px;line-height:1.1;margin:7px 0}.sub{color:var(--muted);max-width:720px}.health{border:1px solid var(--line);background:#0a1620;border-radius:999px;padding:10px 15px;font-weight:800;white-space:nowrap}.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:8px}.healthy .dot{background:var(--green);box-shadow:0 0 14px var(--green)}.degraded .dot{background:var(--amber);box-shadow:0 0 14px var(--amber)}.offline .dot{background:var(--red)}
.alert{display:none;border:1px solid #664d1f;background:#231d10;color:#ffe4a8;padding:14px 16px;border-radius:13px;margin:0 0 18px}.alert.show{display:block}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.card{background:linear-gradient(160deg,#10202e,#0a151f);border:1px solid var(--line);border-radius:16px;padding:17px;min-width:0}.label{color:var(--muted);font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.08em}.value{font-size:27px;font-weight:850;margin-top:7px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.detail{color:var(--muted);font-size:12px;margin-top:4px}.wide{grid-column:span 2}.section{margin-top:24px}.section h2{font-size:17px;margin:0 0 12px}.bar{height:10px;background:#07111a;border:1px solid var(--line);border-radius:999px;overflow:hidden;margin:13px 0 7px}.fill{height:100%;background:linear-gradient(90deg,var(--blue),var(--cyan));width:0}.stages{display:grid;gap:9px}.stage{display:grid;grid-template-columns:34px minmax(170px,1.4fr) minmax(120px,1fr) 110px 90px;align-items:center;gap:12px;padding:12px 14px;border:1px solid var(--line);border-radius:12px;background:#0a151f}.stage.current{border-color:var(--cyan);box-shadow:inset 3px 0 var(--cyan)}.stage.completed{opacity:.86}.stage.locked{opacity:.55}.n{font-weight:900;color:var(--cyan)}.stage-title{font-weight:750}.pill{justify-self:start;border:1px solid var(--line);border-radius:999px;padding:3px 8px;font-size:11px;text-transform:uppercase;font-weight:800}.pill.current{color:var(--cyan)}.pill.completed{color:var(--green)}.pill.locked{color:var(--muted)}
.cycles{width:100%;border-collapse:collapse}.cycles th,.cycles td{text-align:left;padding:10px;border-bottom:1px solid var(--line)}.cycles th{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.07em}.ok{color:var(--green)}.bad{color:var(--red)}.muted{color:var(--muted)}.footer{display:flex;justify-content:space-between;gap:20px;color:var(--muted);font-size:12px;margin:22px 0}.skeleton{animation:pulse 1.4s infinite}@keyframes pulse{50%{opacity:.45}}
.ask-row{display:flex;gap:10px}.ask-row input{flex:1;min-width:0;border:1px solid var(--line);background:#07111a;color:var(--text);border-radius:11px;padding:12px 14px;font:inherit}.ask-row button{border:0;border-radius:11px;padding:0 18px;background:linear-gradient(135deg,var(--blue),var(--cyan));color:#041019;font-weight:850;cursor:pointer}.native-answer{margin-top:13px;padding:13px;border-radius:11px;background:#07111a;border:1px solid var(--line);min-height:50px}.proof{margin-top:8px;color:var(--muted);font-size:11px}
.game-controls{display:flex;gap:9px;flex-wrap:wrap;margin:12px 0}.game-controls select,.game-input{border:1px solid var(--line);background:#07111a;color:var(--text);border-radius:10px;padding:10px 12px;font:inherit}.game-controls button,.game-actions button,.token{border:0;border-radius:10px;padding:10px 14px;background:#173247;color:var(--text);font-weight:800;cursor:pointer}.game-controls button.primary,.game-actions button.primary{background:linear-gradient(135deg,var(--blue),var(--cyan));color:#041019}.game-prompt{font-size:17px;font-weight:750;margin:14px 0;white-space:pre-line}.tokens,.choices{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.token.selected,.choice.selected{outline:2px solid var(--cyan);background:#164b61}.choice.correct-answer{outline:2px solid var(--green);background:#153d31}.choice{border:1px solid var(--line);border-radius:10px;padding:10px 13px;background:#07111a;cursor:pointer}.game-actions{display:flex;gap:9px;flex-wrap:wrap;margin-top:12px}.game-result{display:none;margin-top:14px;padding:14px;border-radius:11px;border:1px solid var(--line);background:#07111a}.game-result.show{display:block}.game-result.correct{border-color:#246e52}.game-result.wrong{border-color:#7d3b43}.answer-reveal{font-weight:800;margin-top:8px}.why{color:var(--muted);margin-top:6px}
.transfer-grid{display:grid;grid-template-columns:180px 1fr;gap:9px;margin-top:12px}.transfer-grid textarea,.transfer-grid input,.transfer-grid select{border:1px solid var(--line);background:#07111a;color:var(--text);border-radius:10px;padding:11px 12px;font:inherit}.transfer-grid textarea{min-height:72px;resize:vertical}.transfer-grid button{border:0;border-radius:10px;padding:11px 14px;background:linear-gradient(135deg,var(--blue),var(--cyan));color:#041019;font-weight:850;cursor:pointer}.transfer-result{margin-top:14px;border:1px solid var(--line);border-radius:12px;padding:14px;background:#07111a}.parse-grid{display:grid;grid-template-columns:repeat(4,minmax(100px,1fr));gap:8px;margin-top:10px}.parse-cell{background:#0d1b27;border:1px solid var(--line);padding:9px;border-radius:9px}.parse-cell span{display:block;color:var(--muted);font-size:10px;text-transform:uppercase}.transfer-badge{display:inline-block;border:1px solid var(--cyan);color:var(--cyan);border-radius:999px;padding:3px 8px;font-size:11px;font-weight:800;margin-right:6px}
.coverage-summary{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;margin:13px 0}.coverage-stat{border:1px solid var(--line);background:#07111a;border-radius:11px;padding:12px}.coverage-stat strong{display:block;font-size:21px;margin-top:3px}.coverage-note{margin-top:11px;padding:11px 13px;border-left:3px solid var(--amber);background:#17170f;color:#dfc98e;border-radius:8px}
.spider-controls{display:flex;gap:9px;flex-wrap:wrap;margin:12px 0}.spider-controls input{flex:1;min-width:180px;border:1px solid var(--line);background:#07111a;color:var(--text);border-radius:10px;padding:10px 12px}.spider-controls button{border:0;border-radius:10px;padding:10px 14px;background:#173247;color:var(--text);font-weight:800;cursor:pointer}.spider-controls button.primary{background:linear-gradient(135deg,var(--blue),var(--cyan));color:#041019}.spider-metrics{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin:12px 0}.spider-metric{border:1px solid var(--line);background:#07111a;border-radius:10px;padding:9px}.spider-metric strong{display:block;font-size:18px}.spider-board{position:relative;min-height:430px;overflow:hidden;border:1px solid #24455c;border-radius:15px;background:radial-gradient(circle at 50% 45%,#102d43 0,#07111a 64%);box-shadow:inset 0 0 70px #02070b}.spider-board:before{content:"";position:absolute;inset:0;background-image:linear-gradient(rgba(41,217,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(41,217,255,.035) 1px,transparent 1px);background-size:34px 34px}.web-lines{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}.web-lines line{stroke:#1d6f89;stroke-width:.35;opacity:.55;stroke-dasharray:2 2}.word-node{position:absolute;transform:translate(-50%,-50%);border:1px solid #25516a;background:#0b1b28;color:#b9d5e7;border-radius:999px;padding:6px 10px;font-size:11px;max-width:145px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;box-shadow:0 0 0 3px rgba(41,217,255,.02);transition:.35s}.word-node.current{border-color:var(--cyan);color:#fff;box-shadow:0 0 24px rgba(41,217,255,.55)}.word-node.read{border-color:#277b5c;color:var(--green)}.word-node.stepped{animation:wordGlitch .55s steps(2,end)}@keyframes wordGlitch{0%{transform:translate(-50%,-50%) skew(0);text-shadow:none}22%{transform:translate(calc(-50% + 3px),-50%) skew(-8deg);text-shadow:-3px 0 #ff4f7a,3px 0 #29d9ff}48%{letter-spacing:.16em;filter:blur(.5px)}75%{transform:translate(calc(-50% - 2px),-50%) skew(5deg)}100%{transform:translate(-50%,-50%);letter-spacing:normal;filter:none}}.semantic-spider{position:absolute;width:112px;height:96px;transform:translate(-50%,-50%) rotate(var(--heading,0deg));transform-origin:50% 50%;filter:drop-shadow(0 0 10px rgba(41,217,255,.85));transition:left 1.35s cubic-bezier(.28,.02,.16,1),top 1.35s cubic-bezier(.28,.02,.16,1),transform .38s ease-out;z-index:5;overflow:visible}.semantic-spider .leg{fill:none;stroke:#5ab8ff;stroke-width:3.2;stroke-linecap:round;stroke-linejoin:round}.semantic-spider .joint{fill:#ff4f7a;stroke:#ff91aa;stroke-width:.7;filter:drop-shadow(0 0 3px #ff4f7a)}.semantic-spider .foot{fill:#8beaff}.semantic-spider .abdomen{fill:#071019;stroke:#29d9ff;stroke-width:3}.semantic-spider .shell{fill:url(#spiderBodyGlow);stroke:#7eeaff;stroke-width:2.2}.semantic-spider .head{fill:#122e43;stroke:#7eeaff;stroke-width:2}.semantic-spider .eye{fill:#fff;filter:drop-shadow(0 0 2px #fff)}.semantic-spider .fang{fill:none;stroke:#ff4f7a;stroke-width:2;stroke-linecap:round}.semantic-spider.walking{filter:drop-shadow(0 0 15px rgba(41,217,255,1))}.spider-source{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}.source-chip{border:1px solid var(--line);border-radius:999px;padding:4px 9px;color:var(--muted);font-size:11px}.source-chip.live{color:var(--green);border-color:#277b5c}.spider-pages{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:10px}.spider-page{border:1px solid var(--line);border-radius:9px;padding:9px;background:#09151f}.spider-page .ok{font-weight:800}@media(prefers-reduced-motion:reduce){.semantic-spider{transition:left 2.5s linear,top 2.5s linear,transform .8s}.word-node.stepped{animation:none}}
@media(max-width:900px){.grid{grid-template-columns:repeat(2,1fr)}.coverage-summary{grid-template-columns:repeat(2,1fr)}.stage{grid-template-columns:30px 1fr 90px}.stage .family,.stage .attempts{display:none}.top{display:block}.health{display:inline-block;margin-top:14px}}
@media(max-width:540px){.wrap{padding:18px}.grid{grid-template-columns:1fr}.wide{grid-column:span 1}.title{font-size:28px}.stage{grid-template-columns:28px 1fr}.stage .accuracy{display:none}}
</style>
</head>
<body><main class="wrap">
<div class="top"><div><div class="eyebrow">AION Learning Centre</div><h1 class="title">English Intelligence Progress</h1><div class="sub">Native memory growth, closed-book ability and curriculum depth. Qwen may teach; only AION's model-free examinations can advance competence.</div></div><div id="health" class="health skeleton"><span class="dot"></span>Loading</div></div>
<div id="alert" class="alert"></div>
<div class="grid">
 <div class="card wide"><div class="label">Current layer</div><div id="stage" class="value">—</div><div class="bar"><div id="stageFill" class="fill"></div></div><div id="stageDetail" class="detail">Loading curriculum</div></div>
 <div class="card"><div class="label">Closed-book accuracy</div><div id="accuracy" class="value">—</div><div id="attempts" class="detail">— attempts</div></div>
 <div class="card"><div class="label">Last completed cycle</div><div id="cycleAge" class="value">—</div><div id="teacher" class="detail">—</div></div>
 <div class="card"><div class="label">Reference entries</div><div id="lexemes" class="value">—</div><div class="detail">Available teaching material; not learned</div></div>
 <div class="card"><div class="label">Words encountered</div><div id="encountered" class="value">—</div><div class="detail">Concept capsules currently being learned</div></div>
 <div class="card"><div class="label">Active vocabulary</div><div id="activeVocabulary" class="value">—</div><div class="detail">Passed production and entered retention</div></div>
 <div class="card"><div class="label">Mastered vocabulary</div><div id="masteredVocabulary" class="value">—</div><div class="detail">Passed the full delayed-retention sequence</div></div>
 <div class="card"><div class="label">Semantic links</div><div id="relations" class="value">—</div><div class="detail">Synonyms, contrasts and concept links</div></div>
 <div class="card"><div class="label">Teacher lessons</div><div id="lessons" class="value">—</div><div class="detail">Study material; not exam evidence</div></div>
 <div class="card"><div class="label">SD intelligence store</div><div id="storage" class="value">—</div><div id="storageDetail" class="detail">—</div></div>
 <div class="card"><div class="label">Learning Centre assessment</div><div id="competency" class="value">—</div><div id="competencyDetail" class="detail">—</div></div>
</div>
<section class="section card"><h2>Unseen Transfer Lab</h2><div class="detail">Create material Aion has never seen. Its answer comes from lexical memory and a native semantic parse—not a sentence template. The expected answer remains sealed until after Aion responds.</div><div class="transfer-grid"><select id="transferKind"><option value="sentence_qa">Question about a sentence</option><option value="word_order">Order my words</option></select><textarea id="transferMaterial" placeholder="Before lunch, Xanthe calculated the report in the garden."></textarea><input id="transferQuestion" placeholder="Where did the action happen?"><input id="transferExpected" placeholder="Expected answer for independent grading (optional)"><input id="transferReason" placeholder="Why that answer is correct (optional)"><button id="runTransfer" class="primary">Test Aion on unseen material</button></div><div id="transferResult" class="transfer-result muted">No owner-created transfer test has run yet.</div><div id="transferStats" class="proof">Transfer results are kept separate from guided practice.</div></section>
<section class="section card"><h2>Guided English practice — scaffolded</h2><div class="detail">These generated games are useful practice, but use known sentence families and must not be treated as general-English transfer evidence. You can solve one yourself or let Aion practise it.</div><div class="game-controls"><select id="gameFamily"><option value="mixed">Mixed games</option><option value="sentence_unscramble">Jumbled sentence</option><option value="missing_word">Missing word</option><option value="tense_transform">Change tense</option><option value="negation_transform">Make negative</option><option value="sentence_comprehension">Understand sentence</option><option value="grammar_repair">Repair grammar</option></select><select id="gameDifficulty"><option value="1">Level 1</option><option value="2">Level 2</option><option value="3">Level 3</option><option value="4">Level 4</option><option value="5">Level 5</option></select><button id="newGame" class="primary">New guided game</button></div><div id="gamePrompt" class="game-prompt muted">Choose a guided game and difficulty.</div><div id="gameChoices" class="choices"></div><input id="gameAnswer" class="game-input" style="display:none;width:100%" placeholder="Type the completed sentence"><div class="game-actions"><button id="humanAnswer" class="primary" disabled>Check my answer</button><button id="aionAnswer" disabled>Let Aion practise</button><button id="clearTokens" style="display:none">Clear order</button></div><div id="gameResult" class="game-result"></div><div id="gameStats" class="proof">No guided games played yet.</div></section>
<section class="section card"><h2>Speak with native Aion</h2><div class="detail" style="margin-bottom:11px">Answers use only concepts Aion has acquired and retained. Dictionary-only material is labelled as reference material. Qwen, cloud models and token prediction are disconnected.</div><div class="ask-row"><input id="nativeQuestion" placeholder="Try: What does calm mean?" maxlength="4000"><button id="askNative">Ask Aion</button></div><div id="nativeAnswer" class="native-answer muted">Aion is ready for a native-English question.</div><div id="nativeProof" class="proof"></div><div id="correctionBox" style="display:none;margin-top:12px"><div class="detail">If Aion is wrong, provide the correction and why. It will be learned only if independent evidence verifies it.</div><div class="ask-row" style="margin-top:8px"><input id="correctedAnswer" placeholder="Correct answer"><input id="correctionReason" placeholder="Why is this correct?"><button id="correctAion">Teach correction</button></div><div id="correctionResult" class="proof"></div></div></section>
<section class="section card"><h2>English Coverage Ledger</h2><div class="detail">A capability map based on sealed regression tests. It shows exactly what was tested and passed; it does not infer understanding from the size of the dictionary.</div><div class="coverage-summary"><div class="coverage-stat"><div class="label">Reference senses</div><strong id="coverageSenses">—</strong></div><div class="coverage-stat"><div class="label">Distinct lemmas</div><strong id="coverageLemmas">—</strong></div><div class="coverage-stat"><div class="label">Multi-role words</div><strong id="coverageMultiPos">—</strong></div><div class="coverage-stat"><div class="label">Stored word forms</div><strong id="coverageMorphology">—</strong></div></div><div style="overflow:auto"><table class="cycles"><thead><tr><th>Capability family</th><th>Tested</th><th>Passed</th><th>Accuracy</th><th>Confidence</th></tr></thead><tbody id="coverageRows"><tr><td colspan="5" class="muted">No coverage run recorded.</td></tr></tbody></table></div><div id="coverageBoundary" class="coverage-note">These are regression results, not a claim of general English mastery.</div></section>
<section class="section card"><h2>Aion Semantic Spider</h2><div class="detail">A capped local crawler moves through dictionary definitions and thesaurus relationships word by word. Wikipedia context is limited and cached. Reading never counts as learning: every eight-word page must pass an exact page-specific, model-free Word Wall examination before it can close.</div><div class="spider-controls"><input id="spiderSeed" value="language" placeholder="Seed word"><button id="startSpider" class="primary">Start crawling</button><button id="pauseSpider">Pause</button><button id="stepSpider">Single step</button></div><div class="spider-metrics"><div class="spider-metric"><span class="label">Certified pages</span><strong id="spiderPages">0</strong></div><div class="spider-metric"><span class="label">Words read</span><strong id="spiderWords">0</strong></div><div class="spider-metric"><span class="label">Discovered</span><strong id="spiderDiscoveries">0</strong></div><div class="spider-metric"><span class="label">Frontier</span><strong id="spiderFrontier">0</strong></div><div class="spider-metric"><span class="label">Certified tests</span><strong id="spiderTests">0</strong></div><div class="spider-metric"><span class="label">Accuracy</span><strong id="spiderAccuracy">—</strong></div></div><div id="spiderBoard" class="spider-board"><svg id="spiderLines" class="web-lines" viewBox="0 0 100 100" preserveAspectRatio="none"></svg><div id="spiderNodes"></div><svg id="semanticSpider" class="semantic-spider" viewBox="0 0 130 110" style="left:50%;top:50%" aria-label="Aion semantic spider"><defs><radialGradient id="spiderBodyGlow"><stop offset="0" stop-color="#235675"/><stop offset="1" stop-color="#08131d"/></radialGradient></defs><g id="spiderLegs"><path id="leg0" class="leg"/><path id="leg1" class="leg"/><path id="leg2" class="leg"/><path id="leg3" class="leg"/><path id="leg4" class="leg"/><path id="leg5" class="leg"/><path id="leg6" class="leg"/><path id="leg7" class="leg"/><circle id="joint0" class="joint" r="2.4"/><circle id="joint1" class="joint" r="2.4"/><circle id="joint2" class="joint" r="2.4"/><circle id="joint3" class="joint" r="2.4"/><circle id="joint4" class="joint" r="2.4"/><circle id="joint5" class="joint" r="2.4"/><circle id="joint6" class="joint" r="2.4"/><circle id="joint7" class="joint" r="2.4"/><circle id="foot0" class="foot" r="1.6"/><circle id="foot1" class="foot" r="1.6"/><circle id="foot2" class="foot" r="1.6"/><circle id="foot3" class="foot" r="1.6"/><circle id="foot4" class="foot" r="1.6"/><circle id="foot5" class="foot" r="1.6"/><circle id="foot6" class="foot" r="1.6"/><circle id="foot7" class="foot" r="1.6"/></g><g id="spiderBody"><ellipse class="abdomen" cx="65" cy="67" rx="18" ry="25"/><ellipse class="shell" cx="65" cy="54" rx="16" ry="18"/><circle class="head" cx="65" cy="35" r="13"/><circle class="eye" cx="60" cy="31" r="2.4"/><circle class="eye" cx="70" cy="31" r="2.4"/><path class="fang" d="M59 43 Q61 48 64 44 M71 43 Q69 48 66 44"/></g></svg></div><div id="spiderSources" class="spider-source"></div><div id="spiderPagesList" class="spider-pages"></div><div id="spiderStatus" class="proof">The crawler is ready.</div></section>
<section class="section card"><h2>Native Reading Academy</h2><div class="detail">Aion automatically discovers online books, downloads each source into temporary storage, extracts it, and deletes the original file immediately. It rapidly reads every sentence, retains compact meaning and provenance, and selects novel, ambiguous and representative material for deeper closed-book examination. Exposure is never counted as mastery.</div><div class="coverage-summary"><div class="coverage-stat"><div class="label">Books and documents</div><strong id="readingSources">—</strong></div><div class="coverage-stat"><div class="label">Online books imported</div><strong id="readingOnline">—</strong></div><div class="coverage-stat"><div class="label">Temporary files retained</div><strong id="readingRawCache">—</strong></div><div class="coverage-stat"><div class="label">Text compacted</div><strong id="readingCompacted">—</strong></div><div class="coverage-stat"><div class="label">Sentences read</div><strong id="readingProgress">—</strong></div><div class="coverage-stat"><div class="label">Rapid exposure</div><strong id="readingExposure">—</strong></div><div class="coverage-stat"><div class="label">Latest speed</div><strong id="readingSpeed">—</strong></div><div class="coverage-stat"><div class="label">Comprehension</div><strong id="readingAccuracy">—</strong></div><div class="coverage-stat"><div class="label">Words experienced</div><strong id="readingWords">—</strong></div><div class="coverage-stat"><div class="label">Sourced claims</div><strong id="readingClaims">—</strong></div><div class="coverage-stat"><div class="label">Corrections due</div><strong id="readingCorrections">—</strong></div><div class="coverage-stat"><div class="label">Retention due</div><strong id="readingRetention">—</strong></div><div class="coverage-stat"><div class="label">Reading cycles</div><strong id="readingCycles">—</strong></div><div class="coverage-stat"><div class="label">PDFs accepted</div><strong id="readingPdfs">—</strong></div><div class="coverage-stat"><div class="label">Imports quarantined</div><strong id="readingQuarantined">—</strong></div></div><div class="transfer-grid"><input id="readingTitle" placeholder="Book or document title"><input id="readingAuthor" placeholder="Author"><input id="readingSubject" placeholder="Subject, for example science"><textarea id="readingText" placeholder="Paste text here, or place EPUB, PDF, TXT or Markdown books in a watched reading-library folder."></textarea><button id="ingestReading">Add to reading library</button><button id="runReading" class="primary">Run a high-speed reading batch</button></div><div id="readingResult" class="coverage-note">The online reader automatically maintains the queue; local reading-library folders remain available for your own material.</div><div id="readingSourceList" class="proof"></div></section>
<section class="section card"><h2>English Practice Gym</h2><div class="detail">Wordwall-style activities now train acquired meanings, context choice, native sentence production, transformation, reading, controlled writing and conversation. Practice is concentrated into concept cohorts; only concepts that pass the complete preparation package are released to unfamiliar transfer exams. Every wrong answer receives a verified explanation and a delayed, different retest.</div><div class="coverage-summary"><div class="coverage-stat"><div class="label">Attempts last hour</div><strong id="gymRecent">—</strong></div><div class="coverage-stat"><div class="label">Recent accuracy</div><strong id="gymAccuracy">—</strong></div><div class="coverage-stat"><div class="label">Transfer ready</div><strong id="gymReady">—</strong></div><div class="coverage-stat"><div class="label">Nearly ready</div><strong id="gymNearly">—</strong></div><div class="coverage-stat"><div class="label">Corrections due</div><strong id="gymDue">—</strong></div><div class="coverage-stat"><div class="label">Retests cleared</div><strong id="gymCleared">—</strong></div><div class="coverage-stat"><div class="label">Learning rewards</div><strong id="gymRewards">—</strong></div><div class="coverage-stat"><div class="label">Practice cycles</div><strong id="gymCycles">—</strong></div></div><div id="gymFamilies" class="coverage-note">Waiting for the first governed practice cycle.</div></section>
<section class="section card"><h2>Native Language Workshop</h2><div class="detail">Connected-language training combines clause and inference comprehension, native sentence production, paraphrasing, multi-turn dialogue and delayed vocabulary retention. Qwen may author sealed lessons, but it disconnects before Aion plans, parses or answers. Workshop results guide correction and retesting but do not grant mastery.</div><div class="coverage-summary"><div class="coverage-stat"><div class="label">Attempts last hour</div><strong id="workshopRecent">—</strong></div><div class="coverage-stat"><div class="label">Recent accuracy</div><strong id="workshopAccuracy">—</strong></div><div class="coverage-stat"><div class="label">Correction retries due</div><strong id="workshopDue">—</strong></div><div class="coverage-stat"><div class="label">Retries cleared</div><strong id="workshopCleared">—</strong></div><div class="coverage-stat"><div class="label">Workshop cycles</div><strong id="workshopCycles">—</strong></div></div><div id="workshopFamilies" class="coverage-note">Waiting for the first connected-language workshop cycle.</div></section>
<section class="section card"><h2>Semantic Transfer Academy</h2><div class="detail">The academy concentrates unfamiliar transfer into a focused 32-concept cohort. The system fixes a guaranteed parseable semantic frame and answer role first; local Qwen varies only safe names, objects and settings. Aion then answers with Qwen disconnected.</div><div class="coverage-summary"><div class="coverage-stat"><div class="label">Eligible concepts</div><strong id="academyEligible">—</strong></div><div class="coverage-stat"><div class="label">Focused cohort</div><strong id="academyCohort">—</strong></div><div class="coverage-stat"><div class="label">Near productive</div><strong id="academyNearProductive">—</strong></div><div class="coverage-stat"><div class="label">Contract-built exams</div><strong id="academyCompiledTransfers">—</strong></div><div class="coverage-stat"><div class="label">Attempts last hour</div><strong id="academyRecent">—</strong></div><div class="coverage-stat"><div class="label">Recalled use</div><strong id="academyRecalled">—</strong></div><div class="coverage-stat"><div class="label">Contextual use</div><strong id="academyContextual">—</strong></div><div class="coverage-stat"><div class="label">Productive use</div><strong id="academyProductive">—</strong></div><div class="coverage-stat"><div class="label">Recent free transfer</div><strong id="academyFreeAccuracy">—</strong></div><div class="coverage-stat"><div class="label">Current remedies</div><strong id="academyRemedies">—</strong></div><div class="coverage-stat"><div class="label">Cooling down</div><strong id="academyCooling">—</strong></div></div><div id="academyStatus" class="coverage-note">Waiting for the first automated semantic-transfer cycle.</div></section>
<section class="section"><h2>Foundation archive and advanced curriculum</h2><p class="muted">Completed foundations remain visible as certificates. Advanced promotion requires fresh, mostly unrepeated, free-response transfer.</p><div id="stages" class="stages"></div></section>
<section class="section card"><h2>Recent closed-book cycles</h2><div style="overflow:auto"><table class="cycles"><thead><tr><th>Layer</th><th>Result</th><th>Score</th><th>Qwen in exam</th><th>Promotion</th></tr></thead><tbody id="cycles"></tbody></table></div></section>
<div class="footer"><span id="claim">Stored words are not general English mastery.</span><span id="updated">—</span></div>
</main>
<script>
const $=id=>document.getElementById(id);const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=v=>new Intl.NumberFormat().format(Number(v||0));const pct=v=>v==null?'—':`${(Number(v)*100).toFixed(1)}%`;
const age=s=>{if(s==null)return'unknown';if(s<60)return`${Math.round(s)} sec`;if(s<3600)return`${Math.round(s/60)} min`;return`${(s/3600).toFixed(1)} hr`};
let spiderRunning=false,spiderBusy=false,lastSpiderWord='';
const spiderMotion={x:50,y:50,angle:0,moveUntil:0};
const spiderLegSpec=[[-1,52,39,13,16],[-1,50,49,5,38],[-1,50,61,5,72],[-1,52,72,14,96],[1,78,39,117,16],[1,80,49,125,38],[1,80,61,125,72],[1,78,72,116,96]];
const easeStep=p=>p*p*(3-2*p);
function animateSpiderRig(t){const spider=$('semanticSpider'),reduced=matchMedia('(prefers-reduced-motion: reduce)').matches,walking=!reduced&&t<spiderMotion.moveUntil;if(spider)spider.classList.toggle('walking',walking);spiderLegSpec.forEach((spec,i)=>{const[side,hx,hy,bx,by]=spec,group=(i+(i>3?1:0))%2,phase=((t/520)+(group*.5))%1,stepping=walking&&phase<.46,p=stepping?easeStep(phase/.46):0,planted=(phase-.46)/.54;let stride=0,lift=0;if(walking){stride=stepping?-9+(18*p):9-(18*Math.max(0,planted));lift=stepping?Math.sin(Math.PI*p)*8:0}const fx=bx+side*lift*.24,fy=by+stride,kx=(hx+fx)/2+side*(11+lift*.35),ky=(hy+fy)/2-lift*.72,leg=$(`leg${i}`),joint=$(`joint${i}`),foot=$(`foot${i}`);if(leg)leg.setAttribute('d',`M${hx} ${hy} L${kx.toFixed(2)} ${ky.toFixed(2)} L${fx.toFixed(2)} ${fy.toFixed(2)}`);if(joint){joint.setAttribute('cx',kx);joint.setAttribute('cy',ky)}if(foot){foot.setAttribute('cx',fx);foot.setAttribute('cy',fy);foot.setAttribute('r',stepping?'2.25':'1.6')}});const body=$('spiderBody');if(body)body.setAttribute('transform',`translate(0 ${(walking?Math.sin(t/65)*1.8:Math.sin(t/700)*.45).toFixed(2)})`);requestAnimationFrame(animateSpiderRig)}
requestAnimationFrame(animateSpiderRig);
function renderSpider(s){spiderRunning=!!s.running;$('spiderPages').textContent=num(s.pages_completed);$('spiderWords').textContent=num(s.words_read);$('spiderDiscoveries').textContent=num(s.discoveries);$('spiderFrontier').textContent=`${num(s.frontier_queued)} / ${num(s.caps?.max_frontier)}`;$('spiderTests').textContent=`${num(s.tests_correct)} / ${num(s.tests_attempted)}`;$('spiderAccuracy').textContent=pct(s.test_accuracy);const page=(s.pages||[])[0]||{},words=page.words||[],discoveries=page.discoveries||[],arrived=!!s.current_word&&s.current_word!==lastSpiderWord;const labels=[];for(const word of words)if(!labels.includes(word.lemma))labels.push(word.lemma);for(const item of discoveries)if(labels.length<16&&!labels.includes(item.lemma))labels.push(item.lemma);if(!labels.length&&s.seed)labels.push(s.seed);const positions=labels.map((_,i)=>{const angle=-Math.PI/2+(Math.PI*2*i/Math.max(1,labels.length));const ring=i%3===0?29:38;return{x:50+Math.cos(angle)*ring,y:49+Math.sin(angle)*ring}});$('spiderNodes').innerHTML=labels.map((label,i)=>`<div class="word-node ${label===s.current_word?`current ${arrived?'stepped':''}`:words.some(w=>w.lemma===label)?'read':''}" style="left:${positions[i].x}%;top:${positions[i].y}%" title="${esc(label)}">${esc(label)}</div>`).join('');$('spiderLines').innerHTML=positions.map((p,i)=>i?`<line x1="${positions[0].x}" y1="${positions[0].y}" x2="${p.x}" y2="${p.y}"/>`:'').join('');const current=Math.max(0,labels.indexOf(s.current_word)),pos=positions[current]||{x:50,y:50},spider=$('semanticSpider'),dx=pos.x-spiderMotion.x,dy=pos.y-spiderMotion.y;if(Math.hypot(dx,dy)>.5){spiderMotion.angle=Math.atan2(dy,dx)*180/Math.PI+90;spider.style.setProperty('--heading',`${spiderMotion.angle}deg`)}spider.style.left=`${pos.x}%`;spider.style.top=`${pos.y}%`;spiderMotion.x=pos.x;spiderMotion.y=pos.y;if(arrived){spiderMotion.moveUntil=performance.now()+1380;lastSpiderWord=s.current_word}const assets=s.sources?.assets||[];$('spiderSources').innerHTML=`<span class="source-chip ${assets.length?'live':''}">Local Dictionary ${assets.length?'connected':'unavailable'}</span><span class="source-chip live">Local thesaurus graph</span><span class="source-chip ${s.sources?.wikipedia_mode==='network_cached'?'live':''}">Wikipedia ${esc(String(s.sources?.wikipedia_mode||'disabled').replaceAll('_',' '))}</span><span class="source-chip live">Exact page exams</span><span class="source-chip">Single SD writer</span>`;$('spiderPagesList').innerHTML=(s.pages||[]).map(p=>{const t=p.test||{},coverage=`${num(t.coverage_count)}/${num(t.coverage_total||s.caps?.words_per_page)}`;return`<div class="spider-page"><b>Page ${num(p.page_number)}</b><div>${esc(p.seed)}</div><div class="${p.status==='tested'?'ok':'muted'}">${esc(String(p.status).replaceAll('_',' '))} · ${num((p.words||[]).length)}/${num(s.caps?.words_per_page)}</div>${p.status==='tested'?`<div>${coverage} page words tested · ${num(t.correct)}/${num(t.attempted)} correct</div>`:p.status==='legacy_uncertified'?`<div>${coverage} historical page coverage · excluded from certified totals</div>`:''}</div>`}).join('');$('spiderStatus').textContent=`${s.running?'Crawling':'Paused'} · current word: ${s.current_word||'—'} · a page cannot close until all its own words are examined · no model grades tests`;}
function render(d){const h=$('health');h.className=`health ${d.health}`;h.innerHTML=`<span class="dot"></span>${esc(d.learning_active?'Learning normally':d.health==='offline'?'Offline':'Needs attention')}`;
 const alert=$('alert');if(d.blockers?.length){alert.className='alert show';alert.innerHTML=`<b>Learning blocker:</b> ${d.blockers.map(esc).join(' · ')}`}else alert.className='alert';
 $('stage').textContent=d.stage.curriculum_complete?`Complete · ${d.stage.current_number} of ${d.stage.total}`:`${d.stage.current_number} of ${d.stage.total} · ${d.stage.title}`;$('stageFill').style.width=`${d.stage.progress*100}%`;$('stageDetail').textContent=d.stage.curriculum_complete?'All native layers passed; continued cycles now provide retention evidence.':`${d.stage.consecutive_passes}/${d.stage.required_consecutive_passes} consecutive passes toward the next layer`;
 $('accuracy').textContent=pct(d.memory.practice_accuracy);$('attempts').textContent=`${num(d.memory.practice_attempts)} closed-book attempts · model disconnected`;
 $('cycleAge').textContent=age(d.teacher.last_success_age_seconds);$('teacher').textContent=`${d.teacher.cycles} completed cycles · ${d.teacher.model||'teacher unavailable'}`;
 $('lexemes').textContent=num(d.memory.verified_lexemes);$('encountered').textContent=num(d.memory.encountered_words);$('activeVocabulary').textContent=num(d.memory.active_vocabulary);$('masteredVocabulary').textContent=num(d.memory.mastered_words);$('relations').textContent=num(d.memory.relations);$('lessons').textContent=num(d.memory.teacher_lessons);
 $('storage').textContent=d.storage.sd_mounted?'Mounted':'Unavailable';$('storageDetail').textContent=`${d.storage.free_gib??'—'} GiB free · ${d.memory.journal_mode||'unknown'} journal`;
 $('competency').textContent=String(d.learning_centre.overall_level||'unassessed').replaceAll('_',' ');$('competencyDetail').textContent=`${num(d.learning_centre.evidence_records)} distinct evidence records · ${num(d.learning_centre.raw_evidence_records)} raw receipts`;
 if(d.games)$('gameStats').textContent=`${num(d.games.attempts)} attempts · ${pct(d.games.accuracy)} accuracy · ${num(d.games.verified_corrections)} verified corrections · ${num(d.games.remediation_rules_due)} remedial rules due`;
 if(d.transfer)$('transferStats').textContent=`${num(d.transfer.first_seen_challenges)} first-seen challenges · ${num(d.transfer.attempts)} attempts · ${pct(d.transfer.accuracy)} independently graded accuracy · ${pct(d.transfer.average_confidence)} average confidence · ${num(d.transfer.reinforcements)} reinforcements · ${num(d.transfer.remediation_due)} remedies due`;
 const reading=d.reading_academy||{},online=reading.online_reader||{};$('readingSources').textContent=`${num(reading.sources_completed)} / ${num(reading.sources)}`;$('readingOnline').textContent=num(online.sources_imported);$('readingRawCache').textContent=num(online.temporary_files_retained);$('readingCompacted').textContent=`${num(Math.round(Number(reading.sentence_characters_compacted||0)/1000))}k chars`;$('readingProgress').textContent=`${num(reading.sentences_processed)} / ${num(reading.sentences_available)}`;$('readingExposure').textContent=num(reading.sentences_exposure_only);$('readingSpeed').textContent=reading.latest_cycle_sentences_per_second==null?'—':`${Number(reading.latest_cycle_sentences_per_second).toFixed(1)}/sec`;$('readingAccuracy').textContent=pct(reading.recent_accuracy??reading.accuracy);$('readingWords').textContent=num(reading.distinct_words_experienced);$('readingClaims').textContent=num(reading.provenanced_claims);$('readingCorrections').textContent=`${num(reading.corrections_due_now)} now · ${num(reading.corrections_due)} scheduled`;$('readingRetention').textContent=`${num(reading.retention_due)} now · ${num(reading.retention_scheduled)} scheduled`;$('readingCycles').textContent=num(reading.cycles);$('readingPdfs').textContent=num(reading.pdfs_ready);$('readingQuarantined').textContent=num(reading.imports_quarantined);$('readingSourceList').textContent=(reading.source_list||[]).length?(reading.source_list||[]).map(s=>`${s.title} — ${num(s.next_sentence_index)}/${num(s.sentence_count)} sentences · ${String(s.format||'text').toUpperCase()} · extraction ${pct(s.extraction_quality)} · ${String(s.status).replaceAll('_',' ')}`).join(' · '):'No reading sources have been loaded yet.';
 const gym=d.practice_gym||{};$('gymRecent').textContent=num(gym.attempts_last_hour);$('gymAccuracy').textContent=pct(gym.recent_accuracy??gym.accuracy);$('gymReady').textContent=num(gym.transfer_ready_concepts);$('gymNearly').textContent=num(gym.nearly_transfer_ready_concepts);$('gymRewards').textContent=num(gym.rewards);$('gymDue').textContent=num(gym.corrections_due);$('gymCleared').textContent=num(gym.corrections_cleared);$('gymCycles').textContent=num(gym.cycles);const gymFamilies=Object.entries(gym.recent_families||gym.families||{});$('gymFamilies').textContent=gymFamilies.length?gymFamilies.map(([name,row])=>`${name.replaceAll('_',' ')}: ${num(row.correct)}/${num(row.attempts)} (${pct(row.accuracy)}) last hour`).join(' · '):'Waiting for the first governed practice cycle.';
 const workshop=d.language_workshop||{};$('workshopRecent').textContent=num(workshop.attempts_last_hour);$('workshopAccuracy').textContent=pct(workshop.recent_accuracy??workshop.accuracy);$('workshopDue').textContent=num(workshop.remediation_due);$('workshopCleared').textContent=num(workshop.remediation_cleared);$('workshopCycles').textContent=num(workshop.cycles);const workshopFamilies=Object.entries(workshop.recent_families||workshop.families||{});$('workshopFamilies').textContent=workshopFamilies.length?workshopFamilies.map(([name,row])=>`${name.replaceAll('_',' ')}: ${num(row.correct)}/${num(row.attempts)} (${pct(row.accuracy)}) last hour`).join(' · '):'Waiting for the first connected-language workshop cycle.';
 const academy=d.semantic_transfer_academy||{},pipeline=academy.focused_cohort_pipeline||{};$('academyEligible').textContent=num(academy.eligible_acquired_concepts);$('academyCohort').textContent=`${num(academy.focused_cohort_active)} active`;$('academyNearProductive').textContent=num(Number(pipeline.three_free_successes||0)+Number(pipeline.four_plus_needing_family_variety||0));$('academyCompiledTransfers').textContent=num(academy.compiled_transfer_contracts);$('academyRecent').textContent=num(academy.attempts_last_hour);$('academyRecalled').textContent=num(academy.recalled_use_concepts);$('academyContextual').textContent=num(academy.contextual_use_concepts);$('academyProductive').textContent=num(academy.productive_use_concepts);$('academyFreeAccuracy').textContent=pct(academy.recent_free_transfer_accuracy);$('academyRemedies').textContent=num(academy.remediation_due);$('academyCooling').textContent=num(academy.concepts_cooling_down);$('academyStatus').textContent=academy.cycles?`${num(academy.attempted)} sealed attempts total · ${num(academy.guided_foundations)} guided · ${num(academy.remedial_retries)} corrective retries · ${num(academy.free_transfer_attempts)} free transfers (${pct(academy.free_transfer_accuracy)} lifetime) · ${num(academy.focused_cohort_graduated)} cohort graduates · ${num(academy.remediation_verified)} remedies cleared · ${num(academy.rejected)} unsafe/invalid teacher drafts rejected · ${num(academy.teacher_slot_fallbacks)} slot fallbacks · student model always disconnected`:'Waiting for the next supervised learning-centre cycle.';
 const coverage=d.coverage||{};$('coverageSenses').textContent=num(coverage.lexical_senses);$('coverageLemmas').textContent=num(coverage.sense_lemmas);$('coverageMultiPos').textContent=num(coverage.multi_part_of_speech_lemmas);$('coverageMorphology').textContent=num(coverage.morphology_forms);const ledger=Object.entries(coverage.latest_categories||{});$('coverageRows').innerHTML=ledger.length?ledger.map(([name,row])=>`<tr><td>${esc(name.replaceAll('_',' '))}</td><td>${num(row.tested)}</td><td class="${row.passed===row.tested?'ok':'bad'}">${num(row.passed)}</td><td>${pct(row.accuracy)}</td><td>${pct(row.average_confidence)}</td></tr>`).join(''):`<tr><td colspan="5" class="muted">No coverage run recorded.</td></tr>`;$('coverageBoundary').textContent=coverage.claim_boundary||'Regression coverage is not general English mastery.';
 if(d.semantic_spider)renderSpider(d.semantic_spider);
 $('stages').innerHTML=d.curriculum.map(s=>`<div class="stage ${esc(s.status)}"><div class="n">${s.number}</div><div><div class="stage-title">${esc(s.title)}</div><div class="muted">${esc(s.track)} · ${esc(s.id)}${s.implemented?'':' · examination not implemented'}</div></div><div class="family muted">${esc(s.family)}</div><div class="attempts">${num(s.attempts)}/${num(s.minimum_attempts)}<div class="muted">${num(s.unique_tasks)} unique · ${pct(s.unique_ratio)} fresh</div></div><div class="accuracy">${pct(s.accuracy)}</div><div class="pill ${esc(s.status)}">${esc(s.status)}</div></div>`).join('');
 const rows=[...(d.recent_cycles||[])].reverse();$('cycles').innerHTML=rows.length?rows.map(c=>`<tr><td>${esc(c.stage_title||c.stage_id||'—')}</td><td class="${c.status==='completed'?'ok':'bad'}">${esc(c.status||'—')}</td><td>${c.total?`${c.correct}/${c.total} · ${pct(c.score)}`:'—'}</td><td class="${c.model_used===false&&c.cloud_used===false?'ok':'bad'}">${c.model_used===false&&c.cloud_used===false?'Disconnected':'Check'}</td><td>${c.promoted?'Advanced':c.stage_passed?'Pass recorded':'No'}</td></tr>`).join(''):`<tr><td colspan="5" class="muted">No completed cycles recorded.</td></tr>`;
 $('claim').textContent=d.claim_boundary;$('updated').textContent=`Updated ${new Date(d.generated_at).toLocaleString()}`}
async function spiderPost(action,body){const options={method:'POST',headers:{'Content-Type':'application/json'}};if(body)options.body=JSON.stringify(body);const r=await fetch(`/api/aion/english-intelligence/semantic-spider/${action}`,options);if(!r.ok)throw Error(`HTTP ${r.status}`);const data=await r.json();renderSpider(data);return data}
async function spiderTick(){if(!spiderRunning||spiderBusy)return;spiderBusy=true;try{await spiderPost('step')}catch(e){$('spiderStatus').textContent=`Crawler paused: ${e.message}`;spiderRunning=false}finally{spiderBusy=false}}
async function ingestReading(){const title=$('readingTitle').value.trim(),text=$('readingText').value.trim();if(!title||!text)return;$('readingResult').textContent='Adding the source and preserving its sentence order…';const r=await fetch('/api/aion/english-intelligence/reading-academy/ingest',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title,text,author:$('readingAuthor').value.trim()||'Unknown',subject:$('readingSubject').value.trim()||'general',license:'owner-provided',source_ref:'English progress panel'})});if(!r.ok)throw Error(`HTTP ${r.status}`);const d=await r.json();$('readingResult').textContent=`${d.title||title}: ${num(d.sentences??d.sentence_count)} sentences ${d.status==='already_ingested'?'were already in the library':'added to the reading queue'}.`;refresh()}
async function runReading(){const out=$('readingResult');out.textContent='Aion is reading and answering with its native English system…';const r=await fetch('/api/aion/english-intelligence/reading-academy/run',{method:'POST'});if(!r.ok)throw Error(`HTTP ${r.status}`);const d=await r.json();out.textContent=d.status==='library_complete'?'The current library is fully read; delayed retention checks will run when due.':`${num(d.sentences_read)} sentences read · ${num(d.exercises_correct)}/${num(d.exercises_attempted)} comprehension answers correct · ${num(d.new_concepts_encountered)} new concept encounters · ${num(d.claims_recorded)} sourced claims · no model used.`;refresh()}
let refreshBusy=false;async function refresh(){if(refreshBusy)return;refreshBusy=true;try{const r=await fetch('/api/aion/english-intelligence/progress',{cache:'no-store'});if(!r.ok)throw Error(`HTTP ${r.status}`);render(await r.json())}catch(e){const h=$('health');h.className='health offline';h.innerHTML='<span class="dot"></span>Panel unavailable';const a=$('alert');a.className='alert show';a.textContent=e.message}finally{refreshBusy=false}}
let currentTurnId='';async function askNative(){const q=$('nativeQuestion').value.trim();if(!q)return;$('nativeAnswer').className='native-answer muted';$('nativeAnswer').textContent='Aion is reasoning…';$('nativeProof').textContent='';$('correctionBox').style.display='none';try{const r=await fetch('/api/aion/english-intelligence/conversation/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q,session_id:'english-progress-panel'})});if(!r.ok)throw Error(`HTTP ${r.status}`);const d=await r.json();currentTurnId=d.turn_id;$('correctionBox').style.display='block';$('nativeAnswer').className=`native-answer ${d.status==='answered'?'ok':d.status==='reference_only'?'muted':'bad'}`;$('nativeAnswer').textContent=d.answer;const knowledge=d.knowledge_status==='acquired'?`Acquired concept · ${String(d.acquisition_stage||'').replaceAll('_',' ')}`:d.knowledge_status==='reference_only'?`Reference only · ${String(d.acquisition_stage||'not started').replaceAll('_',' ')}`:String(d.knowledge_status||d.status).replaceAll('_',' ');$('nativeProof').textContent=`${knowledge} · ${Math.round(Number(d.confidence||0)*100)}% confidence · ${d.evidence.length} evidence item${d.evidence.length===1?'':'s'} · Native Aion · no Qwen · no cloud · no token prediction`;}catch(e){$('nativeAnswer').className='native-answer bad';$('nativeAnswer').textContent=`Unable to ask Aion: ${e.message}`}}
async function correctAion(){const proposed=$('correctedAnswer').value.trim();if(!currentTurnId||!proposed)return;const r=await fetch(`/api/aion/english-intelligence/conversation/${encodeURIComponent(currentTurnId)}/correction`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({proposed_answer:proposed,reason:$('correctionReason').value.trim(),source_ref:''})});if(!r.ok)throw Error(`HTTP ${r.status}`);const d=await r.json();$('correctionResult').textContent=d.verified?`Verified correction accepted. ${d.remedial_action.replaceAll('_',' ')}. It must still pass closed-book practice.`:`Not learned automatically: ${d.verification_reason}`;refresh()}
async function runTransfer(){const kind=$('transferKind').value,material=$('transferMaterial').value.trim(),question=$('transferQuestion').value.trim(),expected_answer=$('transferExpected').value.trim(),answer_reason=$('transferReason').value.trim();if(!material)return;const out=$('transferResult');out.className='transfer-result muted';out.textContent='Aion is building a native parse…';const r=await fetch('/api/aion/english-intelligence/transfer/challenge',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind,material,question,expected_answer,answer_reason})});if(!r.ok)throw Error(`HTTP ${r.status}`);const d=await r.json(),a=d.attempt,p=a.parse||{},f=p.frame||{},g=p.grounding||{},se=a.semantic_evidence||null;const verdict=a.correct===null?'Not independently graded':a.correct?'Correct':'Incorrect';const cells=Object.entries(f).map(([k,v])=>`<div class="parse-cell"><span>${esc(k)}</span>${esc(v??'—')}</div>`).join('');const clauses=(p.clauses||[]).map((c,i)=>`<div class="parse-cell"><span>${c.subordinate?'Subordinate clause':'Main clause'} ${i+1}</span>${esc((c.tokens||[]).join(' '))}<div class="proof">subject=${esc(c.subject||'—')} · action=${esc(c.action||'—')} · object=${esc(c.object||c.complement||'—')} · negated=${esc(c.negated)}</div></div>`).join('');const semanticProof=se?`<div class="proof ok">Acquired meaning proof · ${esc(se.target_lemma)} · ${esc(se.target_concept_id)} · stage ${esc(se.target_stage)} · bridge ${esc((se.semantic_bridge||[]).join(', '))} · target reference fallback: ${se.target_reference_fallback?'yes':'no'} · no model/cloud</div>`:'';out.className=`transfer-result ${a.correct===false?'bad':a.correct===true?'ok':''}`;out.innerHTML=`<span class="transfer-badge">${a.first_seen?'First seen':'Repeated material'}</span><span class="transfer-badge">${esc(verdict)}</span>${se?'<span class="transfer-badge">Acquired meaning used</span>':''}<h3>${esc(a.answer)}</h3><div>${esc(a.explanation)}</div><div class="parse-grid">${cells}</div>${clauses?`<div class="parse-grid">${clauses}</div>`:''}${semanticProof}<div class="proof">Confidence ${Math.round(Number(a.confidence||0)*100)}% · acquired ${num(g.acquired)} · reference ${num(g.reference)} · structural ${num(g.structural)} · unknown ${num(g.unknown)} · ambiguities ${(p.ambiguities||[]).map(esc).join(', ')||'none'} · no model/cloud</div>${a.correct===false?`<div class="answer-reveal">Sealed answer: ${esc(a.correct_answer)}</div>`:''}`;refresh()}
let currentGame=null,selectedAnswer='',orderedTokens=[];
function gameAnswerValue(){return currentGame?.response_mode==='token_order'?orderedTokens.join(' ').replace(/\s+([,.?!])/g,'$1'):$('gameAnswer').style.display==='none'?selectedAnswer:$('gameAnswer').value.trim()}
function renderGame(g){currentGame=g;selectedAnswer='';orderedTokens=[];$('gamePrompt').className='game-prompt';$('gamePrompt').textContent=g.prompt;const box=$('gameChoices');box.innerHTML='';$('gameAnswer').value='';$('gameAnswer').style.display='none';$('clearTokens').style.display=g.response_mode==='token_order'?'inline-block':'none';for(const value of g.choices||[]){const el=document.createElement('button');el.className=g.response_mode==='token_order'?'token':'choice';el.textContent=value;el.onclick=()=>{if(g.response_mode==='token_order'){orderedTokens.push(value);el.disabled=true;el.classList.add('selected');$('gameAnswer').style.display='block';$('gameAnswer').value=gameAnswerValue()}else{selectedAnswer=value;[...box.children].forEach(x=>x.classList.remove('selected'));el.classList.add('selected')}};box.appendChild(el)}$('humanAnswer').disabled=false;$('aionAnswer').disabled=false;$('gameResult').className='game-result';$('gameResult').innerHTML=''}
async function newGame(){const family=$('gameFamily').value,difficulty=Number($('gameDifficulty').value);const r=await fetch('/api/aion/english-intelligence/games/new',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({family,difficulty})});if(!r.ok)throw Error(`HTTP ${r.status}`);renderGame(await r.json())}
async function submitGame(player){if(!currentGame)return;const answer=player==='aion'?'':gameAnswerValue();if(player==='human'&&!answer)return;const r=await fetch(`/api/aion/english-intelligence/games/${encodeURIComponent(currentGame.game_id)}/answer`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({answer,player})});if(!r.ok)throw Error(`HTTP ${r.status}`);const d=await r.json(),result=$('gameResult');[...$('gameChoices').children].forEach(x=>{if(String(x.textContent).trim()===String(d.correct_answer).trim())x.classList.add('correct-answer')});result.className=`game-result show ${d.correct?'correct':'wrong'}`;result.innerHTML=`<b>${d.correct?'Correct':'Not quite'}${player==='aion'?' — Aion answered':''}</b><div>Aion/player answer: ${esc(d.answer||'No answer')}</div>${d.correct?'':`<div class="answer-reveal">Correct answer: ${esc(d.correct_answer)}</div>`}<div class="why">Why: ${esc(d.explanation)}</div><div class="proof">${d.correction?'Verified correction stored and related retry scheduled.':'Result recorded.'} No model or cloud was used.</div>`;refresh()}
$('newGame').addEventListener('click',()=>newGame().catch(e=>{$('gamePrompt').textContent=e.message}));$('humanAnswer').addEventListener('click',()=>submitGame('human'));$('aionAnswer').addEventListener('click',()=>submitGame('aion'));$('clearTokens').addEventListener('click',()=>{orderedTokens=[];$('gameAnswer').value='';[...$('gameChoices').children].forEach(x=>{x.disabled=false;x.classList.remove('selected')})});
$('askNative').addEventListener('click',askNative);$('nativeQuestion').addEventListener('keydown',e=>{if(e.key==='Enter')askNative()});
$('correctAion').addEventListener('click',()=>correctAion().catch(e=>{$('correctionResult').textContent=e.message}));
$('runTransfer').addEventListener('click',()=>runTransfer().catch(e=>{$('transferResult').textContent=e.message}));
$('ingestReading').addEventListener('click',()=>ingestReading().catch(e=>{$('readingResult').textContent=e.message}));$('runReading').addEventListener('click',()=>runReading().catch(e=>{$('readingResult').textContent=e.message}));
$('startSpider').addEventListener('click',()=>spiderPost('start',{seed:$('spiderSeed').value.trim()||'language'}).catch(e=>{$('spiderStatus').textContent=e.message}));$('pauseSpider').addEventListener('click',()=>spiderPost('pause').catch(e=>{$('spiderStatus').textContent=e.message}));$('stepSpider').addEventListener('click',()=>{spiderBusy=true;spiderPost('step').catch(e=>{$('spiderStatus').textContent=e.message}).finally(()=>spiderBusy=false)});
refresh();setInterval(refresh,10000);setInterval(spiderTick,1900);
</script></body></html>"""


__all__ = ["router"]
