(function initDesktopBoardroomRenderer(global) {
  function ensureThree() {
    if (!global.THREE) {
      throw new Error("THREE must be loaded before desktop-boardroom-renderer.js");
    }
    return global.THREE;
  }


  /*
   * AION Spatial Boardroom Asset Pipeline v1
   * ----------------------------------------------------
   * Purpose:
   * - Prepare the boardroom renderer for real GLB/GLTF assets.
   * - Keep the current primitive renderer as the safe fallback.
   * - Do not require external network access.
   * - Do not break if no GLTFLoader or assets exist yet.
   */
  const AION_BOARDROOM_ASSET_MANIFEST = {
    robot_agent: {
      file: "robot_agent.glb",
      fallback: "primitive_robot",
    },
    executive_chair: {
      file: "executive_chair.glb",
      fallback: "primitive_chair",
    },
    boardroom_table: {
      file: "boardroom_table.glb",
      fallback: "primitive_table",
    },
    boardroom_room: {
      file: "boardroom_room.glb",
      fallback: "primitive_room",
    },
    hologram_panel: {
      file: "hologram_panel.glb",
      fallback: "primitive_panel",
    },
  };

  const aionBoardroomAssetCache = {
    requested: false,
    ready: false,
    failed: false,
    assets: {},
    errors: {},
  };

  function getAionBoardroomAssetUrl(fileName) {
    const clean = String(fileName || "").replace(/^\/+/, "");
    try {
      return new URL(`./assets/boardroom/${clean}`, document.baseURI).href;
    } catch {
      return `./assets/boardroom/${clean}`;
    }
  }

  function getOptionalGLTFLoader() {
    const THREE = ensureThree();

    if (typeof global.GLTFLoader === "function") {
      return new global.GLTFLoader();
    }

    if (THREE && typeof THREE.GLTFLoader === "function") {
      return new THREE.GLTFLoader();
    }

    return null;
  }

  function loadAionBoardroomAssetsOnce(onReady) {
    const loader = getOptionalGLTFLoader();

    if (aionBoardroomAssetCache.requested) {
      if (aionBoardroomAssetCache.ready && typeof onReady === "function") onReady();

      const canRetryMissingLoader =
        !!loader &&
        aionBoardroomAssetCache.failed === true &&
        !!aionBoardroomAssetCache.errors.loader;

      if (!canRetryMissingLoader) return;

      aionBoardroomAssetCache.requested = false;
      aionBoardroomAssetCache.failed = false;
      delete aionBoardroomAssetCache.errors.loader;
    }

    if (!loader) {
      aionBoardroomAssetCache.requested = true;
      aionBoardroomAssetCache.failed = true;
      aionBoardroomAssetCache.errors.loader = "GLTFLoader not available yet; waiting for bridge.";
      return;
    }

    aionBoardroomAssetCache.requested = true;

    const entries = Object.entries(AION_BOARDROOM_ASSET_MANIFEST);

    let pending = entries.length;
    if (!pending) {
      aionBoardroomAssetCache.ready = true;
      if (typeof onReady === "function") onReady();
      return;
    }

    entries.forEach(([key, meta]) => {
      const url = getAionBoardroomAssetUrl(meta.file);

      loader.load(
        url,
        (gltf) => {
          aionBoardroomAssetCache.assets[key] = gltf.scene || gltf.scenes?.[0] || null;
          pending -= 1;

          if (pending <= 0) {
            aionBoardroomAssetCache.ready = true;
            if (typeof onReady === "function") onReady();
          }
        },
        undefined,
        (error) => {
          aionBoardroomAssetCache.errors[key] = error?.message || String(error || "asset load failed");
          pending -= 1;

          if (pending <= 0) {
            aionBoardroomAssetCache.ready = Object.keys(aionBoardroomAssetCache.assets).length > 0;
            if (aionBoardroomAssetCache.ready && typeof onReady === "function") onReady();
          }
        },
      );
    });
  }


  // AION O4C: normalize real GLB boardroom agent visibility.
  function aionBoardroomObjectHasVisibleMesh(object) {
    let hasMesh = false;
    object?.traverse?.((child) => {
      if (child?.isMesh && child.geometry) hasMesh = true;
    });
    return hasMesh;
  }

  function normalizeAionBoardroomAgentModel(object, options = {}) {
    const THREE = ensureThree();
    if (!object) return null;

    const box = new THREE.Box3().setFromObject(object);
    if (!Number.isFinite(box.min.x) || !Number.isFinite(box.max.x)) return object;

    const size = new THREE.Vector3();
    const center = new THREE.Vector3();
    box.getSize(size);
    box.getCenter(center);

    const maxDim = Math.max(size.x || 0, size.y || 0, size.z || 0);
    if (!maxDim || !Number.isFinite(maxDim)) return object;

    const targetHeight = Number(options.targetHeight || 1.75);
    const scale = targetHeight / maxDim;

    object.position.sub(center);
    object.scale.multiplyScalar(scale);

    const normalizedBox = new THREE.Box3().setFromObject(object);
    const normalizedSize = new THREE.Vector3();
    normalizedBox.getSize(normalizedSize);

    object.position.y += Math.max(0.18, normalizedSize.y / 2 + 0.14);
    object.position.z += Number(options.zOffset || 0.08);

    object.traverse?.((child) => {
      if (child?.isMesh) {
        child.castShadow = true;
        child.receiveShadow = true;
        if (child.material) {
          child.material.depthWrite = true;
          child.material.depthTest = true;
          child.material.transparent = child.material.transparent === true;
        }
      }
    });

    object.name = options.name || object.name || "aion_normalized_real_agent";
    return object;
  }

  function cloneAionBoardroomAsset(key) {
    const asset = aionBoardroomAssetCache.assets[key];
    if (!asset || typeof asset.clone !== "function") return null;

    const clone = asset.clone(true);

    if (!aionBoardroomObjectHasVisibleMesh(clone)) {
      return null;
    }

    clone.traverse?.((child) => {
      if (child.isMesh) {
        child.castShadow = true;
        child.receiveShadow = true;
      }
    });

    return clone;
  }

  function hasAionBoardroomAsset(key) {
    return !!aionBoardroomAssetCache.assets[key];
  }

  /* BEGIN AION O19C SYNTHETIC SEAT IDENTITY MASK LOCK */
  /*
   * The seated GLB owns the exact black visor surface as an independent source
   * material. This small shared rig adds only animated eyes and voice bars. It
   * works for both Executive and Board mode
   * and does not depend on modifying the source GLB.
   */
  function addAionSyntheticSeatIdentityMask(parent, options = {}) {
    const THREE = ensureThree();
    if (!parent) return null;

    const key = String(options.key || "agent").trim().toLowerCase();
    const accent = Number.isFinite(Number(options.accent))
      ? Number(options.accent)
      : 0xf2af0d;
    const scale = Number(options.scale || 1);
    const face = new THREE.Group();
    face.name = `aion_synthetic_identity_mask_${key}`;
    face.position.set(
      Number(options.x || 0),
      Number(options.y || 1.5),
      Number(options.z || 0.36),
    );
    face.scale.setScalar(scale);

    const glowMaterial = new THREE.MeshBasicMaterial({
      color: accent,
      transparent: true,
      opacity: 0.98,
      depthTest: false,
      depthWrite: false,
    });
    const eyes = [];
    [-0.073, 0.073].forEach((x, index) => {
      const eye = new THREE.Mesh(
        new THREE.SphereGeometry(0.031, 18, 12),
        glowMaterial.clone(),
      );
      eye.name = `aion_synthetic_face_eye_${key}_${index}`;
      eye.scale.set(1.5, 0.58, 0.45);
      eye.position.set(x, 0.042, 0.182);
      face.add(eye);
      eyes.push(eye);
    });

    const voiceBars = [];
    [-0.044, -0.022, 0, 0.022, 0.044].forEach((x, index) => {
      const bar = new THREE.Mesh(
        new THREE.BoxGeometry(0.012, 0.026, 0.012),
        glowMaterial.clone(),
      );
      bar.name = `aion_synthetic_voice_bar_${key}_${index}`;
      bar.position.set(x, -0.058, 0.187);
      face.add(bar);
      voiceBars.push(bar);
    });

    parent.add(face);
    face.traverse?.((child) => {
      if (child?.isMesh) child.renderOrder = 40;
    });
    face.userData.aionSyntheticIdentity = true;
    face.userData.seed = key.split("").reduce((sum, char) => sum + char.charCodeAt(0), 0) * 0.017;
    face.userData.eyes = eyes;
    face.userData.voiceBars = voiceBars;

    if (current) {
      current.syntheticFaceRigs = current.syntheticFaceRigs || [];
      current.syntheticFaceRigs.push(face);
    }
    return face;
  }
  /* END AION O19C SYNTHETIC SEAT IDENTITY MASK LOCK */


  if (!global.__aionBoardroomGLTFReadyRetryInstalled) {
    global.__aionBoardroomGLTFReadyRetryInstalled = true;

    global.addEventListener("aion:gltf-loader-ready", () => {
      aionBoardroomAssetCache.requested = false;
      aionBoardroomAssetCache.failed = false;
      delete aionBoardroomAssetCache.errors.loader;

      loadAionBoardroomAssetsOnce(() => {
        if (!current) return;
        rebuildWorld(current.options?.snapshot || {}, current.options || {});
      });
    });
  }

  global.__aionBoardroomAssetPipeline = {
    manifest: AION_BOARDROOM_ASSET_MANIFEST,
    cache: aionBoardroomAssetCache,
    loadOnce: loadAionBoardroomAssetsOnce,
    hasAsset: hasAionBoardroomAsset,
  };


  const BOARDROOM_ZONES = {
    coo: {
      label: "COO Core",
      angle: null,
      position: [0, 0, 0],
      color: 0x1a8aff,
      scale: 1.26,
      dark: true,
    },
    marketing: { label: "Marketing", angle: -90, color: 0x1a8aff, scale: 1.1 },
    sales: { label: "Sales", angle: -30, color: 0x1a8aff, scale: 1.2 },
    operations: { label: "Operations", angle: 30, color: 0x1a8aff, scale: 1.2 },
    hr: { label: "HR", angle: 90, color: 0x1a8aff, scale: 1.06 },
    support: { label: "Support", angle: 150, color: 0x1a8aff, scale: 1.2 },
    finance: { label: "Finance", angle: 210, color: 0x1a8aff, scale: 1.2 },
    ceo: { label: "CEO", position: [-6.8, 0, -24.2], color: 0x60a5fa, scale: 0.92 },
    aion: { label: "AION", position: [0, 0, -26.6], color: 0x8b5cf6, scale: 0.94 },
    openai: { label: "OpenAI", position: [6.8, 0, -24.2], color: 0x22c55e, scale: 0.92 },
  };

  const FLOOR_STAGE_LAYOUT = [
    [-3.55, 0.12, -0.2],
    [-1.2, 0.12, -0.55],
    [1.25, 0.12, -0.2],
    [3.55, 0.12, -0.8],
    [3.1, 0.12, 1.15],
  ];

  const FLOOR_AGENT_LAYOUT = [
    [-2.2, 0.18, 2.0],
    [0, 0.18, 2.35],
    [2.2, 0.18, 2.0],
    [3.45, 0.18, 1.9],
  ];

  let current = null;
  let currentPortrait = null;

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function polar(radius, angleDeg) {
    const angle = (angleDeg * Math.PI) / 180;
    return [Math.cos(angle) * radius, Math.sin(angle) * radius];
  }

  function zonePosition(key, radius) {
    const zone = BOARDROOM_ZONES[key];
    if (!zone) return [0, 0, 0];
    if (Array.isArray(zone.position)) return zone.position.slice();
    const p = polar(radius, zone.angle);
    return [p[0], 0, p[1]];
  }

  function money(value) {
    if (value == null || value === "") return "—";
    if (typeof value === "number") return `£${value.toLocaleString("en-GB")}`;
    return String(value);
  }

  function percent(value) {
    if (value == null || value === "") return "—";
    if (typeof value === "number") return `${value}%`;
    return String(value);
  }

  function asText(value) {
    if (value == null || value === "") return "—";
    return String(value);
  }

  function seatStateColor(state) {
    if (state === "blocked") return 0xef4444;
    if (state === "warning") return 0xf59e0b;
    if (state === "escalated") return 0xf97316;
    if (state === "failed") return 0xef4444;
    if (state === "waiting_approval") return 0xf59e0b;
    if (state === "running") return 0x1a8aff;
    return 0x22c55e;
  }

  function runtimeStatusColor(status) {
    if (status === "running") return 0x1a8aff;
    if (status === "waiting_approval") return 0xf59e0b;
    if (status === "failed") return 0xef4444;
    if (status === "completed") return 0x22c55e;
    if (status === "queued") return 0x64748b;
    return 0x8b5cf6;
  }

  function disposeMaterial(material) {
    if (!material) return;
    if (Array.isArray(material)) {
      material.forEach(disposeMaterial);
      return;
    }
    if (material.map) material.map.dispose?.();
    if (material.alphaMap) material.alphaMap.dispose?.();
    material.dispose?.();
  }

  function disposeObject(object) {
    if (!object) return;
    object.traverse?.((child) => {
      if (child.geometry) child.geometry.dispose?.();
      if (child.material) disposeMaterial(child.material);
    });
  }

  function getDepartmentSeatId(departmentKey) {
    return {
      marketing: "seat_marketing",
      sales: "seat_sales",
      operations: "seat_ops",
      finance: "seat_finance",
      support: "seat_support",
      hr: "seat_hr",
      coo: "seat_coo",
    }[departmentKey] || null;
  }

  function getFloors(snapshot) {
    return snapshot?.floors || snapshot?.summary?.floors || {};
  }

  function getRenderableDepartmentKeys(snapshot) {
    const floorKeys = Object.keys(getFloors(snapshot) || {});
    const departmentKeys = safeArray(snapshot?.departments)
      .map((item) => item?.key || item?.id)
      .filter(Boolean);

    return Array.from(
      new Set([...departmentKeys, ...floorKeys].filter((key) => BOARDROOM_ZONES[key])),
    );
  }

  function getWorkspaceDisplay(snapshot) {
    const workspace = snapshot?.workspace || snapshot?.summary?.workspace || {};
    return {
      name:
        workspace?.name ||
        workspace?.title ||
        workspace?.slug ||
        snapshot?.workspaceId ||
        "Workspace",
      subtitle:
        workspace?.business_type ||
        workspace?.industry ||
        workspace?.category ||
        workspace?.slug ||
        "Local runtime",
    };
  }

  function clearInteractiveObjects() {
    if (!current) return;
    current.interactives = [];
  }

  function registerInteractive(mesh, meta) {
    if (!current || !mesh) return;
    current.interactives.push({ mesh, meta });
  }

  function disposeCurrent() {
    if (currentPortrait) {
      const portrait = currentPortrait;
      currentPortrait = null;
      portrait.dispose?.();
    }

    if (!current) return;

    if (current.rafId) {
      global.cancelAnimationFrame(current.rafId);
    }

    if (current.onResize) {
      global.removeEventListener("resize", current.onResize);
    }

    if (current.controlsCleanup) {
      current.controlsCleanup();
    }

    if (current.pointerCleanup) {
      current.pointerCleanup();
    }

    if (current.rootGroup) {
      current.scene.remove(current.rootGroup);
      disposeObject(current.rootGroup);
    }

    if (current.scene) {
      disposeObject(current.scene);
    }

    if (current.renderer) {
      current.renderer.dispose?.();
      current.renderer.forceContextLoss?.();
      if (current.renderer.domElement?.parentNode) {
        current.renderer.domElement.parentNode.removeChild(current.renderer.domElement);
      }
    }

    if (current.container) {
      current.container.innerHTML = "";
    }

    current = null;
  }

  function makeTextSprite(text, options) {
    const THREE = ensureThree();
    const opts = options || {};

    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");

    const fontSize = opts.fontSize || 42;
    const fontWeight = opts.fontWeight || 800;
    const paddingX = opts.paddingX || 26;
    const paddingY = opts.paddingY || 16;
    const color = opts.color || "#0f172a";
    const background = opts.background || "rgba(255,255,255,0)";
    const border = opts.border || "rgba(255,255,255,0)";
    const borderWidth = Number.isFinite(Number(opts.borderWidth)) ? Number(opts.borderWidth) : 3;
    const fontFamily =
      opts.fontFamily ||
      "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";

    ctx.font = `${fontWeight} ${fontSize}px ${fontFamily}`;
    const metrics = ctx.measureText(String(text));
    const textWidth = Math.ceil(metrics.width);
    const width = Math.max(64, textWidth + paddingX * 2);
    const height = Math.max(48, fontSize + paddingY * 2);

    canvas.width = width;
    canvas.height = height;

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = background;
    ctx.fillRect(0, 0, width, height);
    if (borderWidth > 0) {
      ctx.strokeStyle = border;
      ctx.lineWidth = borderWidth;
      ctx.strokeRect(borderWidth / 2, borderWidth / 2, width - borderWidth, height - borderWidth);
    }
    ctx.font = `${fontWeight} ${fontSize}px ${fontFamily}`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = color;
    ctx.fillText(String(text), width / 2, height / 2);

    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;
    texture.colorSpace = THREE.SRGBColorSpace;

    const material = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      depthTest: false,
      depthWrite: false,
    });

    const sprite = new THREE.Sprite(material);
    const aspect = width / height;
    const heightWorld = opts.heightWorld || 1;
    const widthWorld = heightWorld * aspect;

    sprite.scale.set(widthWorld, heightWorld, 1);
    return sprite;
  }

  function addLine(parent, a, b, color, opacity) {
    const THREE = ensureThree();
    const geometry = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(a[0], a[1], a[2]),
      new THREE.Vector3(b[0], b[1], b[2]),
    ]);

    const material = new THREE.LineBasicMaterial({
      color,
      transparent: true,
      opacity: opacity == null ? 0.22 : opacity,
    });

    const line = new THREE.Line(geometry, material);
    parent.add(line);
    return line;
  }

  function getSeatById(snapshot, seatId) {
    return safeArray(snapshot?.seats).find((seat) => seat?.id === seatId) || null;
  }

  function getPulse(snapshot) {
    return snapshot?.pulse || snapshot?.summary?.pulse || {};
  }

  function getCenter(snapshot) {
    return snapshot?.center || snapshot?.summary?.center || {};
  }

  function getRuntime(snapshot) {
    return snapshot?.runtime || snapshot?.summary?.runtime || {};
  }

  function getDepartmentRuntimeMap(snapshot, departmentKey) {
    const runs = safeArray(getRuntime(snapshot)?.runs);
    const out = {};

    runs
      .filter((run) => run?.department_key === departmentKey)
      .forEach((run) => {
        const agentId = run?.agent_id;
        if (!agentId) return;

        if (!out[agentId]) {
          out[agentId] = {
            count: 1,
            status: run?.status,
          };
          return;
        }

        out[agentId].count += 1;
        out[agentId].status = run?.status || out[agentId].status;
      });

    return out;
  }

  function buildHexFloor(label, color, x, z, options) {
    const THREE = ensureThree();
    const opts = options || {};

    const group = new THREE.Group();
    const scale = opts.scale || 1;
    const dark = !!opts.dark;
    const active = !!opts.active;

    const outerRadius = 3.55 * scale;
    const innerRadius = 2.82 * scale;
    const accentRadius = 2.9 * scale;
    const centerRadius = 2.08 * scale;

    const outerColor = dark ? 0x14223c : 0xd7dee9;
    const innerColor = dark ? 0x21345a : 0xedf2f8;
    const textColor = dark ? "#f8fafc" : "#334155";

    const outer = new THREE.Mesh(
      new THREE.CylinderGeometry(outerRadius, outerRadius, 0.22 * scale, 6),
      new THREE.MeshStandardMaterial({
        color: outerColor,
        roughness: 0.92,
        metalness: 0.05,
      }),
    );
    outer.position.y = -0.14 * scale;
    group.add(outer);

    const inner = new THREE.Mesh(
      new THREE.CylinderGeometry(innerRadius, innerRadius, 0.09 * scale, 6),
      new THREE.MeshStandardMaterial({
        color: innerColor,
        roughness: 0.95,
        metalness: 0.02,
      }),
    );
    inner.position.y = -0.02 * scale;
    group.add(inner);

    const accent = new THREE.Mesh(
      new THREE.CylinderGeometry(accentRadius, accentRadius, 0.018 * scale, 6),
      new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: dark ? 0.24 : active ? 0.2 : 0.1,
      }),
    );
    accent.position.y = 0.035 * scale;
    group.add(accent);

    const centerGlow = new THREE.Mesh(
      new THREE.CylinderGeometry(centerRadius, centerRadius, 0.02 * scale, 6),
      new THREE.MeshBasicMaterial({
        color: 0x1a8aff,
        transparent: true,
        opacity: active ? 0.1 : 0.04,
      }),
    );
    centerGlow.position.y = 0.05 * scale;
    group.add(centerGlow);

    if (active) {
      const highlight = new THREE.Mesh(
        new THREE.TorusGeometry(outerRadius * 0.78, 0.06 * scale, 18, 48, Math.PI * 2),
        new THREE.MeshBasicMaterial({
          color: 0x69e2ff,
          transparent: true,
          opacity: 0.9,
        }),
      );
      highlight.rotation.x = Math.PI / 2;
      highlight.position.y = 0.1 * scale;
      group.add(highlight);
    }

    const labelSprite = makeTextSprite(label, {
      fontSize: label === "COO Core" ? 54 : 42,
      fontWeight: 800,
      color: textColor,
      heightWorld: label === "COO Core" ? 1.12 * scale : 0.92 * scale,
    });
    labelSprite.position.set(0, 1.18 * scale, 0);
    group.add(labelSprite);

    if (opts.subtext) {
      const subSprite = makeTextSprite(opts.subtext, {
        fontSize: 22,
        fontWeight: 700,
        color: opts.subtextColor || "#64748b",
        heightWorld: 0.38 * scale,
      });
      subSprite.position.set(0, 0.52 * scale, 0);
      group.add(subSprite);
    }

    if (opts.stateText) {
      const stateSprite = makeTextSprite(String(opts.stateText).toUpperCase(), {
        fontSize: 18,
        fontWeight: 800,
        color: opts.stateColorText || "#22c55e",
        heightWorld: 0.25 * scale,
      });
      stateSprite.position.set(0, 0.22 * scale, 2.35 * scale);
      group.add(stateSprite);
    }

    group.position.set(x, 0, z);
    return group;
  }

  function buildMetricPad(label, value, x, z, accent) {
    const THREE = ensureThree();
    const group = new THREE.Group();

    const base = new THREE.Mesh(
      new THREE.BoxGeometry(1.9, 0.12, 1.12),
      new THREE.MeshStandardMaterial({
        color: 0xffffff,
        roughness: 0.94,
        metalness: 0.02,
      }),
    );
    base.position.y = 0.06;
    group.add(base);

    const top = new THREE.Mesh(
      new THREE.BoxGeometry(1.9, 0.012, 1.12),
      new THREE.MeshBasicMaterial({
        color: accent || 0x1a8aff,
        transparent: true,
        opacity: 0.12,
      }),
    );
    top.position.y = 0.126;
    group.add(top);

    const labelSprite = makeTextSprite(label, {
      fontSize: 18,
      fontWeight: 700,
      color: "#64748b",
      heightWorld: 0.22,
    });
    labelSprite.position.set(0, 0.17, -0.14);
    group.add(labelSprite);

    const valueSprite = makeTextSprite(asText(value), {
      fontSize: 28,
      fontWeight: 800,
      color: "#0f172a",
      heightWorld: 0.32,
    });
    valueSprite.position.set(0, 0.17, 0.18);
    group.add(valueSprite);

    group.position.set(x, 0, z);
    return group;
  }

  function buildStageNode(stage, position, active) {
    const THREE = ensureThree();
    const group = new THREE.Group();
    const color = seatStateColor(stage?.state);

    const base = new THREE.Mesh(
      new THREE.CylinderGeometry(0.72, 0.72, 0.12, 24),
      new THREE.MeshStandardMaterial({
        color: 0xffffff,
        roughness: 0.92,
        metalness: 0.03,
      }),
    );
    base.position.y = 0.08;
    group.add(base);

    const top = new THREE.Mesh(
      new THREE.CylinderGeometry(0.72, 0.72, 0.014, 24),
      new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: active ? 0.3 : 0.14,
      }),
    );
    top.position.y = 0.145;
    group.add(top);

    const statusDot = new THREE.Mesh(
      new THREE.CircleGeometry(0.09, 20),
      new THREE.MeshBasicMaterial({ color }),
    );
    statusDot.rotation.x = -Math.PI / 2;
    statusDot.position.set(0, 0.16, 0.56);
    group.add(statusDot);

    if (active) {
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(0.82, 0.03, 16, 40),
        new THREE.MeshBasicMaterial({ color: 0x1a8aff }),
      );
      ring.rotation.x = Math.PI / 2;
      ring.position.y = 0.18;
      group.add(ring);
    }

    const labelSprite = makeTextSprite(stage?.label || "Stage", {
      fontSize: 18,
      fontWeight: 700,
      color: "#64748b",
      heightWorld: 0.21,
    });
    labelSprite.position.set(0, 0.18, -0.06);
    group.add(labelSprite);

    const countSprite = makeTextSprite(asText(stage?.count ?? 0), {
      fontSize: 30,
      fontWeight: 800,
      color: "#0f172a",
      heightWorld: 0.32,
    });
    countSprite.position.set(0, 0.18, 0.18);
    group.add(countSprite);

    if (typeof stage?.value === "number") {
      const valueSprite = makeTextSprite(money(stage.value), {
        fontSize: 16,
        fontWeight: 700,
        color: "#0f4ea8",
        heightWorld: 0.18,
      });
      valueSprite.position.set(0, 0.18, 0.42);
      group.add(valueSprite);
    }

    group.position.set(position[0], position[1], position[2]);
    return { group, mesh: base };
  }

  function buildAgentNode(agent, position, runtimeMeta, active) {
    const THREE = ensureThree();
    const group = new THREE.Group();

    const tint = seatStateColor(agent?.state);
    const statusColor = runtimeMeta?.status ? runtimeStatusColor(runtimeMeta.status) : null;

    const base = new THREE.Mesh(
      new THREE.BoxGeometry(0.5, 0.06, 0.5),
      new THREE.MeshStandardMaterial({
        color: 0x9fb7d9,
        roughness: 0.5,
        metalness: 0.12,
      }),
    );
    base.position.y = 0.02;
    group.add(base);

    const body = new THREE.Mesh(
      new THREE.BoxGeometry(0.28, 0.86, 0.28),
      new THREE.MeshStandardMaterial({
        color: 0xd9f3ff,
        emissive: 0x4cc9ff,
        emissiveIntensity: 0.18,
        roughness: 0.3,
        metalness: 0.15,
        transparent: true,
        opacity: 0.92,
      }),
    );
    body.position.y = 0.48;
    group.add(body);

    const head = new THREE.Mesh(
      new THREE.BoxGeometry(0.28, 0.24, 0.22),
      new THREE.MeshStandardMaterial({
        color: 0xeef8ff,
        emissive: 0x7c3aed,
        emissiveIntensity: 0.12,
        roughness: 0.24,
        metalness: 0.18,
        transparent: true,
        opacity: 0.95,
      }),
    );
    head.position.y = 1.02;
    group.add(head);

    const visor = new THREE.Mesh(
      new THREE.PlaneGeometry(0.14, 0.07),
      new THREE.MeshBasicMaterial({ color: 0x0b2545 }),
    );
    visor.position.set(0, 1.02, 0.115);
    group.add(visor);

    const leftEye = new THREE.Mesh(
      new THREE.CircleGeometry(0.01, 16),
      new THREE.MeshBasicMaterial({ color: tint }),
    );
    leftEye.position.set(-0.03, 1.02, 0.12);
    group.add(leftEye);

    const rightEye = new THREE.Mesh(
      new THREE.CircleGeometry(0.01, 16),
      new THREE.MeshBasicMaterial({ color: tint }),
    );
    rightEye.position.set(0.03, 1.02, 0.12);
    group.add(rightEye);

    const innerHalo = new THREE.Mesh(
      new THREE.TorusGeometry(0.34, 0.018, 16, 48),
      new THREE.MeshBasicMaterial({
        color: 0x69e2ff,
        transparent: true,
        opacity: 0.45,
      }),
    );
    innerHalo.rotation.x = Math.PI / 2;
    innerHalo.position.y = 0.06;
    group.add(innerHalo);

    if (statusColor != null) {
      const outerHalo = new THREE.Mesh(
        new THREE.RingGeometry(0.5, 0.67, 48),
        new THREE.MeshBasicMaterial({
          color: statusColor,
          transparent: true,
          opacity: 0.16,
          side: THREE.DoubleSide,
        }),
      );
      outerHalo.rotation.x = -Math.PI / 2;
      outerHalo.position.y = 0.075;
      group.add(outerHalo);
    }

    if (active) {
      const selectRing = new THREE.Mesh(
        new THREE.TorusGeometry(0.38, 0.018, 16, 40),
        new THREE.MeshBasicMaterial({
          color: 0x8b5cf6,
          transparent: true,
          opacity: 0.7,
        }),
      );
      selectRing.rotation.x = Math.PI / 2;
      selectRing.position.y = 0.52;
      group.add(selectRing);
    }

    const labelSprite = makeTextSprite(agent?.label || "Agent", {
      fontSize: 18,
      fontWeight: 700,
      color: "#0f172a",
      heightWorld: 0.18,
    });
    labelSprite.position.set(0, 1.36, 0);
    group.add(labelSprite);

    if (agent?.role) {
      const roleSprite = makeTextSprite(agent.role, {
        fontSize: 14,
        fontWeight: 700,
        color: "#64748b",
        heightWorld: 0.14,
      });
      roleSprite.position.set(0, 1.54, 0);
      group.add(roleSprite);
    }

    if (typeof agent?.workload === "number") {
      const loadSprite = makeTextSprite(`Load ${agent.workload}`, {
        fontSize: 12,
        fontWeight: 800,
        color: "#0f4ea8",
        heightWorld: 0.12,
      });
      loadSprite.position.set(0, 1.69, 0);
      group.add(loadSprite);
    }

    if (agent?.displayTag) {
      const tagSprite = makeTextSprite(String(agent.displayTag).toUpperCase(), {
        fontSize: 12,
        fontWeight: 800,
        color: "#0f4ea8",
        background: "rgba(223,246,255,0.95)",
        paddingX: 16,
        paddingY: 10,
        heightWorld: 0.12,
      });
      tagSprite.position.set(0, 1.86, 0);
      group.add(tagSprite);
    }

    if (runtimeMeta?.count > 0) {
      const badge = new THREE.Mesh(
        new THREE.SphereGeometry(0.11, 18, 18),
        new THREE.MeshBasicMaterial({ color: statusColor || 0x1a8aff }),
      );
      badge.position.set(0.44, 1.1, 0);
      group.add(badge);

      const countSprite = makeTextSprite(runtimeMeta.count, {
        fontSize: 14,
        fontWeight: 800,
        color: "#ffffff",
        heightWorld: 0.08,
      });
      countSprite.position.set(0.44, 1.1, 0.09);
      group.add(countSprite);
    }

    group.position.set(position[0], position[1], position[2]);
    return { group, mesh: body };
  }

  function buildFlowLink(flow, fromPosition, toPosition, active) {
    const THREE = ensureThree();
    const group = new THREE.Group();

    const color =
      flow?.exception || (flow?.blockedCount ?? 0) > 0
        ? 0xef4444
        : flow?.bottleneck
          ? 0xf59e0b
          : seatStateColor(flow?.state);

    const material = new THREE.LineBasicMaterial({
      color: active ? 0x1a8aff : color,
      transparent: true,
      opacity: active ? 0.95 : flow?.exception || flow?.bottleneck ? 0.8 : 0.48,
    });

    const geometry = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(fromPosition[0], 0.1, fromPosition[2]),
      new THREE.Vector3(toPosition[0], 0.1, toPosition[2]),
    ]);

    group.add(new THREE.Line(geometry, material));

    const midX = (fromPosition[0] + toPosition[0]) / 2;
    const midZ = (fromPosition[2] + toPosition[2]) / 2;

    const badge = new THREE.Mesh(
      new THREE.CircleGeometry(active ? 0.2 : 0.15, 20),
      new THREE.MeshBasicMaterial({
        color: active ? 0x1a8aff : color,
        transparent: true,
        opacity: active ? 0.25 : 0.12,
      }),
    );
    badge.rotation.x = -Math.PI / 2;
    badge.position.set(midX, 0.11, midZ);
    group.add(badge);

    const countSprite = makeTextSprite(flow?.count ?? 0, {
      fontSize: 14,
      fontWeight: 800,
      color: "#334155",
      heightWorld: 0.1,
    });
    countSprite.position.set(midX, 0.18, midZ);
    group.add(countSprite);

    if (flow?.blockedCount) {
      const blockedSprite = makeTextSprite(`${flow.blockedCount} blocked`, {
        fontSize: 11,
        fontWeight: 800,
        color: "#ef4444",
        heightWorld: 0.08,
      });
      blockedSprite.position.set(midX, 0.18, midZ + 0.22);
      group.add(blockedSprite);
    }

    return group;
  }

  function getStagePositionById(stages, id) {
    const index = safeArray(stages).findIndex((item) => item?.id === id);
    if (index < 0) return null;
    return FLOOR_STAGE_LAYOUT[index] || null;
  }

  function renderDepartmentInterior(
    parent,
    departmentKey,
    floorState,
    floorPosition,
    selectedInspectorTarget,
    snapshot,
  ) {
    const group = new global.THREE.Group();
    const stages = safeArray(floorState?.stages);
    const agents = safeArray(floorState?.agents);
    const flows = safeArray(floorState?.flows);
    const runtimeMap = getDepartmentRuntimeMap(snapshot, departmentKey);

    const localMetricAccent = {
      marketing: 0x1a8aff,
      sales: 0x22c55e,
      finance: 0xf59e0b,
      operations: 0x8b5cf6,
      support: 0x22c55e,
      hr: 0xef4444,
    }[departmentKey] || 0x1a8aff;

    const seat = getSeatById(snapshot, getDepartmentSeatId(departmentKey));

    const kpis = safeArray(seat?.kpis);
    const kpiA = kpis[0];
    const kpiB = kpis[1];
    const kpiC = kpis[2];
    const kpiD = kpis[3];
    const kpiE = kpis[4];

    if (kpiA) group.add(buildMetricPad(kpiA.label || "KPI", kpiA.value ?? "—", -2.4, -2.25, localMetricAccent));
    if (kpiB) group.add(buildMetricPad(kpiB.label || "KPI", kpiB.value ?? "—", 0, -2.35, localMetricAccent));
    if (kpiC) group.add(buildMetricPad(kpiC.label || "KPI", kpiC.value ?? "—", 2.4, -2.25, localMetricAccent));
    if (kpiD) group.add(buildMetricPad(kpiD.label || "KPI", kpiD.value ?? "—", -1.2, 3.05, localMetricAccent));
    if (kpiE) group.add(buildMetricPad(kpiE.label || "KPI", kpiE.value ?? "—", 1.2, 3.05, localMetricAccent));

    stages.forEach((stage, index) => {
      const pos = FLOOR_STAGE_LAYOUT[index];
      if (!pos) return;

      const active =
        selectedInspectorTarget &&
        selectedInspectorTarget.kind === `${departmentKey}_stage` &&
        selectedInspectorTarget.stageId === stage.id;

      const built = buildStageNode(stage, pos, active);
      group.add(built.group);
      registerInteractive(built.mesh, {
        type: "stage",
        departmentKey,
        stageId: stage.id,
      });
    });

    flows.forEach((flow) => {
      const from = getStagePositionById(stages, flow?.fromStageId);
      const to = getStagePositionById(stages, flow?.toStageId);
      if (!from || !to) return;

      const active =
        selectedInspectorTarget &&
        selectedInspectorTarget.kind === `${departmentKey}_flow` &&
        selectedInspectorTarget.flowId === flow.id;

      group.add(buildFlowLink(flow, from, to, active));
    });

    agents.forEach((agent, index) => {
      const pos = FLOOR_AGENT_LAYOUT[index];
      if (!pos) return;

      const active =
        selectedInspectorTarget &&
        selectedInspectorTarget.kind === `${departmentKey}_agent` &&
        selectedInspectorTarget.agentId === agent.id;

      const built = buildAgentNode(agent, pos, runtimeMap[agent?.id], active);
      group.add(built.group);
      registerInteractive(built.mesh, {
        type: "agent",
        departmentKey,
        agentId: agent.id,
      });

      const hub = FLOOR_STAGE_LAYOUT[Math.min(index, Math.max(stages.length - 1, 0))];
      if (hub) {
        addLine(
          group,
          [hub[0], 0.08, hub[2] + 0.15],
          [pos[0], 0.08, pos[2] - 0.35],
          seatStateColor(agent?.state),
          0.36,
        );
      }
    });

    group.position.set(floorPosition[0], floorPosition[1], floorPosition[2]);
    parent.add(group);
    return group;
  }

  function buildBillboard(parent, snapshot) {
    const THREE = ensureThree();
    const group = new THREE.Group();
    const workspaceDisplay = getWorkspaceDisplay(snapshot);

    const pole = new THREE.Mesh(
      new THREE.CylinderGeometry(0.14, 0.14, 4.3, 24),
      new THREE.MeshStandardMaterial({ color: 0xc8d4e6, roughness: 0.82 }),
    );
    pole.position.set(0, 2.25, 0.28);
    group.add(pole);

    const arcRadius = 9.6;
    const arcAngle = Math.PI / 2.55;
    const panelHeight = 4.4;

    const shell = new THREE.Mesh(
      new THREE.CylinderGeometry(
        arcRadius,
        arcRadius,
        panelHeight,
        72,
        1,
        true,
        -arcAngle / 2,
        arcAngle,
      ),
      new THREE.MeshStandardMaterial({
        color: 0xf8fbff,
        transparent: true,
        opacity: 0.96,
        side: THREE.DoubleSide,
        metalness: 0.04,
        roughness: 0.88,
      }),
    );
    shell.position.set(0, 2.9, 2.95);
    shell.rotation.y = Math.PI;
    group.add(shell);

    const accent = new THREE.Mesh(
      new THREE.CylinderGeometry(
        arcRadius - 0.06,
        arcRadius - 0.06,
        panelHeight - 0.18,
        72,
        1,
        true,
        -arcAngle / 2,
        arcAngle,
      ),
      new THREE.MeshBasicMaterial({
        color: 0x1a8aff,
        transparent: true,
        opacity: 0.04,
        side: THREE.DoubleSide,
      }),
    );
    accent.position.set(0, 2.9, 2.84);
    accent.rotation.y = Math.PI;
    group.add(accent);

    const title = makeTextSprite(workspaceDisplay.name, {
      fontSize: 56,
      fontWeight: 900,
      color: "#f8fafc",
      heightWorld: 1.25,
    });
    title.position.set(0, 3.8, 2.4);
    group.add(title);

    const subtitle = makeTextSprite(workspaceDisplay.subtitle, {
      fontSize: 36,
      fontWeight: 800,
      color: "#93c5fd",
      heightWorld: 0.68,
    });
    subtitle.position.set(0, 3.05, 2.4);
    group.add(subtitle);

    group.position.set(0, 0, -36);
    group.rotation.y = Math.PI;
    parent.add(group);
    return group;
  }

  /* BEGIN AION O15G SNAPSHOT EXECUTIVE BOTS LOCK */
  /*
   * O15G fix:
   * - This was the remaining hard-coded visual table layer.
   * - It used to draw only CEO / AION / OpenAI.
   * - It now draws CEO, AION and actually connected provider seats from snapshot.seats.
   * - Missing providers are not faked.
   */
  function buildExecutiveBots(parent, snapshot = {}) {
    const sourceSeats = safeArray(snapshot?.seats)
      .map((seat) => {
        if (!seat || typeof seat !== "object") return null;

        const key = String(seat.key || seat.provider_id || seat.id || "").trim().toLowerCase();
        const label = String(seat.label || key || "").trim().replace(" / Google", "");
        const status = String(seat.status || "").trim().toLowerCase();
        const seatType = String(seat.seat_type || "").trim().toLowerCase();

        const alwaysOn = ["ceo", "aion"].includes(key);
        const connected = seat.connected === true || status === "connected" || status === "always_on";
        const allowed =
          alwaysOn ||
          seatType === "connected_provider" ||
          ["gemma", "openai", "gemini", "claude", "grok"].includes(key);

        if (!key || !label) return null;
        if (!allowed) return null;
        if (!alwaysOn && !connected) return null;

        return {
          key,
          label,
          color:
            key === "ceo" ? 0x60a5fa :
            key === "aion" ? 0x8b5cf6 :
            key === "gemma" ? 0x60a5fa :
            key === "openai" ? 0x22c55e :
            key === "gemini" ? 0x38bdf8 :
            key === "claude" ? 0xf59e0b :
            key === "grok" ? 0xef4444 :
            0x8b5cf6,
          scale: key === "aion" ? 0.94 : 0.9,
        };
      })
      .filter(Boolean);

    const seen = new Set();
    const seats = sourceSeats.filter((seat) => {
      if (seen.has(seat.key)) return false;
      seen.add(seat.key);
      return true;
    });

    const fallbackSeats = [
      { key: "ceo", label: "CEO", color: 0x60a5fa, scale: 0.9 },
      { key: "aion", label: "AION", color: 0x8b5cf6, scale: 0.94 },
      { key: "gemma", label: "Gemma", color: 0x60a5fa, scale: 0.9 },
    ];

    const visibleSeats = seats.length ? seats : fallbackSeats;
    const center = (visibleSeats.length - 1) / 2;
    const spacing = visibleSeats.length <= 3
      ? 6.8
      : Math.min(4.2, 15.2 / Math.max(1, visibleSeats.length - 1));

    visibleSeats.forEach((seat, index) => {
      const offset = index - center;
      const curve = center > 0 ? 1 - Math.abs(offset) / center : 1;
      const x = offset * spacing;
      const z = -24.2 - curve * 2.4;

      parent.add(buildHexFloor(seat.label, seat.color, x, z, { scale: seat.scale }));
    });
  }
  /* END AION O15G SNAPSHOT EXECUTIVE BOTS LOCK */

  

