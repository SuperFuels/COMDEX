import ctypes
import pytest
from backend.modules.aion_inference.gptoss_joined_projection import join_gate_up
from backend.modules.aion_inference.gptoss_expert_frame_store import ctypes_component_pointer_array


def test_original_bytes_and_adjacent_native_views():
    value={p:{'weight':bytes([i])*16,'bias':bytes([i+4])*4} for i,p in enumerate(('gate','up','down'))}
    packed=join_gate_up(value)
    refs,pointers=ctypes_component_pointer_array([packed[p]['weight'] for p in ('gate','up')])
    assert pointers[1]==pointers[0]+16
    for p in value:
        for k in value[p]:assert bytes(packed[p][k])==value[p][k]
    assert sum(len(b) for p in packed.values() for b in p.values())==sum(len(b) for p in value.values() for b in p.values())
    assert packed['gate']['weight'].obj is packed['up']['weight'].obj


def test_incompatible_matrices_rejected():
    with pytest.raises(ValueError):join_gate_up({'gate':{'weight':b'a'},'up':{'weight':b'bb'}})
