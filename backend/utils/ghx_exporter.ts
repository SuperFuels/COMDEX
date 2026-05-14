// utils/ghx_exporter.ts

import { GHXPacket } from "@/types/ghx_types"; // Ensure this points to your GHX type definitions
import { saveAs } from "file-saver";

/**
 * Exports a GHXPacket as a downloadable .ghx.json file.
 * Filename is auto-generated based on the render timestamp.
 */
export function exportGHX(projection: GHXPacket): void {
  const filename = `projection_${projection.rendered_at.replace(/[:.]/g, "-")}.ghx.json`;

  const blob = new Blob([JSON.stringify(projection, null, 2)], {
    type: "application/json",
  });

  saveAs(blob, filename);
}