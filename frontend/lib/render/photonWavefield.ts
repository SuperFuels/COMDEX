// frontend/lib/render/photonWavefield.ts
import * as THREE from "three"

// =====================
// Global cognition pulses
// =====================
let waveBias = 0
let sparkValue = 0
let collapseValue = 0

// --- Cognition → Field Pulses ---
window.addEventListener("photon-wavefield-pulse", (e: any) => {
  waveBias = e.detail.v
  setTimeout(() => (waveBias = 0), 600)
})

window.addEventListener("photon-spark", (e: any) => {
  sparkValue = Math.min(1, sparkValue + e.detail * 2)
  setTimeout(() => (sparkValue = 0), 300)
})

window.addEventListener("photon-collapse", (e: any) => {
  collapseValue = e.detail
  setTimeout(() => (collapseValue = 0), 400)
})


// =====================
// Singleton renderer
// =====================
let renderer: THREE.WebGLRenderer | null = null
let scene: THREE.Scene | null = null
let camera: THREE.Camera | null = null
let material: THREE.ShaderMaterial | null = null

export function initPhotonWavefield(canvas: HTMLCanvasElement) {
  if (renderer) return

  // --- Three init ---
  renderer = new THREE.WebGLRenderer({ canvas, alpha: true })
  renderer.setPixelRatio(window.devicePixelRatio)
  renderer.setSize(window.innerWidth, window.innerHeight)

  scene = new THREE.Scene()
  camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1)

  // --- Shader Material ---
  material = new THREE.ShaderMaterial({
    transparent: true,
    uniforms: {
      time: { value: 0 },
      waveBias: { value: 0 },
      sparkPulse: { value: 0 },
      collapsePulse: { value: 0 },
      resolution: {
        value: new THREE.Vector2(window.innerWidth, window.innerHeight)
      },
    },
    vertexShader: `
      void main() {
        gl_Position = vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform float time;
      uniform float waveBias;
      uniform float sparkPulse;
      uniform float collapsePulse;
      uniform vec2 resolution;

      float field(vec2 p) {
        // breathing base wave
        float breathe = 0.03 * sin(time * 0.35);
        p += breathe;

        float a = atan(p.y, p.x);
        float r = length(p);

        // wave animation
        float w = sin(a * 6.0 + time * 2.0) * 0.3;

        // collapse contracts field radius
        float collapseShift = collapsePulse * -0.25;

        return smoothstep(
          0.35 + w + waveBias * 0.15 + collapseShift,
          0.0,
          r
        );
      }

      void main() {
        vec2 uv = (gl_FragCoord.xy / resolution) * 2.0 - 1.0;
        uv.x *= resolution.x / resolution.y;

        float f = field(uv);

        // base plasma color
        vec3 color = mix(
          vec3(0.05,0.08,0.15),
          vec3(0.2,0.6,1.0),
          f
        );

        // mutation spark glints
        float spark = pow(max(0.0, sin(time * 30.0) * sparkPulse), 6.0);
        color += vec3(1.0, 0.85, 0.5) * spark;

        // collapse ring highlight
        float ring = smoothstep(0.02, 0.0, abs(length(uv) - (0.5 - collapsePulse * 0.3)));
        color = mix(color, vec3(0.9, 0.2, 0.2), ring * collapsePulse);

        gl_FragColor = vec4(color, f * 0.8);
      }
    `,
  })

  const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material)
  scene.add(quad)

  // --- Loop ---
  const animate = (t: number) => {
    if (!material) return

    material.uniforms.time.value = t * 0.001
    material.uniforms.waveBias.value = waveBias
    material.uniforms.sparkPulse.value = sparkValue
    material.uniforms.collapsePulse.value = collapseValue

    renderer!.render(scene!, camera!)
    requestAnimationFrame(animate)
  }

  requestAnimationFrame(animate)
}

// =====================
// Resize
// =====================
window.addEventListener("resize", () => {
  if (!renderer || !material) return
  renderer.setSize(window.innerWidth, window.innerHeight)
  material.uniforms.resolution.value.set(window.innerWidth, window.innerHeight)
})