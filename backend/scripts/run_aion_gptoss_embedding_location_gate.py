"""Controlled SD/local embedding experiment using the unchanged inference gate."""
import argparse
import atexit
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import time
from backend.modules.aion_inference import expert_frame_gguf_reader as reader_module
from backend.modules.aion_inference.gguf_stream_index import read_gguf_stream_index
from backend.scripts.run_aion_gptoss_local_c4_prototype_gate import canonical, digest


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--embedding-manifest',type=Path,required=True)
    parser.add_argument('--embedding-location',choices=('sd','local'),required=True)
    args,remaining=parser.parse_known_args()
    metadata=json.loads(args.embedding_manifest.read_text());body=dict(metadata)
    if body.pop('canonical_sha256',None)!=canonical(body):
        raise RuntimeError('local embedding metadata hash mismatch')
    if metadata.get('schema')!='aion.local-embedding-table.v1':
        raise RuntimeError('unexpected embedding schema')
    tensor=metadata['tensor']; table=args.embedding_manifest.parent/'token-embedding.bin'
    if table.stat().st_size!=tensor['byte_length'] or digest(table)!=metadata['table_sha256']:
        raise RuntimeError('local embedding table size/hash mismatch')
    original=reader_module.ExpertFrameGGUFReader
    class LocationReader(original):
        def __init__(self,manifest_path,source_shard,cache_bytes=128*1024*1024):
            super().__init__(manifest_path,source_shard,cache_bytes)
            self.embedding_read_calls=0;self.embedding_read_seconds=0.;self.embedding_read_bytes=0
            self.embedding_handle=None
            if digest(manifest_path)!=metadata['warehouse_manifest_sha256']:
                raise RuntimeError('embedding table targets a different warehouse')
            self.embedding_source_matches=source_shard==metadata['source_shard']
            if self.embedding_source_matches:
                index=read_gguf_stream_index(self,self.size)
                expected=next(x for x in index['tensors'] if x['name']=='token_embd.weight')
                if any(expected[k]!=tensor[k] for k in tensor):
                    raise RuntimeError('embedding tensor address/type differs from warehouse')
                if args.embedding_location=='local':
                    self.embedding_handle=table.open('rb',buffering=0)
                    atexit.register(self.embedding_handle.close)
        def read_at(self,offset,length):
            start=tensor['absolute_offset']
            is_embedding=(self.embedding_source_matches and offset>=start and offset+length<=start+tensor['byte_length'])
            if not is_embedding:
                return super().read_at(offset,length)
            began=time.perf_counter()
            if self.embedding_handle is None:
                value=super().read_at(offset,length)
            else:
                value=os.pread(self.embedding_handle.fileno(),length,offset-start)
                if len(value)!=length: raise RuntimeError('short local embedding read')
            self.embedding_read_seconds+=time.perf_counter()-began
            self.embedding_read_calls+=1;self.embedding_read_bytes+=length
            return value
        def metrics(self):
            values=super().metrics()
            values.update(embedding_location=args.embedding_location,
                embedding_read_calls=self.embedding_read_calls,
                embedding_read_seconds=self.embedding_read_seconds,
                embedding_read_bytes=self.embedding_read_bytes,
                embedding_table_sha256=metadata['table_sha256'],
                embedding_manifest_sha256=digest(args.embedding_manifest))
            return values
    reader_module.ExpertFrameGGUFReader=LocationReader
    sys.argv=['run_aion_gptoss_first_token_gate',*remaining]
    runpy.run_module('backend.scripts.run_aion_gptoss_first_token_gate',run_name='__main__')

if __name__=='__main__':
    main()
