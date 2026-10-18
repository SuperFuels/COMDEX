import json
import struct
from pathlib import Path


RENDERER = Path("desktop/mac/src/lib/desktop-boardroom-renderer.js").read_text(encoding="utf-8")
ROBOT_ASSETS = (
    Path("desktop/mac/src/assets/boardroom/robot_agent.glb"),
    Path("desktop/mac/assets/boardroom/robot_agent.glb"),
    Path("desktop/mac/public/assets/boardroom/robot_agent.glb"),
)


def _glb_json(path: Path) -> dict:
    payload = path.read_bytes()
    magic, version, total_length = struct.unpack_from("<4sII", payload, 0)
    assert magic == b"glTF"
    assert version == 2
    assert total_length == len(payload)
    json_length, json_type = struct.unpack_from("<I4s", payload, 12)
    assert json_type == b"JSON"
    return json.loads(payload[20 : 20 + json_length].decode("utf-8").rstrip(" \0"))


def test_shared_synthetic_seat_mask_rig_exists():
    assert "O19C SYNTHETIC SEAT IDENTITY MASK LOCK" in RENDERER
    assert "function addAionSyntheticSeatIdentityMask" in RENDERER
    assert "aion_synthetic_identity_mask_" in RENDERER
    assert "aion_synthetic_face_eye_" in RENDERER
    assert "aion_synthetic_voice_bar_" in RENDERER
    assert "function applyAionBlackHeadToRobotGeometry" not in RENDERER
    assert "function buildAionRobotVisorColourTemplate" not in RENDERER


def test_real_visor_is_a_dedicated_source_material_in_every_desktop_asset():
    helper_start = RENDERER.index("function addAionSyntheticSeatIdentityMask")
    helper_end = RENDERER.index("END AION O19C", helper_start)
    helper = RENDERER[helper_start:helper_end]
    assert "SphereGeometry(0.225" not in helper
    assert "aion_synthetic_mask_shell_" not in helper
    assert "applyAionBlackHeadToRobotGeometry" not in RENDERER

    for path in ROBOT_ASSETS:
        document = _glb_json(path)
        material_names = [material.get("name") for material in document["materials"]]
        assert "aion_black_visor" in material_names
        primitives = document["meshes"][0]["primitives"]
        assert len(primitives) == 2
        assert primitives[0]["material"] != primitives[1]["material"]
        index_counts = [document["accessors"][primitive["indices"]]["count"] for primitive in primitives]
        assert sum(index_counts) == 360000
        assert min(index_counts) == 12348


def test_mask_is_added_to_executive_and_board_agents():
    executive = RENDERER.index("function addForcedVisibleExecutiveSeats")
    board = RENDERER.index("function addForcedVisibleBoardTeamSeats")
    executive_block = RENDERER[executive:board]
    board_block = RENDERER[board:RENDERER.index("function seatArc", board)]

    assert "addAionSyntheticSeatIdentityMask(group" in executive_block
    assert "accent: 0xf2af0d" in executive_block
    assert 'y: key === "operations" ? 1.4 : 1.225' in executive_block
    assert "z: 0.11" in executive_block
    assert "addAionSyntheticSeatIdentityMask(group" in board_block
    assert "accent," in board_block
    assert 'y: key === "aion" ? 1.475 : 1.275' in board_block


def test_synthetic_faces_blink_and_voice_bars_move():
    assert "current.syntheticFaceRigs = []" in RENDERER
    assert "const blinkPhase" in RENDERER
    assert "face.userData.voiceBars" in RENDERER
    assert "bar.scale.y" in RENDERER
