# Tessaris Discovery Report — N-Series
**Generated:** 2025-10-10 14:08 UTC

**Series Tag:** `N`
**Modules Detected:** 12

---

## Executive Summary

- **series**: N
- **verified_series**: True
- **series_type**: nonlinear_feedback
- **count**: 19
- **timestamp**: 2025-10-07T10:56Z
- **summary_text**: The N-series consolidated nonlinear field and noise-damping tests. Progression from N1 to N5 shows increasing resilience under stochastic excitation, demonstrating stability convergence and consistent damping feedback behavior. This validates the nonlinear control layer prior to G-series cosmological coupling.

---

## Constants Baseline

- ħ = 0.001
- G = 1e-05
- α = 0.5
- β = 0.2

---

## Module Summaries

### N10_renormalization_summary.json
- **Λ0**: 1e-06
- **mean_Xi**: 0.9214315675410802
- **classification**: Stable (self-renormalized)
- **timestamp**: 2025-10-06T15:57Z

### N11_message_summary.json
- **Λ0**: 1e-06
- **α0**: 0.5
- **fidelity**: -0.5869203321990195
- **energy_ratio**: 45760.684890089826
- **classification**: Degraded
- **timestamp**: 2025-10-06T16:06Z

### N12_phase_summary.json
- **Λ0**: 1e-06
- **α0**: 0.5
- **fidelity_corrected**: 0.7185364563899005
- **classification**: Partially recovered
- **timestamp**: 2025-10-06T16:10Z

### N13_feedback_summary.json
- **Λ0**: 1e-06
- **α0**: 0.5
- **feedback_gain**: 0.3
- **mean_fidelity**: 1.0
- **mean_alpha_ratio**: 1.199393068477938
- **mean_lambda_ratio**: 1.001163868244421
- **classification**: ✅ Self-stabilized (Active Quantum Feedback)
- **timestamp**: 2025-10-06T16:13Z

### N14_persistence_summary.json
- **Λ0**: 1e-06
- **α0**: 0.5
- **feedback_gain**: 0.3
- **cycles**: 3
- **fidelities**: [0.7227925466666841, 0.24687878302067282, 0.047390840705891224]
- **mean_fidelity**: 0.33902072346441603
- **energy_ratios**: [0.8522998875665383, 0.6998999385462523, 0.556863000375458]
- **phase_errors**: [-0.8157947160800219, -1.4850121671536367, -1.4511122858608854]
- **classification**: ❌ Lossy Loop
- **timestamp**: 2025-10-06T16:17Z

### N15_thermal_rephase_summary.json
- **Λ0**: 1e-06
- **α0**: 0.5
- **T_eff**: 3.645e+18
- **ΔE_J**: 1.93842e-05
- **rephase_gain**: 0.35
- **cycles**: 4
- **fidelities**: [0.8162583251913929, 0.8162583251913933, 0.8162583251913932, 0.8162583251913934]
- **phase_errors**: [-0.6113357958310064, -0.6113357958310062, -0.6113357958310063, -0.6113357958310062]
- **mean_fidelity**: 0.8162583251913932
- **mean_phase_error**: -0.6113357958310062
- **classification**: ⚠️ Partially stabilized
- **timestamp**: 2025-10-06T16:20Z

### N4_feedback_summary.json
- **constants_path**: backend/modules/knowledge/constants_v1.1.json
- **cycles**: [{'t0': 2.0, 'duration': 1.0, 'gain_mult': 1.1}, {'t0': 5.0, 'duration': 1.2, 'gain_mult': 1.18}, {'t0': 8.2, 'duration': 1.0, 'gain_mult': 1.12}]
- **stability_index**: 1.0
- **classification**: Stable
- **mean_leakage_proxy**: 2.2763578135511098e-10
- **gains**: [0.0, 0.0, 0.0]

### N5_echo_summary.json
- **α0**: 0.5
- **peak_time**: 0.0
- **delay_ratio**: 0.0
- **classification**: Recovered
- **timestamp**: 2025-10-06T14:27Z

