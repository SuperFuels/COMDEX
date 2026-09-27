import hashlib
import json
import sys
from pathlib import Path
import pytest
from backend.scripts import run_aion_gptoss_embedding_location_gate as probe


def fixture_table(tmp_path):
    warehouse=tmp_path/'warehouse.json';warehouse.write_text('{}')
    tensor=dict(name='token_embd.weight',absolute_offset=8,byte_length=16,ggml_type=0,dimensions=[4,4])
    table=bytes(range(16));(tmp_path/'token-embedding.bin').write_bytes(table)
    metadata=dict(schema='aion.local-embedding-table.v1',tensor=tensor,source_shard='source',
        warehouse_manifest_sha256=probe.digest(warehouse),table_sha256=hashlib.sha256(table).hexdigest())
    metadata['canonical_sha256']=probe.canonical(metadata)
    path=tmp_path/'embedding.json';path.write_text(json.dumps(metadata))
    return warehouse,path,tensor,table


@pytest.mark.parametrize('location',['sd','local'])
def test_row_offset_and_nonembedding_fallback(tmp_path,monkeypatch,location):
    warehouse,path,tensor,table=fixture_table(tmp_path)
    calls=[]
    class FakeReader:
        def __init__(self,*args): self.size=32
        def read_at(self,offset,length):
            calls.append((offset,length))
            return (b'abcdefgh'+table+b'ABCDEFGH')[offset:offset+length]
        def metrics(self): return {}
    monkeypatch.setattr(probe.reader_module,'ExpertFrameGGUFReader',FakeReader)
    monkeypatch.setattr(probe,'read_gguf_stream_index',lambda *args:dict(tensors=[tensor]))
    def run(*args,**kwargs):
        reader=probe.reader_module.ExpertFrameGGUFReader(warehouse,'source')
        assert reader.read_at(10,4)==table[2:6]
        assert reader.read_at(0,4)==b'abcd'
        assert reader.metrics()['embedding_read_calls']==1
        assert reader.metrics()['embedding_read_bytes']==4
        if reader.embedding_handle: reader.embedding_handle.close()
    monkeypatch.setattr(probe.runpy,'run_module',run)
    monkeypatch.setattr(sys,'argv',['probe','--embedding-manifest',str(path),'--embedding-location',location])
    probe.main()
    assert calls==([(10,4),(0,4)] if location=='sd' else [(0,4)])


def test_modified_table_rejected_before_inference(tmp_path,monkeypatch):
    _,path,_,_=fixture_table(tmp_path)
    (tmp_path/'token-embedding.bin').write_bytes(b'x'*16)
    monkeypatch.setattr(sys,'argv',['probe','--embedding-manifest',str(path),'--embedding-location','local'])
    monkeypatch.setattr(probe.runpy,'run_module',lambda *a,**k:pytest.fail('must not execute inference'))
    with pytest.raises(RuntimeError,match='size/hash mismatch'):probe.main()
