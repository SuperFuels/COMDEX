import os
from backend.modules.dna_chain.dna_switch import register_frontend

# ✅ Manual registry (optional – legacy, still supported)
# register_frontend("frontend/components/AIONDashboardClient.tsx")

# ✅ Auto-register all .tsx files in frontend/
def auto_register_frontend_components(directory="frontend"):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".tsx"):
                path = os.path.join(root, file).replace("\\", "/")  # Normalize Windows/Unix paths
                register_frontend(path)

# ✅ Call auto-register
auto_register_frontend_components()