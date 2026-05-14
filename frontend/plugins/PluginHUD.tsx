import React from "react";
import { pluginManager } from "./plugin_manager";

/** Renders any HUD panels returned by plugins.renderHUD(). */
export default function PluginHUD() {
  const [, force] = React.useReducer((x) => x + 1, 0);

  React.useEffect(() => pluginManager.subscribe(() => force()), []);
  const nodes = pluginManager.renderHUD();

  if (!nodes?.length) return null;
  return (
    <div className="pointer-events-none fixed inset-0 z-[60]">
      {nodes.map((n, i) => (
        <div key={i} className="pointer-events-auto">{n}</div>
      ))}
    </div>
  );
}