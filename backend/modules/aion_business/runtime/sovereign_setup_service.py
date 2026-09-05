from __future__ import annotations

import argparse
import json
import os
import platform
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict

from backend.modules.aion_business.runtime.sovereign_brain_setup import (
    SovereignBrainSetup,
    public_setup_choices,
)


def default_brain_root() -> Path:
    configured = os.environ.get("TESSARIS_PILOT_BRAIN_ROOT")
    if configured:
        return Path(configured).expanduser()
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Pilot Brain"
    if system == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
        return base / "Tessaris" / "Pilot Brain"
    base = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    return base / "tessaris" / "pilot-brain"


def _setup_html() -> bytes:
    return b"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Set up Pilot</title><style>
:root{--ink:#17213a;--muted:#68758b;--blue:#1769e8;--line:#dde5ef;--green:#13885f}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 50% -15%,#e7f1ff,#f7f9fc 42%,#fff);color:var(--ink);font:16px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}main{max-width:850px;margin:auto;padding:48px 22px 80px}.mark{display:grid;place-items:center;width:64px;height:64px;border-radius:21px;background:linear-gradient(145deg,#071a35,#1557d6 58%,#29a9ff);color:#fff;font-size:28px}h1{font-size:44px;letter-spacing:-.045em;margin:22px 0 8px}p{color:var(--muted);line-height:1.55}.card{margin-top:30px;padding:28px;background:#fff;border:1px solid var(--line);border-radius:26px;box-shadow:0 18px 50px #233b6012}.field{margin:0 0 20px}label{display:block;font-size:13px;font-weight:800;margin-bottom:8px}input,select{width:100%;padding:14px 15px;border:1px solid #cfd9e7;border-radius:13px;background:#fff;color:var(--ink);font:inherit}button{width:100%;padding:15px 18px;border:0;border-radius:14px;background:linear-gradient(135deg,#1769e8,#624fe8);color:#fff;font:inherit;font-weight:800;cursor:pointer}.promise{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:24px 0}.promise div{padding:14px;border-radius:15px;background:#f2f6fc;color:#526078;font-size:13px}.result{margin-top:18px;padding:16px;border-radius:14px;background:#f3f7fc;color:#53627a;white-space:pre-wrap}.result.good{background:#ebfaf3;color:var(--green)}@media(max-width:620px){h1{font-size:36px}.promise{grid-template-columns:1fr}}
</style></head><body><main><div class="mark">&#9992;</div><h1>Make this Pilot yours.</h1><p>This creates an empty customer-owned AION brain. It starts locally, contains no demo identity or business data and does not require an AI-provider key.</p><div class="promise"><div>Your data stays under your control.</div><div>Models can be changed later.</div><div>Cloud compute remains optional.</div></div><section class="card"><form id="setup"><div class="field"><label for="name">Your name</label><input id="name" maxlength="100" autocomplete="name" required placeholder="Name shown on your private Pilot"></div><div class="field"><label for="deployment">Where will Pilot live?</label><select id="deployment"><option value="personal_computer">This computer</option><option value="home_server">A home server</option><option value="private_vps">My private cloud server</option><option value="business">A business-controlled server</option></select></div><div class="field"><label for="compute">Where should additional intelligence run?</label><select id="compute"><option value="local">Locally on this computer</option><option value="customer_server">On my private server</option><option value="customer_cloud">In my cloud account</option><option value="external_api_optional">Through optional providers I connect</option></select></div><h2>What does your organisation need?</h2><p>Pilot recommends tools from your requirements. It does not label the business small, medium or large.</p><div class="field"><label for="entities">Legal entities</label><input id="entities" type="number" min="1" max="1000" value="1"></div><div class="field"><label for="locations">Locations</label><input id="locations" type="number" min="1" max="10000" value="1"></div><div class="field"><label for="users">People who will use Pilot</label><input id="users" type="number" min="1" max="1000000" value="1"></div><div class="field"><label><input id="projects" type="checkbox" style="width:auto"> We manage projects, teams and budgets</label><label><input id="approvals" type="checkbox" style="width:auto"> We need delegated approvals or separation of duties</label><label><input id="identity" type="checkbox" style="width:auto"> We use business single sign-on</label><label><input id="regulated" type="checkbox" style="width:auto"> We have regulated or residency-controlled data</label></div><button type="submit">Create my Pilot brain</button></form><div id="result" class="result">Pilot will profile only coarse processing, memory and storage capacity. No device serial number is collected.</div></section></main><script>
const form=document.getElementById('setup'),result=document.getElementById('result');form.addEventListener('submit',async event=>{event.preventDefault();const button=form.querySelector('button');button.disabled=true;result.className='result';result.textContent='Creating your encrypted local brain...';try{const requirements={legal_entities:Number(document.getElementById('entities').value),locations:Number(document.getElementById('locations').value),users:Number(document.getElementById('users').value),project_budgeting:document.getElementById('projects').checked,separation_of_duties:document.getElementById('approvals').checked,approval_levels:document.getElementById('approvals').checked?1:0,enterprise_identity:document.getElementById('identity').checked,regulated_data:document.getElementById('regulated').checked,private_compute:document.getElementById('compute').value==='customer_server'||document.getElementById('compute').value==='customer_cloud'};const response=await fetch('/api/setup',{method:'POST',headers:{'Content-Type':'application/json','X-AION-Setup':'local-wizard-v1'},body:JSON.stringify({owner_display_name:document.getElementById('name').value,deployment_profile:document.getElementById('deployment').value,customer_compute:document.getElementById('compute').value,business_requirements:requirements})});const body=await response.json();if(!response.ok)throw new Error(body.error||'Setup failed');result.className='result good';result.textContent=`Pilot is ready.\n\nBrain: ${body.brain_id}\nDeployment: ${body.deployment_profile}\nLocal model plan: ${body.model_plan.tier}\nRecommended tools: ${body.business_requirements.recommended_modules.join(', ')}\nBusiness map: ${body.boardroom_business_map.source_of_truth}\n\nNo provider key was required.`}catch(error){result.textContent=error.message}finally{button.disabled=false}});
</script></body></html>"""


def build_handler(root: str | Path):
    setup = SovereignBrainSetup(root)

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, content_type: str, payload: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/":
                self._send(200, "text/html; charset=utf-8", _setup_html())
                return
            if self.path == "/api/status":
                payload = json.dumps(setup.status(), ensure_ascii=False).encode("utf-8")
                self._send(200, "application/json; charset=utf-8", payload)
                return
            if self.path == "/api/choices":
                payload = json.dumps(public_setup_choices(), ensure_ascii=False).encode("utf-8")
                self._send(200, "application/json; charset=utf-8", payload)
                return
            self.send_error(404)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/api/setup":
                self.send_error(404)
                return
            if self.headers.get("X-AION-Setup") != "local-wizard-v1":
                self._send(403, "application/json; charset=utf-8", b'{"error":"Local setup marker missing"}')
                return
            try:
                size = int(self.headers.get("Content-Length") or "0")
            except ValueError:
                size = 0
            if size < 2 or size > 8192:
                self._send(413, "application/json; charset=utf-8", b'{"error":"Setup request is invalid"}')
                return
            try:
                data: Dict[str, Any] = json.loads(self.rfile.read(size))
                result = setup.initialize(
                    owner_display_name=str(data.get("owner_display_name") or ""),
                    deployment_profile=str(data.get("deployment_profile") or "personal_computer"),
                    customer_compute=str(data.get("customer_compute") or "local"),
                    business_requirements=dict(data.get("business_requirements") or {}),
                )
                payload = json.dumps(result, ensure_ascii=False).encode("utf-8")
                self._send(200, "application/json; charset=utf-8", payload)
            except (ValueError, PermissionError) as exc:
                payload = json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8")
                self._send(400, "application/json; charset=utf-8", payload)
            except Exception:
                self._send(500, "application/json; charset=utf-8", b'{"error":"Pilot setup could not be completed"}')

        def log_message(self, *_: Any) -> None:
            return

    return Handler


def serve(*, root: str | Path, host: str = "127.0.0.1", port: int = 8775, open_browser: bool = True) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("First-run setup must remain bound to this computer")
    server = ThreadingHTTPServer((host, port), build_handler(root))
    if open_browser:
        webbrowser.open(f"http://127.0.0.1:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pilot-brain-setup", description="Local Pilot first-run setup")
    parser.add_argument("--root", type=Path, default=default_brain_root())
    parser.add_argument("--port", type=int, default=8775)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    serve(root=args.root, port=args.port, open_browser=not args.no_browser)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