function buildBoardroomWorld(snapshot, options) {
    const THREE = ensureThree();
    const root = new THREE.Group();

    const pulse = getPulse(snapshot);
    const center = getCenter(snapshot);
    const runtime = getRuntime(snapshot);
    const activeZone = options?.activeZone || "coo";
    const selectedSeatId = options?.selectedSeatId || null;
    const teamMode = options?.boardroomTeamMode || global.__aionSpatialBoardroomTeamMode || "executive";

    const workspaceDisplay = getWorkspaceDisplay(snapshot);

    const colour = {
      marketing: 0x8b5cf6,
      sales: 0x38bdf8,
      finance: 0x22c55e,
      operations: 0xf59e0b,
      support: 0x67e8f9,
      hr: 0xfb7185,
      ceo: 0xe2e8f0,
      aion: 0x93c5fd,
      gemma: 0x60a5fa,
      openai: 0x22c55e,
      claude: 0xf59e0b,
      gemini: 0x67e8f9,
      grok: 0xa78bfa,
    };

    function panelMaterial(hex, opacity) {
      return new THREE.MeshBasicMaterial({
        color: hex,
        transparent: true,
        opacity,
        side: THREE.DoubleSide,
      });
    }

    function standardMaterial(hex, opts = {}) {
      return new THREE.MeshStandardMaterial({
        color: hex,
        roughness: opts.roughness ?? 0.62,
        metalness: opts.metalness ?? 0.12,
        transparent: opts.opacity != null,
        opacity: opts.opacity ?? 1,
        emissive: opts.emissive ?? 0x000000,
        emissiveIntensity: opts.emissiveIntensity ?? 0,
      });
    }

    function addSoftPanel(parent, title, lines, x, y, z, accent, alignRight = false) {
      const group = new THREE.Group();

      const bg = new THREE.Mesh(
        new THREE.BoxGeometry(5.6, 3.7, 0.08),
        standardMaterial(0x0f172a, {
          roughness: 0.42,
          metalness: 0.08,
          opacity: 0.78,
          emissive: 0x020617,
          emissiveIntensity: 0.1,
        }),
      );
      group.add(bg);

      const glow = new THREE.Mesh(
        new THREE.BoxGeometry(5.72, 3.82, 0.04),
        panelMaterial(accent, 0.08),
      );
      glow.position.set(0, 0, 0.055);
      group.add(glow);

      const titleSprite = makeTextSprite(title, {
        fontSize: 28,
        fontWeight: 900,
        color: "#f8fafc",
        heightWorld: 0.28,
      });
      titleSprite.position.set(0, 1.32, 0.11);
      group.add(titleSprite);

      lines.slice(0, 5).forEach((line, index) => {
        const sprite = makeTextSprite(line, {
          fontSize: 18,
          fontWeight: 750,
          color: index === 0 ? "#86efac" : "#cbd5e1",
          heightWorld: 0.18,
        });
        sprite.position.set(0, 0.78 - index * 0.46, 0.11);
        group.add(sprite);
      });

      group.position.set(x, y, z);
      group.rotation.y = alignRight ? -0.34 : 0.34;
      parent.add(group);
      return group;
    }

    function addBackScreen(parent) {
      const screen = new THREE.Mesh(
        new THREE.BoxGeometry(12.6, 6.7, 0.18),
        standardMaterial(0x07111f, {
          roughness: 0.28,
          metalness: 0.22,
          emissive: 0x0b2740,
          emissiveIntensity: 0.44,
        }),
      );
      screen.position.set(0, 6.5, -22.85);
      parent.add(screen);

      const screenGlow = new THREE.Mesh(
        new THREE.BoxGeometry(12.2, 6.25, 0.08),
        panelMaterial(0x38bdf8, 0.13),
      );
      screenGlow.position.set(0, 6.5, -22.72);
      parent.add(screenGlow);

      const title = makeTextSprite(teamMode === "board" ? "BOARD TEAM" : "BOARDROOM", {
        fontSize: 58,
        fontWeight: 950,
        color: "#f8fafc",
        heightWorld: 0.78,
      });
      title.position.set(0, 8.25, -22.55);
      parent.add(title);

      const sub = makeTextSprite(teamMode === "board" ? "TOP LINE STRATEGY MEETING" : "EXECUTIVE OPERATING TEAM", {
        fontSize: 31,
        fontWeight: 850,
        color: "#93c5fd",
        heightWorld: 0.38,
      });
      sub.position.set(0, 7.55, -22.55);
      parent.add(sub);

      const points = [
        [-4.6, 0, 0],
        [-3.4, 0.18, 0],
        [-2.4, 0.1, 0],
        [-1.2, 0.55, 0],
        [0.1, 0.24, 0],
        [1.2, 0.72, 0],
        [2.3, 0.18, 0],
        [3.2, 0.35, 0],
        [4.55, 0.62, 0],
      ].map((p) => new THREE.Vector3(p[0], p[1] + 6.05, -22.46));

      parent.add(
        new THREE.Line(
          new THREE.BufferGeometry().setFromPoints(points),
          new THREE.LineBasicMaterial({
            color: 0x60a5fa,
            transparent: true,
            opacity: 0.62,
          }),
        ),
      );
    }

    function addTable(parent) {
      // Futuristic executive table: pearl composite shell, dark smart-glass work surface,
      // cyan light channels and illuminated architectural pedestals. No ornamental logo.
      const pedestalMaterial = standardMaterial(0xdce7f1, {
        roughness: 0.24,
        metalness: 0.34,
        emissive: 0x6ecff6,
        emissiveIntensity: 0.045,
      });
      [-3.35, 3.35].forEach((x) => {
        const pedestal = new THREE.Mesh(
          new THREE.CylinderGeometry(1.18, 1.62, 1.42, 8),
          pedestalMaterial,
        );
        pedestal.scale.set(1.34, 1, 0.72);
        pedestal.rotation.y = Math.PI / 8;
        pedestal.position.set(x, -0.38, -4.6);
        pedestal.castShadow = true;
        pedestal.receiveShadow = true;
        parent.add(pedestal);

        const pedestalFoot = new THREE.Mesh(
          new THREE.CylinderGeometry(1.55, 1.72, 0.12, 8),
          standardMaterial(0x122235, {
            roughness: 0.24,
            metalness: 0.66,
            emissive: 0x22d3ee,
            emissiveIntensity: 0.16,
          }),
        );
        pedestalFoot.scale.set(1.28, 1, 0.68);
        pedestalFoot.rotation.y = Math.PI / 8;
        pedestalFoot.position.set(x, -1.08, -4.6);
        parent.add(pedestalFoot);

        const pedestalLight = new THREE.Mesh(
          new THREE.BoxGeometry(0.12, 0.96, 0.72),
          panelMaterial(0x67e8f9, 0.82),
        );
        pedestalLight.position.set(x, -0.34, -3.73);
        parent.add(pedestalLight);
      });

      const apron = new THREE.Mesh(
        new THREE.CylinderGeometry(6.72, 7.18, 0.48, 128),
        standardMaterial(0x111d2d, {
          roughness: 0.24,
          metalness: 0.58,
          emissive: 0x062c3d,
          emissiveIntensity: 0.1,
        }),
      );
      apron.scale.set(1.46, 1, 0.72);
      apron.position.set(0, 0.12, -4.6);
      apron.castShadow = true;
      parent.add(apron);

      const compositeEdge = new THREE.Mesh(
        new THREE.CylinderGeometry(6.58, 6.94, 0.24, 128),
        standardMaterial(0xd8e5ef, {
          roughness: 0.2,
          metalness: 0.3,
          emissive: 0x9bdcf4,
          emissiveIntensity: 0.045,
        }),
      );
      compositeEdge.scale.set(1.45, 1, 0.71);
      compositeEdge.position.set(0, 0.48, -4.6);
      compositeEdge.castShadow = true;
      compositeEdge.receiveShadow = true;
      parent.add(compositeEdge);

      const pearlDeck = new THREE.Mesh(
        new THREE.CylinderGeometry(6.42, 6.58, 0.13, 128),
        standardMaterial(0xf4f8fb, {
          roughness: 0.16,
          metalness: 0.24,
          emissive: 0xc9f1ff,
          emissiveIntensity: 0.055,
        }),
      );
      pearlDeck.scale.set(1.43, 1, 0.695);
      pearlDeck.position.set(0, 0.66, -4.6);
      pearlDeck.castShadow = true;
      pearlDeck.receiveShadow = true;
      parent.add(pearlDeck);

      const smartGlass = new THREE.Mesh(
        new THREE.CylinderGeometry(5.82, 5.82, 0.035, 128),
        standardMaterial(0x082338, {
          roughness: 0.12,
          metalness: 0.46,
          opacity: 0.94,
          emissive: 0x0a5d75,
          emissiveIntensity: 0.24,
        }),
      );
      smartGlass.scale.set(1.44, 1, 0.7);
      smartGlass.position.set(0, 0.75, -4.6);
      smartGlass.receiveShadow = true;
      parent.add(smartGlass);

      // Embedded data-light channels make the surface read as an active collaborative console.
      [4.72, 5.42].forEach((radius, index) => {
        const dataChannel = new THREE.Mesh(
          new THREE.TorusGeometry(radius, index === 1 ? 0.055 : 0.025, 12, 128),
          new THREE.MeshBasicMaterial({
            color: index === 1 ? 0x67e8f9 : 0x38bdf8,
            transparent: true,
            opacity: index === 1 ? 0.92 : 0.5,
            depthWrite: false,
          }),
        );
        dataChannel.scale.set(1.44, 0.7, 1);
        dataChannel.rotation.x = Math.PI / 2;
        dataChannel.position.set(0, 0.79 + index * 0.004, -4.6);
        parent.add(dataChannel);
      });

      const collaborationField = new THREE.Mesh(
        new THREE.CylinderGeometry(2.15, 2.15, 0.018, 96),
        new THREE.MeshBasicMaterial({
          color: 0x38bdf8,
          transparent: true,
          opacity: 0.1,
          depthWrite: false,
        }),
      );
      collaborationField.position.set(0, 0.81, -4.6);
      parent.add(collaborationField);

      // Team switching belongs to the interface overlay, not on the physical table.
      // This keeps the collaborative surface clear in every camera position.
    }

    function addAgentSeat(parent, key, label, role, x, z, accent, active) {
      const group = new THREE.Group();

      // AION O4D: hard visible agent anchor.
      // Always render a clean executive-agent silhouette so the boardroom never appears empty.
      // The real GLB, when visible, is added on top of this anchor.
      const agentVisibilityAnchor = new THREE.Group();
      agentVisibilityAnchor.name = `aion_visible_agent_anchor_${key}`;

      const anchorBody = new THREE.Mesh(
        new THREE.CapsuleGeometry(0.18, 0.54, 8, 16),
        new THREE.MeshStandardMaterial({
          color: 0xf8fafc,
          metalness: 0.12,
          roughness: 0.36,
          transparent: true,
          opacity: 0.92,
        }),
      );
      anchorBody.position.set(0, 0.98, 0.34);
      agentVisibilityAnchor.add(anchorBody);

      const anchorHead = new THREE.Mesh(
        new THREE.SphereGeometry(0.18, 24, 16),
        new THREE.MeshStandardMaterial({
          color: 0xffffff,
          metalness: 0.10,
          roughness: 0.30,
          transparent: true,
          opacity: 0.96,
        }),
      );
      anchorHead.scale.set(1.0, 1.08, 0.88);
      anchorHead.position.set(0, 1.48, 0.34);
      agentVisibilityAnchor.add(anchorHead);

      const anchorFace = new THREE.Mesh(
        new THREE.BoxGeometry(0.24, 0.09, 0.025),
        new THREE.MeshBasicMaterial({
          color: active ? 0xfbbf24 : accent,
          transparent: true,
          opacity: active ? 0.95 : 0.82,
          depthWrite: false,
        }),
      );
      anchorFace.position.set(0, 1.49, 0.50);
      agentVisibilityAnchor.add(anchorFace);

      const anchorGlow = new THREE.Mesh(
        new THREE.TorusGeometry(0.36, 0.018, 8, 48),
        new THREE.MeshBasicMaterial({
          color: active ? 0xfbbf24 : accent,
          transparent: true,
          opacity: active ? 0.84 : 0.38,
          depthWrite: false,
        }),
      );
      anchorGlow.rotation.x = Math.PI / 2;
      anchorGlow.position.set(0, 0.04, 0.34);
      agentVisibilityAnchor.add(anchorGlow);

      group.add(agentVisibilityAnchor);

      function addMesh(mesh, px, py, pz, sx = 1, sy = 1, sz = 1) {
        mesh.position.set(px, py, pz);
        mesh.scale.set(sx, sy, sz);
        group.add(mesh);
        return mesh;
      }

      const assetRobot = cloneAionBoardroomAsset("robot_agent");
      const assetChair = cloneAionBoardroomAsset("executive_chair");
      const assetPanel = cloneAionBoardroomAsset("hologram_panel");

      if (assetChair) {
        assetChair.position.set(0, 0.4, 0.2);
        assetChair.scale.set(1.15, 1.15, 1.15);
        group.add(assetChair);
      } else {
        // Curved executive chair fallback — softer and less block-like than the old box chair.
        const chairSeat = new THREE.Mesh(
          new THREE.CylinderGeometry(1.0, 1.12, 0.34, 40, 1, false, 0, Math.PI * 2),
          standardMaterial(0x111827, {
            roughness: 0.42,
            metalness: 0.24,
            emissive: 0x020617,
            emissiveIntensity: 0.08,
          }),
        );
        chairSeat.scale.set(0.9, 0.86, 0.62);
        addMesh(chairSeat, 0, 0.48, 0.28);

        const chairBack = new THREE.Mesh(
          new THREE.CylinderGeometry(0.78, 0.88, 1.62, 48, 1, true, Math.PI * 0.14, Math.PI * 0.72),
          standardMaterial(0x0f172a, {
            roughness: 0.38,
            metalness: 0.26,
            opacity: 0.98,
            side: THREE.DoubleSide,
            emissive: 0x020617,
            emissiveIntensity: 0.1,
          }),
        );
        chairBack.rotation.z = Math.PI / 2;
        chairBack.rotation.y = Math.PI;
        chairBack.scale.set(0.82, 0.52, 0.82);
        addMesh(chairBack, 0, 1.58, -0.34);

        const chairGlow = new THREE.Mesh(
          new THREE.TorusGeometry(0.9, 0.045, 16, 64),
          panelMaterial(accent, active ? 0.78 : 0.42),
        );
        chairGlow.rotation.x = Math.PI / 2;
        addMesh(chairGlow, 0, 0.62, 0.34, 0.86, 0.54, 0.86);
      }

      if (assetRobot) {
        normalizeAionBoardroomAgentModel(assetRobot, {
          targetHeight: active ? 1.55 : 1.42,
          zOffset: 0.0,
          name: `aion_real_agent_model_${key}`,
        });

        // Place the real imported agent directly in front of the chair, above the seat plane.
        // Keep it slightly forward so it does not hide inside the chair/table.
        assetRobot.position.set(0, 0.22, 0.34);
        assetRobot.rotation.y = 0;
        assetRobot.visible = true;
        group.add(assetRobot);

        // Keep anchor behind/under the real model as a fail-safe, but reduce its opacity.
        agentVisibilityAnchor.traverse?.((child) => {
          if (child?.material && "opacity" in child.material) {
            child.material.opacity = Math.min(child.material.opacity || 1, 0.26);
          }
        });
      } else {
        // Robot avatar fallback — rounded head, visor, shoulders, arms, chest panel.
        const lowerBody = new THREE.Mesh(
          new THREE.CapsuleGeometry(0.43, 0.58, 12, 28),
          standardMaterial(0x64748b, {
            roughness: 0.3,
            metalness: 0.38,
            emissive: accent,
            emissiveIntensity: active ? 0.18 : 0.08,
          }),
        );
        lowerBody.rotation.x = 0.04;
        addMesh(lowerBody, 0, 1.12, 0.16, 0.96, 0.94, 0.84);

        const chest = new THREE.Mesh(
          new THREE.CapsuleGeometry(0.58, 0.72, 14, 32),
          standardMaterial(0x94a3b8, {
            roughness: 0.24,
            metalness: 0.36,
            emissive: accent,
            emissiveIntensity: active ? 0.22 : 0.1,
          }),
        );
        chest.rotation.x = 0.08;
        addMesh(chest, 0, 1.48, 0.2, 0.96, 0.9, 0.72);

        const chestGlass = new THREE.Mesh(
          new THREE.BoxGeometry(0.78, 0.36, 0.055),
          standardMaterial(accent, {
            roughness: 0.15,
            metalness: 0.05,
            opacity: 0.68,
            emissive: accent,
            emissiveIntensity: active ? 0.45 : 0.22,
          }),
        );
        addMesh(chestGlass, 0, 1.45, 0.68);

        const shoulderBar = new THREE.Mesh(
          new THREE.CapsuleGeometry(0.16, 1.45, 12, 24),
          standardMaterial(0x475569, {
            roughness: 0.28,
            metalness: 0.4,
            emissive: accent,
            emissiveIntensity: active ? 0.1 : 0.045,
          }),
        );
        shoulderBar.rotation.z = Math.PI / 2;
        addMesh(shoulderBar, 0, 1.86, 0.18);

        [-0.88, 0.88].forEach((side) => {
          const upperArm = new THREE.Mesh(
            new THREE.CapsuleGeometry(0.13, 0.72, 10, 20),
            standardMaterial(0x64748b, {
              roughness: 0.3,
              metalness: 0.36,
              emissive: accent,
              emissiveIntensity: active ? 0.12 : 0.055,
            }),
          );
          upperArm.rotation.z = side * 0.22;
          addMesh(upperArm, side * 0.62, 1.62, 0.22);

          const hand = new THREE.Mesh(
            new THREE.SphereGeometry(0.14, 18, 14),
            standardMaterial(0x94a3b8, {
              roughness: 0.26,
              metalness: 0.35,
            }),
          );
          addMesh(hand, side * 0.72, 1.08, 0.46);
        });

        const neck = new THREE.Mesh(
          new THREE.CylinderGeometry(0.18, 0.2, 0.18, 24),
          standardMaterial(0x94a3b8, {
            roughness: 0.32,
            metalness: 0.35,
          }),
        );
        addMesh(neck, 0, 2.05, 0.15);

        const head = new THREE.Mesh(
          new THREE.SphereGeometry(0.56, 42, 28),
          standardMaterial(0xe2e8f0, {
            roughness: 0.22,
            metalness: 0.24,
            emissive: accent,
            emissiveIntensity: active ? 0.16 : 0.075,
          }),
        );
        head.scale.set(1.06, 0.92, 0.78);
        addMesh(head, 0, 2.36, 0.18);

        const face = new THREE.Mesh(
          new THREE.BoxGeometry(0.82, 0.28, 0.055),
          standardMaterial(0x020617, {
            roughness: 0.12,
            metalness: 0.22,
            emissive: 0x020617,
            emissiveIntensity: 0.5,
          }),
        );
        addMesh(face, 0, 2.36, 0.61);

        [-0.22, 0.22].forEach((eyeX) => {
          const eye = new THREE.Mesh(
            new THREE.SphereGeometry(0.055, 18, 12),
            panelMaterial(accent, 0.98),
          );
          addMesh(eye, eyeX, 2.38, 0.65);
        });

        const antenna = new THREE.Mesh(
          new THREE.CylinderGeometry(0.025, 0.035, 0.34, 12),
          standardMaterial(0x94a3b8, {
            roughness: 0.24,
            metalness: 0.45,
          }),
        );
        antenna.rotation.z = 0.18;
        addMesh(antenna, 0.18, 2.78, 0.11);

        const antennaGlow = new THREE.Mesh(
          new THREE.SphereGeometry(0.07, 18, 12),
          panelMaterial(accent, active ? 0.95 : 0.62),
        );
        addMesh(antennaGlow, 0.22, 2.94, 0.12);
      }

      // AION O4B: clean real GLB agent presentation.
      // The real base.glb agent is now the visual focus. Do not draw the old
      // large hologram monitor/card across the model body.
      const realAgentModelLoaded = !!assetRobot;
      // AION O4B.1: fixed stale holo interaction reference after removing body-blocking overlay.
      let holo = null;
      let seatInteractionObject = group;

      if (!realAgentModelLoaded) {
        // Legacy fallback only: if the GLB robot is unavailable, keep the old
        // holographic department card so fallback primitive agents still have a visible identity.
        holo = assetPanel;

        if (holo) {
          holo.position.set(0, 1.18, 0.92);
          holo.scale.set(1.08, 0.72, 0.72);
          group.add(holo);
        } else {
          holo = new THREE.Mesh(
            new THREE.BoxGeometry(1.72, 0.78, 0.055),
            panelMaterial(0xffffff, active ? 0.8 : 0.45),
          );
          holo.position.set(0, 1.15, 0.94);
          group.add(holo);
        }

        const initial = makeTextSprite(String(label || "?").slice(0, 1).toUpperCase(), {
          fontSize: 64,
          color: "#ffffff",
          background: "rgba(15, 23, 42, 0.08)",
          border: "rgba(255, 255, 255, 0.0)",
          widthWorld: 0.86,
          heightWorld: 0.48,
        });
        initial.position.set(0, 1.17, 1.02);
        group.add(initial);
      }

      // Clean label: move identity above the seat instead of across the agent.
      const labelPlate = makeTextSprite(label, {
        fontSize: 48,
        fontWeight: 950,
        color: "#ffffff",
        background: "rgba(7, 17, 31, 0.97)",
        border: active ? "rgba(251, 191, 36, 0.95)" : "rgba(255, 255, 255, 0.22)",
        borderWidth: active ? 5 : 3,
        widthWorld: Math.max(1.45, String(label || "").length * 0.2),
        heightWorld: 0.42,
      });
      labelPlate.position.set(0, 2.34, 0.54);
      group.add(labelPlate);

      const rolePlate = makeTextSprite(role, {
        fontSize: 23,
        fontWeight: 850,
        color: active ? "#fef3c7" : "#dbeafe",
        background: "rgba(15, 23, 42, 0.88)",
        border: "rgba(148, 163, 184, 0.3)",
        borderWidth: 2,
        widthWorld: Math.max(1.55, String(role || "").length * 0.082),
        heightWorld: 0.26,
      });
      rolePlate.position.set(0, 2.08, 0.54);
      group.add(rolePlate);

      // Invisible click target for the seat. Keeps interactivity without covering the model.
      const cleanClickTarget = new THREE.Mesh(
        new THREE.BoxGeometry(2.25, 2.35, 0.18),
        new THREE.MeshBasicMaterial({
          color: accent,
          transparent: true,
          opacity: 0.001,
          depthWrite: false,
        }),
      );
      cleanClickTarget.position.set(0, 1.15, 0.42);
      cleanClickTarget.name = `aion_clean_agent_click_target_${key}`;
      group.add(cleanClickTarget);
      seatInteractionObject = cleanClickTarget;

      // Subtle base highlight only. No body-blocking monitor panel.
      const cleanBaseRing = new THREE.Mesh(
        new THREE.TorusGeometry(active ? 0.94 : 0.78, 0.026, 10, 72),
        new THREE.MeshBasicMaterial({
          color: active ? 0xfbbf24 : accent,
          transparent: true,
          opacity: active ? 0.92 : 0.28,
          depthWrite: false,
        }),
      );
      cleanBaseRing.rotation.x = Math.PI / 2;
      cleanBaseRing.position.set(0, 0.055, 0.18);
      group.add(cleanBaseRing);

      const seatId = getDepartmentSeatId(key);
      if (seatId) {
        // AION O4B.2: registerInteractive uses clean click target, not removed holo overlay.
        registerInteractive(seatInteractionObject, {
          type: "seat",
          departmentKey: key,
          seatId,
        });
      }

      return group;
    }


    // AION O4E: forced visible executive seat safety layer.
    // This renders clean visible agent seats even if the normal seat list is filtered,
    // hidden, or GLB placement fails. It is intentionally simple and demo-safe.
    function addForcedVisibleExecutiveSeats(parent, options = {}) {
      if (!global.__aionO4FRealRobotAgentSeatDebug) {
        global.__aionO4FRealRobotAgentSeatDebug = true;
        console.info("[AION] O4F real robot_agent.glb seat renderer active");
      }

      const forcedSeats = [
        ["marketing", "Marketing", "Brand & Growth", -7.8, -8.0, 0x38bdf8],
        ["sales", "Sales", "Revenue & Pipeline", -4.7, -9.0, 0x38bdf8],
        ["finance", "Finance", "Financial Stewardship", -1.55, -9.25, 0x38bdf8],
        ["operations", "Operations", "Process & Efficiency", 1.55, -9.25, 0xfbbf24],
        ["support", "Support", "Customer Success", 4.7, -9.0, 0x38bdf8],
        ["hr", "HR", "People & Culture", 7.8, -8.0, 0x38bdf8],
      ];

      const allowedForcedDepartments =
        Array.isArray(options.visibleDepartments) && options.visibleDepartments.length
          ? new Set(
              options.visibleDepartments
                .map((item) => String(item || "").trim().toLowerCase())
                .filter(Boolean),
            )
          : null;

      /* BEGIN AION O16E DEPARTMENT 121 FORCED VISIBLE CENTER AGENT LOCK */
      const isDepartment121ForcedSeatO16E =
        String(options?.cameraMode || "").endsWith("_121") ||
        String(options?.boardroomTeamMode || "").endsWith("_121");
      /* END AION O16E DEPARTMENT 121 FORCED VISIBLE CENTER AGENT LOCK */

      forcedSeats
        .filter(([key]) => !allowedForcedDepartments || allowedForcedDepartments.has(String(key || "").toLowerCase()))
        .forEach(([key, label, role, x, z, accent]) => {
        const group = new THREE.Group();
        group.name = `aion_o4e_forced_visible_seat_${key}`;
        const seatX = isDepartment121ForcedSeatO16E ? 0 : x;
        const seatZ = isDepartment121ForcedSeatO16E ? -8.15 : z;
        group.position.set(seatX, 0.08, seatZ);

        const chair = new THREE.Group();

        const chairSeat = new THREE.Mesh(
          new THREE.BoxGeometry(1.14, 0.16, 0.82),
          new THREE.MeshStandardMaterial({
            color: 0xf8fafc,
            metalness: 0.18,
            roughness: 0.34,
            transparent: true,
            opacity: 0.88,
          }),
        );
        chairSeat.position.set(0, 0.42, 0.16);
        chair.add(chairSeat);

        const chairBack = new THREE.Mesh(
          new THREE.BoxGeometry(1.04, 1.08, 0.14),
          new THREE.MeshStandardMaterial({
            color: 0xe5edf6,
            metalness: 0.12,
            roughness: 0.38,
            transparent: true,
            opacity: 0.82,
          }),
        );
        chairBack.position.set(0, 1.02, -0.28);
        chair.add(chairBack);

        group.add(chair);

        // AION O4F: forced visible seats use real robot_agent GLB.
        // Prefer Kevin's Desktop/base.glb installed as robot_agent.glb.
        // Fall back to the simple white anchor only if the real GLB is unavailable.
        const realSeatRobot = cloneAionBoardroomAsset("robot_agent");

        if (realSeatRobot) {
          normalizeAionBoardroomAgentModel(realSeatRobot, {
            targetHeight: key === "operations" ? 1.62 : 1.48,
            zOffset: 0.0,
            name: `aion_o4f_real_robot_agent_${key}`,
          });

          realSeatRobot.position.x += 0;
          realSeatRobot.position.y += 0.20;
          realSeatRobot.position.z += 0.22;
          realSeatRobot.rotation.y = 0;
          realSeatRobot.visible = true;

          realSeatRobot.traverse?.((child) => {
            if (child?.isMesh) {
              child.visible = true;
              child.castShadow = true;
              child.receiveShadow = true;
              if (child.material) {
                child.material.depthTest = true;
                child.material.depthWrite = true;
                child.material.transparent = child.material.transparent === true;
              }
            }
          });

          group.add(realSeatRobot);
          group.userData.realRobotAgentLoaded = true;
        } else {
          const agent = new THREE.Group();
          agent.name = `aion_o4f_fallback_visible_agent_${key}`;

          const body = new THREE.Mesh(
            new THREE.CapsuleGeometry(0.18, 0.52, 8, 18),
            new THREE.MeshStandardMaterial({
              color: 0xffffff,
              metalness: 0.10,
              roughness: 0.30,
            }),
          );
          body.position.set(0, 0.98, 0.22);
          agent.add(body);

          const head = new THREE.Mesh(
            new THREE.SphereGeometry(0.21, 28, 18),
            new THREE.MeshStandardMaterial({
              color: 0x090b0f,
              metalness: 0.48,
              roughness: 0.2,
            }),
          );
          head.scale.set(0.94, 1.08, 0.84);
          head.position.set(0, 1.48, 0.22);
          agent.add(head);

          const shoulderL = new THREE.Mesh(
            new THREE.SphereGeometry(0.10, 16, 10),
            new THREE.MeshStandardMaterial({ color: 0xdbeafe, metalness: 0.16, roughness: 0.36 }),
          );
          shoulderL.position.set(-0.25, 1.12, 0.20);
          agent.add(shoulderL);

          const shoulderR = shoulderL.clone();
          shoulderR.position.x = 0.25;
          agent.add(shoulderR);

          group.add(agent);
          group.userData.realRobotAgentLoaded = false;
        }

        addAionSyntheticSeatIdentityMask(group, {
          key,
          accent: 0xf2af0d,
          // Anchored to the authored visor centre after robot_agent.glb is
          // normalised into this seat.  The former generic head anchor placed
          // the eyes above and in front of the real visor.
          y: key === "operations" ? 1.4 : 1.225,
          z: 0.11,
          scale: key === "operations" ? 1.03 : 1,
        });

        const ring = new THREE.Mesh(
          new THREE.TorusGeometry(0.62, 0.024, 8, 54),
          new THREE.MeshBasicMaterial({
            color: accent,
            transparent: true,
            opacity: key === "operations" ? 0.95 : 0.42,
            depthWrite: false,
          }),
        );
        ring.rotation.x = Math.PI / 2;
        ring.position.set(0, 0.035, 0.16);
        group.add(ring);

        // CLEAN OVERHEAD DEPARTMENT SIGN: keep the full role in the agent's
        // conversation metadata, but show only the department name in the room.
        // A compact single-line sign remains clear above each executive without
        // restoring the former secondary role strip or obscuring the agent.
        const labelPlate = makeTextSprite(label, {
          fontSize: key === "operations" ? 48 : 44,
          fontWeight: 950,
          color: "#ffffff",
          background: "rgba(7, 17, 31, 0.97)",
          border: key === "operations" ? "rgba(251, 191, 36, 0.95)" : "rgba(255, 255, 255, 0.2)",
          borderWidth: key === "operations" ? 5 : 3,
          widthWorld: Math.max(1.5, String(label).length * 0.2),
          heightWorld: key === "operations" ? 0.42 : 0.38,
        });
        labelPlate.position.set(0, 2.06, 0.34);
        group.add(labelPlate);

        const executiveConversationTarget = new THREE.Mesh(
          new THREE.BoxGeometry(2.3, 2.45, 0.28),
          new THREE.MeshBasicMaterial({
            color: accent,
            transparent: true,
            opacity: 0.001,
            depthWrite: false,
          }),
        );
        executiveConversationTarget.position.set(0, 1.18, 0.34);
        executiveConversationTarget.name = `aion_executive_conversation_target_${key}`;
        group.add(executiveConversationTarget);
        registerInteractive(executiveConversationTarget, {
          type: "seat",
          departmentKey: key,
          seatId: getDepartmentSeatId(key) || `seat_${key}`,
          seatLabel: label,
          seatRole: role,
          teamMode: "executive",
        });

        parent.add(group);
      });

      parent.userData = parent.userData || {};
      parent.userData.aionO4EForcedVisibleSeats = true;
    }


    // AION O4G: forced visible board team seat safety layer.
    // Mirrors O4F executive visible seats, but for Board Team mode.
    function addForcedVisibleBoardTeamSeats(parent, options = {}) {
      /* BEGIN AION O15H.3 BOARD TEAM TABLE SNAPSHOT CALL PATH LOCK */
      /* BEGIN AION O15I BOARD TEAM GLOBAL SNAPSHOT FALLBACK LOCK */
      /*
       * O15I fix:
       * - O15H.3 proved this renderer path can receive an empty local snapshot.
       * - The app-level getBoardroomSnapshot() already contains the live Vault seats.
       * - Prefer the first snapshot source that actually has seats.
       */
      const localOptionSnapshotO15I =
        options && options.snapshot && typeof options.snapshot === "object"
          ? options.snapshot
          : {};
      const localRenderSnapshotO15I =
        snapshot && typeof snapshot === "object"
          ? snapshot
          : {};
      let globalBoardSnapshotO15I = {};
      try {
        globalBoardSnapshotO15I =
          typeof global.getBoardroomSnapshot === "function"
            ? global.getBoardroomSnapshot()
            : {};
      } catch {
        globalBoardSnapshotO15I = {};
      }

      const boardSnapshotO15H3 =
        safeArray(globalBoardSnapshotO15I?.seats).length
          ? globalBoardSnapshotO15I
          : safeArray(localOptionSnapshotO15I?.seats).length
            ? localOptionSnapshotO15I
            : safeArray(localRenderSnapshotO15I?.seats).length
              ? localRenderSnapshotO15I
              : localOptionSnapshotO15I || localRenderSnapshotO15I || {};
      /* END AION O15I BOARD TEAM GLOBAL SNAPSHOT FALLBACK LOCK */
      /* END AION O15H.3 BOARD TEAM TABLE SNAPSHOT CALL PATH LOCK */

      const aionO4GBoardTeamSeatSafetyLayer = "AION O4G: forced visible board team seat safety layer";
      /* BEGIN AION O15F REAL 3D BOARDROOM PROVIDER SEATS LOCK */
      /*
       * O15F fix:
       * - O4G used to hard-code only CEO / AION / OpenAI.
       * - The real 3D board table must now use snapshot.seats.
       * - Only always-on core seats and actually connected provider seats render.
       * - Missing Claude/Grok/etc must not be faked.
       */
      const liveBoardSeatsO15F = safeArray(boardSnapshotO15H3?.seats)
        .map((seat) => {
          if (!seat || typeof seat !== "object") return null;

          const key = String(seat.key || seat.provider_id || seat.id || "").trim().toLowerCase();
          const label = String(seat.label || key || "").trim().replace(" / Google", "");
          const status = String(seat.status || "").trim().toLowerCase();
          const seatType = String(seat.seat_type || "").trim().toLowerCase();
          const alwaysOn = ["ceo", "aion"].includes(key);
          const connected = seat.connected === true || status === "connected" || status === "always_on";
          const allowedSeatType =
            ["founder", "orchestrator", "connected_provider"].includes(seatType) ||
            alwaysOn;

          if (!key || !label) return null;
          if (!allowedSeatType) return null;
          if (!alwaysOn && !connected) return null;

          return {
            key,
            label,
            role:
              seat.role ||
              seat.stance ||
              (key === "ceo"
                ? "Strategic Leadership"
                : key === "aion"
                  ? "Core Intelligence"
                  : "Connected Provider"),
            accent:
              colour[key] ||
              (key === "gemini"
                ? 0x38bdf8
                : key === "gemma"
                  ? 0x60a5fa
                  : key === "openai"
                    ? 0x22c55e
                    : 0x8b5cf6),
          };
        })
        .filter(Boolean);

      const seenBoardSeatKeysO15F = new Set();
      const uniqueBoardSeatsO15F = liveBoardSeatsO15F.filter((seat) => {
        if (seenBoardSeatKeysO15F.has(seat.key)) return false;
        seenBoardSeatKeysO15F.add(seat.key);
        return true;
      });

      const fallbackBoardSeatsO15F = [
        { key: "ceo", label: "CEO", role: "Strategic Leadership", accent: 0x60a5fa },
        { key: "aion", label: "AION", role: "Core Intelligence", accent: 0x8b5cf6 },
        { key: "gemma", label: "Gemma", role: "Local Default Reasoning", accent: 0x60a5fa },
      ];

      const sourceBoardSeatsO15F = uniqueBoardSeatsO15F.length
        ? uniqueBoardSeatsO15F
        : fallbackBoardSeatsO15F;

      
      global.__debugAionO15H3BoardTeamTableSnapshot = {
        snapshotSeatCount: safeArray(boardSnapshotO15H3?.seats).length,
        globalSnapshotSeatCount: safeArray(globalBoardSnapshotO15I?.seats).length,
        optionSnapshotSeatCount: safeArray(localOptionSnapshotO15I?.seats).length,
        renderSnapshotSeatCount: safeArray(localRenderSnapshotO15I?.seats).length,
        liveBoardSeatCount: liveBoardSeatsO15F.length,
        sourceBoardSeatCount: sourceBoardSeatsO15F.length,
        usedFallback: liveBoardSeatsO15F.length === 0,
        labels: sourceBoardSeatsO15F.map((seat) => seat.label || seat[1] || seat.id || seat.key),
      };

      const boardSeatCenterO15F = (sourceBoardSeatsO15F.length - 1) / 2;
      const boardSeatSpacingO15F =
        sourceBoardSeatsO15F.length <= 3
          ? 5.6
          : Math.min(3.2, 13.6 / Math.max(1, sourceBoardSeatsO15F.length - 1));

      const boardSeats = sourceBoardSeatsO15F.map((seat, index) => {
        const offset = index - boardSeatCenterO15F;
        const curve = boardSeatCenterO15F > 0
          ? 1 - Math.abs(offset) / boardSeatCenterO15F
          : 1;

        return [
          seat.key,
          seat.label,
          seat.role,
          offset * boardSeatSpacingO15F,
          -8.72 - curve * 0.48,
          seat.accent,
        ];
      });
      /* END AION O15F REAL 3D BOARDROOM PROVIDER SEATS LOCK */

      if (!global.__aionO4GBoardTeamSeatDebug) {
        global.__aionO4GBoardTeamSeatDebug = true;
        console.info("[AION] O4G board team robot_agent.glb seat renderer active");
      }

      boardSeats.forEach(([key, label, role, x, z, accent]) => {
        const group = new THREE.Group();
        group.name = `aion_o4g_forced_visible_board_seat_${key}`;
        group.position.set(x, 0.08, z);

        const chairSeat = new THREE.Mesh(
          new THREE.BoxGeometry(1.24, 0.18, 0.86),
          new THREE.MeshStandardMaterial({
            color: 0xf8fafc,
            metalness: 0.18,
            roughness: 0.34,
            transparent: true,
            opacity: 0.88,
          }),
        );
        chairSeat.position.set(0, 0.42, 0.16);
        group.add(chairSeat);

        const chairBack = new THREE.Mesh(
          new THREE.BoxGeometry(1.08, 1.12, 0.14),
          new THREE.MeshStandardMaterial({
            color: 0xe5edf6,
            metalness: 0.12,
            roughness: 0.38,
            transparent: true,
            opacity: 0.82,
          }),
        );
        chairBack.position.set(0, 1.04, -0.28);
        group.add(chairBack);

        const realBoardRobot = cloneAionBoardroomAsset("robot_agent");

        if (realBoardRobot) {
          normalizeAionBoardroomAgentModel(realBoardRobot, {
            targetHeight: key === "aion" ? 1.68 : 1.52,
            zOffset: 0.0,
            name: `aion_o4g_real_board_robot_agent_${key}`,
          });

          realBoardRobot.position.x += 0;
          realBoardRobot.position.y += 0.20;
          realBoardRobot.position.z += 0.22;
          realBoardRobot.rotation.y = 0;
          realBoardRobot.visible = true;

          realBoardRobot.traverse?.((child) => {
            if (child?.isMesh) {
              child.visible = true;
              child.castShadow = true;
              child.receiveShadow = true;
              if (child.material) {
                child.material.depthTest = true;
                child.material.depthWrite = true;
                child.material.transparent = child.material.transparent === true;
              }
            }
          });

          group.add(realBoardRobot);
          group.userData.realBoardRobotAgentLoaded = true;
        } else {
          const fallback = new THREE.Group();
          fallback.name = `aion_o4g_fallback_board_agent_${key}`;

          const body = new THREE.Mesh(
            new THREE.CapsuleGeometry(0.20, 0.58, 8, 18),
            new THREE.MeshStandardMaterial({
              color: 0xffffff,
              metalness: 0.10,
              roughness: 0.30,
            }),
          );
          body.position.set(0, 1.0, 0.22);
          fallback.add(body);

          const head = new THREE.Mesh(
            new THREE.SphereGeometry(0.22, 28, 18),
            new THREE.MeshStandardMaterial({
              color: 0x090b0f,
              metalness: 0.48,
              roughness: 0.2,
            }),
          );
          head.scale.set(0.94, 1.08, 0.84);
          head.position.set(0, 1.53, 0.22);
          fallback.add(head);

          group.add(fallback);
          group.userData.realBoardRobotAgentLoaded = false;
        }

        addAionSyntheticSeatIdentityMask(group, {
          key,
          accent,
          // Board seats use a slightly taller normalisation than Executive
          // seats, so their authored visor centre is correspondingly higher.
          y: key === "aion" ? 1.475 : 1.275,
          z: 0.11,
          scale: key === "aion" ? 1.05 : 1,
        });

        const ring = new THREE.Mesh(
          new THREE.TorusGeometry(key === "aion" ? 0.76 : 0.66, 0.026, 8, 64),
          new THREE.MeshBasicMaterial({
            color: accent,
            transparent: true,
            opacity: key === "aion" ? 0.90 : 0.46,
            depthWrite: false,
          }),
        );
        ring.rotation.x = Math.PI / 2;
        ring.position.set(0, 0.035, 0.16);
        group.add(ring);

        /* CLEAN BOARD MEMBER NAME SIGN
         * Keep the room legible at a glance: one compact, high-contrast name
         * sign above each member. Role and connection details remain attached
         * to the interactive seat instead of becoming stacked scenery.
         */
        const labelPlate = makeTextSprite(label, {
          fontSize: key === "aion" ? 50 : 46,
          fontWeight: 950,
          color: "#ffffff",
          background: "rgba(7, 17, 31, 0.97)",
          border: key === "aion" ? "rgba(139, 92, 246, 0.95)" : "rgba(255, 255, 255, 0.24)",
          borderWidth: key === "aion" ? 4 : 2,
          widthWorld: Math.max(1.18, String(label).length * 0.18),
          heightWorld: 0.4,
        });
        labelPlate.position.set(0, 2.1, 0.36);
        group.add(labelPlate);

        /* BEGIN AION O15J REAL AGENT LIVE STATUS BADGE LOCK */
        /*
         * O15J:
         * - The real table agents are now the source of truth.
         * - Keep connection state on the actual interactive 3D agent, without
         *   adding a second visual badge beneath the clean name sign.
         */
        const liveStatusText =
          key === "ceo" || key === "aion"
            ? "ALWAYS ON"
            : "LIVE";

        group.userData.liveStatusText = liveStatusText;
        group.userData.seatRole = role;
        /* END AION O15J REAL AGENT LIVE STATUS BADGE LOCK */

        const boardConversationTarget = new THREE.Mesh(
          new THREE.BoxGeometry(2.3, 2.45, 0.28),
          new THREE.MeshBasicMaterial({
            color: accent,
            transparent: true,
            opacity: 0.001,
            depthWrite: false,
          }),
        );
        boardConversationTarget.position.set(0, 1.18, 0.34);
        boardConversationTarget.name = `aion_board_conversation_target_${key}`;
        group.add(boardConversationTarget);
        registerInteractive(boardConversationTarget, {
          type: "seat",
          departmentKey: key,
          seatId: `seat_provider_${key}`,
          seatLabel: label,
          seatRole: role,
          providerId: key,
          teamMode: "board",
        });

        parent.add(group);
      });

      parent.userData = parent.userData || {};
      parent.userData.aionO4GForcedVisibleBoardSeats = true;
    }

    function seatArc(index, total, radius = 11.8, centerZ = -4.55, startDeg = 158, endDeg = 22) {
      const t = total <= 1 ? 0.5 : index / (total - 1);
      const deg = startDeg + (endDeg - startDeg) * t;
      const rad = (deg * Math.PI) / 180;
      return {
        x: Math.cos(rad) * radius,
        z: centerZ - Math.sin(rad) * radius * 0.7,
      };
    }

    addBackScreen(root);
    addTable(root);

    /* SINGLE CENTRAL BOARDROOM DISPLAY
     * The two angled side displays were unreadable from the seated camera and
     * made the room feel like a monitor showroom. Live context remains in the
     * terminal below; the room keeps one clear meeting focal point.
     */

    const executiveSeats = [
      ["marketing", "Marketing", "Brand & Growth"],
      ["sales", "Sales", "Revenue & Pipeline"],
      ["finance", "Finance", "Financial Stewardship"],
      ["operations", "Operations", "Process & Efficiency"],
      ["support", "Support", "Customer Success"],
      ["hr", "HR", "People & Culture"],
    ];

    /* BEGIN AION O15F BOARD MODE SNAPSHOT SEATS ONLY LOCK */
    /*
     * Board mode must not fake missing providers.
     * It renders founder/orchestrator plus connected_provider seats from snapshot.seats.
     */
    const boardSeatsFromSnapshotO15F = safeArray(snapshot?.seats)
      .map((seat) => {
        if (!seat || typeof seat !== "object") return null;

        const key = String(seat.key || seat.provider_id || seat.id || "").trim().toLowerCase();
        const label = String(seat.label || key || "").trim().replace(" / Google", "");
        const status = String(seat.status || "").trim().toLowerCase();
        const seatType = String(seat.seat_type || "").trim().toLowerCase();
        const alwaysOn = ["ceo", "aion"].includes(key);
        const connected = seat.connected === true || status === "connected" || status === "always_on";
        const allowedSeatType =
          ["founder", "orchestrator", "connected_provider"].includes(seatType) ||
          alwaysOn;

        if (!key || !label) return null;
        if (!allowedSeatType) return null;
        if (!alwaysOn && !connected) return null;

        return [
          key,
          label,
          seat.role ||
            seat.stance ||
            (key === "ceo"
              ? "Strategic Leadership"
              : key === "aion"
                ? "Business Brain"
                : "Connected Provider"),
        ];
      })
      .filter(Boolean);

    const seenBoardModeSeatKeysO15F = new Set();
    const uniqueBoardModeSeatsO15F = boardSeatsFromSnapshotO15F.filter((seat) => {
      const key = String(seat[0] || "");
      if (seenBoardModeSeatKeysO15F.has(key)) return false;
      seenBoardModeSeatKeysO15F.add(key);
      return true;
    });

    const boardSeats = uniqueBoardModeSeatsO15F.length
      ? uniqueBoardModeSeatsO15F
      : [
          ["ceo", "CEO", "Strategic Leadership"],
          ["aion", "AION", "Business Brain"],
          ["gemma", "Gemma", "Local Default Reasoning"],
        ];

    let seatsToRender = teamMode === "board" ? boardSeats : executiveSeats;
    /* END AION O15F BOARD MODE SNAPSHOT SEATS ONLY LOCK */

    /*
     * Department 1:1 mode.
     * Same spatial boardroom renderer, but only the active department director is visible.
     */
    const department121Match = String(teamMode || "").match(/^([a-z0-9_]+)_121$/);
    /* BEGIN AION O16C DEPARTMENT 121 CAMERA CENTER AGENT LOCK */
    const isDepartment121ModeO16C = Boolean(department121Match);
    /* END AION O16C DEPARTMENT 121 CAMERA CENTER AGENT LOCK */
    if (department121Match) {
      const department121Key = department121Match[1];
      const department121Labels = {
        marketing: ["Marketing", "Brand & Growth"],
        sales: ["Sales", "Revenue & Pipeline"],
        finance: ["Finance", "Financial Truth Layer"],
        operations: ["Operations", "Process & Efficiency"],
        support: ["Support", "Customer Success"],
        hr: ["HR", "People & Culture"],
      };
      const department121Label = department121Labels[department121Key] || [
        department121Key.charAt(0).toUpperCase() + department121Key.slice(1),
        "Department Director",
      ];
      seatsToRender = [[department121Key, department121Label[0], department121Label[1]]];
    }

    if (Array.isArray(options.visibleDepartments) && options.visibleDepartments.length) {
      const allowedDepartments = new Set(
        options.visibleDepartments
          .map((item) => String(item || "").trim().toLowerCase())
          .filter(Boolean),
      );
      seatsToRender = seatsToRender.filter(([key]) => allowedDepartments.has(String(key || "").toLowerCase()));
    }

    seatsToRender.forEach(([key, label, role], index) => {
      const pos = isDepartment121ModeO16C
        ? { x: 0, z: -40 }
        : seatArc(index, seatsToRender.length);
      const seatId = getDepartmentSeatId(key);
      const active = activeZone === key || selectedSeatId === seatId || isDepartment121ModeO16C;
      addAgentSeat(root, key, label, role, pos.x, pos.z, colour[key] || 0x60a5fa, active);
    });

    if (teamMode !== "board") {
      addForcedVisibleExecutiveSeats(root, options || {});
    } else if (teamMode === "board") {
      addForcedVisibleBoardTeamSeats(root, options || {});
    }


    const queue = makeTextSprite(
      teamMode === "board"
        ? "BOARD MODE · TOP LINE STRATEGY"
        : String(teamMode || "").endsWith("_121")
          ? "1:1 DEPARTMENT ROOM · SAFE EXECUTION"
          : "EXECUTIVE MODE · SAFE EXECUTION",
      {
        fontSize: 24,
        fontWeight: 900,
        color: "#fed7aa",
        background: "rgba(15,23,42,0.72)",
        paddingX: 28,
        paddingY: 14,
        heightWorld: 0.32,
      },
    );
    queue.position.set(7.7, 2.25, 3.0);
    root.add(queue);

    return root;
  }

  

