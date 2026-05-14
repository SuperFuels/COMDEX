#!/usr/bin/env python3
import os, json, math, argparse
from pathlib import Path
import numpy as np

from backend.photon_algebra.utils.load_constants import load_constants

def lap_1d(f):
    return np.roll(f, -1) - 2.0 * f + np.roll(f, 1)

def main():
    ap = argparse.ArgumentParser(description="Emit time-resolved M6 u,v stacks for X-series.")
    ap.add_argument("--frames", type=int, default=128)
    ap.add_argument("--stride", type=int, default=5, help="simulation steps per saved frame")
    ap.add_argument("--N", type=int, default=512)
    ap.add_argument("--dt", type=float, default=0.001)
    ap.add_argument("--dx", type=float, default=1.0)
    ap.add_argument("--damping", type=float, default=0.035)
    ap.add_argument("--clip", type=float, default=6.0)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--out_dir", type=str, default="backend/modules/knowledge")
    ap.add_argument("--diffusion", type=float, default=None,
                    help="override diffusion strength; otherwise uses env PAEV_DIFFUSION_STRENGTH or default 0.0 (X1-safe)")
    args = ap.parse_args()

    const = load_constants(version="v1.2")
    Λ = float(const["Λ"]); α = float(const["α"]); β = float(const["β"]); χ = float(const.get("χ", 1.0))
    c_eff = math.sqrt(α / (1.0 + Λ))

    # diffusion: arg > env > default (default is strict X1-safe)
    diff_env_raw = os.getenv("PAEV_DIFFUSION_STRENGTH", None)
    if args.diffusion is not None:
        diffusion_strength = float(args.diffusion)
        diffusion_source = "arg"
    elif diff_env_raw is not None:
        diffusion_strength = float(diff_env_raw)
        diffusion_source = "env"
    else:
        diffusion_strength = 0.0
        diffusion_source = "default"

    np.random.seed(args.seed)

    N = args.N
    x = np.linspace(-N//2, N//2, N)

    # initial condition aligned with your M6-style setup
    u = 0.6 * np.exp(-0.02 * (x - 5.0)**2)
    v = np.zeros_like(u)

    steps_total = args.frames * args.stride
    u_stack = np.zeros((args.frames, N), dtype=np.float32)
    v_stack = np.zeros((args.frames, N), dtype=np.float32)

    dt = float(args.dt)
    clipv = float(args.clip)

    frame = 0
    for n in range(steps_total):
        u_xx = lap_1d(u)
        a = (c_eff**2) * u_xx - Λ*u - β*v + χ*np.clip(u**3, -clipv, clipv)
        v = v + dt * a
        v = v * (1.0 - args.damping * dt)
        u = u + dt * v

        # diffusion/noise
        if diffusion_strength != 0.0:
            u = u + diffusion_strength * np.random.normal(0, 1, size=u.shape) * dt

        u = np.clip(u, -clipv, clipv)
        v = np.clip(v, -clipv, clipv)

        if (n + 1) % args.stride == 0:
            u_stack[frame] = u.astype(np.float32)
            v_stack[frame] = v.astype(np.float32)
            frame += 1

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    np.save(out_dir / "M6_field_stack.npy", u_stack)
    np.save(out_dir / "M6_velocity_stack.npy", v_stack)
    np.save(out_dir / "M6_field.npy", u_stack[-1])
    np.save(out_dir / "M6_velocity.npy", v_stack[-1])

    meta = {
        "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "dt_base": dt,
        "dx": float(args.dx),
        "stride": int(args.stride),
        "frames": int(args.frames),
        "N": int(N),
        "damping": float(args.damping),
        "clip_value": clipv,
        "diffusion_strength": float(diffusion_strength),
        "diffusion_source": diffusion_source,
        "diffusion_env_raw": diff_env_raw,
        "seed": int(args.seed),
        "c_eff": float(c_eff),
        "constants_version": "v1.2",
    }
    (out_dir / "M6_meta.json").write_text(json.dumps(meta, indent=2))

    print(f"✅ wrote {out_dir/'M6_field_stack.npy'}  shape={u_stack.shape}")
    print(f"✅ wrote {out_dir/'M6_velocity_stack.npy'} shape={v_stack.shape}")
    print(f"✅ wrote {out_dir/'M6_meta.json'}")
    print(f"✅ wrote {out_dir/'M6_field.npy'} and {out_dir/'M6_velocity.npy'} (last frame)")

if __name__ == "__main__":
    main()