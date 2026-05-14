// frontend/types/three-examples.d.ts

// ───────── TextGeometry ─────────
declare module "three/examples/jsm/geometries/TextGeometry" {
  import { BufferGeometry } from "three";

  export class TextGeometry extends BufferGeometry {
    constructor(text: string, parameters?: any);
  }
}

// ───────── FontLoader / Font ─────────
declare module "three/examples/jsm/loaders/FontLoader" {
  import { Loader } from "three";

  export class Font {
    type: string;
    data: any;
  }

  export class FontLoader extends Loader<any> {
    load(
      url: string,
      onLoad?: (font: Font) => void,
      onProgress?: (event: ProgressEvent) => void,
      onError?: (event: ErrorEvent) => void
    ): void;

    parse(json: any): Font;
  }
}

// bundled font JSON
declare module "three/examples/fonts/helvetiker_regular.typeface.json" {
  const fontData: any;
  export default fontData;
}

// ───────── fat-line helpers (Line2) ─────────
declare module "three/examples/jsm/lines/Line2" {
  import { LineSegments } from "three";

  export class Line2 extends LineSegments {
    constructor(geometry?: any, material?: any);
  }
}

declare module "three/examples/jsm/lines/LineMaterial" {
  import { Material, Vector2 } from "three";

  export class LineMaterial extends Material {
    constructor(parameters?: any);
    resolution: Vector2;
    linewidth: number;
    dashed: boolean;
  }
}

declare module "three/examples/jsm/lines/LineGeometry" {
  import { BufferGeometry } from "three";

  export class LineGeometry extends BufferGeometry {
    setPositions(positions: number[] | Float32Array): this;
    setColors(colors: number[] | Float32Array): this;
  }
}