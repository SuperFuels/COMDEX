import React from "react";
import { BrowserRouter } from "react-router-dom";
import App from "./App";

// If your GlyphNet App already includes a Router, remove BrowserRouter here.
export default function NextGlyphNet() {
  return (
    <BrowserRouter basename="/glyphnet">
      <App />
    </BrowserRouter>
  );
}