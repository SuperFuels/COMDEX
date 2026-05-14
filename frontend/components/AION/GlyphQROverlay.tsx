// frontend/components/AION/GlyphQROverlay.tsx
import React from "react";

interface GlyphQROverlayProps {
  visible: boolean;
  glyphData?: string;
}

const GlyphQROverlay: React.FC<GlyphQROverlayProps> = ({ visible, glyphData }) => {
  if (!visible) return null;

  return (
    <div className="absolute top-4 right-4 z-50 animate-fade-in">
      <div className="bg-white/90 backdrop-blur-md border border-gray-300 shadow-xl rounded-xl p-4 w-40">
        <h2 className="text-sm font-semibold text-gray-800 mb-2">📛 GlyphQR</h2>
        <div className="w-32 h-32 bg-gray-100 border rounded-md flex items-center justify-center text-center text-[11px] text-gray-700 font-mono p-2 overflow-hidden">
          {glyphData || "⟦ ID | Container : Tessaris → Access ⟧"}
        </div>
      </div>
    </div>
  );
};

export default GlyphQROverlay;