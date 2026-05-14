import React from "react";
import { useFrame } from "@react-three/fiber";

interface ObserverViewportProps {
  observerPosition: [number, number, number];
}

const ObserverViewport: React.FC<ObserverViewportProps> = ({ observerPosition }) => {
  useFrame(({ camera }) => {
    camera.position.set(...observerPosition);
    camera.lookAt(0, 0, 0);
  });

  return null;
};

export default ObserverViewport;