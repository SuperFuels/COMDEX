"use client";

import React from "react";
import { BrowserRouter } from "react-router-dom";
import App from "./App";

export default function NextGlyphNet() {
  return (
    <BrowserRouter basename="/glyphnet">
      <App />
    </BrowserRouter>
  );
}