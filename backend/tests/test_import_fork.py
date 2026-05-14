# ✅ Test Fork model import and basic instantiation

def test_fork_model_import():
    try:
        from backend.models.fork import Fork
        print("✅ Import successful: Fork")

        # Test instantiation
        fork = Fork(
            id="test_fork_001",
            parent_wave_id="wave_abc123",
            linked_beam_id="beam_xyz456",
            sqi_score=0.98,
            innovation_score=0.85,
            mutation_type="logical",
            creator_id="tester_agent",
            source_context="Testing Fork model"
        )

        print("✅ Instantiation successful:", fork)

    except Exception as e:
        print("❌ Import or instantiation failed:", str(e))

if __name__ == "__main__":
    test_fork_model_import()