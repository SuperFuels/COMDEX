import numpy as np,torch
from backend.modules.hexcore.object_centric_action_chunk_policy import ObjectChunkPolicy,project_world,unproject_pixels,intersect_horizontal_plane
def test_projection_roundtrip():
 p=np.array([[.5,0,.055],[.45,.1,.3]],np.float32);uv,d=project_world(p);np.testing.assert_allclose(unproject_pixels(uv,d),p,atol=1e-5)
 np.testing.assert_allclose(intersect_horizontal_plane(uv[:1]),p[:1],atol=1e-5)
def test_chunk_and_spatial_shapes():
 m=ObjectChunkPolicy(chunk=12);o=m(torch.zeros(2,96,128,3,dtype=torch.uint8),torch.zeros(2,18),torch.zeros(2,2));assert o['uv'].shape==(2,2,2) and o['chunk'].shape==(2,12,8) and o['step'].shape==(2,8)
