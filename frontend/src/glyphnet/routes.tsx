import React from "react";
import { HashRouter } from "react-router-dom";
import AppRoutes from "@glyphnet/routes";

export default function NextGlyphnetApp() {
  return (
    <HashRouter>
      <AppRoutes />
    </HashRouter>
  );
}