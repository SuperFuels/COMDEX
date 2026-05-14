// frontend/hooks/useQFCFocus.tsx
import React, { createContext, useContext, useState, ReactNode } from "react";

// 🧠 Define the focus point type
export type QFCFocusPoint = [number, number, number] | null;

// 🧠 Context type
interface QFCFocusContextType {
  focusPoint: QFCFocusPoint;
  setFocusPoint: (point: QFCFocusPoint) => void;
}

// 🌀 Create context
const QFCFocusContext = createContext<QFCFocusContextType | undefined>(undefined);

// 🌌 Provider component
type QFCFocusProviderProps = {
  children: ReactNode;
};

export const QFCFocusProvider: React.FC<QFCFocusProviderProps> = ({ children }) => {
  const [focusPoint, setFocusPoint] = useState<QFCFocusPoint>(null);

  return (
    <QFCFocusContext.Provider value={{ focusPoint, setFocusPoint }}>
      {children}
    </QFCFocusContext.Provider>
  );
};

// 🧭 Hook to access context
export const useQFCFocus = (): QFCFocusContextType => {
  const context = useContext(QFCFocusContext);
  if (!context) {
    throw new Error("useQFCFocus must be used within a QFCFocusProvider");
  }
  return context;
};