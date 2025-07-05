# backend/routes/aion_command.py
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import subprocess

router = APIRouter()

# Whitelist of allowed commands (safe Python scripts or operations)
ALLOWED_COMMANDS = {
    "run_learning_cycle": "python backend/scripts/aion_learning_cycle.py",
    "run_dream": "python backend/scripts/run_dream.py",
    "boot_skill": "python backend/scripts/boot_skill.py",
    "status_check": "python backend/scripts/status_report.py"
}

class CommandInput(BaseModel):
    command: str

@router.post("/api/aion/command")
async def run_aion_command(input: CommandInput, request: Request):
    cmd_key = input.command.strip()

    if cmd_key not in ALLOWED_COMMANDS:
        raise HTTPException(status_code=403, detail=f"❌ Command not allowed: {cmd_key}")

    cmd = ALLOWED_COMMANDS[cmd_key]
    try:
        result = subprocess.run(cmd, shell=True, check=True, text=True, capture_output=True)
        return {"output": result.stdout.strip() or "✅ Command executed successfully."}
    except subprocess.CalledProcessError as e:
        return {"error": f"❌ Execution failed: {e.stderr.strip()}"}
