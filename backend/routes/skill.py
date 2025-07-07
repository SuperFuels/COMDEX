from fastapi import APIRouter, Body
from backend.modules.skills.boot_loader import load_json, save_json
from backend.modules.skills.reflector import reflect_on_skill
import os

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

router = APIRouter()

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "../../modules/skills/aion_memory.json")

def get_next_skill():
    memory_data = load_json(MEMORY_FILE)
    for skill in memory_data:
        if skill.get("status") == "queued":
            skill["status"] = "in_progress"
            save_json(MEMORY_FILE, memory_data)
            return skill
    return None

@router.post("/aion/boot-skill")
def boot_next_skill():
    skill = get_next_skill()
    if not skill:
        return {"message": "No queued skills left."}
    return {"skill": skill}

@router.post("/aion/skill-reflect")
def reflect_skill(data: dict = Body(...)):
    title = data.get("title")
    success = data.get("success", True)
    notes = data.get("notes", "")
    result = reflect_on_skill(title, success, notes)
    if result:
        return {"status": "updated", "skill": result}
    return {"error": "Skill not found"}

@router.get("/aion/boot-skills")
def get_all_skills():
    memory_data = load_json(MEMORY_FILE)
    return {"skills": memory_data}