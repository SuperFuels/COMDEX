"use client";

import React from "react";
import { HashRouter, Routes, Route } from "react-router-dom";
import AppRoutes from "@glyphnet/routes";
import DevTools from "./routes/DevTools";

export default function NextGlyphnetApp() {
  return (
    <HashRouter>
      <Routes>
        {/* ✅ DevTools route */}
        <Route path="/devtools" element={<DevTools />} />

        {/* ✅ Everything else stays in your existing route tree */}
        <Route path="/*" element={<AppRoutes />} />
      </Routes>
    </HashRouter>
  );
}