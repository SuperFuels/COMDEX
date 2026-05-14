# File: backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/modules/physics_module.py

import math
from typing import Dict, Any


class PhysicsModule:
    def __init__(self):
        print("✅ PhysicsModule initialized")

    def gravity_force(self, engine, particle: Dict[str, Any]):
        """Calculate gravitational force vector based on engine gravity field."""
        g = engine.fields.get("gravity", 1.0)
        return (0.0, -g * particle.get("mass", 1.0), 0.0)

    def magnetic_force(self, engine, particle: Dict[str, Any]):
        """Calculate magnetic force vector based on charge and magnetism."""
        m = engine.fields.get("magnetism", 1.0)
        charge = particle.get("charge", 1.0)
        return (m * charge * 0.1, 0.0, 0.0)

    def wave_push(self, engine, particle: Dict[str, Any]):
        """Wave frequency propulsion push (SQI effect)."""
        wf = engine.fields.get("wave_frequency", 1.0)
        return (0.0, wf * 0.05, wf * 0.02)

    def update_particles(self, engine, dt: float):
        """Particle dynamics update with density feedback and field forces."""
        for p in engine.particles:
            p.setdefault("charge", 1.0)
            p.setdefault("density", 1.0)
            p.setdefault("vx", 0.0); p.setdefault("vy", 0.0); p.setdefault("vz", 0.0)
            p.setdefault("x", 0.0); p.setdefault("y", 0.0); p.setdefault("z", 0.0)
            p.setdefault("mass", 1.0)
            p.setdefault("life", 1.0)

            # Apply forces
            gx, gy, gz = self.gravity_force(engine, p)
            mx, my, mz = self.magnetic_force(engine, p)
            wx, wy, wz = self.wave_push(engine, p)

            # Velocity update
            p["vx"] += (gx + mx + wx) * dt
            p["vy"] += (gy + my + wy) * dt
            p["vz"] += (gz + mz + wz) * dt

            # Position update
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["z"] += p["vz"] * dt

            # Velocity delta tracking
            speed = math.sqrt(p["vx"] ** 2 + p["vy"] ** 2 + p["vz"] ** 2)
            p["velocity_delta"] = speed - p.get("last_speed", 0)
            p["last_speed"] = speed

            # Life decay
            p["life"] -= engine.decay_rate * dt

        # Auto-trim expired particles
        engine.particles = [p for p in engine.particles if p["life"] > 0]

        # 🌱 SQI Seed (Ignition G1)
        if engine.tick_count == 1 and engine.current_stage == engine.stages.index("G1"):
            engine.resonance_filtered.append(engine.fields["wave_frequency"])
            engine.log_event(f"🌱 SQI Seed injected at ignition: {engine.fields['wave_frequency']:.4f}")

    def decay_particles(self, engine, dt: float):
        """Decay particle life and remove dead particles."""
        engine.particles = [p for p in engine.particles if p.get("life", 1.0) > 0]
        for p in engine.particles:
            if "life" not in p:
                p["life"] = 1.0
            p["life"] -= engine.decay_rate * dt

    def seed_particles_if_low(self, engine):
        """Auto-respawn baseline particles if population drops."""
        if len(engine.particles) < 200:
            count = 250 if len(engine.particles) == 0 else 50
            print(f"⚠ Particle count low ({len(engine.particles)}). Injecting {count} baseline protons.")
            engine.spawn_particles(count=count, velocity=0.5)