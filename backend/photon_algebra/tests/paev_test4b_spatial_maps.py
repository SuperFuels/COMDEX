# backend/photon_algebra/tests/paev_test4b_spatial_maps.py
import os, numpy as np, matplotlib.pyplot as plt
os.makedirs("docs/theory/figures", exist_ok=True)

N=256
x=y=np.linspace(-np.pi,np.pi,N); X,Y=np.meshgrid(x,y)
rng = np.random.default_rng(7)

phi = 10*X
A = 0.5+0.5*np.cos(phi)
# decoupled
B0 = 0.5+0.5*np.cos(10*X+ rng.normal(0,0.2))
# resonant (partial lock)
B1 = 0.5+0.5*np.cos( (1-0.6)*10*X + 0.6*phi + 0.4 )
# entangled (shared phase noise)
shared = rng.normal(0,0.1,size=X.shape)
B2 = 0.5+0.5*np.cos(phi+shared+0.2)

fig,axs=plt.subplots(2,3,figsize=(9,6))
for ax,img,title in [
    (axs[0,0],A,"A"),
    (axs[0,1],B0,"B decoupled"),
    (axs[0,2],B1,"B resonant"),
    (axs[1,0],B2,"B entangled"),
    (axs[1,1],(A-B0)**2,"Δ2 decoupled"),
    (axs[1,2],(A-B2)**2,"Δ2 entangled"),
]:
    im=ax.imshow(img,origin="lower"); ax.set_title(title); ax.axis("off")
fig.tight_layout(); plt.savefig("docs/theory/figures/PAEV_Test4B_Maps.png",dpi=300)
print("✅ Saved docs/theory/figures/PAEV_Test4B_Maps.png")