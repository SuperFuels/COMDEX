"""RGB-only object keypoint and nominal/recovery routing components."""
from __future__ import annotations
import torch
from torch import nn
from torch.nn import functional as F

class RGBObjectKeypoint(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder=nn.Sequential(
            nn.Conv2d(3,24,5,2,2),nn.GroupNorm(6,24),nn.SiLU(),
            nn.Conv2d(24,48,3,2,1),nn.GroupNorm(8,48),nn.SiLU(),
            nn.Conv2d(48,72,3,2,1),nn.GroupNorm(8,72),nn.SiLU(),
            nn.Conv2d(72,96,3,2,1),nn.GroupNorm(8,96),nn.SiLU(),nn.Flatten())
        self.head=nn.Sequential(nn.Linear(96*48,256),nn.SiLU(),nn.Linear(256,96),nn.SiLU(),nn.Linear(96,2))
    def forward(self,rgb):
        if rgb.shape[-1] in (3,4):rgb=rgb[...,:3].permute(0,3,1,2)
        rgb=rgb.float()/255.0 if rgb.dtype==torch.uint8 else rgb.float()
        rgb=F.interpolate(rgb,(96,128),mode='bilinear',align_corners=False)
        return torch.sigmoid(self.head(self.encoder(rgb)))*torch.tensor([127.,95.],device=rgb.device)