function buildSceneShell(scene) {
    const THREE = ensureThree();

    scene.background = new THREE.Color("#cbd5e1");
    scene.fog = new THREE.Fog("#cbd5e1", 30, 104);

    const ambient = new THREE.AmbientLight(0xffffff, 0.54);
    scene.add(ambient);

    const hemi = new THREE.HemisphereLight(0xdbeafe, 0x1f2937, 0.76);
    scene.add(hemi);

    const key = new THREE.DirectionalLight(0xffffff, 1.55);
    key.position.set(-9, 18, 12);
    key.castShadow = true;
    key.shadow.mapSize.width = 2048;
    key.shadow.mapSize.height = 2048;
    key.shadow.camera.near = 0.5;
    key.shadow.camera.far = 80;
    key.shadow.camera.left = -28;
    key.shadow.camera.right = 28;
    key.shadow.camera.top = 28;
    key.shadow.camera.bottom = -28;
    scene.add(key);

    const warm = new THREE.DirectionalLight(0xffdcc2, 1.05);
    warm.position.set(12, 8, 10);
    scene.add(warm);

    const cool = new THREE.DirectionalLight(0xaed8ff, 0.78);
    cool.position.set(0, 7, -18);
    scene.add(cool);

    const rim = new THREE.DirectionalLight(0x7dd3fc, 0.86);
    rim.position.set(0, 6, 16);
    scene.add(rim);

    const tableSpot = new THREE.SpotLight(0x93c5fd, 1.35, 48, Math.PI * 0.21, 0.58, 1.6);
    tableSpot.position.set(0, 12.5, 2.5);
    tableSpot.target.position.set(0, 0.5, -5);
    tableSpot.castShadow = true;
    tableSpot.shadow.mapSize.width = 2048;
    tableSpot.shadow.mapSize.height = 2048;
    scene.add(tableSpot);
    scene.add(tableSpot.target);

    const agentRimLeft = new THREE.PointLight(0x60a5fa, 1.25, 26, 1.45);
    agentRimLeft.position.set(-9.5, 4.2, -8.5);
    scene.add(agentRimLeft);

    const agentRimRight = new THREE.PointLight(0x67e8f9, 1.15, 26, 1.45);
    agentRimRight.position.set(9.5, 4.2, -8.5);
    scene.add(agentRimRight);

    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(96, 96),
      new THREE.MeshStandardMaterial({
        color: 0xdbe3ee,
        roughness: 0.58,
        metalness: 0.08,
      }),
    );
    floor.rotation.x = -Math.PI / 2;
    floor.position.set(0, -0.98, 0);
    scene.add(floor);

    const floorGlow = new THREE.Mesh(
      new THREE.PlaneGeometry(42, 28),
      new THREE.MeshBasicMaterial({
        color: 0xffffff,
        transparent: true,
        opacity: 0.18,
        side: THREE.DoubleSide,
      }),
    );
    floorGlow.rotation.x = -Math.PI / 2;
    floorGlow.position.set(0, -0.955, -8);
    scene.add(floorGlow);

    const grid = new THREE.GridHelper(
      96,
      88,
      new THREE.Color("#c8d5e4"),
      new THREE.Color("#edf3f9"),
    );
    grid.position.set(0, -0.94, 0);
    grid.material.transparent = true;
    grid.material.opacity = 0.26;
    scene.add(grid);

    const backWall = new THREE.Mesh(
      new THREE.PlaneGeometry(52, 24),
      new THREE.MeshStandardMaterial({
        color: 0xf8fafc,
        roughness: 0.72,
        metalness: 0.02,
      }),
    );
    backWall.position.set(0, 7.7, -25.2);
    scene.add(backWall);

    const rearShadow = new THREE.Mesh(
      new THREE.PlaneGeometry(34, 13),
      new THREE.MeshBasicMaterial({
        color: 0x163247,
        transparent: true,
        opacity: 0.085,
        side: THREE.DoubleSide,
      }),
    );
    rearShadow.position.set(0, 6.6, -25.05);
    scene.add(rearShadow);

    /* FUTURISTIC ARCHITECTURAL BACKDROP
     * A dimensional pearl-metal feature wall, recessed bays and cyan light
     * channels replace the former empty white wall and floating side TVs.
     */
    const featureWall = new THREE.Mesh(
      new THREE.BoxGeometry(35.5, 14.2, 0.38),
      new THREE.MeshStandardMaterial({
        color: 0xe3ebf2,
        roughness: 0.3,
        metalness: 0.22,
        emissive: 0x8acbe4,
        emissiveIntensity: 0.025,
      }),
    );
    featureWall.position.set(0, 7.25, -24.82);
    featureWall.receiveShadow = true;
    scene.add(featureWall);

    [-15.2, -10.2, -5.15, 5.15, 10.2, 15.2].forEach((x, index) => {
      const architecturalPanel = new THREE.Mesh(
        new THREE.BoxGeometry(index === 2 || index === 3 ? 4.35 : 4.5, 11.65, 0.16),
        new THREE.MeshStandardMaterial({
          color: index % 2 === 0 ? 0xf3f7fa : 0xd8e3eb,
          roughness: 0.38,
          metalness: 0.16,
          emissive: 0x9ddcf0,
          emissiveIntensity: index % 2 === 0 ? 0.018 : 0.035,
        }),
      );
      architecturalPanel.position.set(x, 7.2, -24.53);
      architecturalPanel.receiveShadow = true;
      scene.add(architecturalPanel);
    });

    [-17.6, -12.7, -7.65, 7.65, 12.7, 17.6].forEach((x) => {
      const lightFin = new THREE.Mesh(
        new THREE.BoxGeometry(0.085, 11.9, 0.055),
        new THREE.MeshBasicMaterial({
          color: 0x67e8f9,
          transparent: true,
          opacity: 0.58,
        }),
      );
      lightFin.position.set(x, 7.2, -24.38);
      scene.add(lightFin);
    });

    [1.35, 13.05].forEach((y) => {
      const horizonLight = new THREE.Mesh(
        new THREE.BoxGeometry(35.2, 0.075, 0.055),
        new THREE.MeshBasicMaterial({
          color: 0x93c5fd,
          transparent: true,
          opacity: 0.42,
        }),
      );
      horizonLight.position.set(0, y, -24.36);
      scene.add(horizonLight);
    });

    const leftWall = new THREE.Mesh(
      new THREE.PlaneGeometry(30, 22),
      new THREE.MeshStandardMaterial({
        color: 0xeef4fb,
        roughness: 0.82,
        metalness: 0.02,
        transparent: true,
        opacity: 0.92,
        side: THREE.DoubleSide,
      }),
    );
    leftWall.position.set(-25.5, 7.2, -13);
    leftWall.rotation.y = Math.PI * 0.18;
    scene.add(leftWall);

    const rightWall = leftWall.clone();
    rightWall.position.set(25.5, 7.2, -13);
    rightWall.rotation.y = -Math.PI * 0.18;
    scene.add(rightWall);

    const ceiling = new THREE.Mesh(
      new THREE.PlaneGeometry(58, 36),
      new THREE.MeshStandardMaterial({
        color: 0xf8fafc,
        roughness: 0.86,
        metalness: 0.03,
      }),
    );
    ceiling.rotation.x = Math.PI / 2;
    ceiling.position.set(0, 16.2, -5);
    scene.add(ceiling);

    const ceilingGlow = new THREE.Mesh(
      new THREE.TorusGeometry(9.8, 0.16, 24, 128),
      new THREE.MeshBasicMaterial({
        color: 0xffffff,
        transparent: true,
        opacity: 0.9,
      }),
    );
    ceilingGlow.rotation.x = Math.PI / 2;
    ceilingGlow.position.set(0, 15.95, -6.2);
    scene.add(ceilingGlow);

    const ceilingHalo = new THREE.Mesh(
      new THREE.TorusGeometry(10.6, 0.035, 16, 128),
      new THREE.MeshBasicMaterial({
        color: 0x93c5fd,
        transparent: true,
        opacity: 0.28,
      }),
    );
    ceilingHalo.rotation.x = Math.PI / 2;
    ceilingHalo.position.set(0, 15.9, -6.2);
    scene.add(ceilingHalo);

    [
      [-21.5, 6.5, -15.7, 0.28],
      [-18.2, 6.2, -13.2, 0.18],
      [21.5, 6.5, -15.7, -0.28],
      [18.2, 6.2, -13.2, -0.18],
    ].forEach(([x, y, z, rot]) => {
      const windowPanel = new THREE.Mesh(
        new THREE.PlaneGeometry(9.8, 11.4),
        new THREE.MeshBasicMaterial({
          color: 0xdbeafe,
          transparent: true,
          opacity: 0.32,
          side: THREE.DoubleSide,
        }),
      );
      windowPanel.position.set(x, y, z);
      windowPanel.rotation.y = rot;
      scene.add(windowPanel);

      const windowGlow = new THREE.Mesh(
        new THREE.PlaneGeometry(8.4, 9.2),
        new THREE.MeshBasicMaterial({
          color: 0xffffff,
          transparent: true,
          opacity: 0.16,
          side: THREE.DoubleSide,
        }),
      );
      windowGlow.position.set(x, y, z + 0.04);
      windowGlow.rotation.y = rot;
      scene.add(windowGlow);
    });
  }


  function applyCameraPose(camera, pose) {
    camera.position.set(
      pose.radius * Math.sin(pose.theta) * Math.cos(pose.phi),
      pose.y,
      pose.radius * Math.cos(pose.theta) * Math.cos(pose.phi),
    );
    camera.lookAt(pose.targetX, pose.targetY, pose.targetZ);
  }

  
