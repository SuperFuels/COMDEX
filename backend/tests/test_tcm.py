from backend.modules.aion_prediction.temporal_coherence_memory import TemporalCoherenceMemory

tcm = TemporalCoherenceMemory()

# feed a repeating pattern to teach it
sequence = ["Φ", "λ", "Ω", "Φ", "λ", "Ω", "Φ", "λ", "Ω"]

# simulate learning of transitions
for i in range(len(sequence) - 1):
    a, b = sequence[i], sequence[i + 1]
    tcm.update_sequence(a)
    tcm.update_markov(a, b)

# test prediction
tcm.update_sequence("Φ")
pred = tcm.predict_next()
print("pred:", pred)