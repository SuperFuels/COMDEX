import * as React from "react";
import { QWaveBeam } from "@/components/QuantumField/beam_renderer";
import BeamLogicOverlay from "@/components/QuantumField/BeamLogicOverlay";

type Params = {
  beamData: any[] | null;
  setSelectedBeam: React.Dispatch<React.SetStateAction<any | null>>;
};

export default function renderQWaveBeams({ beamData, setSelectedBeam }: Params) {
  return (beamData || [])
    .filter((beam) => beam?.source && beam?.target)
    .map((b: any) => {
      const {
        source,
        target,
        qwave,
        id,
        predicted,
        collapse_state,
        sqiScore,
      } = b;

      const hasLogicPacket = qwave?.logic_packet;
      const midPosition: [number, number, number] = [
        (source[0] + target[0]) / 2,
        (source[1] + target[1]) / 2,
        (source[2] + target[2]) / 2,
      ];

      return (
        <React.Fragment key={`beam-${id ?? `${source}-${target}`}`}>
          <group
            onClick={() =>
              setSelectedBeam({
                source,
                target,
                qwave,
                id,
                predicted,
                collapse_state,
                sqiScore,
              })
            }
          >
            <QWaveBeam
              source={source as [number, number, number]}
              target={target as [number, number, number]}
              prediction={predicted}
              collapseState={collapse_state}
              sqiScore={sqiScore || 0}
              show
            />
          </group>

          {hasLogicPacket && (
            <BeamLogicOverlay
              position={midPosition}
              packet={qwave.logic_packet}
              visible
            />
          )}
        </React.Fragment>
      );
    });
}