declare module "@react-three/fiber" {
  export const Canvas: any;
  export function useFrame(cb: (...args: any[]) => void): void;
  export function useThree(): any;
}