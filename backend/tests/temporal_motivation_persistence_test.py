from backend.modules.aion_language.temporal_motivation_persistence import MOTIVE

print("=== 🧪 Temporal Motivation Persistence Test Start ===")
index = MOTIVE.compute_persistence()
print("Final Persistence Index:", index)
print("=== ✅ Test Complete ===")