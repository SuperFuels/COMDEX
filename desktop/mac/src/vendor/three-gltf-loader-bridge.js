import { GLTFLoader } from './three/GLTFLoader.js';

window.GLTFLoader = GLTFLoader;

if (window.THREE) {
  window.THREE.GLTFLoader = GLTFLoader;
}

console.log('[AION] GLTFLoader bridge ready');
window.dispatchEvent(new CustomEvent('aion:gltf-loader-ready', {
  detail: { loaded: true }
}));
