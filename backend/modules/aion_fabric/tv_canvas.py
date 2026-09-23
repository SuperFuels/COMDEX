from __future__ import annotations

import html
import ipaddress
import json
import os
import secrets
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

import qrcode
import qrcode.image.svg

from .god_view import GodViewData, god_view_html


def _lan_address(preferred_peer: str | None = None) -> str:
    """Resolve the mother's LAN address without sending application data."""
    peer = preferred_peer or "192.0.2.1"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect((peer, 9))
            address = str(probe.getsockname()[0])
    except OSError:
        address = socket.gethostbyname(socket.gethostname())
    parsed = ipaddress.ip_address(address)
    if not parsed.is_private or parsed.is_loopback:
        raise RuntimeError("A private LAN address is required for the TV Canvas")
    return address


def _qr_svg(value: str) -> bytes:
    image = qrcode.make(value, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=3)
    return image.to_string(encoding="unicode").encode("utf-8")


@lru_cache(maxsize=96)
def _local_spanish_speech(text: str) -> bytes:
    """Create bounded natural speech, with a private local fallback."""
    phrase = " ".join(str(text).split())[:240]
    def configured_value(name: str) -> str:
        direct = os.getenv(name, "").strip()
        if direct and direct.isascii():
            return direct
        for environment_path in (Path(".env.local"), Path("backend/.env.local")):
            try:
                for raw_line in environment_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if raw_line.strip().startswith(f"{name}="):
                        candidate = raw_line.split("=", 1)[1].strip().strip("'\"")
                        return candidate if candidate and candidate.isascii() else ""
            except OSError:
                continue
        return ""

    elevenlabs_key = configured_value("ELEVENLABS_API_KEY")
    if phrase and elevenlabs_key:
        voice_id = configured_value("ELEVENLABS_VOICE_ID") or "C9fbwSpEaejywLWx722Z"
        payload = json.dumps(
            {
                "text": phrase,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.42,
                    "similarity_boost": 0.8,
                    "style": 0.24,
                    "use_speaker_boost": True,
                },
            }
        ).encode("utf-8")
        request = Request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128",
            data=payload,
            headers={"xi-api-key": elevenlabs_key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=18) as response:
                natural_audio = response.read(2_000_001)
            if len(natural_audio) <= 2_000_000 and (
                natural_audio.startswith(b"ID3") or natural_audio.startswith((b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"))
            ):
                return natural_audio
        except (OSError, UnicodeError):
            pass

    direct_key = os.getenv("OPENAI_API_KEY", "").strip()
    api_key = direct_key if direct_key.startswith("sk-") and direct_key.isascii() else ""
    if not api_key:
        try:
            from backend.modules.vault.ai_provider_key_store import get_ai_provider_secret

            vaulted_key = str(get_ai_provider_secret("openai") or "").strip()
            api_key = vaulted_key if vaulted_key.startswith("sk-") and vaulted_key.isascii() else ""
        except Exception:
            api_key = ""
    if not api_key:
        candidate = configured_value("OPENAI_API_KEY")
        api_key = candidate if candidate.startswith("sk-") else ""
    if phrase and api_key:
        payload = json.dumps(
            {
                "model": "gpt-4o-mini-tts",
                "voice": "marin",
                "input": phrase,
                "instructions": (
                    "Speak in natural Spanish from Spain as a warm, encouraging primary-school teacher. "
                    "Use clear pronunciation, gentle energy, natural intonation, and a slightly slower learning pace. "
                    "Do not add or remove words."
                ),
                "response_format": "wav",
            }
        ).encode("utf-8")
        request = Request(
            "https://api.openai.com/v1/audio/speech",
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=18) as response:
                natural_audio = response.read(2_000_001)
            if natural_audio.startswith(b"RIFF") and len(natural_audio) <= 2_000_000:
                return natural_audio
        except (OSError, UnicodeError):
            pass
    say = shutil.which("say")
    if not phrase or not say:
        return b""
    with tempfile.TemporaryDirectory(prefix="aion-education-speech-") as directory:
        output = f"{directory}/speech.wav"
        subprocess.run(
            [say, "-v", "Monica", "-r", "145", "-o", output, "--data-format=LEI16@22050", phrase],
            check=True,
            timeout=8,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        with open(output, "rb") as audio:
            return audio.read(1_000_001)[:1_000_000]


def _canvas_html(token: str) -> bytes:
    safe_token = html.escape(token, quote=True)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pilot TV</title>
<style>
:root{{--bg:#f7f9fc;--panel:#fff;--line:#e3e8f0;--ink:#182238;--muted:#6c7890;--blue:#246bfd;--green:#19a974;--amber:#d97b00;--shadow:#30486a18}}
*{{box-sizing:border-box}}html,body{{margin:0;width:100%;height:100%;overflow:hidden;color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}body{{background:radial-gradient(circle at 50% -20%,#e3efff 0,#f7f9fc 42%,#fff 100%)}}
.shell{{height:100vh;padding:4.2vh 4.5vw 3vh;display:grid;grid-template-rows:auto 1fr auto;gap:2.7vh}}header{{display:flex;justify-content:space-between;align-items:center}}header>div:first-child{{display:grid;grid-template-columns:auto 1fr;column-gap:1.1vw;align-items:center}}header>div:first-child:before{{content:'P';grid-row:1/3;display:grid;place-items:center;width:3.5vw;height:3.5vw;border-radius:1.05vw;color:#fff;font-size:1.9vw;font-weight:850;background:conic-gradient(from 210deg,#4285f4,#7c4dff,#ea4335,#fbbc05,#34a853,#4285f4);box-shadow:0 .8vw 2vw #4279cc30}}.brand{{grid-column:2;letter-spacing:.18em;color:#5b718d;font-size:.82vw;font-weight:850;text-transform:uppercase}}h1{{grid-column:2;font-size:2.2vw;line-height:1;margin:.35vh 0 0;letter-spacing:-.045em}}.online{{font-size:1vw;padding:.7vw 1.15vw;border:1px solid #bee9d4;border-radius:99px;color:#13885f;background:#ecfbf4;box-shadow:0 .3vw 1vw #2034500c}}
.content{{display:grid;grid-template-columns:1.5fr .7fr;gap:1.35vw;min-height:0}}.hero,.rail>div{{border:1px solid var(--line);background:rgba(255,255,255,.94);border-radius:1.7vw;box-shadow:0 .8vw 2.8vw var(--shadow)}}.hero{{padding:2.5vw;display:flex;flex-direction:column;justify-content:space-between;min-height:0}}.kicker{{color:var(--blue);font-size:.85vw;text-transform:uppercase;letter-spacing:.15em;font-weight:850}}#headline{{font-size:3.15vw;line-height:1.05;margin:.8vh 0 1.1vh;max-width:92%;letter-spacing:-.05em}}#detail{{color:var(--muted);font-size:1.25vw;line-height:1.42;max-width:94%}}.experiences{{display:grid;grid-template-columns:repeat(4,1fr);gap:.75vw;margin:2.2vh 0 1vh}}.experience{{min-height:8.2vw;padding:1vw;border:1px solid var(--line);border-radius:1.25vw;background:#fff;box-shadow:0 .4vw 1.5vw #30486a0d;font:inherit;color:inherit;text-align:left}}.experience:disabled{{cursor:not-allowed}}.experience i{{display:grid;place-items:center;width:2.6vw;height:2.6vw;border-radius:.8vw;background:#f0f3ff;font-style:normal;font-size:1.35vw}}.experience:nth-child(2) i{{background:#eaf7ff}}.experience:nth-child(3) i{{background:#eafaf2}}.experience:nth-child(4) i{{background:#fff4e7}}.experience strong{{display:block;font-size:1.15vw;margin-top:.8vh}}.experience span{{display:block;color:var(--muted);font-size:.78vw;line-height:1.25;margin-top:.25vh}}.list{{display:grid;grid-template-columns:repeat(4,1fr);gap:.75vw;margin-top:1.2vh}}.pill{{padding:.85vw 1vw;border:1px solid var(--line);border-radius:1vw;background:#fbfcff}}.pill strong{{display:block;font-size:1.45vw;color:var(--blue)}}.pill span{{font-size:.76vw;color:var(--muted)}}#results{{display:none;grid-template-columns:1fr 1fr;gap:.7vw;margin-top:1.4vh;overflow:hidden}}.result{{padding:.8vw 1vw;border:1px solid var(--line);border-left:.24vw solid var(--blue);background:#fbfcff;border-radius:.8vw;font-size:.78vw}}.result strong{{display:block;font-size:1vw}}.result span{{color:var(--muted)}}
.home-logo,.home-search{{display:none}}.shell.home-mode{{padding:3.6vh 4.5vw 2.5vh}}.home-mode header>div:first-child{{display:block}}.home-mode header>div:first-child:before{{display:none}}.home-mode header h1{{font-size:1.75vw;line-height:1.05;margin:.4vh 0 0}}.home-mode .brand{{font-size:.72vw}}.home-mode .content{{display:block}}.home-mode .hero{{height:100%;padding:0 8.5vw;border:0;background:transparent;box-shadow:none;display:block;text-align:center}}.home-mode .rail,.home-mode .kicker,.home-mode #metrics{{display:none}}.home-mode .home-logo{{display:grid;place-items:center;width:5.4vw;height:5.4vw;margin:4.2vh auto 2.5vh;border-radius:1.55vw;color:#fff;font-size:2.85vw;font-weight:850;background:#4285f4;background:conic-gradient(from 210deg,#4285f4,#7c4dff,#ea4335,#fbbc05,#34a853,#4285f4);box-shadow:0 1.1vw 2.8vw #4279cc35}}.home-mode #headline{{max-width:none;margin:0;font-size:3.45vw;letter-spacing:-.055em}}.home-mode #detail{{max-width:none;margin:1.2vh 0 0;font-size:1.3vw}}.home-mode .home-search{{display:grid;grid-template-columns:1fr auto;align-items:center;max-width:65vw;min-height:6.9vw;margin:2.5vh auto 4vh;padding:.7vw .8vw .7vw 2vw;border:1px solid #dfe5ee;border-radius:1.8vw;background:#fff;box-shadow:0 1.1vw 3.2vw #34496b16;text-align:left;color:#737f92;font-size:1.22vw}}.home-mode .home-search button{{border:0;border-radius:1.25vw;padding:1.2vw 1.8vw;color:#fff;background:linear-gradient(135deg,#246bfd,#7657e8);font:inherit;font-weight:750;box-shadow:0 .5vw 1.4vw #3f65d733}}.home-mode .experiences{{max-width:80vw;margin:0 auto;gap:1.25vw;text-align:left}}.home-mode .experience{{min-height:10.8vw;padding:1.45vw;border-radius:1.55vw;box-shadow:0 .55vw 1.8vw #2c3b5510}}.home-mode .experience i{{width:3.3vw;height:3.3vw;border-radius:1vw;font-size:1.7vw}}.home-mode .experience strong{{font-size:1.45vw;margin-top:1.35vh}}.home-mode .experience span{{font-size:.95vw;line-height:1.35;margin-top:.5vh}}
.rail{{display:grid;grid-template-rows:.72fr 1fr 1fr;gap:1vw}}.rail>div{{padding:1.35vw}}.label{{color:var(--muted);font-size:.7vw;text-transform:uppercase;letter-spacing:.13em;font-weight:750}}.big{{font-size:2.8vw;font-weight:800;color:var(--blue);margin-top:.35vh}}#heard{{font-size:1.05vw;line-height:1.3;margin-top:.65vh;color:var(--ink)}}#reply,#belief,#plan{{color:var(--green);font-size:.88vw;line-height:1.35;margin-top:.6vh}}#belief{{color:var(--blue)}}#plan{{color:var(--amber)}}footer{{display:flex;justify-content:space-between;color:var(--muted);font-size:.78vw;padding:0 .3vw}}#clock{{color:var(--ink);font-weight:750}}.pulse{{display:inline-block;width:.55vw;height:.55vw;border-radius:50%;background:var(--green);margin-right:.55vw}}#pair-qr{{display:none;width:15vw;min-width:170px;background:white;border:1px solid var(--line);border-radius:1.2vw;padding:.65vw;margin-top:1.5vh;box-shadow:0 .8vw 2vw var(--shadow)}}
#private-workspace{{display:none;grid-template-columns:repeat(auto-fit,minmax(9vw,1fr));max-width:84vw;margin:1.2vh auto 0;gap:.7vw;text-align:left}}#private-workspace .experience{{min-height:7.5vw;padding:.9vw}}#private-workspace .experience strong{{font-size:1.02vw}}#private-workspace .experience span{{font-size:.7vw}}#private-workspace.locked .experience{{opacity:.58;background:#f3f5f9}}#private-workspace.locked .experience strong:after{{content:' · Locked';color:var(--muted);font-size:.62vw;font-weight:700}}#workspace-lock{{display:none;max-width:80vw;margin:1.2vh auto 0;padding:1vw 1.3vw;border:1px solid #dfe5ee;border-radius:1.2vw;background:#ffffffb8;color:var(--muted);font-size:.9vw}}
#private-presentation{{display:none;position:fixed;inset:0;z-index:20;padding:5vh 6vw;background:#f7f9fc;color:var(--ink);overflow:hidden}}#private-presentation.visible{{display:block}}#private-presentation .presentation-meta{{color:var(--blue);font-size:1vw;text-transform:uppercase;letter-spacing:.13em;font-weight:800}}#private-presentation h2{{font-size:3.2vw;margin:1.4vh 0 2.5vh}}#presentation-content{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1.2vw;max-height:72vh;overflow:hidden}}#presentation-content article{{padding:1.25vw;border:1px solid var(--line);border-radius:1.1vw;background:#fff}}#presentation-content strong{{display:block;font-size:1.15vw;margin-bottom:.6vh}}#presentation-content span{{display:block;color:var(--muted);font-size:.92vw;line-height:1.4;white-space:pre-wrap}}#private-presentation footer{{position:absolute;left:6vw;right:6vw;bottom:3vh}}
/* Pilot mark: a simple forward-moving jet silhouette, shared with the dashboard. */
header>div:first-child:before,.home-mode .home-logo{{content:'';color:transparent;font-size:0;background:#4285f4;background-image:conic-gradient(from 210deg,#4285f4,#7c4dff,#ea4335,#fbbc05,#34a853,#4285f4)}}.home-mode .home-logo{{position:relative}}.home-mode .home-logo:after{{content:'';position:absolute;inset:22%;background:#fff;-webkit-clip-path:polygon(50% 2%,58% 28%,94% 49%,94% 60%,58% 49%,58% 77%,72% 90%,72% 98%,50% 89%,28% 98%,28% 90%,42% 77%,42% 49%,6% 60%,6% 49%,42% 28%);clip-path:polygon(50% 2%,58% 28%,94% 49%,94% 60%,58% 49%,58% 77%,72% 90%,72% 98%,50% 89%,28% 98%,28% 90%,42% 77%,42% 49%,6% 60%,6% 49%,42% 28%);filter:drop-shadow(0 .12vw .12vw #17315b35)}}
header>div:first-child:before,.home-mode .home-logo{{background:#0b2a55;background-image:linear-gradient(145deg,#071a35 0%,#1557d6 52%,#29a9ff 100%)}}.home-mode .home-logo:after{{inset:25% 13%;transform:rotate(-5deg);-webkit-clip-path:polygon(2% 56%,27% 43%,38% 41%,48% 46%,68% 45%,81% 33%,88% 7%,98% 7%,94% 44%,99% 48%,99% 63%,75% 69%,68% 84%,57% 84%,53% 69%,35% 68%,32% 77%,24% 75%,23% 66%,5% 64%,0% 59%);clip-path:polygon(2% 56%,27% 43%,38% 41%,48% 46%,68% 45%,81% 33%,88% 7%,98% 7%,94% 44%,99% 48%,99% 63%,75% 69%,68% 84%,57% 84%,53% 69%,35% 68%,32% 77%,24% 75%,23% 66%,5% 64%,0% 59%)}}
</style></head><body><div class="shell">
<header><div><div class="brand">Tessaris · Your local intelligence</div><h1>Pilot</h1></div><div class="online"><span class="pulse"></span>Pilot online</div></header>
<main class="content"><section class="hero"><div><div class="home-logo">P</div><div id="kicker" class="kicker">Pilot Home</div><div id="headline">What would you like to do?</div><div id="detail">Choose an experience or ask Pilot naturally.</div><div class="home-search"><span>Ask Pilot anything…</span><button type="button" tabindex="-1">Ask Pilot</button><button type="button" onclick="location.href='/tv/{safe_token}/god-view'">🌍 God View</button></div><div id="experiences" class="experiences"></div><div id="private-workspace"></div><div id="workspace-lock">Private areas are locked. Use a trusted phone to acquire this television.</div><img id="pair-qr" alt="Scan to connect a phone to Pilot"><div id="results"></div></div><div id="metrics" class="list"></div></section>
<aside class="rail"><div><div class="label">Television volume</div><div id="volume" class="big">—</div><div id="tv-state" class="label">Waiting for state</div></div><div><div class="label">Autopilot belief</div><div id="belief">Building a truthful screen-state model…</div><div id="plan">No active plan</div></div><div><div class="label">Last conversation</div><div id="heard">Say “Pilot” followed by a command.</div><div id="reply">Listening locally…</div></div></aside></main>
<footer><div><span id="active-person">No private person signed in</span> · no control keys or private memory stored on TV</div><div id="clock"></div></footer>
</div><section id="private-presentation" aria-live="polite"><div class="presentation-meta" id="presentation-meta"></div><h2 id="presentation-title"></h2><div id="presentation-content"></div><footer>Deliberately presented from the active person's authorized repository · closes automatically when authority expires</footer></section><script>
const stateUrl='/tv/{safe_token}/state';
const copy={{home:['Pilot Home','What would you like to do?','Choose an experience or ask Pilot naturally.'],mesh:['Device Mesh','One intelligence. Every reachable surface.','Pilot is mapping capable devices, their transports, permissions, and verified controls across the local fabric.'],tasks:['My Tasks','Your day, organised.','Review personal tasks, shared responsibilities, reminders and requests waiting for you.'],calendar:['My Calendar','Your time, clearly arranged.','Review your private schedule and actions prepared for your approved calendar services.'],boardroom:['Pilot Boardroom','Your business command centre.','Boardroom remains separately authenticated from the household workspace.'],files:['My Files','Your approved documents on the big screen.','Open saved proposals, research and assets without exposing another person’s files.'],iot:['Connected Home','Your household devices in one place.','Review connected devices, their state, permissions and available controls.'],work:['Personal Work','A workspace for everyone.','A dedicated place for research, writing, study and personal projects—without requiring a business.'],briefing:['Live Briefing','Your environment at a glance.','Pilot is combining current TV state, nearby fabric nodes, and recent voice activity into one calm view.'],companion:['Phone Controller','Put Pilot in your hand.','Open the private address shown below on a phone connected to this Wi-Fi, then enter the access code.'],games:['Pilot Games','Cloud gaming, composed across the TV and phone.','Pilot launches GeForce NOW on this display, keeps sign-in private on your phone, and hands live gameplay to the LG Mobile Gamepad.'],education:['Pilot Learning Centre','¡Vamos a aprender español!','Choose an answer on the private phone controller. Pilot adapts the next challenge to what needs more practice.'],research:['Pilot Live Research','Current answers, built for this screen.','Pilot researched the request on the mother brain. Say “open the first result” to continue.'],agent:['Pilot Agent Task','Planning the outcome, not just opening an app.','Pilot observed the TV, researched the request, and stopped at the private approval boundary.']}};
function pill(value,label){{return `<div class="pill"><strong>${{value}}</strong><span>${{label}}</span></div>`}}
const tilePresentation={{games:['🎮','Open cloud gaming on the television.'],aion:['📺','Put Pilot on the big screen and control the room.'],education_start:['🎓','Start the interactive Learning Centre.'],shopping:['🛒','Find, compare and prepare a purchase.'],tasks:['✓','Your private lists and reminders.'],calendar:['▣','Your private schedule and approved events.'],files:['▤','Your approved documents and saved assets.'],work:['✦','Research, writing, study and personal projects.'],devices:['⌁','Connect and manage permitted household devices.'],personal:['●','Unlock your private Pilot.'],household:['⌂','Unlock household tools.'],workspace:['◇','No Workspace membership is exposed while locked.'],boardroom:['◆','No Boardroom membership is exposed while locked.']}};
let lastSurfaceManifest='';
function renderSurfaceTiles(s){{const manifest=s.surface_manifest||{{}},hash=manifest.payload_hash||'';if(!hash||hash===lastSurfaceManifest)return;lastSurfaceManifest=hash;const makeTile=tile=>{{const id=String(tile.tile_id||''),base=id.split('.')[0],presentation=tilePresentation[id]||tilePresentation[base]||['•','Authorized by your current signed membership.'],button=document.createElement('button');button.className='experience'+(tile.privacy==='locked'?' locked':'');button.dataset.authorityDomain=String(tile.authority_domain||'');button.disabled=tile.privacy==='locked';const icon=document.createElement('i'),strong=document.createElement('strong'),detail=document.createElement('span');icon.textContent=presentation[0];strong.textContent=String(tile.label||'Pilot');detail.textContent=tile.privacy==='locked'?presentation[1]:(String(tile.role||'')?presentation[1]+' · '+String(tile.role).replaceAll('_',' '):presentation[1]);button.append(icon,strong,detail);return button}},tiles=Array.isArray(manifest.tiles)?manifest.tiles:[],publicTiles=tiles.filter(x=>x.privacy==='public'),privateTiles=tiles.filter(x=>x.privacy!=='public');document.getElementById('experiences').replaceChildren(...publicTiles.map(makeTile));document.getElementById('private-workspace').replaceChildren(...privateTiles.map(makeTile))}}
function presentationCards(value,prefix=''){{const cards=[];if(Array.isArray(value))value.slice(0,12).forEach((item,index)=>cards.push(...presentationCards(item,prefix?prefix+' '+(index+1):String(index+1))));else if(value&&typeof value==='object')Object.entries(value).slice(0,20).forEach(([key,item])=>{{if(item&&typeof item==='object')cards.push(...presentationCards(item,prefix?prefix+' · '+key:key));else cards.push([prefix?prefix+' · '+key:key,String(item??'')])}});else cards.push([prefix||'Details',String(value??'')]);return cards.slice(0,16)}}
function renderPresentation(s){{const panel=document.getElementById('private-presentation'),presentation=s.presentation||null;if(!presentation){{panel.classList.remove('visible');document.getElementById('presentation-title').textContent='';document.getElementById('presentation-content').replaceChildren();return}}document.getElementById('presentation-meta').textContent=String(presentation.content_kind||'presentation')+' · '+String(presentation.authority_domain||'authorized');document.getElementById('presentation-title').textContent=String(presentation.title||'Pilot');const nodes=presentationCards(presentation.content).map(([label,value])=>{{const article=document.createElement('article'),strong=document.createElement('strong'),span=document.createElement('span');strong.textContent=label;span.textContent=value;article.append(strong,span);return article}});document.getElementById('presentation-content').replaceChildren(...nodes);panel.classList.add('visible')}}
let lastSpeakNonce=-1;
function speakSpanish(text,nonce){{if(!text||nonce===lastSpeakNonce||!('speechSynthesis'in window))return;lastSpeakNonce=nonce;window.speechSynthesis.cancel();const utterance=new SpeechSynthesisUtterance(text);utterance.lang='es-ES';utterance.rate=.82;window.speechSynthesis.speak(utterance)}}
async function refresh(){{try{{const s=await (await fetch(stateUrl,{{cache:'no-store'}})).json();document.querySelector('.shell').classList.toggle('home-mode',s.view==='home');const c=copy[s.view]||copy.home;const b=s.autopilot_belief||{{}};const p=s.active_plan||s.last_plan||null;const task=(s.tv_agent&&s.tv_agent.active_task)||null;const prepared=(task&&task.prepared_result)||{{}};const edu=s.education||{{}},lesson=edu.session||null,profile=lesson?((edu.profiles||{{}})[lesson.profile_id]||{{}}):{{}};const privateWorkspace=s.private_workspace||{{}},privateTasks=privateWorkspace.tasks||[];const second=s.view==='boardroom'?pill(s.boardroom_sessions,'boardroom sessions'):pill(s.enrolled_nodes,'enrolled');document.getElementById('kicker').textContent=s.view==='education'&&lesson?(lesson.category+' · Round '+lesson.round_number):c[0];document.getElementById('headline').textContent=s.view==='education'&&lesson?lesson.prompt:s.view==='tasks'?(privateTasks.length?privateTasks.filter(x=>x.status==='open').length+' open task'+(privateTasks.filter(x=>x.status==='open').length===1?'':'s'):'No tasks yet'):s.view==='research'&&s.research?('Results for “'+s.research.query+'”'):s.view==='agent'&&task?(prepared.title||task.request):c[1];document.getElementById('detail').textContent=s.view==='education'&&lesson?((lesson.feedback?lesson.feedback+'  ':'')+(lesson.instruction||lesson.explanation||'')):s.view==='companion'?('Address: '+(s.companion_url||'unavailable')+'  ·  Access code: '+(s.companion_code||'unavailable')):s.view==='research'&&s.research?s.research.answer:s.view==='agent'&&task?((prepared.summary||'Status: '+task.status)+((task.approval&&task.approval.state==='pending')?(' On your phone open '+(s.companion_url||'the companion surface')+' and enter '+(s.companion_code||'the code shown here')+'.'):' ')):c[2];const results=document.getElementById('results');const items=s.view==='tasks'?privateTasks.map(x=>({{title:x.title,detail:(x.status||'open').replaceAll('_',' ')+(x.assigned_to_me?' · assigned to you':''),reason:''}})):s.view==='education'&&lesson?(lesson.choices||[]).map(x=>({{title:String.fromCharCode(65+x.index)+'. '+x.text,detail:'Choose on the phone',reason:''}})):s.view==='agent'&&task?(prepared.items||[]):((s.research&&s.research.items)||[]);results.style.display=((s.view==='tasks'||s.view==='education'||s.view==='research'||s.view==='agent')&&items.length)?'grid':'none';results.replaceChildren(...items.slice(0,8).map((x,i)=>{{const card=document.createElement('div');card.className='result';const title=document.createElement('strong');title.textContent=s.view==='education'?x.title:(i+1)+'. '+x.title;const detail=document.createElement('span');detail.textContent=(x.detail||'')+(x.reason?' · '+x.reason:'');card.append(title,detail);return card}}));document.getElementById('metrics').innerHTML=s.view==='education'&&lesson?pill(profile.stars||0,'stars')+pill(profile.streak||0,'streak')+pill(profile.correct||0,'correct')+pill(profile.attempts||0,'attempts'):pill(s.fabric_nodes,'fabric nodes')+second+pill(s.verified_actions,'verified actions')+pill(Math.round((b.confidence||0)*100)+'%','belief confidence');document.getElementById('volume').textContent=s.tv_volume==null?'—':s.tv_volume;document.getElementById('tv-state').textContent=s.view==='education'&&lesson?lesson.display_name:(s.tv_name||'Connected television');document.getElementById('belief').textContent=s.view==='education'?'Adaptive practice · local curriculum':(b.surface||'unknown')+(b.view?' · '+b.view:'')+' — '+(b.evidence||'No evidence yet');document.getElementById('plan').textContent=s.view==='education'?'Words, listening and conversation':task?(task.route+' · '+task.status):p?(p.name+' · '+p.status+' · '+(p.summary||p.goal||'')):'No active plan';document.getElementById('heard').textContent=s.view==='education'?'Listen, think, then choose on the phone.':(s.last_transcript||'Say “Pilot” followed by a command.');document.getElementById('reply').textContent=s.view==='education'&&lesson?(lesson.phase==='feedback'?'Press Next challenge on the phone.':'AION is listening for your answer.'):(s.last_response||'Listening locally…');const active=s.active_identity||{{}};document.getElementById('active-person').textContent=active.display_name?('Active: '+active.display_name):'No private person signed in';if(s.view==='education'&&lesson)speakSpanish(lesson.speak_text,lesson.speak_nonce)}}catch(e){{document.getElementById('reply').textContent='Reconnecting to the mother brain…'}}}}
async function refreshPairing(){{try{{const s=await(await fetch(stateUrl,{{cache:'no-store'}})).json();const qr=document.getElementById('pair-qr');qr.style.display=s.view==='companion'?'block':'none';document.getElementById('experiences').style.display=s.view==='home'?'grid':'none';if(s.view==='companion'&&!qr.src)qr.src=stateUrl.replace('/state','/pair.svg')}}catch(e){{}}}}
async function refreshWorkspace(){{try{{const s=await(await fetch(stateUrl,{{cache:'no-store'}})).json(),active=s.active_identity||{{}},summary=s.workspace_summary||{{}},home=s.view==='home',workspace=document.getElementById('private-workspace'),lock=document.getElementById('workspace-lock');renderSurfaceTiles(s);workspace.style.display=home?'grid':'none';workspace.classList.toggle('locked',home&&!active.persona_id);lock.style.display=home&&!active.persona_id?'block':'none';if(home&&active.persona_id){{document.getElementById('headline').textContent='Welcome, '+active.display_name;document.getElementById('detail').textContent='Only this person’s currently authorized Personal, Household, Workspace and Boardroom areas are shown. The screen locks after five minutes without activity.';const taskTile=[...workspace.querySelectorAll('.experience')].find(x=>x.querySelector('strong')?.textContent==='Tasks'),taskText=taskTile?.querySelector('span');if(taskText)taskText.textContent=(summary.open_tasks||0)+' open · '+(summary.waiting_for_acceptance||0)+' awaiting you'}}}}catch(e){{}}}}
async function refreshPresentation(){{try{{renderPresentation(await(await fetch(stateUrl,{{cache:'no-store'}})).json())}}catch(e){{renderPresentation({{}})}}}}
setInterval(refresh,1500);setInterval(refreshPairing,1500);setInterval(refreshWorkspace,1500);setInterval(refreshPresentation,1500);setInterval(()=>document.getElementById('clock').textContent=new Date().toLocaleTimeString([],{{hour:'2-digit',minute:'2-digit'}}),1000);refresh();refreshPairing();refreshWorkspace();refreshPresentation();
</script></body></html>""".encode("utf-8")


def _education_html(token: str, action_token: str) -> bytes:
    safe_token = html.escape(token, quote=True)
    safe_action_token = html.escape(action_token, quote=True)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pilot Learning Centre · Spanish Learning Centre</title><style>
:root{{--ink:#09203b;--blue:#2368ff;--cyan:#41d7ff;--yellow:#ffd752;--green:#52dc91;--red:#ff7184;--white:#fff}}
*{{box-sizing:border-box}}html,body{{margin:0;width:100%;height:100%;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--ink)}}
body{{background:radial-gradient(circle at 85% 15%,#fff9c8 0,transparent 28%),radial-gradient(circle at 12% 88%,#baf3ff 0,transparent 32%),linear-gradient(140deg,#effbff,#fff4dd)}}
.app{{height:100vh;padding:4vh 5vw;display:grid;grid-template-rows:auto 1fr auto;gap:2.5vh}}header{{display:flex;justify-content:space-between;align-items:center}}.brand{{font-size:1.3vw;font-weight:900;letter-spacing:.16em;color:var(--blue)}}.learner{{display:flex;gap:1vw;align-items:center;font-size:1.25vw;font-weight:800}}.stat{{background:white;border-radius:99px;padding:.7vw 1.2vw;box-shadow:0 .5vw 2vw #20508018}}
main{{background:#ffffffdd;border:2px solid #ffffff;border-radius:2.2vw;padding:2vw 4vw;box-shadow:0 2vw 7vw #2c6ca825;display:grid;grid-template-rows:auto auto auto 1fr;min-height:0}}.category{{font-size:1.1vw;text-transform:uppercase;letter-spacing:.14em;color:var(--blue);font-weight:900}}#visual{{font-size:7vw;line-height:1;text-align:center;filter:drop-shadow(0 .6vw .7vw #214e7730);margin:.4vh 0;height:16vh}}#visual img{{height:100%;max-width:32vw;border-radius:1.2vw}}h1{{font-size:4vw;line-height:1;margin:.5vh 0;text-align:center}}#instruction{{font-size:1.55vw;text-align:center;color:#496681;min-height:2.2em}}#choices{{display:grid;grid-template-columns:repeat(3,1fr);gap:1.4vw;align-items:stretch;margin-top:1vh}}button{{font:inherit;border:3px solid transparent;border-radius:1.5vw;background:white;color:var(--ink);font-size:2vw;font-weight:850;padding:1.5vw;box-shadow:0 .7vw 2vw #234d7620;outline:none}}button:focus{{border-color:var(--blue);transform:scale(1.035);box-shadow:0 0 0 .45vw #2368ff22,0 1vw 3vw #234d7630}}button.correct{{background:#d9ffe9;border-color:var(--green)}}button.wrong{{background:#ffe1e6;border-color:var(--red)}}button.control{{font-size:1.25vw;padding:1vw 1.5vw}}footer{{display:flex;justify-content:space-between;align-items:center}}.controls{{display:flex;gap:1vw}}#feedback{{font-size:1.5vw;font-weight:850;color:var(--blue)}}.profile{{background:#eef4ff}}#next{{background:var(--green)}}
</style></head><body><div class="app"><header><div><div class="brand">TESSARIS · PILOT EDUCATION</div><div style="font-size:2.1vw;font-weight:900">Learning Centre</div></div><div class="learner"><span id="learner" class="stat">Explorer</span><span id="score" class="stat">✅ 0/50</span><span id="stars" class="stat">⭐ 0</span><span id="streak" class="stat">🔥 0</span></div></header>
<main><div id="category" class="category">Getting ready</div><div id="visual" role="img" aria-label="Learning picture">✨</div><h1 id="prompt">¡Vamos a aprender!</h1><div><div id="instruction">Use the LG remote arrows and press OK. <span id="input-status">Waiting for controller input…</span></div><div id="choices"></div></div></main>
<footer><div id="feedback">Choose the best answer. · Natural AI-generated learning voice</div><div class="controls"><button class="control profile" data-profile="explorer_a">Explorer A</button><button class="control profile" data-profile="explorer_b">Explorer B</button><button id="repeat" class="control">🔊 Hear AI voice again</button><button id="next" class="control">Next ▶</button></div></footer></div><audio id="lesson-voice" preload="auto"></audio>
<script>
window.addEventListener('DOMContentLoaded',()=>{{
  const choices=document.getElementById('choices'),visual=document.getElementById('visual'),voice=document.getElementById('lesson-voice');
  let pendingVoice=false,lastAutoAdvance='',autoAdvanceTimer=0;
  const playLessonVoice=()=>{{
    if(!lesson||!lesson.speak_nonce)return;
    voice.src=base+'/education/audio?nonce='+encodeURIComponent(lesson.speak_nonce);
    voice.play().then(()=>pendingVoice=false).catch(()=>pendingVoice=true);
  }};
  speak=(text,nonce)=>{{
    if(!text||nonce===lastNonce)return;
    lastNonce=nonce;
    playLessonVoice();
  }};
  const replace=choices.replaceChildren.bind(choices);
  choices.replaceChildren=(...nodes)=>{{
    const oldButtons=[...choices.querySelectorAll('button')];
    const focusedIndex=oldButtons.indexOf(document.activeElement);
    replace(...nodes);
    if(typeof lesson!=='undefined'&&lesson){{
      if(lesson.illustration_uri){{const image=document.createElement('img');image.src=lesson.illustration_uri;image.alt=lesson.visual_alt||'Original learning illustration';visual.replaceChildren(image)}}
      else visual.textContent=lesson.visual||'Learning activity';
    }}
    if(focusedIndex>=0)requestAnimationFrame(()=>{{
      const newButtons=[...choices.querySelectorAll('button')];
      const target=newButtons[Math.min(focusedIndex,newButtons.length-1)];
      if(target&&!target.disabled)target.focus();
    }});
  }};
  const baseRender=render;
  render=(education)=>{{
    baseRender(education);
    if(!lesson)return;
    const total=Number(lesson.lesson_total||50),correct=Number(lesson.correct_in_session||0);
    document.getElementById('score').textContent='✅ '+correct+'/'+total;
    document.getElementById('category').textContent=lesson.category+' · Question '+Math.min(lesson.round_number,total)+'/'+total;
    const buttons=[...choices.querySelectorAll('button')];
    if(lesson.phase==='feedback'){{
      visual.textContent=lesson.was_correct?'✅':'❌';
      document.getElementById('feedback').style.color=lesson.was_correct?'#16834a':'#c52f46';
      buttons.forEach((button,index)=>{{
        if(index===lesson.selected_index&&!lesson.was_correct)button.textContent='❌ '+button.textContent;
        if((lesson.choices||[])[index]&&lesson.choices[index].text===lesson.correct_text)button.textContent='✅ '+button.textContent;
      }});
      document.getElementById('next').style.display='none';
      const key=lesson.profile_id+':'+lesson.round_number+':'+lesson.speak_nonce;
      if(lastAutoAdvance!==key){{
        lastAutoAdvance=key;
        clearTimeout(autoAdvanceTimer);
        const advance=()=>act('next',{{expected_round:lesson.round_number}});
        autoAdvanceTimer=setTimeout(advance,9000);
        voice.onended=()=>{{if(lastAutoAdvance===key){{clearTimeout(autoAdvanceTimer);autoAdvanceTimer=setTimeout(advance,850)}}}};
      }}
    }}else{{
      voice.onended=null;
      visual.textContent=lesson.visual||'💬';
      document.getElementById('feedback').style.color='var(--blue)';
    }}
  }};
  document.addEventListener('keydown',()=>{{if(pendingVoice)playLessonVoice()}},true);
  document.addEventListener('pointerdown',()=>{{if(pendingVoice)playLessonVoice()}},true);
}});
</script>
<script>const base='/tv/{safe_token}',actionToken='{safe_action_token}';let lesson=null,lastNonce=-1,lastPhase='',lastGamepadAction=0,gamepadHeld='',inputStatus='Waiting for controller input…';async function act(command,args={{}}){{const r=await fetch(base+'/education/action',{{method:'POST',headers:{{'Content-Type':'application/x-www-form-urlencoded','X-AION-Education':actionToken}},body:new URLSearchParams({{command,arguments:JSON.stringify(args)}})}});const j=await r.json();if(!r.ok)throw new Error(j.error||'Action failed');render(j.education)}}function speak(text,nonce){{if(!text||nonce===lastNonce||!('speechSynthesis'in window))return;lastNonce=nonce;speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(text);u.lang='es-ES';u.rate=.8;speechSynthesis.speak(u)}}function render(education){{lesson=(education||{{}}).session||null;if(!lesson)return;const profile=((education.profiles||{{}})[lesson.profile_id]||{{}});document.getElementById('learner').textContent=lesson.display_name;document.getElementById('stars').textContent='⭐ '+(profile.stars||0);document.getElementById('streak').textContent='🔥 '+(profile.streak||0);document.getElementById('category').textContent=lesson.category+' · Round '+lesson.round_number;document.getElementById('prompt').textContent=lesson.prompt;document.getElementById('instruction').childNodes[0].nodeValue=(lesson.instruction||lesson.explanation||'')+'  ';document.getElementById('input-status').textContent=inputStatus;document.getElementById('feedback').textContent=lesson.feedback||'Choose the best answer.';const choices=document.getElementById('choices');choices.replaceChildren(...(lesson.choices||[]).map(choice=>{{const b=document.createElement('button');b.tabIndex=0;b.textContent=String.fromCharCode(65+choice.index)+'. '+choice.text;b.disabled=lesson.phase!=='question';if(lesson.phase==='feedback')b.className=choice.text===lesson.correct_text?'correct':choice.index===lesson.selected_index?'wrong':'';b.onclick=()=>act('answer',{{choice_index:choice.index}});return b}}));document.getElementById('next').style.display=lesson.phase==='feedback'?'block':'none';speak(lesson.speak_text,lesson.speak_nonce);if(lastPhase!==lesson.phase){{lastPhase=lesson.phase;setTimeout(()=>{{const target=lesson.phase==='feedback'?document.getElementById('next'):choices.querySelector('button:not([disabled])');if(target)target.focus()}},100)}}}}async function refresh(){{try{{const s=await(await fetch(base+'/state',{{cache:'no-store'}})).json();render(s.education||{{}})}}catch(e){{document.getElementById('feedback').textContent='Reconnecting to AION…'}}}}document.getElementById('repeat').onclick=()=>act('repeat');document.getElementById('next').onclick=()=>act('next');document.querySelectorAll('[data-profile]').forEach(b=>b.onclick=()=>act('start',{{profile_id:b.dataset.profile}}));function moveFocus(direction){{const focusable=[...document.querySelectorAll('button:not([disabled])')].filter(x=>getComputedStyle(x).display!=='none');if(!focusable.length)return;let i=focusable.indexOf(document.activeElement);if(i<0)i=direction>0?-1:0;i=(i+direction+focusable.length)%focusable.length;focusable[i].focus()}}function activateFocus(){{const active=document.activeElement;if(active&&active.tagName==='BUTTON'&&!active.disabled)active.click();else moveFocus(1)}}document.addEventListener('keydown',e=>{{const code=Number(e.keyCode||e.which||0),legacy={{37:'ArrowLeft',38:'ArrowUp',39:'ArrowRight',40:'ArrowDown',13:'Enter'}},key=e.key&&e.key!=='Unidentified'?e.key:legacy[code];inputStatus='TV remote connected';document.getElementById('input-status').textContent=inputStatus;if(key==='ArrowRight'||key==='ArrowDown'){{moveFocus(1);e.preventDefault()}}else if(key==='ArrowLeft'||key==='ArrowUp'){{moveFocus(-1);e.preventDefault()}}else if(key==='Enter'||key==='OK'){{activateFocus();e.preventDefault()}}}});function pollGamepads(time){{const pads=navigator.getGamepads?navigator.getGamepads():[];const p=[...pads].find(Boolean);let action='';if(p){{inputStatus='LG gamepad connected';document.getElementById('input-status').textContent=inputStatus;const b=p.buttons||[],a=p.axes||[];if((b[15]&&b[15].pressed)||(a[0]||0)>.55||(b[13]&&b[13].pressed)||(a[1]||0)>.55)action='next';else if((b[14]&&b[14].pressed)||(a[0]||0)<-.55||(b[12]&&b[12].pressed)||(a[1]||0)<-.55)action='previous';else if((b[0]&&b[0].pressed)||(b[9]&&b[9].pressed))action='select'}}if(action&&action!==gamepadHeld&&time-lastGamepadAction>220){{lastGamepadAction=time;if(action==='next')moveFocus(1);else if(action==='previous')moveFocus(-1);else activateFocus()}}gamepadHeld=action;requestAnimationFrame(pollGamepads)}}window.addEventListener('gamepadconnected',()=>{{inputStatus='LG gamepad connected';document.getElementById('input-status').textContent=inputStatus}});requestAnimationFrame(pollGamepads);setInterval(refresh,1400);refresh();</script></body></html>'''.encode("utf-8")


class TVCanvasService:
    """Token-protected, read-only LAN display surface for a television browser."""

    def __init__(
        self,
        state_provider: Callable[[], Dict[str, Any]],
        *,
        education_handler: Callable[[str, Dict[str, Any]], Dict[str, Any]] | None = None,
        private_workspace_provider: Callable[[str], Dict[str, Any]] | None = None,
        surface_manifest_provider: Callable[[], Dict[str, Any]] | None = None,
        presentation_provider: Callable[[], Dict[str, Any] | None] | None = None,
        preferred_peer: str | None = None,
        port: int = 8766,
        token: str | None = None,
        education_action_token: str | None = None,
    ) -> None:
        self.state_provider = state_provider
        self.education_handler = education_handler
        self.private_workspace_provider = private_workspace_provider
        self.surface_manifest_provider = surface_manifest_provider
        self.presentation_provider = presentation_provider
        self.address = _lan_address(preferred_peer)
        self.port = port
        self.token = token or secrets.token_urlsafe(24)
        self.education_action_token = education_action_token or secrets.token_urlsafe(24)
        self.god_view = GodViewData()
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._view = "home"
        self._last_transcript = ""
        self._last_response = ""
        self._latest_tv_volume: int | None = None
        self._god_control: Dict[str, Any] = {"sequence": 0, "command": "", "arguments": {}, "issued_at": 0.0}
        self._companion_url: str | None = None
        self._companion_code: str | None = None

    @property
    def public_url(self) -> str:
        port = self._server.server_port if self._server else self.port
        return f"http://{self.address}:{port}/tv/{self.token}"

    @property
    def education_url(self) -> str:
        return f"{self.public_url}/education"

    def set_view(self, view: str) -> None:
        if view not in {"home", "mesh", "tasks", "calendar", "boardroom", "files", "iot", "work", "briefing", "companion", "games", "god_view", "education", "entertainment", "research", "agent"}:
            raise ValueError("Unknown TV Canvas view")
        with self._lock:
            self._view = view

    def set_companion(self, url: str, code: str) -> None:
        with self._lock:
            self._companion_url = url
            self._companion_code = code

    def send_god_control(self, command: str, arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
        allowed = {"up", "down", "left", "right", "select", "back", "pilot", "earth", "nasa", "iss", "track_iss", "lapland", "home_region"}
        if command not in allowed:
            raise ValueError("Unknown God View controller command")
        with self._lock:
            self._god_control = {
                "sequence": int(self._god_control["sequence"]) + 1,
                "command": command,
                "arguments": dict(arguments or {}),
                "issued_at": time.time(),
            }
            return dict(self._god_control)

    def record_voice_result(self, transcript: str, result: Dict[str, Any]) -> None:
        receipt = result.get("receipt", {})
        after = receipt.get("after", {}) if isinstance(receipt, dict) else {}
        receipt_list = result.get("receipts", [])
        observed_volume = after.get("volume")
        for item in receipt_list if isinstance(receipt_list, list) else []:
            candidate = item.get("after", {}).get("volume") if isinstance(item, dict) else None
            if isinstance(candidate, int):
                observed_volume = candidate
        with self._lock:
            self._last_transcript = transcript
            self._last_response = str(result.get("spoken_response") or "")
            if isinstance(observed_volume, int):
                self._latest_tv_volume = observed_volume

    def snapshot(self) -> Dict[str, Any]:
        status = self.state_provider()
        visible = [
            node for node in status.get("nodes", [])
            if not node.get("profile", {}).get("metadata", {}).get("hidden_from_topology")
        ]
        tv = next(
            (node for node in visible if node.get("profile", {}).get("metadata", {}).get("webos_pairing") == "paired"),
            None,
        )
        with self._lock:
            view = self._view
            transcript = self._last_transcript
            response = self._last_response
            volume = self._latest_tv_volume
            companion_url = self._companion_url
            companion_code = self._companion_code
        if volume is None and tv:
            latest = tv.get("profile", {}).get("metadata", {}).get("webos_latest_state", {}).get("volume", {})
            raw_volume = latest.get("volume") if isinstance(latest, dict) else None
            if isinstance(raw_volume, int):
                volume = raw_volume
        ledger = status.get("ledger", {})
        autopilot = status.get("tv_autopilot", {})
        comdex = status.get("comdex_bridge", {})
        research = status.get("tv_research")
        active_identity = dict((status.get("private_identity") or {}).get("active_shared_identity") or {})
        outward_view = view
        if view in {"tasks", "calendar", "boardroom", "files", "iot", "work"} and not active_identity.get("persona_id"):
            outward_view = "home"
        private_workspace = None
        if active_identity.get("persona_id") and self.private_workspace_provider:
            private_workspace = self.private_workspace_provider(str(active_identity["persona_id"]))
        surface_manifest = self.surface_manifest_provider() if self.surface_manifest_provider else None
        presentation = self.presentation_provider() if self.presentation_provider else None
        if view == "entertainment":
            latest_entertainment = dict(status.get("entertainment", {}).get("latest") or {})
            research = {
                "query": latest_entertainment.get("request", "entertainment across services"),
                "answer": latest_entertainment.get("answer", "Current cross-service options"),
                "items": latest_entertainment.get("items", []),
            }
            outward_view = "research"
        return {
            "view": outward_view,
            "fabric_nodes": len(visible),
            "enrolled_nodes": sum(node.get("enrollment") == "enrolled" for node in visible),
            "verified_actions": int(ledger.get("webos_action_receipts", 0)),
            "audit_chain_valid": bool(status.get("audit_chain_valid")),
            "tv_name": tv.get("profile", {}).get("name") if tv else None,
            "tv_volume": volume,
            "last_transcript": transcript,
            "last_response": response,
            "autopilot_belief": autopilot.get("belief", {}),
            "active_plan": autopilot.get("active_plan"),
            "last_plan": autopilot.get("last_plan"),
            "boardroom_sessions": int(comdex.get("boardroom_sessions", 0)),
            "intelligence_modules_present": int(comdex.get("intelligence_modules_present", 0)),
            "research": research,
            "tv_agent": status.get("tv_agent", {}),
            "entertainment": status.get("entertainment", {}),
            "education": status.get("education", {}),
            "companion_url": companion_url,
            "companion_code": companion_code,
            "active_identity": active_identity or None,
            "workspace_summary": status.get("pilot_inbox_shared_summary") if active_identity else None,
            "private_workspace": private_workspace if active_identity else None,
            "surface_manifest": surface_manifest,
            "presentation": presentation,
        }

    def start(self) -> None:
        service = self

        class Handler(BaseHTTPRequestHandler):
            def _send(self, payload: bytes, content_type: str, status: int = 200, *, god_view: bool = False) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "no-store")
                policy = (
                    "default-src 'self'; style-src 'self' 'unsafe-inline' https://cesium.com; "
                    "script-src 'self' 'unsafe-inline' https://cesium.com; connect-src 'self' https://cesium.com https://tile.openstreetmap.org; "
                    "img-src 'self' data: blob: https://cesium.com https://tile.openstreetmap.org https://epic.gsfc.nasa.gov; "
                    "frame-src https://www.youtube-nocookie.com https://www.youtube.com; worker-src blob:"
                    if god_view
                    else "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'"
                )
                self.send_header("Content-Security-Policy", policy)
                self.send_header("Referrer-Policy", "strict-origin-when-cross-origin" if god_view else "no-referrer")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self) -> None:  # noqa: N802
                base = f"/tv/{service.token}"
                parsed = urlparse(self.path)
                query = parse_qs(parsed.query)
                if parsed.path.rstrip("/") == base:
                    self._send(_canvas_html(service.token), "text/html; charset=utf-8")
                elif parsed.path == f"{base}/god-view":
                    self._send(god_view_html(service.token), "text/html; charset=utf-8", god_view=True)
                elif parsed.path == f"{base}/god-view/earth.png":
                    asset = Path(__file__).with_name("assets") / "god-view-earth-v1.png"
                    self._send(asset.read_bytes(), "image/png", god_view=True)
                elif parsed.path == f"{base}/god-view/geocode":
                    try:
                        payload = service.god_view.geocode(str(query.get("query", [""])[0]))
                        self._send(json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8")
                    except (OSError, ValueError, json.JSONDecodeError) as exc:
                        self._send(json.dumps({"error": str(exc)}).encode("utf-8"), "application/json; charset=utf-8", 503)
                elif parsed.path == f"{base}/god-view/weather":
                    try:
                        payload = service.god_view.weather(query.get("lat", [""])[0], query.get("lon", [""])[0])
                        self._send(json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8")
                    except (OSError, ValueError, json.JSONDecodeError) as exc:
                        self._send(json.dumps({"error": str(exc)}).encode("utf-8"), "application/json; charset=utf-8", 503)
                elif parsed.path == f"{base}/god-view/flights":
                    try:
                        payload = service.god_view.flights(query.get("lat", [""])[0], query.get("lon", [""])[0])
                        self._send(json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8")
                    except (OSError, ValueError, json.JSONDecodeError) as exc:
                        self._send(json.dumps({"error": str(exc)}).encode("utf-8"), "application/json; charset=utf-8", 503)
                elif parsed.path == f"{base}/god-view/nasa-earth":
                    try:
                        payload = service.god_view.nasa_earth()
                        self._send(json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8")
                    except (OSError, ValueError, json.JSONDecodeError) as exc:
                        self._send(json.dumps({"error": str(exc)}).encode("utf-8"), "application/json; charset=utf-8", 503)
                elif parsed.path == f"{base}/god-view/nasa-earth/image.png":
                    try:
                        self._send(service.god_view.nasa_earth_image(), "image/png", god_view=True)
                    except (OSError, ValueError, json.JSONDecodeError) as exc:
                        self._send(str(exc).encode("utf-8"), "text/plain; charset=utf-8", 503)
                elif parsed.path.startswith(f"{base}/god-view/tile/"):
                    try:
                        parts = parsed.path.rsplit("/", 3)
                        zoom, tile_x, tile_y = parts[-3], parts[-2], parts[-1].removesuffix(".png")
                        self._send(service.god_view.map_tile(zoom, tile_x, tile_y), "image/png", god_view=True)
                    except (OSError, ValueError, json.JSONDecodeError) as exc:
                        self._send(str(exc).encode("utf-8"), "text/plain; charset=utf-8", 503)
                elif parsed.path == f"{base}/god-view/iss":
                    try:
                        payload = service.god_view.iss_position()
                        self._send(json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8")
                    except (OSError, ValueError, json.JSONDecodeError) as exc:
                        self._send(json.dumps({"error": str(exc)}).encode("utf-8"), "application/json; charset=utf-8", 503)
                elif parsed.path == f"{base}/god-view/control":
                    with service._lock:
                        payload = dict(service._god_control)
                    self._send(json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8")
                elif parsed.path == f"{base}/education":
                    self._send(_education_html(service.token, service.education_action_token), "text/html; charset=utf-8")
                elif parsed.path.startswith(f"{base}/education/audio"):
                    lesson = dict((service.snapshot().get("education") or {}).get("session") or {})
                    try:
                        audio = _local_spanish_speech(str(lesson.get("speak_text") or ""))
                    except (OSError, subprocess.SubprocessError):
                        audio = b""
                    media_type = "audio/mpeg" if audio.startswith((b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")) else "audio/wav"
                    self._send(audio or b"Speech unavailable", media_type if audio else "text/plain; charset=utf-8", 200 if audio else 503)
                elif parsed.path == f"{base}/pair.svg":
                    companion_url = service.snapshot().get("companion_url")
                    if companion_url:
                        self._send(_qr_svg(str(companion_url)), "image/svg+xml")
                    else:
                        self._send(b"Pairing unavailable", "text/plain; charset=utf-8", 404)
                elif parsed.path == f"{base}/state":
                    payload = json.dumps(service.snapshot(), ensure_ascii=False).encode("utf-8")
                    self._send(payload, "application/json; charset=utf-8")
                else:
                    self._send(b"Not found", "text/plain; charset=utf-8", 404)

            def do_POST(self) -> None:  # noqa: N802
                base = f"/tv/{service.token}"
                if self.path != f"{base}/education/action" or service.education_handler is None:
                    self._send(b"Read-only display", "text/plain; charset=utf-8", 405)
                    return
                try:
                    if not secrets.compare_digest(self.headers.get("X-AION-Education", ""), service.education_action_token):
                        raise PermissionError("Invalid learning-session request")
                    length = int(self.headers.get("Content-Length", "0"))
                    if length <= 0 or length > 2048:
                        raise ValueError("Invalid learning-session request")
                    form = parse_qs(self.rfile.read(length).decode("utf-8"), strict_parsing=True)
                    command = str(form.get("command", [""])[0])
                    arguments = json.loads(str(form.get("arguments", ["{}"])[0]))
                    if command not in {"start", "answer", "next", "repeat"} or not isinstance(arguments, dict):
                        raise ValueError("Unsupported learning-session action")
                    payload = json.dumps(service.education_handler(command, arguments), ensure_ascii=False).encode("utf-8")
                    self._send(payload, "application/json; charset=utf-8")
                except PermissionError as exc:
                    self._send(json.dumps({"error": str(exc)}).encode("utf-8"), "application/json; charset=utf-8", 403)
                except (ValueError, KeyError, json.JSONDecodeError) as exc:
                    self._send(json.dumps({"error": str(exc)}).encode("utf-8"), "application/json; charset=utf-8", 400)

            def log_message(self, format: str, *args: object) -> None:
                return

        self._server = ThreadingHTTPServer(("0.0.0.0", self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, name="aion-tv-canvas", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
        if self._thread:
            self._thread.join(timeout=3)
