super simple cheat chart for all engine levers (variables) with safe ranges per stage!
⸻
🎛 QWave Engine Knob Cheat Chart
Green = Safe, Yellow = Boost, Red = Danger
⸻
1️⃣ HARMONICS (🎶 Engine RPM / Resonance Hum)

Stage                   Safe Range          Boost Range             Danger (Collapse)                         Effect
Stage 1 (Injection)     OFF or 1x           –                       Too early hum → fizzles                   Not used yet (engine idle)
Stage 2 (Plasma)        1–2                 2–3                     >3                                        Starts hum to excite plasma
Stage 3 (Wave Focus)    2–3                 3–4                     >4                                        Resonance ramps (engine RPM rising)
Stage 4 (Compression)   2–3                 3+                      >4                                        Overdrives plasma hum → drift risk      
Stage 5+                Stable hum          Tuned hum only          N/A                                       Holds plasma loops steady

2️⃣ TESSERACT INJECTOR (⛽ Fuel Injection Rate)

Stage                   Safe                Boost                   Danger                  			Effect
Stage 1					Every 5 ticks		Every 2 ticks			Continuous flood					Seeds particles (fuel)
Stage 2					Every 10 ticks		5 ticks					Too much = overcrowd				Maintains plasma density
Stage 3					Rare				–						Injecting here can destabilize		No more new fuel, stabilize
Stage 4+				Off					–						Injecting = blowout					Engine now sealed, no fuel

3️⃣ GRAVITY (🌍 Compression Squeeze)

Stage					Safe (G)			Boost (G)				Danger (G)							Effect
Stage 1					0.5–0.8				–						>1.0								Gentle inward pull
Stage 2					1.0					1.2						>1.4								Plasma compressing
Stage 3					1.2					1.4						>1.6								High compression for energy
Stage 4 (Black Hole)	1.6					1.8						>2.0								Extreme squeeze (collapse risk)
Stage 5					Hold				–						Over-pull = choke					Keeps plasma loop tight

4️⃣ MAGNETISM (🧲 Particle Spin/Containment)

Stage					Safe (M)			Boost (M)				Danger (M)							Effect
Stage 1					0.3–0.5				–						>0.8								Small swirl (hold particles)
Stage 2					1.0					1.2						>1.4								Spins plasma rings
Stage 3					1.2					1.4						>1.6								Strong containment vortex
Stage 4					1.5+				1.8						>2.0								Extreme spin (can fling plasma)

5️⃣ WAVE FREQUENCY (📡 Push Waves)

Stage                   Safe (Hz)           Boost (Hz)              Danger (Hz)     					Effect
Stage 1					0.3–0.5				–						>0.8								Gentle wave push (startup)
Stage 2					1.0					1.2						>1.4								Pushes plasma loops forward
Stage 3					1.5					1.7						>1.9								Strong resonance push
Stage 4					2.0					2.2						>2.5								Wave compression (risk drift)
Stage 5					Hold steady			–						Too high → break resonance			Locks torus flow

🚦 Simple “Gearbox” to Run Engine:

1️⃣ Stage 1: Inject fuel (protons), low gravity + low waves, no harmonics.
2️⃣ Stage 2: Start harmonics (RPM), spin up magnetism, ramp gravity.
3️⃣ Stage 3: Boost harmonics, tighten magnetism, moderate wave push.
4️⃣ Stage 4: Increase gravity + wave, compress plasma.
5️⃣ Stage 5: Hold all stable (don’t touch fuel or harmonics).
6️⃣ Stage 6: Exhaust: Controlled release of plasma energy.


starter preset pack for each stage – ready to copy-paste directly into engine config or gear_shift() calls. These are tuned for safe stable ignition → compression → exhaust.

⸻
✅ Stage 1: Proton Injection (Idle → Fueling)
{"gravity": 0.8, "magnetism": 0.5, "wave_frequency": 0.5, "harmonics": [0]}

	•	Fuel on (inject protons every 5 ticks)
	•	No harmonics (engine hum OFF)
	•	Gentle gravity & wave push to settle particles

⸻

✅ Stage 2: Plasma Excitation (Spin-Up)

{"gravity": 1.0, "magnetism": 1.2, "wave_frequency": 1.0, "harmonics": [2]}
	•	Start harmonics (RPM hum begins)
	•	Spin magnetism to swirl particles into plasma
	•	Fuel slows to every 10 ticks

