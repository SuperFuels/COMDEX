from backend.symatics.core.srk_kernel import SymaticsReasoningKernel

def run_resonant_entropy_test():
    srk = SymaticsReasoningKernel()
    srk.superpose(1.0, 0.7)
    srk.measure(0.5)
    srk.entangle(0.3, 0.9)

    for ext in srk.extensions:
        if hasattr(ext, "feedback"):
            ext.feedback(srk)

    print("\nResonant-Entropy diagnostics:")
    print(srk.diagnostics().get("resonant_entropy_feedback"))
    print(srk.diagnostics().get("resonant_entropy_trend"))

if __name__ == "__main__":
    run_resonant_entropy_test()