"""Object-centric visual geometry and phase-consistent action chunks."""
from __future__ import annotations
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

EYE=np.asarray([1.65,1.65,1.45],np.float32); TARGET=np.asarray([.45,0,.45],np.float32)
FOCAL_PX=24.0/20.955*128.0
FORWARD=(TARGET-EYE)/np.linalg.norm(TARGET-EYE); RIGHT=np.cross(FORWARD,[0,0,1]).astype(np.float32);RIGHT/=np.linalg.norm(RIGHT);UP=np.cross(RIGHT,FORWARD).astype(np.float32)

def project_world(points:np.ndarray):
    q=np.asarray(points,np.float32)-EYE; x=q@RIGHT;y=q@UP;depth=q@FORWARD
    return np.stack((64+FOCAL_PX*x/depth,48-FOCAL_PX*y/depth),-1),depth

def unproject_pixels(uv:np.ndarray,depth:np.ndarray):
    uv=np.asarray(uv,np.float32);depth=np.asarray(depth,np.float32)
    x=(uv[...,0]-64)*depth/FOCAL_PX;y=-(uv[...,1]-48)*depth/FOCAL_PX
    return EYE+depth[...,None]*FORWARD+x[...,None]*RIGHT+y[...,None]*UP

def intersect_horizontal_plane(uv:np.ndarray,z:float=.055):
    uv=np.asarray(uv,np.float32);x=(uv[...,0]-64)/FOCAL_PX;y=-(uv[...,1]-48)/FOCAL_PX
    direction=FORWARD+x[...,None]*RIGHT+y[...,None]*UP
    scale=(float(z)-EYE[2])/direction[...,2]
    return EYE+scale[...,None]*direction

class ObjectChunkPolicy(nn.Module):
    def __init__(self,proprio_dim=18,action_dim=8,chunk=16):
        super().__init__();self.chunk=chunk;self.action_dim=action_dim
        self.encoder=nn.Sequential(nn.Conv2d(3,32,5,2,2),nn.SiLU(),nn.Conv2d(32,64,3,2,1),nn.SiLU(),nn.Conv2d(64,96,3,1,1),nn.SiLU())
        self.heatmap=nn.Conv2d(96,2,1);self.pool=nn.Sequential(nn.AdaptiveAvgPool2d((4,4)),nn.Flatten(),nn.Linear(96*16,256),nn.SiLU())
        # Object/goal-attended slots, not only global averages, own geometry.
        self.depth=nn.Sequential(nn.Linear(256+2*96+4,256),nn.SiLU(),nn.Linear(256,2))
        self.trunk=nn.Sequential(nn.Linear(256+2*96+4+2+proprio_dim+2,512),nn.SiLU(),nn.Linear(512,384),nn.SiLU())
        self.chunk_head=nn.Linear(384,chunk*action_dim);self.step_head=nn.Linear(384,action_dim)
    def forward(self,rgb,proprio,phase):
        if rgb.shape[-1] in (3,4):rgb=rgb[...,:3].permute(0,3,1,2)
        rgb=rgb.float()/255 if rgb.dtype==torch.uint8 else rgb.float();rgb=F.interpolate(rgb,(96,128),mode="bilinear",align_corners=False)
        feature=self.encoder(rgb);logits=self.heatmap(feature);b,c,h,w=logits.shape
        probability=logits.reshape(b,c,-1).softmax(-1);yy,xx=torch.meshgrid(torch.linspace(0,95,h,device=rgb.device),torch.linspace(0,127,w,device=rgb.device),indexing="ij")
        uv=torch.stack(((probability*xx.flatten()).sum(-1),(probability*yy.flatten()).sum(-1)),-1)
        slots=torch.einsum('bcn,bdn->bcd',probability,feature.reshape(b,feature.shape[1],-1))
        pooled=self.pool(feature);uvn=uv/torch.tensor([127.,95.],device=uv.device)
        visual_state=torch.cat((pooled,slots.flatten(1),uvn.flatten(1)),-1);depth=self.depth(visual_state)
        state=self.trunk(torch.cat((visual_state,depth,proprio.float(),phase.float()),-1))
        return {"uv":uv,"depth":depth,"chunk":self.chunk_head(state).reshape(b,self.chunk,self.action_dim),"step":self.step_head(state),"heatmap":logits}
