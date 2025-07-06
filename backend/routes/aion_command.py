from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import subprocess
from backend.modules.command_registry import resolve_command
from backend.modules.aion_core import AIONEngine  # your internal AION engine interface

router = APIRouter()

# -------------------------
# 1. Fuzzy Smart Command
# -------------------------

class CommandInput(BaseModel):
    command: str

@router.post("/api/aion/command")
async def execute_command(request: Request):
    body = await request.json()
    raw_command = body.get("command", "").strip()

    if not raw_command:
        return {"error": "No command provided."}

    command_info = resolve_command(raw_command)

    if not command_info:
        return {"error": f"Unknown command: {raw_command}"}

    route = command_info.get("route")
    method = command_info.get("method", "post")
    label = command_info.get("label", route)
    stub = command_info.get("stub", False)

    if stub:
        return {"message": f"🛠️ This is a stubbed command: {label}", "stub": True}

    try:
        if method == "get":
            result = await AIONEngine.get(route)
        else:
            result = await AIONEngine.post(route)
        return {"message": result, "label": label}
    except Exception as e:
        return {"error": f"Failed to run {label}: {str(e)}"}

# -------------------------
# 2. Static Shell Fallback
# -------------------------

ALLOWED_COMMANDS = {
    "run_learning_cycle": "python backend/scripts/aion_learning_cycle.py",
    "run_dream": "python backend/scripts/run_dream.py",
    "boot_skill": "python backend/scripts/boot_skill.py",
    "status_check": "python backend/scripts/status_report.py"
}

@router.post("/api/aion/shell-command")
async def run_static_shell(input: CommandInput):
    cmd_key = input.command.strip()

    if cmd_key not in ALLOWED_COMMANDS:
        raise HTTPException(status_code=403, detail=f"❌ Command not allowed: {cmd_key}")

    cmd = ALLOWED_COMMANDS[cmd_key]
    try:
        result = subprocess.run(cmd, shell=True, check=True, text=True, capture_output=True)
        return {"output": result.stdout.strip() or "✅ Shell command executed successfully."}
    except subprocess.CalledProcessError as e:
        return {"error": f"❌ Execution failed: {e.stderr.strip()}"}