function setupSimpleOrbitControls(renderer, camera, options = {}) {
        const isDepartment121CameraO16C =
      String(options?.cameraMode || "").endsWith("_121") ||
      String(options?.boardroomTeamMode || "").endsWith("_121");

    const state = isDepartment121CameraO16C
      ? {
          isDragging: false,
          lastX: 0,
          lastY: 0,

          // O16C: closer 1:1 department room camera, focused on the centred director.
          theta: 0,
          phi: 0.038,
          radius: 8.2,
          y: 2.85,
          targetX: 0,
          targetY: 1.65,
          targetZ: -8.15,
        }
      : {
          isDragging: false,
          lastX: 0,
          lastY: 0,

          // AION seated POV: the table is centred at z=-4.6 and its near edge is
          // approximately z=0.2. Keep the camera just behind that edge so the
          // opening frame reads as a seat at the table, not a view from the room.
          theta: 0,
          phi: 0.045,
          radius: 4.6,
          y: 2.5,
          targetX: 0,
          targetY: 1.45,
          targetZ: -6.4,
        };

    applyCameraPose(camera, state);

    function onMouseDown(event) {
      state.isDragging = true;
      state.lastX = event.clientX;
      state.lastY = event.clientY;
    }

    function onMouseMove(event) {
      if (!state.isDragging) return;
      const dx = event.clientX - state.lastX;
      const dy = event.clientY - state.lastY;
      state.lastX = event.clientX;
      state.lastY = event.clientY;

      state.theta -= dx * 0.0045;
      state.phi = clamp(state.phi - dy * 0.0025, -0.06, 0.55);
      state.y = clamp(state.y - dy * 0.006, 2.8, 9.5);
      applyCameraPose(camera, state);
    }

    function onMouseUp() {
      state.isDragging = false;
    }

    function onWheel(event) {
      event.preventDefault();
      state.radius = clamp(state.radius + event.deltaY * 0.012, 3.8, 28);
      applyCameraPose(camera, state);
    }

    const el = renderer.domElement;
    el.addEventListener("mousedown", onMouseDown);
    global.addEventListener("mousemove", onMouseMove);
    global.addEventListener("mouseup", onMouseUp);
    el.addEventListener("wheel", onWheel, { passive: false });

    return function cleanup() {
      el.removeEventListener("mousedown", onMouseDown);
      global.removeEventListener("mousemove", onMouseMove);
      global.removeEventListener("mouseup", onMouseUp);
      el.removeEventListener("wheel", onWheel);
    };
  }

  function setupPointerInteraction(renderer, camera) {
    const THREE = ensureThree();
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();

    function getHit(event) {
      if (!current) return null;
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);

      const hits = raycaster.intersectObjects(
        current.interactives.map((item) => item.mesh),
        false,
      );

      if (!hits.length) return null;

      const found = current.interactives.find((item) => item.mesh === hits[0].object);
      return found ? found.meta : null;
    }

    function handleSelection(meta) {
      if (!current || !meta) return;
      const options = current.options || {};

      if (meta.type === "team_mode_switch") {
        const nextMode = options.boardroomTeamMode === "board" ? "executive" : "board";
        options.boardroomTeamMode = nextMode;
        global.__aionSpatialBoardroomTeamMode = nextMode;
        rebuildWorld(options.snapshot, options);
        return;
      }

      if (meta.type === "seat") {
        options.activeZone = meta.departmentKey;
        options.selectedSeatId = meta.seatId;
        options.selectedInspectorTarget = { kind: "seat", seatId: meta.seatId };

        if (typeof options.onActiveZoneChange === "function") {
          options.onActiveZoneChange(meta.departmentKey);
        }
        if (typeof options.onSeatSelect === "function") {
          options.onSeatSelect(meta.seatId, meta.departmentKey, {
            ...meta,
            teamMode: meta.teamMode || options.boardroomTeamMode || global.__aionSpatialBoardroomTeamMode || "executive",
          });
        }
        if (typeof options.onInspectorTargetChange === "function") {
          options.onInspectorTargetChange({ kind: "seat", seatId: meta.seatId });
        }
      }

      if (meta.type === "stage") {
        options.activeZone = meta.departmentKey;
        options.selectedSeatId = getDepartmentSeatId(meta.departmentKey);
        options.selectedInspectorTarget = {
          kind: `${meta.departmentKey}_stage`,
          stageId: meta.stageId,
        };

        if (typeof options.onActiveZoneChange === "function") {
          options.onActiveZoneChange(meta.departmentKey);
        }
        if (typeof options.onSeatSelect === "function") {
          options.onSeatSelect(options.selectedSeatId, meta.departmentKey);
        }
        if (typeof options.onInspectorTargetChange === "function") {
          options.onInspectorTargetChange({
            kind: `${meta.departmentKey}_stage`,
            stageId: meta.stageId,
          });
        }
      }

      if (meta.type === "agent") {
        options.activeZone = meta.departmentKey;
        options.selectedSeatId = getDepartmentSeatId(meta.departmentKey);
        options.selectedInspectorTarget = {
          kind: `${meta.departmentKey}_agent`,
          agentId: meta.agentId,
        };

        if (typeof options.onActiveZoneChange === "function") {
          options.onActiveZoneChange(meta.departmentKey);
        }
        if (typeof options.onSeatSelect === "function") {
          options.onSeatSelect(options.selectedSeatId, meta.departmentKey);
        }
        if (typeof options.onInspectorTargetChange === "function") {
          options.onInspectorTargetChange({
            kind: `${meta.departmentKey}_agent`,
            agentId: meta.agentId,
          });
        }
      }

      rebuildWorld(options.snapshot, options);

      if (typeof options.requestRender === "function") {
        options.requestRender();
      }
    }

    function onClick(event) {
      const meta = getHit(event);
      if (meta) {
        handleSelection(meta);
      }
    }

    function onMove(event) {
      const meta = getHit(event);
      renderer.domElement.style.cursor = meta ? "pointer" : "default";
    }

    renderer.domElement.addEventListener("click", onClick);
    renderer.domElement.addEventListener("mousemove", onMove);

    return function cleanup() {
      renderer.domElement.removeEventListener("click", onClick);
      renderer.domElement.removeEventListener("mousemove", onMove);
      renderer.domElement.style.cursor = "default";
    };
  }



  function applyAionCinematicMeshQuality(root) {
    if (!root) return;

    root.traverse?.((child) => {
      if (!child || !child.isMesh) return;

      child.castShadow = true;
      child.receiveShadow = true;

      if (child.material) {
        const materials = Array.isArray(child.material) ? child.material : [child.material];

        materials.forEach((mat) => {
          if (!mat) return;

          if ("roughness" in mat && typeof mat.roughness === "number") {
            mat.roughness = Math.max(0.18, Math.min(mat.roughness, 0.72));
          }

          if ("metalness" in mat && typeof mat.metalness === "number") {
            mat.metalness = Math.max(mat.metalness, 0.08);
          }

          mat.needsUpdate = true;
        });
      }
    });
  }


  function rebuildWorld(snapshot, options) {
    if (!current) return;

    clearInteractiveObjects();
    current.syntheticFaceRigs = [];

    if (current.rootGroup) {
      current.scene.remove(current.rootGroup);
      disposeObject(current.rootGroup);
      current.rootGroup = null;
    }

    const rootGroup = buildBoardroomWorld(snapshot || {}, options || {});
    applyAionCinematicMeshQuality(rootGroup);
    current.scene.add(rootGroup);
    current.rootGroup = rootGroup;
    current.options = {
      ...(current.options || {}),
      ...(options || {}),
      snapshot: snapshot || {},
    };

    if (current.teamModeButton) {
      const isBoardMode = current.options.boardroomTeamMode === "board";
      current.teamModeButton.textContent = isBoardMode ? "Show Executive Team" : "Show Board Team";
      current.teamModeButton.setAttribute(
        "aria-label",
        isBoardMode ? "Switch to Executive Team" : "Switch to Board Team",
      );
    }
  }


  /* BEGIN AION O18F REAL AGENT ONLY PORTRAIT RENDERER LOCK */
    function mountAionO18FRealAgentOnlyPortrait(container, options = {}) {
    if (!container) {
      throw new Error("mountAionO18FRealAgentOnlyPortrait requires a container");
    }

    container.innerHTML = "";
    container.dataset.aionO18pCleanAgentPortrait = "true";

    const width = Math.max(260, container.clientWidth || 320);
    const height = Math.max(320, container.clientHeight || 390);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x020617);

    const camera = new THREE.PerspectiveCamera(32, width / height, 0.1, 80);
    camera.position.set(0, 1.52, 6.2);
    camera.lookAt(0, 1.50, 0);

    const portraitRenderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
      powerPreference: "high-performance",
    });

    portraitRenderer.setClearColor(0x020617, 1);
    portraitRenderer.setSize(width, height);
    portraitRenderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    portraitRenderer.domElement.style.width = "100%";
    portraitRenderer.domElement.style.height = "100%";
    portraitRenderer.domElement.dataset.aionO18pCleanAgentPortraitCanvas = "true";
    container.appendChild(portraitRenderer.domElement);

    const ambient = new THREE.HemisphereLight(0xffffff, 0x111827, 2.65);
    scene.add(ambient);

    const key = new THREE.DirectionalLight(0xffffff, 3.6);
    key.position.set(2.4, 4.6, 5.4);
    scene.add(key);

    const fill = new THREE.DirectionalLight(0x93c5fd, 2.1);
    fill.position.set(-3.0, 2.8, 4.4);
    scene.add(fill);

    const rim = new THREE.DirectionalLight(0x67e8f9, 2.2);
    rim.position.set(0, 3.4, -4.5);
    scene.add(rim);

    const agentRoot = new THREE.Group();
    agentRoot.name = "AION_O18P_CLEAN_AGENT_ONLY_ROOT";
    agentRoot.position.set(0, 0.44, 0);
    scene.add(agentRoot);

    function brightenAgentO18P(object) {
      object.traverse((node) => {
        if (!node?.isMesh || !node.material) return;
        const materials = Array.isArray(node.material) ? node.material : [node.material];
        materials.forEach((mat) => {
          if (!mat) return;
          if (mat.color?.setHex) mat.color.setHex(0xf8fafc);
          if (mat.emissive?.setHex) {
            mat.emissive.setHex(0x60a5fa);
            mat.emissiveIntensity = 0.08;
          }
          mat.transparent = false;
          mat.opacity = 1;
          mat.roughness = 0.32;
          mat.metalness = 0.06;
          mat.depthWrite = true;
          mat.needsUpdate = true;
        });
      });
    }

    function addFallbackPortraitAgentO18P() {
      const fallback = new THREE.Group();
      fallback.name = "AION_O18P_FALLBACK_CLEAN_AGENT_ONLY";

      const bodyMat = new THREE.MeshStandardMaterial({
        color: 0xf8fafc,
        emissive: 0x1d4ed8,
        emissiveIntensity: 0.08,
        metalness: 0.06,
        roughness: 0.32,
      });

      const head = new THREE.Mesh(new THREE.SphereGeometry(0.32, 32, 24), bodyMat);
      head.position.set(0, 2.22, 0);
      fallback.add(head);

      const torso = new THREE.Mesh(new THREE.CapsuleGeometry(0.38, 0.76, 12, 24), bodyMat);
      torso.position.set(0, 1.48, 0);
      fallback.add(torso);

      const leftArm = new THREE.Mesh(new THREE.CapsuleGeometry(0.08, 0.58, 8, 16), bodyMat);
      leftArm.position.set(-0.44, 1.48, 0);
      leftArm.rotation.z = -0.18;
      fallback.add(leftArm);

      const rightArm = new THREE.Mesh(new THREE.CapsuleGeometry(0.08, 0.58, 8, 16), bodyMat);
      rightArm.position.set(0.44, 1.48, 0);
      rightArm.rotation.z = 0.18;
      fallback.add(rightArm);

      fallback.scale.set(0.98, 0.98, 0.98);
      agentRoot.add(fallback);
    }

    function installAgentO18P() {
      agentRoot.clear();

      const realAgent = cloneAionBoardroomAsset("robot_agent");
      if (realAgent) {
        normalizeAionBoardroomAgentModel(realAgent, {
          scale: 0.72,
          yOffset: 0,
          forceFront: true,
        });

        realAgent.name = "AION_O18P_CLEAN_REAL_AGENT_ONLY";
        realAgent.position.set(0, 0, 0);
        realAgent.rotation.set(0, Math.PI, 0);
        brightenAgentO18P(realAgent);
        agentRoot.add(realAgent);
      } else {
        addFallbackPortraitAgentO18P();
      }
    }

    installAgentO18P();
    loadAionBoardroomAssetsOnce(() => {
      installAgentO18P();
      portraitRenderer.render(scene, camera);
    });

    let disposed = false;
    let frame = 0;
    let portraitRafId = null;
    let lastPortraitRenderAt = 0;

    function animate(now = 0) {
      if (disposed) return;

      // A remounted department surface used to leave this animation and its
      // WebGL context alive forever.  Stop immediately when the owner leaves
      // the document, and draw the subtle portrait motion at 10fps only while
      // it is actually visible.
      if (!container.isConnected) {
        disposed = true;
        try { portraitRenderer.dispose(); } catch {}
        try { portraitRenderer.forceContextLoss?.(); } catch {}
        return;
      }

      const rect = container.getBoundingClientRect?.();
      const isVisible =
        rect
        && rect.width > 0
        && rect.height > 0
        && rect.bottom >= 0
        && rect.top <= (window.innerHeight || 0);

      if (isVisible && now - lastPortraitRenderAt >= 100) {
        frame += 1;
        agentRoot.rotation.y = Math.sin(frame * 0.04) * 0.025;
        portraitRenderer.render(scene, camera);
        lastPortraitRenderAt = now;
      }

      portraitRafId = requestAnimationFrame(animate);
    }

    portraitRafId = requestAnimationFrame(animate);

    function resize() {
      if (disposed) return;
      const nextWidth = Math.max(260, container.clientWidth || 320);
      const nextHeight = Math.max(320, container.clientHeight || 390);
      camera.aspect = nextWidth / nextHeight;
      camera.updateProjectionMatrix();
      portraitRenderer.setSize(nextWidth, nextHeight);
    }

    window.addEventListener("resize", resize);

    return {
      scene,
      camera,
      renderer: portraitRenderer,
      root: agentRoot,
      dispose() {
        disposed = true;
        if (portraitRafId) window.cancelAnimationFrame(portraitRafId);
        window.removeEventListener("resize", resize);
        try {
          portraitRenderer.dispose();
          portraitRenderer.forceContextLoss?.();
        } catch (error) {
          console.warn("[AION] O18P clean portrait dispose failed", error);
        }
        if (container) container.innerHTML = "";
      },
      updateBoardroom(nextOptions = {}) {
        options = { ...options, ...nextOptions };
        installAgentO18P();
        portraitRenderer.render(scene, camera);
      },
    };
  }


  function updateBoardroom(nextOptions) {
    if (!current) return;
    const merged = {
      ...(current.options || {}),
      ...(nextOptions || {}),
    };
    rebuildWorld(merged.snapshot, merged);
  }

  function mountBoardroom(container, options) {
    const o18fCameraMode = String(options?.cameraMode || "");
    const o18fTeamMode = String(options?.boardroomTeamMode || "");
    const o18fIsDepartment121 =
      o18fCameraMode.endsWith("_121") ||
      o18fTeamMode.endsWith("_121") ||
      options?.agentPortraitMode === true;

    if (o18fIsDepartment121) {
      disposeCurrent();
      currentPortrait = mountAionO18FRealAgentOnlyPortrait(container, options || {});
      return currentPortrait;
    }

    const THREE = ensureThree();
    const opts = options || {};
    disposeCurrent();

    if (!container) {
      throw new Error("mountBoardroom requires a container");
    }

    const width = Math.max(1, container.clientWidth);
    const height = Math.max(1, container.clientHeight);

    const scene = new THREE.Scene();
    buildSceneShell(scene);

    const camera = new THREE.PerspectiveCamera(52, width / height, 0.1, 400);
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
    });

    /*
     * AION O14I performance lock:
     * Keep the spatial boardroom crisp enough, but avoid hammering the GPU on
     * high-DPI Mac displays while the rest of the desktop is scrolling.
     */
    renderer.setPixelRatio(Math.min(global.devicePixelRatio || 1, 1.5));
    renderer.setSize(width, height);
    renderer.outputColorSpace = THREE.SRGBColorSpace;

    if ("ACESFilmicToneMapping" in THREE) {
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 0.94;
    }

    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    container.innerHTML = "";
    const containerStyle = global.getComputedStyle?.(container);
    if (!containerStyle || containerStyle.position === "static") {
      container.style.position = "relative";
    }
    container.appendChild(renderer.domElement);

    const controlsCleanup = setupSimpleOrbitControls(renderer, camera, opts);
    const pointerCleanup = setupPointerInteraction(renderer, camera);

    const onResize = function onResize() {
      if (!current || !current.container) return;
      const nextWidth = Math.max(1, current.container.clientWidth);
      const nextHeight = Math.max(1, current.container.clientHeight);
      current.camera.aspect = nextWidth / nextHeight;
      current.camera.updateProjectionMatrix();
      current.renderer.setSize(nextWidth, nextHeight);
    };

    global.addEventListener("resize", onResize);

    current = {
      container,
      renderer,
      scene,
      camera,
      onResize,
      controlsCleanup,
      pointerCleanup,
      rafId: null,
      lastRenderAt: 0,
      interactives: [],
      options: {
        snapshot: opts.snapshot || {},
        viewMode: opts.viewMode || "spatial",
        activeZone: opts.activeZone || "coo",
        selectedSeatId: opts.selectedSeatId || null,
        selectedInspectorTarget: opts.selectedInspectorTarget || null,
        boardroomTeamMode: opts.boardroomTeamMode || window.__aionSpatialBoardroomTeamMode || "executive",
        visibleDepartments: Array.isArray(opts.visibleDepartments) ? opts.visibleDepartments : null,
        cameraMode: opts.cameraMode || "",
        o16cDepartment121Camera:
          String(opts.cameraMode || "").endsWith("_121") ||
          String(opts.boardroomTeamMode || "").endsWith("_121"),
        onActiveZoneChange: opts.onActiveZoneChange,
        onSeatSelect: opts.onSeatSelect,
        onInspectorTargetChange: opts.onInspectorTargetChange,
        requestRender: opts.requestRender,
      },
      rootGroup: null,
      syntheticFaceRigs: [],
      teamModeButton: null,
    };

    const teamModeButton = document.createElement("button");
    teamModeButton.type = "button";
    teamModeButton.dataset.aionBoardroomTeamSwitch = "true";
    teamModeButton.style.position = "absolute";
    teamModeButton.style.left = "50%";
    teamModeButton.style.bottom = "16px";
    teamModeButton.style.transform = "translateX(-50%)";
    teamModeButton.style.zIndex = "12";
    teamModeButton.style.padding = "10px 18px";
    teamModeButton.style.border = "1px solid rgba(15, 23, 42, 0.28)";
    teamModeButton.style.borderRadius = "4px";
    teamModeButton.style.background = "rgba(255, 255, 255, 0.94)";
    teamModeButton.style.color = "#0f172a";
    teamModeButton.style.font = "800 12px Inter, ui-sans-serif, system-ui, sans-serif";
    teamModeButton.style.letterSpacing = "0.08em";
    teamModeButton.style.textTransform = "uppercase";
    teamModeButton.style.boxShadow = "0 8px 24px rgba(15, 23, 42, 0.16)";
    teamModeButton.style.cursor = "pointer";
    teamModeButton.style.backdropFilter = "blur(10px)";
    teamModeButton.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (!current) return;
      const nextMode = current.options.boardroomTeamMode === "board" ? "executive" : "board";
      current.options.boardroomTeamMode = nextMode;
      global.__aionSpatialBoardroomTeamMode = nextMode;
      rebuildWorld(current.options.snapshot, current.options);
    });
    container.appendChild(teamModeButton);
    current.teamModeButton = teamModeButton;

    loadAionBoardroomAssetsOnce(() => {
      if (!current) return;
      rebuildWorld(current.options.snapshot, current.options);
    });

    rebuildWorld(current.options.snapshot, current.options);

    const animate = function animate() {
      if (!current) return;

      const now =
        global.performance && typeof global.performance.now === "function"
          ? global.performance.now()
          : Date.now();

      const rect = current.container?.getBoundingClientRect?.();
      const isVisible =
        rect &&
        rect.width > 0 &&
        rect.height > 0 &&
        rect.bottom >= 0 &&
        rect.top <= (global.innerHeight || 0);

      /*
       * AION O14I performance lock:
       * - render at about 30fps max instead of every browser frame
       * - skip WebGL drawing when the boardroom canvas is off-screen
       * This keeps scrolling responsive without removing the live 3D room.
       */
      if (isVisible && now - (current.lastRenderAt || 0) >= 33) {
        const faceTime = now * 0.001;
        (current.syntheticFaceRigs || []).forEach((face) => {
          if (!face?.userData?.aionSyntheticIdentity) return;
          const seed = Number(face.userData.seed || 0);
          const blinkPhase = (faceTime + seed) % 4.8;
          const eyeScaleY = blinkPhase > 4.64 ? 0.08 : 0.58;
          (face.userData.eyes || []).forEach((eye) => {
            if (eye?.scale) eye.scale.y = eyeScaleY;
          });
          (face.userData.voiceBars || []).forEach((bar, index) => {
            if (!bar?.scale) return;
            bar.scale.y = 0.72 + Math.abs(Math.sin(faceTime * 2.1 + seed + index * 0.72)) * 0.58;
          });
        });
        current.renderer.render(current.scene, current.camera);
        current.lastRenderAt = now;
      }

      current.rafId = global.requestAnimationFrame(animate);
    };

    animate();
    return current;
  }

  global.TessarisDesktopBoardroomRenderer = {
    mountBoardroom,
    updateBoardroom,
    mountAionO18FRealAgentOnlyPortrait,
    disposeBoardroom: disposeCurrent,
  };
})(window);
/* BEGIN AION O15D BOARDROOM CONNECTED PROVIDER VISIBILITY LOCK */
/*
 * Fix:
 * - Boardroom snapshot already contains CEO, AION, Gemma, OpenAI, Gemini.
 * - Older 3D render path can visually drop connected_provider seats.
 * - This lock adds a DOM/3D-visible provider rail over the spatial boardroom
 *   using the actual renderer state snapshot, so connected Vault providers
 *   are visible and missing providers are not faked.
 */
