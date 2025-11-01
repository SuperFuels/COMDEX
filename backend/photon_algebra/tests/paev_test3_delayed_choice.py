#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Photon Algebra Evaluation (PAEV)
Test 3π - Delayed-Choice Visibility Collapse
--------------------------------------------
Demonstrates that tightening π (reducing spatial bandwidth)
after interference formation reduces measurable visibility.
"""

import numpy as np
from backend.photon_algebra.utils.visibility import project_with_pi, compute_visibility

# ---------------------------------------------------------------------
# Generate fine interference pattern
# ---------------------------------------------------------------------
H = W = 512
x = np.linspace(-10e-3, 10e-3, W)
X = np.tile(x, (H, 1))

# Fine fringes -> sensitive to π-spatial blurring
raw = np.array([
    0.5 + 0.5 * np.cos(2 * np.pi * 96 * X + t * 0.4)  # 96 fringes
    for t in range(8)
])

# ---------------------------------------------------------------------
# Apply π before and after "delayed choice"
# ---------------------------------------------------------------------
I_before = project_with_pi(raw, pi_spatial=1,  pi_temporal=1)   # full coherence
I_after  = project_with_pi(raw, pi_spatial=16, pi_temporal=1)   # tightened π -> decoherence

V_before = compute_visibility(I_before)
V_after  = compute_visibility(I_after)

print(f"Before π-tightening: V={V_before:.3f} -> After: V={V_after:.3f}")