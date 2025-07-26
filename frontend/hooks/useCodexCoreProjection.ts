// frontend/hooks/useCodexCoreProjection.ts

import { useEffect, useState } from "react";
import { useWebSocket } from "./useWebSocket";

export function useCodexCoreProjection(containerId: string) {
  const [projection, setProjection] = useState<any | null>(null);
  const { lastJsonMessage } = useWebSocket(`/ws/ghx_core/${containerId}`);

  useEffect(() => {
    if (lastJsonMessage?.event === "ghx_projection") {
      setProjection(lastJsonMessage.payload);
    }
  }, [lastJsonMessage]);

  return projection;
}