(function installAionO15DBoardroomConnectedProviderVisibilityLock() {
  if (typeof window === "undefined") return;
  if (window.__aionO15DBoardroomConnectedProviderVisibilityInstalled === true) return;
  window.__aionO15DBoardroomConnectedProviderVisibilityInstalled = true;

  const STYLE_ID = "aion-o15d-boardroom-connected-provider-visibility-style";
  const RAIL_ID = "aionO15DBoardroomConnectedProviderRail";

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function installStyle() {
    if (document.getElementById(STYLE_ID)) return;

    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      #${RAIL_ID} {
        position: absolute;
        left: 50%;
        bottom: 74px;
        transform: translateX(-50%);
        z-index: 30;
        display: flex;
        align-items: flex-end;
        justify-content: center;
        gap: 18px;
        pointer-events: none;
        max-width: calc(100% - 120px);
      }

      #${RAIL_ID} .aion-o15d-provider-seat {
        min-width: 92px;
        max-width: 128px;
        display: grid;
        justify-items: center;
        gap: 5px;
        filter: drop-shadow(0 10px 18px rgba(15, 23, 42, .20));
      }

      #${RAIL_ID} .aion-o15d-provider-avatar {
        width: 36px;
        height: 36px;
        border-radius: 999px;
        background:
          radial-gradient(circle at 50% 28%, rgba(255,255,255,.95), rgba(226,232,240,.86) 42%, rgba(148,163,184,.86) 100%);
        border: 1px solid rgba(15,23,42,.18);
      }

      #${RAIL_ID} .aion-o15d-provider-label {
        padding: 4px 7px;
        border-radius: 3px;
        background: rgba(5, 9, 23, .92);
        color: #ffffff;
        font-size: 10px;
        line-height: 1;
        font-weight: 950;
        letter-spacing: .02em;
        text-align: center;
        white-space: nowrap;
      }

      #${RAIL_ID} .aion-o15d-provider-status {
        padding: 3px 6px;
        border-radius: 999px;
        background: rgba(22, 163, 74, .92);
        color: #ffffff;
        font-size: 8px;
        line-height: 1;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: .08em;
      }
    `;
    document.head.appendChild(style);
  }

  function normaliseProviderSeat(seat) {
    if (!seat || typeof seat !== "object") return null;

    const id = String(seat.provider_id || seat.key || seat.id || "").trim().toLowerCase();
    const label = String(seat.label || id || "").trim();

    if (!id || !label) return null;

    const isProvider =
      seat.seat_type === "connected_provider" ||
      seat.provider_id ||
      ["gemma", "openai", "gemini", "claude", "grok"].includes(id);

    const isVisible =
      seat.connected === true ||
      seat.status === "connected" ||
      seat.status === "always_on" ||
      ["ceo", "aion"].includes(id);

    if (!isProvider && !["ceo", "aion"].includes(id)) return null;
    if (!isVisible) return null;

    return {
      id,
      label: label.replace(" / Google", ""),
      status: ["ceo", "aion"].includes(id) ? "always on" : "connected",
    };
  }

  function connectedSeatsFromState(rendererState = {}) {
    const snapshot = rendererState.snapshot || {};
    const fromSnapshot = safeArray(snapshot.seats).map(normaliseProviderSeat).filter(Boolean);

    const seen = new Set();
    return fromSnapshot.filter((seat) => {
      if (seen.has(seat.id)) return false;
      seen.add(seat.id);
      return true;
    });
  }

  function findMount() {
    return (
      document.getElementById("spatialBoardroomMount") ||
      document.querySelector(".spatial-boardroom-mount") ||
      document.querySelector("[data-aion-spatial-boardroom-main-panel='true']")
    );
  }

  function renderProviderRail(rendererState = {}) {
    const mount = findMount();
    if (!mount) return;

    installStyle();

    const seats = connectedSeatsFromState(rendererState);
    if (!seats.length) return;

    const parent = mount.parentElement || mount;
    const computed = window.getComputedStyle(parent);
    if (computed.position === "static") {
      parent.style.position = "relative";
    }

    let rail = parent.querySelector(`#${RAIL_ID}`);
    if (!rail) {
      rail = document.createElement("div");
      rail.id = RAIL_ID;
      rail.setAttribute("data-aion-o15d-boardroom-connected-provider-rail", "true");
      parent.appendChild(rail);
    }

    rail.innerHTML = seats.map((seat) => `
      <div class="aion-o15d-provider-seat" data-aion-o15d-provider-seat="${escapeHtml(seat.id)}">
        <div class="aion-o15d-provider-label">${escapeHtml(seat.label)}</div>
        <div class="aion-o15d-provider-avatar"></div>
        <div class="aion-o15d-provider-status">${escapeHtml(seat.status)}</div>
      </div>
    `).join("");
  }

  function patchRenderer() {
    const renderer = window.TessarisDesktopBoardroomRenderer;
    if (!renderer || renderer.__aionO15DProviderRailPatched === true) return false;

    const originalMount = renderer.mountBoardroom;
    const originalUpdate = renderer.updateBoardroom;

    if (typeof originalMount === "function") {
      renderer.mountBoardroom = function mountBoardroomWithProviderRailO15D(mount, rendererState = {}) {
        const result = originalMount.apply(this, arguments);
        window.setTimeout(() => renderProviderRail(rendererState), 0);
        window.setTimeout(() => renderProviderRail(rendererState), 120);
        return result;
      };
    }

    if (typeof originalUpdate === "function") {
      renderer.updateBoardroom = function updateBoardroomWithProviderRailO15D(rendererState = {}) {
        const result = originalUpdate.apply(this, arguments);
        window.setTimeout(() => renderProviderRail(rendererState), 0);
        window.setTimeout(() => renderProviderRail(rendererState), 120);
        return result;
      };
    }

    renderer.__aionO15DProviderRailPatched = true;
    return true;
  }

  patchRenderer();
  window.setTimeout(patchRenderer, 250);
  window.setTimeout(patchRenderer, 1000);

  window.__debugAionO15DProviderRail = function debugAionO15DProviderRail() {
    const rail = document.getElementById(RAIL_ID);
    return {
      installed: true,
      rendererPatched: window.TessarisDesktopBoardroomRenderer?.__aionO15DProviderRailPatched === true,
      railExists: Boolean(rail),
      visibleProviderLabels: rail
        ? [...rail.querySelectorAll(".aion-o15d-provider-label")].map((el) => el.textContent.trim())
        : [],
      snapshotSeats: safeArray(window.getBoardroomSnapshot?.().seats).map((seat) => ({
        id: seat.id,
        label: seat.label,
        provider_id: seat.provider_id,
        seat_type: seat.seat_type,
        connected: seat.connected,
        status: seat.status,
      })),
    };
  };

  console.info("[AION] O15D Boardroom connected provider visibility lock installed");
})();
 /* END AION O15D BOARDROOM CONNECTED PROVIDER VISIBILITY LOCK */


