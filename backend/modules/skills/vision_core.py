# File: backend/modules/perception/vision_core.py

import cv2
import numpy as np
from typing import List, Dict, Optional
import os

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# 🔁 Glyph + Memory integration
from backend.modules.glyphos.glyph_logic import glyph_from_label
from backend.modules.consciousness.memory_bridge import MemoryBridge
from backend.modules.codex.codex_scroll_builder import build_codex_scroll

class VisionCore:
    def __init__(self):
        self.memory = MemoryBridge()
        print("[VisionCore] Initialized")

    def process_image(
        self,
        image_path: str,
        save_output: bool = True,
        include_codex_scroll: bool = False
    ) -> dict:
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image at: {image_path}")

        height, width, _ = image.shape

        # Simulated object detection (can be replaced with YOLO/Vit in future)
        detections = [
            {"label": "object_1", "bbox": [int(0.1*width), int(0.1*height), int(0.3*width), int(0.3*height)]},
            {"label": "object_2", "bbox": [int(0.5*width), int(0.4*height), int(0.7*width), int(0.6*height)]}
        ]

        glyph_nodes = []
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            label = det["label"]
            symbol = glyph_from_label(label) or "👁"  # fallback glyph
            det["glyph"] = symbol

            # Draw
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 165, 255), 2)
            cv2.putText(image, f"{symbol} {label}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)

            # Add symbolic node
            glyph_nodes.append({
                "symbol": symbol,
                "value": label,
                "coord": [x1, y1, x2, y2],
                "source": "vision_core"
            })

            # 🧠 Memory write
            self.memory.write(
                role="vision",
                content=f"Detected {label} as {symbol} at [{x1}, {y1}, {x2}, {y2}]",
                tags=["vision", "detection", label, symbol]
            )

        if save_output:
            output_path = self._build_output_path(image_path)
            cv2.imwrite(output_path, image)
            print(f"[VisionCore] Saved output to {output_path}")
        else:
            output_path = None

        # Optional CodexLang scroll view
        codex_scroll = build_codex_scroll(glyph_nodes, include_coords=True) if include_codex_scroll else None

        return {
            "input": image_path,
            "output_image": output_path,
            "detections": detections,
            "glyph_nodes": glyph_nodes,
            "codex_scroll": codex_scroll
        }

    def _build_output_path(self, image_path: str) -> str:
        base, ext = os.path.splitext(image_path)
        return f"{base}_vision{ext}"