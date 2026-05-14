import os
import json
import difflib
from backend.modules.dna_chain.dna_registry import list_proposals, mark_approved, apply_proposal
from backend.modules.dna_chain.mutation_checker import check_mutation_against_soul_laws

def print_menu():
    print("\n🧬 DNA Mutation CLI Menu")
    print("1. List Proposals")
    print("2. View Proposal Diff")
    print("3. Simulate Soul Law Check")
    print("4. Approve + Apply Mutation")
    print("5. Exit")

def list_all():
    proposals = list_proposals()
    print(f"📜 Found {len(proposals)} proposals:")
    for p in proposals:
        print(f" - {p['proposal_id']} | Approved: {p.get('approved', False)}")

def view_diff():
    pid = input("Enter proposal_id: ").strip()
    proposals = list_proposals()
    match = next((p for p in proposals if p["proposal_id"] == pid), None)
    if not match:
        print("❌ Proposal not found.")
        return
    print("\n--- Unified Diff ---")
    print(match["diff"])

def simulate_laws():
    pid = input("Enter proposal_id: ").strip()
    proposals = list_proposals()
    match = next((p for p in proposals if p["proposal_id"] == pid), None)
    if not match:
        print("❌ Proposal not found.")
        return
    violations = check_mutation_against_soul_laws(match["diff"])
    if not violations:
        print("✅ No violations.")
    else:
        print("⚠️ Violations Detected:")
        for v in violations:
            print(f" - [{v['severity'].upper()}] {v['title']} (trigger: '{v['trigger']}')")

def approve_apply():
    pid = input("Enter proposal_id: ").strip()
    confirm = input("Are you SURE you want to approve and apply this? (yes/no): ")
    if confirm.lower() != "yes":
        print("❌ Cancelled.")
        return
    mark_approved(pid)
    apply_proposal(pid)
    print("✅ Mutation applied.")

def main():
    while True:
        print_menu()
        choice = input("Choose: ").strip()
        if choice == "1":
            list_all()
        elif choice == "2":
            view_diff()
        elif choice == "3":
            simulate_laws()
        elif choice == "4":
            approve_apply()
        elif choice == "5":
            break
        else:
            print("❌ Invalid choice.")

if __name__ == "__main__":
    main()
