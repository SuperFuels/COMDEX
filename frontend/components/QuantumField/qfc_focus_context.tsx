import React, { createContext, useContext, useState } from "react";

type FocusContextType = {
  focusPoint?: [number, number, number];
  setFocusPoint: (point?: [number, number, number]) => void;
};

const QFCFocusContext = createContext<FocusContextType>({
  focusPoint: undefined,
  setFocusPoint: () => {},
});

export const QFCFocusProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [focusPoint, setFocusPoint] = useState<[number, number, number]>();

  return (
    <QFCFocusContext.Provider value={{ focusPoint, setFocusPoint }}>
      {children}
    </QFCFocusContext.Provider>
  );
};

export const useQFCFocus = () => useContext(QFCFocusContext);