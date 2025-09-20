from symatics.signature import Signature
from symatics.operators import OPS

# "Distance as signature" toy: measure equals canonical signature.
# Pretend σ_1m has frequency marker f1, σ_2m has f2, etc.
σ_1m = Signature(amplitude=1.0, frequency=1_000.0, phase=0.0, polarization="H", meta={"unit":"1m"})
σ_2m = Signature(amplitude=1.0, frequency=2_000.0, phase=0.0, polarization="H", meta={"unit":"2m"})

μ = OPS["μ"].impl

print("μ(σ_1m) =", μ(σ_1m))
print("μ(σ_2m) =", μ(σ_2m))