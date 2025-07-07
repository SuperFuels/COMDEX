import cv2
import os

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# Path to the image
file_path = os.path.join(os.path.dirname(__file__), "tester_image.jpg")

# Load image
img = cv2.imread(file_path)

if img is None:
    print("❌ Failed to load image.")
else:
    print("✅ Image loaded successfully.")
    print(f"Shape: {img.shape}")

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Detect edges using Canny
    edges = cv2.Canny(gray, 100, 200)

    # Save the edge image
    output_path = os.path.join(os.path.dirname(__file__), "edges_output.jpg")
    cv2.imwrite(output_path, edges)

    print(f"✅ Edges saved to {output_path}")