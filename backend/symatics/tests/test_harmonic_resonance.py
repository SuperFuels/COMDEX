import json
from backend.symatics.core.srk7_harmonic_resonance import SRKExtension
from backend.symatics.core.srk_kernel import SymaticsReasoningKernel

def run_harmonic_resonance_test():
    print("\n=== Running SRK-7 Harmonic-Resonance Synchronization Test ===")

    kernel = SymaticsReasoningKernel()

    # Load prior SRK layers manually (SRK-3 -> SRK-6)
    for ext_name in [
        "srk3_entropy", 
        "srk4_resonance", 
        "srk41_resonant_entropy", 
        "srk5_coherent_field", 
        "srk6_harmonic_coupling"
    ]:
        try:
            kernel.load_extension(ext_name)
        except Exception as e:
            print(f"[SRK] Warning: Failed to load {ext_name}: {e}")

    # Integrate SRK-7
    srk7 = SRKExtension()
    srk7.integrate(kernel)

    # Mock resonance + harmonic coupling data (simulating prior kernels)
    kernel.resonance_field = type("Mock", (), {"resonance_feedback": {"R": 0.27}})()
    kernel.harmonic_coupling = type("Mock", (), {"last_feedback": {"H": 0.31}})()

    feedback = srk7.feedback(kernel)

    print("\n[Feedback Packet]")
    print(json.dumps(feedback, indent=2))

    diag = srk7.diagnostics(kernel)
    print("\n[Diagnostics Snapshot]")
    print(json.dumps(diag, indent=2))

    if feedback.get("passed"):
        print("✅ SRK-7 harmonic-resonance synchronization passed.")
    else:
        print("⚠️ SRK-7 harmonic-resonance synchronization unstable.")

if __name__ == "__main__":
    run_harmonic_resonance_test()