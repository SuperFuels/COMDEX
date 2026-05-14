// ✅ File: frontend/pages/api/spawn_container_from_node.ts
import type { NextApiRequest, NextApiResponse } from "next";
import fs from "fs";
import path from "path";
import { randomUUID } from "crypto";

/**
 * Broadcast to the QFC visualizer via HTTP (preferred), or no-op if no URL is set.
 * Set one of these in your env:
 *  - QFC_BROADCAST_URL (full URL to the broadcast endpoint)
 *  - QFC_BACKEND_URL (base URL; we will POST to `${QFC_BACKEND_URL}/visualization/broadcast_qfc_update`)
 */
async function broadcast(containerId: string, payload: any): Promise<void> {
  const explicitUrl = process.env.QFC_BROADCAST_URL;
  const base = process.env.QFC_BACKEND_URL;
  const url = explicitUrl ?? (base ? `${base.replace(/\/$/, "")}/visualization/broadcast_qfc_update` : "");

  if (!url) {
    console.log("[broadcast_qfc_update:no-op] missing QFC_BROADCAST_URL/QFC_BACKEND_URL");
    return;
  }

  try {
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ containerId, payload }),
    });
  } catch (err) {
    console.log("[broadcast_qfc_update:failed]", (err as Error).message);
  }
}

// 🧬 Main handler
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const { nodeId, originPosition } = req.body as {
    nodeId?: string;
    originPosition?: [number, number, number];
  };

  if (!nodeId) {
    return res.status(400).json({ error: "Missing nodeId" });
  }

  try {
    // ✅ Generate new container ID + filename
    const newContainerId = `spawned_${nodeId}_${randomUUID().slice(0, 8)}.dc.json`;
    const containerPath = path.join(process.cwd(), "public", "containers", newContainerId);

    // ✅ Create symbolic container file from template
    const containerData = {
      id: newContainerId,
      label: `Spawned from node ${nodeId}`,
      originNode: nodeId,
      glyphs: [] as any[],
      memory: [
        {
          type: "spawn",
          sourceNode: nodeId,
          summary: `Container created from node ${nodeId}`,
          timestamp: Date.now(),
        },
      ],
    };

    // ✅ Ensure directory exists
    fs.mkdirSync(path.dirname(containerPath), { recursive: true });

    // ✅ Save new container file
    fs.writeFileSync(containerPath, JSON.stringify(containerData, null, 2), "utf8");

    // ✅ Emit symbolic node + link back to canvas
    const newNode = {
      id: `spawned-${randomUUID().slice(0, 6)}`,
      label: `📦 ${newContainerId.replace(".dc.json", "")}`,
      containerId: newContainerId,
      position:
        (originPosition as [number, number, number]) ??
        ([Math.random() * 4 - 2, Math.random() * 4 - 2, 0] as [number, number, number]),
      glyphTrace: [
        {
          summary: "Container spawned",
          intent: "create_container_from_node",
          tick: Date.now(),
        },
      ],
    };

    const newLink = {
      id: `link-${randomUUID().slice(0, 6)}`,
      source: nodeId,
      target: newNode.id,
      type: "spawn",
    };

    // ✅ Broadcast live to QFC WebSocket clients via backend
    await broadcast(newContainerId, { nodes: [newNode], links: [newLink] });

    // ✅ Return new container ID
    res.status(200).json({ newContainerId });
  } catch (err) {
    console.error("❌ Container spawn error:", err);
    res.status(500).json({ error: "Failed to spawn container" });
  }
}