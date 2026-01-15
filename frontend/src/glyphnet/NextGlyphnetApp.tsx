"use client";

import React from "react";
import App from "./App";

// If your GlyphNet uses HashRouter inside App already, you're done.
// If it doesn't, wrap it here with HashRouter.
// import { HashRouter } from "react-router-dom";

export default function NextGlyphnetApp() {
  return (
    // <HashRouter>
      <App />
    // </HashRouter>
  );
}