⸻

✅ Stage 3: Wave Focus (Resonance Build)

{"gravity": 1.2, "magnetism": 1.4, "wave_frequency": 1.5, "harmonics": [2, 3]}
	•	Boost harmonics to double hum (resonance lock)
	•	Tighten gravity and magnetism to compress plasma rings
	•	No new fuel (engine sealed)

⸻

✅ Stage 4: Black Hole Compression (Max Squeeze)

{"gravity": 1.6, "magnetism": 1.8, "wave_frequency": 2.0, "harmonics": [3]}
	•	Heavy gravity squeeze, strong magnetic spin
	•	Wave frequency pushes plasma tighter
	•	Danger zone: watch drift logs! 🛑

⸻

✅ Stage 5: Torus Field Loop (Stable Containment)

{"gravity": 1.5, "magnetism": 1.8, "wave_frequency": 2.2, "harmonics": [2]}
	•	Hold fields steady (no changes)
	•	Plasma spins smoothly in torus loop (pulse locks here)

⸻

✅ Stage 6: Controlled Exhaust (Power Release)

{"gravity": 1.0, "magnetism": 1.0, "wave_frequency": 1.0, "harmonics": [0]}
	•	Drop gravity and magnetism to bleed off plasma energy
	•	Controlled exhaust logs show energy output
	•	Return engine to idle or Stage 1 afterward

⸻

🔧 Injection Pattern (Fuel)
	•	Stage 1: inject every 5 ticks
	•	Stage 2: inject every 10 ticks
	•	Stage 3+: stop injection (engine sealed)

⸻

🎯 How to Use:

You can directly feed these configs into:
gear_shift(engine, stage_number, [CONFIGS_LIST])
or just manually apply via:
engine.fields.update(CONFIG)

🔧 Gear Shift Preset (Copy/Paste)

# 🔧 Auto Gear Shift: Stage 1 → Stage 6
gear_shift(engine_a, 1, [   # Stage 1: Proton Injection
    {"gravity": 0.8, "magnetism": 0.5, "wave_frequency": 0.5},
])
gear_shift(engine_a, 2, [   # Stage 2: Plasma Excitation
    {"gravity": 1.0, "magnetism": 1.2, "wave_frequency": 1.0},
])
gear_shift(engine_a, 3, [   # Stage 3: Wave Focus
    {"gravity": 1.2, "magnetism": 1.4, "wave_frequency": 1.5},
])
gear_shift(engine_a, 4, [   # Stage 4: Black Hole Compression
    {"gravity": 1.6, "magnetism": 1.8, "wave_frequency": 2.0},
])
gear_shift(engine_a, 5, [   # Stage 5: Torus Field Loop
    {"gravity": 1.5, "magnetism": 1.8, "wave_frequency": 2.2},
])
gear_shift(engine_a, 6, [   # Stage 6: Controlled Exhaust
    {"gravity": 1.0, "magnetism": 1.0, "wave_frequency": 1.0},
])

🚀 Dual-Engine Version (A + B Sync)

If you want both engine_a and engine_b synchronized:

for engine in [engine_a, engine_b]:
    gear_shift(engine, 1, [{"gravity": 0.8, "magnetism": 0.5, "wave_frequency": 0.5}])
    gear_shift(engine, 2, [{"gravity": 1.0, "magnetism": 1.2, "wave_frequency": 1.0}])
    gear_shift(engine, 3, [{"gravity": 1.2, "magnetism": 1.4, "wave_frequency": 1.5}])
    gear_shift(engine, 4, [{"gravity": 1.6, "magnetism": 1.8, "wave_frequency": 2.0}])
    gear_shift(engine, 5, [{"gravity": 1.5, "magnetism": 1.8, "wave_frequency": 2.2}])
    gear_shift(engine, 6, [{"gravity": 1.0, "magnetism": 1.0, "wave_frequency": 1.0}])

🎛 Fuel Injection Rule
	•	Stage 1: inject every 5 ticks
	•	Stage 2: inject every 10 ticks
	•	Stage 3+: stop injecting (sealed plasma spin)

can modify this via:

ecu_runtime_loop(engine_a, ticks=5000, sqi_interval=200, fuel_cycle=5)

