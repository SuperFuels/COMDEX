import * as React from "react";

export type PanelTypeId = "atomsheet" | "sqs";

export type PanelRegistration = {
  id: PanelTypeId;
  title: string;
  icon?: React.ReactNode;
  component: React.ComponentType<any>; // your panel’s props shape
  makeDefaultProps?: () => Record<string, any>;
};

const _registry = new Map<PanelTypeId, PanelRegistration>();

export function registerPanel(p: PanelRegistration) {
  _registry.set(p.id, p);
}

export function getPanel(id: PanelTypeId) {
  return _registry.get(id);
}

export function listPanels(): PanelRegistration[] {
  return Array.from(_registry.values());
}