/* BEGIN AION O16D DEPARTMENT 121 VISIBLE CENTER AGENT LOCK */
/*
 * O16D:
 * - O16C moved the 1:1 department agent to x=0 but too far into the table.
 * - The table occluded the robot.
 * - The visible centre position is now the centre-back table edge: x=0, z=-8.25.
 */
 /* END AION O16D DEPARTMENT 121 VISIBLE CENTER AGENT LOCK */


/* BEGIN AION O16G DEPARTMENT 121 LOWER TABLE POV LOCK */
/*
 * O16G:
 * - 1:1 department view was clean but too elevated.
 * - Lowered camera to board-table seated height.
 * - Kept agent fixed at the visible centre-back table position.
 */
 /* END AION O16G DEPARTMENT 121 LOWER TABLE POV LOCK */


/* BEGIN AION O18C5 REAL AGENT PORTRAIT CAMERA LOCK */
/*
 * O18C5:
 * - Keeps the real robot_agent.glb / real 3D renderer.
 * - Retracts fake HUD overlay from O18B.
 * - Converts department 1:1 view into a FaceTime-style portrait camera.
 */
/* END AION O18C5 REAL AGENT PORTRAIT CAMERA LOCK */


/* BEGIN AION O18D REAL AGENT SAFE PORTRAIT CAMERA LOCK */
/*
 * O18D:
 * Safe department 1:1 camera.
 * Keeps the real 3D agent visible without the broken extreme close-up.
 * Values: phi 0.038, radius 8.2, y 2.85, targetY 1.65, targetZ -8.15.
 */
