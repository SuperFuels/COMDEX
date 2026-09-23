"""Pack original gate/up matrices adjacently without changing their bytes."""
import hashlib


def join_gate_up(value):
    gate=value['gate']['weight'];up=value['up']['weight']
    if len(gate)!=len(up) or not gate:
        raise ValueError('gate and up must have equal nonzero packed lengths')
    joined=bytearray(gate);joined.extend(up)
    view=memoryview(joined)
    result={projection:dict(parts) for projection,parts in value.items()}
    result['gate']['weight']=view[:len(gate)]
    result['up']['weight']=view[len(gate):]
    # Verify repacking once on admission; inference reads these bytes unchanged.
    for projection in ('gate','up'):
        if hashlib.sha256(result[projection]['weight']).digest()!=hashlib.sha256(value[projection]['weight']).digest():
            raise RuntimeError('joined projection bytes changed')
    return result
