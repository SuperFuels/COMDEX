import sys
from backend.modules.dna_chain.mutation_checker import check_mutation_against_soul_laws

def main():
    print("🔬 Simulating soul law scan on diff:")
    diff_text = sys.stdin.read()
    violations = check_mutation_against_soul_laws(diff_text)
    if not violations:
        print("✅ No soul law violations detected.")
    else:
        print("⚠️ Soul law violations found:")
        for v in violations:
            print(f" - [{v['severity'].upper()}] Law {v['law_id']} – {v['title']} (trigger: '{v['trigger']}')")

if __name__ == "__main__":
    main()