/* END AION O18D REAL AGENT SAFE PORTRAIT CAMERA LOCK */


/* BEGIN AION O18F REAL AGENT ONLY PORTRAIT RENDERER EXPORT LOCK */
/*
 * Department/function 1:1 windows now use a renderer-level agent-only portrait mode.
 * Normal boardroom mode remains unchanged.
 */
/* END AION O18F REAL AGENT ONLY PORTRAIT RENDERER EXPORT LOCK */


/* BEGIN AION O18G AGENT PORTRAIT BODY POSITION LOCK */
/*
 * O18G:
 * Fixes O18F real-agent FaceTime portrait framing.
 * - Camera pulled back from 5.2 to 7.2.
 * - Agent root moved up from -0.98 to -0.08.
 * - Real GLB scale reduced from 1.72 to 0.92.
 * - Internal 3D label hidden so it does not overlay the agent body.
 */
/* END AION O18G AGENT PORTRAIT BODY POSITION LOCK */


/* BEGIN AION O18H DARK PORTRAIT REMOVE OVERLAY LOCK */
/*
 * O18H:
 * - Removes the large circular FaceTime halo overlay.
 * - Switches portrait renderer background to dark.
 * - Brightens the real robot_agent.glb material so the agent is visible.
 */
/* END AION O18H DARK PORTRAIT REMOVE OVERLAY LOCK */


