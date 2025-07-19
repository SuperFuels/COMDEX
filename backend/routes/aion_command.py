from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import subprocess

from backend.modules.command_registry import resolve_command, list_commands
from backend.modules.consciousness.consciousness_manager import ConsciousnessManager as AIONEngine
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
from backend.utils.internal_client import get_client  # ✅ Delayed import-safe

# ✅ DNA Switch registration
DNA_SWITCH.register(__file__)

# ✅ Router and Memory
router = APIRouter()
memory = MemoryEngine()

# -------------------------
# 1. Smart Command Executor
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
        tokens_used = len(label) // 4
        memory.store({
            "label": f"command:{label}",
            "content": f"🛠️ Stub command '{label}' triggered (no real execution).\nEstimated tokens used: {tokens_used}",
            "tokens": tokens_used
        })
        return {"message": f"🛠️ This is a stubbed command: {label}", "stub": True}

    # ✅ Special handling: approve_dna --id=xyz --key=secret
    if route == "/api/aion/dna/approve":
        try:
            parts = raw_command.split("--")
            args = {k.strip(): v.strip() for k, v in (part.split("=") for part in parts[1:])}
            proposal_id = args.get("id")
            master_key = args.get("key")
            if not proposal_id or not master_key:
                raise ValueError("Missing required arguments")

            client = get_client()  # ✅ Safe delayed client
            response = client.post(route, json={
                "proposal_id": proposal_id,
                "master_key": master_key
            })

            result = response.json()
            result_str = str(result)
            tokens_used = (len(label) + len(result_str)) // 4

            memory.store({
                "label": f"command:{label}",
                "content": f"✅ DNA Approval command ran.\nResult: {result_str[:300]}\nEstimated tokens used: {tokens_used}",
                "tokens": tokens_used
            })
            return result
        except Exception as e:
            return {"error": f"Failed to run approval command: {str(e)}"}

    try:
        if method == "get":
            result = await AIONEngine.get(route)
        else:
            result = await AIONEngine.post(route)

        result_str = str(result)
        tokens_used = (len(label) + len(result_str)) // 4

        memory.store({
            "label": f"command:{label}",
            "content": f"✅ Command '{label}' executed successfully.\nResult: {result_str[:300]}\nEstimated tokens used: {tokens_used}",
            "tokens": tokens_used
        })

        return {"message": result, "label": label}

    except Exception as e:
        return {"error": f"Failed to run {label}: {str(e)}"}

# -------------------------
# 2. Static Shell Executor
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
        output = result.stdout.strip() or "✅ Shell command executed successfully."
        tokens_used = (len(cmd_key) + len(output)) // 4

        memory.store({
            "label": f"shell:{cmd_key}",
            "content": f"✅ Shell command '{cmd_key}' executed.\nOutput: {output[:300]}\nEstimated tokens used: {tokens_used}",
            "tokens": tokens_used
        })

        return {"output": output}
    except subprocess.CalledProcessError as e:
        return {"error": f"❌ Execution failed: {e.stderr.strip()}"}

# -------------------------
# 3. Command Registry Viewer
# -------------------------

@router.get("/api/aion/command/registry")
async def get_command_registry():
    return {"commands": list_commands()}