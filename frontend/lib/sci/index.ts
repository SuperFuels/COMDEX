// SCI Event Bus: frontend/lib/sci/index.ts

type SCIHandler = (data: any) => void;
const listeners = new Map<string, SCIHandler[]>();

export function listenSCI(event: string, handler: SCIHandler) {
  if (!listeners.has(event)) listeners.set(event, []);
  listeners.get(event)!.push(handler);

  // unsubscribe
  return () => {
    listeners.set(
      event,
      (listeners.get(event) || []).filter(h => h !== handler)
    );
  };
}

export function emitSCI(event: string, payload: any) {
  (listeners.get(event) || []).forEach(fn => fn(payload));
}