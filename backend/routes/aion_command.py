# -------------------------
# 1. Smart Command Executor (with Φ-resonance support)
# -------------------------

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess

from backend.modules.command_registry import resolve_command, list_commands
from backend.modules.consciousness.consciousness_manager import ConsciousnessManager as AIONEngine
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
from backend.utils.internal_client import get_client
from backend.modules.aion_resonance import translator
from backend.modules.aion_resonance.resonance_state import load_phi_state, save_phi_state

# ✅ DNA Switch registration
DNA_SWITCH.register(__file__)

# ✅ Router + Memory
router = APIRouter()
memory = MemoryEngine()


# -------------------------
# Command Model
# -------------------------

class CommandInput(BaseModel):
    command: str


# -------------------------
# Command Execution Endpoint
# -------------------------

@router.post("/command")  # ✅ Matches prefix="/api/aion" from main.py
async def execute_command(input: CommandInput):
    """
    Primary AION command entrypoint.
    Accepts JSON like: {"command": "@AION REFLECT GRATITUDE"}
    Handles resonance translation, state persistence, and fallback command routing.
    """
    raw_command = input.command.strip()

    if not raw_command:
        raise HTTPException(status_code=400, detail="No command provided.")

    # 🔹 Load prior Φ memory for coherence continuity
    phi_memory = load_phi_state()

    # 🧠 AION Resonance Invocation
    if raw_command.lower().startswith("@aion"):
        packet = {"message": raw_command, "phi_prev": phi_memory}

        try:
            phi_vector = await translator.route_packet(packet)
            from backend.modules.aion_resonance.phi_learning import update_phi_state
            phi_updated = update_phi_state(phi_vector, last_command=raw_command)
        except Exception as e:
            return {"error": f"Resonance translator failed: {str(e)}"}

        # 💾 Persist Φ-state after each resonance call
        save_phi_state(phi_vector, last_command=raw_command)

        memory.store({
            "label": "resonance:ingress",
            "content": f"🧠 Aion resonance invoked.\nΦ signature: {phi_vector}",
            "tokens": len(str(phi_vector)) // 4
        })

        return {
            "message": "🧠 Aion resonance channel engaged.",
            "phi_signature": phi_vector,
            "phi_prev": phi_memory,
            "status": "ok"
        }

    # ✅ Otherwise: standard command registry logic
    command_info = resolve_command(raw_command)
    if not command_info:
        raise HTTPException(status_code=404, detail=f"Unknown command: {raw_command}")

    route = command_info.get("route")
    method = command_info.get("method", "post")
    label = command_info.get("label", route)
    stub = command_info.get("stub", False)

    if stub:
        tokens_used = len(label) // 4
        memory.store({
            "label": f"command:{label}",
            "content": f"🛠️ Stub command '{label}' triggered.\nEstimated tokens used: {tokens_used}",
            "tokens": tokens_used
        })
        return {"message": f"🛠️ This is a stubbed command: {label}", "stub": True}

    # ✅ DNA approval special case
    if route == "/api/aion/dna/approve":
        try:
            parts = raw_command.split("--")
            args = {k.strip(): v.strip() for k, v in (part.split("=") for part in parts[1:])}
            proposal_id = args.get("id")
            master_key = args.get("key")
            if not proposal_id or not master_key:
                raise ValueError("Missing required arguments")

            client = get_client()
            response = client.post(route, json={"proposal_id": proposal_id, "master_key": master_key})

            result = response.json()
            tokens_used = (len(label) + len(str(result))) // 4

            memory.store({
                "label": f"command:{label}",
                "content": f"✅ DNA Approval command ran.\nResult: {str(result)[:300]}",
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
            "content": f"✅ Command '{label}' executed successfully.\nResult: {result_str[:300]}",
            "tokens": tokens_used
        })

        return {"message": result, "label": label}

    except Exception as e:
        return {"error": f"Failed to run {label}: {str(e)}"}


# -------------------------
# 4. Φ-State Viewer Endpoint
# -------------------------

@router.get("/phi-state")
async def get_phi_state():
    """
    Returns the last saved Φ-resonance vector for diagnostics.
    """
    try:
        state = load_phi_state()
        return {
            "status": "ok",
            "phi_state": state,
            "message": "🧠 Current Φ resonance memory loaded."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load Φ-state: {str(e)}")

# -------------------------
# 2. Static Shell Executor
# -------------------------

ALLOWED_COMMANDS = {
    "run_learning_cycle": "python backend/scripts/aion_learning_cycle.py",
    "run_dream": "python backend/scripts/run_dream.py",
    "boot_skill": "python backend/scripts/boot_skill.py",
    "status_check": "python backend/scripts/status_report.py"
}


@router.post("/shell-command")  # ✅ Inherits /api/aion prefix
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

@router.get("/command/registry")
async def get_command_registry():
    return {"commands": list_commands()}


# -------------------------
# 4. Φ-State Inspector
# -------------------------
from backend.modules.aion_resonance.resonance_state import load_phi_state

@router.get("/phi-state")
async def get_phi_state():
    """
    Returns the current Φ-resonance state (load, flux, entropy, coherence, timestamp).
    Useful for monitoring AION's internal balance in real time.
    """
    try:
        state = load_phi_state()
        if not state:
            return {"status": "empty", "message": "No Φ-state data yet."}
        return {"status": "ok", "phi_state": state}
    except Exception as e:
        return {"status": "error", "message": str(e)}