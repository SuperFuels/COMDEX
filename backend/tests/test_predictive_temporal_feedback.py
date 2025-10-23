from backend.modules.aion_prediction.predictive_bias_layer import PredictiveBias

pb = PredictiveBias()
sequence = ["Φ", "λ", "Ω", "Φ", "λ", "Ω", "Φ"]

for sym in sequence:
    pb.observe(sym)

# Evaluate prediction accuracy using final symbol
pred, p = pb.predict_next("Φ")
print("prediction:", pred, "p≈", round(p, 2))
success = pb.evaluate(pred)
print("success:", success)