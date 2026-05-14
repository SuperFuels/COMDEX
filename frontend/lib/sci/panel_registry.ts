// =====================================================
//  SCI Panel Registry
//  Centralized registry for all SCI panels (AtomSheet, SQS, Goals, Memory, etc.)
// =====================================================

import * as React from "react";

// 🧠 Extendable panel ID type
export type PanelTypeId =
  | "atomsheet"
  | "sqs"
  | "goals"
  | "memory"  // newly added Memory Scrolls panel
  | "editor";

export type PanelRegistration = {
  id: PanelTypeId;
  title: string;
  icon?: React.ReactNode;
  component: React.ComponentType<any>;
  makeDefaultProps?: () => Record<string, any>;
};

// Internal registry
const _registry = new Map<PanelTypeId, PanelRegistration>();

// Register a new panel
export function registerPanel(p: PanelRegistration) {
  _registry.set(p.id, p);
}

// Retrieve a panel by ID
export function getPanel(id: PanelTypeId) {
  return _registry.get(id);
}

// List all registered panels
export function listPanels(): PanelRegistration[] {
  return Array.from(_registry.values());
}