// ✅ File: pages/api/spawn_container_from_node.ts
import { NextApiRequest, NextApiResponse } from "next";
import { v4 as uuidv4 } from "uuid";
import fs from "fs";
import path from "path";

// 🧠 Import server-side broadcast hook
import { broadcast_qfc_update } from "@/backend/modules/visualization/broadcast_qfc_update";

// 🧬 Main handler
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const { nodeId, originPosition } = req.body;

  if (!nodeId) {
    return res.status(400).json({ error: "Missing nodeId" });
  }

  try {
    // ✅ Generate new container ID + filename
    const newContainerId = `spawned_${nodeId}_${uuidv4().slice(0, 8)}.dc.json`;
    const containerPath = path.join(process.cwd(), "public", "containers", newContainerId);

    // ✅ Create symbolic container file from template
    const containerData = {
      id: newContainerId,
      label: `Spawned from node ${nodeId}`,
      originNode: nodeId,
      glyphs: [],
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
    fs.writeFileSync(containerPath, JSON.stringify(containerData, null, 2));

    // ✅ Emit symbolic node + link back to canvas
    const newNode = {
      id: `spawned-${uuidv4().slice(0, 6)}`,
      label: `📦 ${newContainerId.replace(".dc.json", "")}`,
      containerId: newContainerId,
      position: originPosition || [Math.random() * 4 - 2, Math.random() * 4 - 2, 0],
      glyphTrace: [
        {
          summary: "Container spawned",
          intent: "create_container_from_node",
          tick: Date.now(),
        },
      ],
    };

    const newLink = {
      id: `link-${uuidv4().slice(0, 6)}`,
      source: nodeId,
      target: newNode.id,
      type: "spawn",
    };

    // ✅ Broadcast live to QFC WebSocket clients
    await broadcast_qfc_update(newContainerId, {
      nodes: [newNode],
      links: [newLink],
    });

    // ✅ Return new container ID
    res.status(200).json({ newContainerId });
  } catch (err) {
    console.error("❌ Container spawn error:", err);
    res.status(500).json({ error: "Failed to spawn container" });
  }
}