### N6_noise_summary.json
- **sigmas**: [1e-05, 1.584893192461114e-05, 2.5118864315095822e-05, 3.9810717055349695e-05, 6.309573444801929e-05, 0.0001, 0.00015848931924611142, 0.0002511886431509582, 0.00039810717055349735, 0.000630957344480193, 0.001, 0.001584893192461114, 0.002511886431509582, 0.003981071705534973, 0.006309573444801936, 0.01, 0.01584893192461114, 0.025118864315095822, 0.039810717055349734, 0.06309573444801936, 0.1]
- **fidelities**: [0.9999999529185996, 0.9999999961486661, 0.9999999842711881, 0.9999999681982925, 0.9999998725555616, 0.9999998455999142, 0.999999640390924, 0.9999990746529865, 0.9999976916968334, 0.9999941890657512, 0.9999860693988828, 0.9999635606806379, 0.9999121274318225, 0.9997757012829948, 0.9994404898138585, 0.9987263252618395, 0.9962567936524547, 0.9909331193691421, 0.9783358241006799, 0.9487593701737453, 0.8780697161296276]
- **fidelity_threshold**: 0.9
- **sigma_at_90pct**: 0.06309573444801936

### N7_capacity_summary.json
- **sigmas**: [1e-05, 1.623776739188721e-05, 2.6366508987303556e-05, 4.281332398719396e-05, 6.951927961775606e-05, 0.00011288378916846884, 0.00018329807108324357, 0.00029763514416313193, 0.0004832930238571752, 0.0007847599703514606, 0.0012742749857031334, 0.00206913808111479, 0.003359818286283781, 0.005455594781168515, 0.008858667904100823, 0.01438449888287663, 0.023357214690901212, 0.03792690190732246, 0.06158482110660261, 0.1]
- **fidelities**: [0.9999717905208462, 0.9999541941039878, 0.9999256214518051, 0.9998792258446917, 0.9998038897408178, 0.9996815607438136, 0.9994829258328252, 0.999160387379648, 0.9986366582043485, 0.9977862443568636, 0.9964053852729514, 0.9941632774805517, 0.9905230191076396, 0.9846138675681062, 0.9750264921300176, 0.9594919371525104, 0.9344088474147277, 0.894278962366114, 0.8316104931241965, 0.7397500610934767]
- **classical_capacity**: [16.609510640466674, 15.910221773321332, 15.2109172320257, 14.51160869478065, 13.812306882680621, 13.113024127600362, 12.413777325321238, 11.714591979612143, 11.01550830168959, 10.316590814590924, 9.617943732256355, 8.919735715329798, 8.22223971739673, 7.525896898151728, 6.831418429031166, 6.139945733049219, 5.453297706345634, 4.7743394670762, 4.107501003788345, 3.4594316055218877]
- **quantum_capacity**: [-8.139764756941363e-05, -0.0001321739324784595, -0.00021462708930578329, -0.00034852264408442315, -0.0005659655956958443, -0.0009191141845631747, -0.0014927326601108966, -0.002424646261129894, -0.0039391457411717045, -0.006401730925047, -0.010409328201449968, -0.016940290544348913, -0.02760725452194812, -0.04509240576983065, -0.07392012039363675, -0.12188854856814575, -0.20287460870786206, -0.3427113606013708, -0.592438436248126, -1.0603969120141556]
- **sigma_at_90pct**: 0.03792690190732246
- **timestamp**: 2025-10-06T15:44Z

### N8_energy_summary.json
- **κ**: 0.31622776601683794
- **T**: 3.6453299936831903e+18
- **E_threshold_eV**: 121101742251165.38
- **fidelity_threshold**: 0.9
- **timestamp**: 2025-10-06T15:48Z

### N9_backreaction_summary.json
- **mean_balance_ratio**: 12977397.40342073
- **classification**: Runaway curvature (collapse)
- **timestamp**: 2025-10-06T15:52Z

---

## Discovery Classification

This N-Series represents a verified discovery event within the Tessaris physics framework.
Registered automatically on 2025-10-10 14:08 UTC.


---

**Generated by Tessaris Build System**

All constants referenced: ħ, G, Λ, α, β from registry v1.2.
