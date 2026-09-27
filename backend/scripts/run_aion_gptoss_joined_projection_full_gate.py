"""Run the existing inference gate with controlled original/joined projections."""
import argparse,ctypes,hashlib,runpy,sys
from pathlib import Path
from backend.modules.aion_inference import gptoss_expert_frame_store as stores
from backend.modules.aion_inference.gptoss_joined_projection import join_gate_up
from backend.scripts.run_aion_gptoss_local_c4_prototype_gate import digest


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--projection-kernel',choices=('original','joined'),required=True)
    parser.add_argument('--joined-library',type=Path,required=True)
    args,rest=parser.parse_known_args()
    library_hash=digest(args.joined_library)
    original_load=stores.GptOssExpertFrameStore._load_value
    original_metrics=stores.GptOssExpertFrameStore.metrics
    def load(self,layer,expert):return join_gate_up(original_load(self,layer,expert))
    def metrics(self):
        result=original_metrics(self)
        result.update(projection_kernel=args.projection_kernel,gate_up_packed_adjacent=True,joined_library_sha256=library_hash)
        return result
    stores.GptOssExpertFrameStore._load_value=load
    stores.GptOssExpertFrameStore.metrics=metrics
    if args.projection_kernel=='joined':
        original_cdll=ctypes.CDLL
        candidate=original_cdll(str(args.joined_library))
        def cdll(name,*a,**k):
            result=original_cdll(name,*a,**k)
            if Path(str(name)).name=='libaion-gptoss-moe.dylib':
                result.aion_gptoss_moe_finish=candidate.aion_gptoss_moe_finish_joined
                result.aion_gptoss_moe_finish_active=candidate.aion_gptoss_moe_finish_joined_active
                result._joined_kernel_library=candidate
            return result
        ctypes.CDLL=cdll
    sys.argv=['run_aion_gptoss_first_token_gate',*rest]
    runpy.run_module('backend.scripts.run_aion_gptoss_first_token_gate',run_name='__main__')

if __name__=='__main__':main()