/* BEGIN AION O18I REMOVE PORTRAIT HALO COMPLETELY LOCK */
/*
 * O18I:
 * Removes the giant circular/halo overlay from the FaceTime portrait renderer.
 * Keeps the real 3D agent and replaces the circle with a subtle rectangular dark backplate.
 */
/* END AION O18I REMOVE PORTRAIT HALO COMPLETELY LOCK */


/* BEGIN AION O18J FORCE REMOVE PORTRAIT OVAL LOCK */
/*
 * O18J:
 * Force-removes portrait-only halo/ring/backGlow overlays from O18F renderer.
 * The FaceTime frame should now contain only the real 3D agent on a dark background.
 */
/* END AION O18J FORCE REMOVE PORTRAIT OVAL LOCK */


/* BEGIN AION O18K CLEAN REAL AGENT PORTRAIT RENDERER LOCK */
/*
 * O18K:
 * Replaces the portrait renderer with a clean agent-only scene.
 * No halo. No RingGeometry. No backGlow. No table. No boardroom. No internal label.
 */
/* END AION O18K CLEAN REAL AGENT PORTRAIT RENDERER LOCK */


/* BEGIN AION O18M SANITIZE PORTRAIT WEBGL SCENE EXPORT LOCK */
/*
 * O18M:
 * Force-removes the visible portrait oval from the actual WebGL scene.
 * It hides RingGeometry/CircleGeometry/halo/glow/backdrop/label meshes and any oversized dark flat mesh.
 */
/* END AION O18M SANITIZE PORTRAIT WEBGL SCENE EXPORT LOCK */


/* BEGIN AION O18N2 ROBUST REMOVE PORTRAIT BACKDROP LOCK */
/*
 * O18N2:
 * Robustly removes the actual portrait renderer backdrop/halo/backGlow meshes.
 * This targets the visible oval/circle inside the WebGL portrait scene.
 */
/* END AION O18N2 ROBUST REMOVE PORTRAIT BACKDROP LOCK */


/* BEGIN AION O18P REBUILD CLEAN AGENT PORTRAIT NO FRAME LOCK */
/*
 * O18P:
 * Full reset of the function portrait renderer.
 * Real robot_agent.glb only.
 * No boardroom. No backdrop plane. No halo. No ring. No glow. No label mesh. No oval.
 */
/* END AION O18P REBUILD CLEAN AGENT PORTRAIT NO FRAME LOCK */


/* BEGIN AION O18S AGENT PORTRAIT LIFT LOCK */
/*
 * O18S:
 * Lifts the real agent inside the terminal portrait frame.
 * agentRoot y: 0.44
 * camera lookAt y: 1.50
 */
/* END AION O18S AGENT PORTRAIT LIFT LOCK */