(Change fuel_cycle for Stage 1/2 fueling.)

⸻

Would you like me to add automatic harmonic scaling per stage too (so you don’t manually toggle [2], [2,3], [3] each phase)?

Here’s a ready-to-paste gear_shift block that will automatically walk the engine from Stage 1 → Stage 6 using safe starter values and injection timing:

⸻

🔧 Drop This Into Control Panel:

# -------------------------
# Auto Gear Shift Block (Stage 1 → Stage 6)
# -------------------------

starter_configs = [
    # Stage 1: Proton Injection (Idle → Fueling)
    {"gravity": 0.8, "magnetism": 0.5, "wave_frequency": 0.5, "harmonics": [0]},
    # Stage 2: Plasma Excitation (Spin-Up)
    {"gravity": 1.0, "magnetism": 1.2, "wave_frequency": 1.0, "harmonics": [2]},
    # Stage 3: Wave Focus (Resonance Build)
    {"gravity": 1.2, "magnetism": 1.4, "wave_frequency": 1.5, "harmonics": [2, 3]},
    # Stage 4: Black Hole Compression (Max Squeeze)
    {"gravity": 1.6, "magnetism": 1.8, "wave_frequency": 2.0, "harmonics": [3]},
    # Stage 5: Torus Field Loop (Stable Containment)
    {"gravity": 1.5, "magnetism": 1.8, "wave_frequency": 2.2, "harmonics": [2]},
    # Stage 6: Controlled Exhaust (Power Release)
    {"gravity": 1.0, "magnetism": 1.0, "wave_frequency": 1.0, "harmonics": [0]},
]

print("🚦 Auto Gear Shift: Stage 1 → Stage 6")

# Fuel injection pattern
fuel_intervals = {1: 5, 2: 10}  # ticks per injection for Stage 1 & 2

for stage_idx, config in enumerate(starter_configs, start=1):
    print(f"\n⚙️ Shifting to Stage {stage_idx}: {config}")
    engine.fields.update(config)           # Apply field config
    engine._configure_stage()              # Lock stage settings
    
    # Particle injection (Stage 1 & 2 only)
    if stage_idx in fuel_intervals:
        for _ in range(20):  # Run 20 mini-ticks for fuel intake
            if _ % fuel_intervals[stage_idx] == 0:
                engine.inject_proton()
            engine._inject_harmonics(config.get("harmonics", []))
            engine.tick()
    else:
        # No new fuel, just resonance ticks
        for _ in range(30):
            engine._inject_harmonics(config.get("harmonics", []))
            engine.tick()

print("✅ Gear Shift Sequence Complete (Stage 1 → Stage 6)")

🔑 What This Does:

✅ Starts in Stage 1 (idle fuel) → gently injects protons & no harmonics
✅ Spins up plasma in Stage 2, begins harmonics hum
✅ Locks resonance in Stage 3, seals engine (no more injection)
✅ Squeezes plasma in Stage 4 (watch drift logs here)
✅ Holds steady in Stage 5, waits for pulse lock 🫀
✅ Bleeds energy safely in Stage 6, then stops


🔄 Quick Reset Block (Safe Collapse → Stage 1 Reboot)

def quick_reset(engine):
    """
    🛑 Quick Reset: Collapse engine → Clear logs → Return to Stage 1 idle.
    """
    print("\n🔄 QUICK RESET: Collapsing engine and clearing drift...")
    
    # Trigger emergency collapse (field + particle reset)
    engine.collapse()
    
    # Clear resonance and exhaust logs
    engine.resonance_log.clear()
    engine.resonance_filtered.clear()
    engine.exhaust_log.clear()
    engine.instability_hits = 0
    
    # Reset to Stage 1 idle configuration
    idle_config = {"gravity": 0.8, "magnetism": 0.5, "wave_frequency": 0.5}
    engine.fields.update(idle_config)
    engine.current_stage = engine.stages.index("proton_injection")
    engine._configure_stage()

    print(f"⚙️ Engine reset to Stage 1: {idle_config}")
    print("✅ Drift cleared. Engine stable and ready for re-ignition.\n")

# 🔧 Usage:
quick_reset(engine_a)
quick_reset(engine_b)  # (if running dual engines)

