import React from 'react';

interface GlyphQROverlayProps {
  visible: boolean;
  glyphData?: string;
}

const GlyphQROverlay: React.FC<GlyphQROverlayProps> = ({ visible, glyphData }) => {
  if (!visible) return null;

  return (
    <div className="absolute top-4 right-4 z-50 bg-white/80 rounded-xl shadow-xl p-4 border border-gray-300">
      <h2 className="text-sm font-semibold mb-2 text-gray-800">GlyphQR</h2>
      <div className="w-32 h-32 bg-gray-100 flex items-center justify-center text-xs rounded-md border">
        {glyphData || "⟦ ID | Container : Tessaris → Access ⟧"}
      </div>
    </div>
  );
};

export default GlyphQROverlay;