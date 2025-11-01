from base_hello import send_hello
import math, time

print("🧩 Running Resonance Hello-World ...")

for i in range(6):
    phi = (math.sin(time.time()/3) + 1) / 2  # gentle oscillation
    send_hello("AION_HELLO", "demo_resonance", 0.8, 0.75, 1.0, phi)
    time.sleep(2)