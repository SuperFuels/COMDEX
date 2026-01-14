// src/routes.tsx
import React from "react";
import { Routes, Route } from "react-router-dom";
import App from "./App";
import DevRFPanel from "./dev/DevRFPanel";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<App />} />
      <Route path="/dev/rf" element={<DevRFPanel />} />
    </Routes>
  );
}