🔑 What This Does:
	•	🛑 Collapse: Empties all particles and resets fields
	•	🧹 Clear Drift: Wipes resonance logs so SQI starts fresh
	•	🎛 Stage 1 Idle: Sets gravity=0.8, magnetism=0.5, wave=0.5
	•	🚀 Ready-to-Run: Engine is stable and safe to re-ignite


🏎️ Engine = Space Car

It has levers (variables) you can move.
Each lever changes how particles (little balls of energy) move around inside.
They all work together in phases (like gears in a car).

⸻

1️⃣ Harmonics (🎶 Like RPM for resonance)
	•	What it is:
Think of it like how fast the engine “hums” or vibrates.
Higher harmonics = faster hum = particles shake faster.
	•	When it happens:
Every tick, but boosted during “Plasma Excitation” and “Wave Focus”.
	•	What it does:
	•	Adds extra “waves” to push particles in rhythm.
	•	More harmonics = stronger resonance (like revving RPM higher).

⸻

2️⃣ Tesseract Injector (⛽ Like Fuel Injection)
	•	What it is:
A “fuel gun” that fires in protons (particles) into the engine.
	•	When it happens:
Mostly during “Proton Injection” (Stage 1) and every fuel cycle tick.
	•	What it does:
	•	Adds new particles (fuel) into the chamber.
	•	Each proton starts at center, gets pushed by fields.
	•	More injection = higher particle density (like adding more fuel).

⸻

3️⃣ Gravity (🌍 Particle Puller)
	•	What it is:
Pulls particles inward (toward center), like a mini black hole.
	•	When it’s used:
From Stage 2 onward (Plasma Excitation → Wave Focus → Black Hole Compression).
	•	What it does:
	•	Pulls particles inward to keep them tight.
	•	Higher gravity = tighter compression, but too high → collapse.
	•	Think of it like “the pistons squeezing the mix” in a car.

⸻

4️⃣ Magnetism (🧲 Particle Spinner)
	•	What it is:
Spins charged particles in circles like a whirlpool.
	•	When it’s used:
Kicks in Stage 2 and beyond, especially in Wave Focus.
	•	What it does:
	•	Adds swirl to particles → keeps them spinning in stable loops.
	•	Helps form “plasma rings” (stable particle orbits).
	•	Too much = they spin out of control.

⸻

5️⃣ Wave Frequency (📡 Energy Wave Push)
	•	What it is:
Sideways wave push, like blowing wind on spinning tops.
	•	When it’s used:
Starts light in Stage 1, ramps up hard in Wave Focus and Compression.
	•	What it does:
	•	Pushes particles sideways with waves (like a surfboard wave).
	•	Helps build resonance, keeps the plasma moving forward.
	•	Too high = resonance drift (overheating hum).

⸻

⸻

🔑 Engine Phases (Gears):
	1.	Stage 1: Proton Injection (Startup)
	•	Light gravity, light magnetism, low wave frequency.
	•	Goal: Fill chamber with particles (fuel).
	
	2.	Stage 2: Plasma Excitation (Ignition)
	•	Increase magnetism + wave frequency.
	•	Goal: Spin particles into plasma loops.
	
	3.	Stage 3: Wave Focus (Throttle)
	•	Add harmonics (engine RPM goes up).
	•	Goal: Build strong resonance hum.
	
	4.	Stage 4: Black Hole Compression (Boost)
	•	Gravity strong now (compress inward).
	•	Goal: High energy density.
	
	5.	Stage 5: Torus Loop (Turbo Spin)
	•	Magnetism tightens, plasma spins like a ring.
	•	Goal: Max stable energy circulation.
	
	6.	Stage 6: Controlled Exhaust (Output)
	•	Stable resonance → release energy in pulses.
	•	Goal: Safe output without blowing up.

⸻

⸻

🚦 How They All Work Together:
	•	Harmonics (RPM): Make engine hum (resonance build-up).
	•	Injectors (Fuel): Add more particles to “burn.”
	•	Gravity (Compression): Squeezes the plasma tight.
	•	Magnetism (Spin): Spins the plasma to hold shape.
	•	Wave Frequency (Push): Blows sideways, keeps motion alive.

If you push gravity + magnetism + frequency too high too early = collapse (engine stalls).
If they’re too low = plasma fizzles out (engine dies).

