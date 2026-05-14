import os

# IMPORTANT:
# Adjust the import below to whatever your fusion kernel exposes as a "run server" / "main"
# (Search for "if __name__ == '__main__'" in tessaris_cognitive_fusion_kernel.py)
from backend.modules.aion_cognition.tessaris_cognitive_fusion_kernel import main  # <-- change if needed

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    # If your main() accepts host/port/path, pass them here.
    # Otherwise, patch the module to read PORT from env and bind 0.0.0.0.
    main(host="0.0.0.0", port=port, path="/ws/fusion")  # <-- change signature if needed