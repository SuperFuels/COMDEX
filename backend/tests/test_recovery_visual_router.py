import torch
from backend.modules.hexcore.recovery_visual_router import RGBObjectKeypoint

def test_rgb_keypoint_contract():
 model=RGBObjectKeypoint();out=model(torch.zeros(3,96,128,3,dtype=torch.uint8));assert out.shape==(3,2);assert torch.isfinite(out).all();assert (out>=0).all();assert (out[:,0]<=127).all();assert (out[:,1]<=95).all()
