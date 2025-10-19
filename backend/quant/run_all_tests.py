# ===============================
# 📁 backend/quant/run_all_tests.py
# ===============================
"""
Tessaris Q-Series Integrated Validation Runner
----------------------------------------------
Aggregates self-tests across all Q-Series modules.

Usage:
    PYTHONPATH=. python backend/quant/run_all_tests.py

Each Q-Module must implement `run_test()` returning a dict.
The output is a unified JSON summary of coherence, resonance,
and execution integrity across the entire Q-Series software layer.
"""

from importlib import import_module
import json
import traceback


# ----------------------------------------------------------------------
# Module registry — each Q-Series subsystem must have a run_test() entry
# ----------------------------------------------------------------------
MODULES = [
    ("QPy", "backend.quant.qpy.qpy_module", "QPyModule"),
    ("QData", "backend.quant.qdata.qdata_module", "QDataModule"),
    ("QPlot", "backend.quant.qplot.qplot_module", "QPlotModule"),
    ("QLearn", "backend.quant.qlearn.qlearn_module", "QLearnModule"),
    ("QMath", "backend.quant.qmath.qmath_module", "QMathModule"),
    ("QTensor", "backend.quant.qtensor.qtensor_module", "QTensorModule"),
    ("QLang", "backend.quant.qlang.qlang_module", "QLangModule"),
    ("QCompiler", "backend.quant.qcompiler.qcompiler_module", "QCompilerModule"),
    ("QVision", "backend.quant.qvision.qvision_module", "QVisionModule"),
    ("QWeb", "backend.quant.qweb.qweb_module", "QWebModule"),
    ("QSheets", "backend.quant.qsheets.qsheets_core", "QSheetsCore"),
    ("QTools", "backend.quant.qtools.qtools_utils", None),
]


# ----------------------------------------------------------------------
# Core test runner
# ----------------------------------------------------------------------
def run_all_tests():
    results = {}
    for name, mod_path, cls_name in MODULES:
        try:
            mod = import_module(mod_path)
            if cls_name:
                cls = getattr(mod, cls_name)
                instance = cls() if callable(cls) else cls
                if hasattr(instance, "run_test"):
                    results[name] = instance.run_test()
                else:
                    results[name] = {"status": "skipped", "reason": "no run_test()"}
            else:
                if hasattr(mod, "run_test"):
                    results[name] = mod.run_test()
                else:
                    results[name] = {"status": "skipped", "reason": "no run_test()"}
        except Exception as e:
            results[name] = {
                "status": "error",
                "error": str(e),
                "trace": traceback.format_exc().splitlines()[-3:],
            }
    return results


# ----------------------------------------------------------------------
# Extended: GHX Feedback / Resonance Telemetry Validation
# ----------------------------------------------------------------------
if __name__ == "__main__":
    summary = run_all_tests()

    try:
        from backend.quant.telemetry.resonance_telemetry import ResonanceTelemetry
        # 🩹 FIXED PATH BELOW
        from backend.modules.visualization.ghx_feedback_bridge import GHXFeedbackBridge

        tele = ResonanceTelemetry()
        bridge = GHXFeedbackBridge()
        metrics = tele.update()
        packet = bridge.emit_sync({}, metrics)

        summary["GHXFeedback"] = {
            "packet_keys": list(packet["metrics"].keys()),
            "status": "ok"
        }
    except Exception as e:
        summary["GHXFeedback"] = {"status": "error", "error": str(e)}

    print(json.dumps(summary, indent=2))