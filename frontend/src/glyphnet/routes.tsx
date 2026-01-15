"use client";

import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";

import DevTools from "./routes/DevTools";

export default function GlyphnetRoutes() {
  return (
    <Routes>
      {/* land somewhere useful */}
      <Route path="/" element={<Navigate to="/devtools" replace />} />

      {/* DevTools */}
      <Route path="/devtools" element={<DevTools />} />

      {/* optional alias */}
      <Route path="/dev-tools" element={<Navigate to="/devtools" replace />} />

      {/* fallback */}
      <Route path="*" element={<Navigate to="/devtools" replace />} />
    </Routes>
  );
}