"use client";

import React from "react";
import { HashRouter } from "react-router-dom";
import GlyphnetRoutes from "./routes";

export default function NextGlyphnetApp() {
  return (
    <HashRouter>
      <GlyphnetRoutes />
    </HashRouter>
  );
}