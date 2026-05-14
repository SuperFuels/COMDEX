(function initDesktopBoardroomRenderer(global) {
  function ensureThree() {
    if (!global.THREE) {
      throw new Error("THREE must be loaded before desktop-boardroom-renderer.js");
    }
    return global.THREE;
  }

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

  function buildExecutiveBots(parent) {
    const ceo = buildHexFloor("CEO", 0x60a5fa, -6.8, -24.2, { scale: 0.9 });
    const aion = buildHexFloor("AION", 0x8b5cf6, 0, -26.6, { scale: 0.94 });
    const openai = buildHexFloor("OpenAI", 0x22c55e, 6.8, -24.2, { scale: 0.9 });

    parent.add(ceo);
    parent.add(aion);
    parent.add(openai);
  }

  function buildBoardroomWorld(snapshot, options) {
    const THREE = ensureThree();
    const root = new THREE.Group();
    const pulse = getPulse(snapshot);
    const center = getCenter(snapshot);
    const floors = getFloors(snapshot);
    const activeZone = options?.activeZone || "coo";
    const selectedInspectorTarget = options?.selectedInspectorTarget || null;
    const selectedSeatId = options?.selectedSeatId || null;
    const ringRadius = 14.2;

    buildBillboard(root, snapshot);
    buildExecutiveBots(root);

    const positions = {};
    Object.keys(BOARDROOM_ZONES).forEach((key) => {
      positions[key] = zonePosition(key, ringRadius);
    });

    [
      ["coo", "marketing"],
      ["coo", "sales"],
      ["coo", "operations"],
      ["coo", "hr"],
      ["coo", "support"],
      ["coo", "finance"],
    ].forEach(([a, b]) => {
      addLine(
        root,
        [positions[a][0], -0.08, positions[a][2]],
        [positions[b][0], -0.08, positions[b][2]],
        0x8ea3bf,
        0.24,
      );
    });

    const centerSubtext = [
      `Cash ${center.cash || money(pulse?.cash?.onHand)}`,
      `Rev ${center.revenue || money(pulse?.sales?.revenue)}`,
      `Backlog ${center.pipeline || asText(pulse?.ops?.backlog)}`,
    ].join(" · ");

    const cooFloor = buildHexFloor(
      "COO Core",
      0x1a8aff,
      positions.coo[0],
      positions.coo[2],
      {
        dark: true,
        scale: 1.26,
        active: activeZone === "coo" || selectedSeatId === "seat_coo",
        subtext: centerSubtext,
        subtextColor: "#93c5fd",
        stateText: center.health || pulse?.risk?.cash || "LOW",
        stateColorText: "#22c55e",
      },
    );
    root.add(cooFloor);

    const cooPads = new THREE.Group();
    cooPads.position.set(positions.coo[0], 0, positions.coo[2]);
    cooPads.add(buildMetricPad("Cash", money(pulse?.cash?.onHand), -1.35, -0.72, 0x1a8aff));
    cooPads.add(buildMetricPad("Revenue", money(pulse?.sales?.revenue), 0, -0.72, 0x1a8aff));
    cooPads.add(buildMetricPad("GM", percent(pulse?.finance?.grossMarginPct), 1.35, -0.72, 0x22c55e));
    cooPads.add(buildMetricPad("Stock Value", money(pulse?.stock?.value), -1.35, 0.05, 0xf59e0b));
    cooPads.add(buildMetricPad("Days Cover", `${asText(pulse?.stock?.daysCover)}d`, 0, 0.05, 0xf59e0b));
    cooPads.add(buildMetricPad("Backlog", asText(pulse?.ops?.backlog), 1.35, 0.05, 0x8b5cf6));
    cooPads.add(buildMetricPad("Creditor Days", `${asText(pulse?.finance?.creditorDays)}d`, -1.35, 0.82, 0x64748b));
    cooPads.add(buildMetricPad("Debtor Days", `${asText(pulse?.finance?.debtorDays)}d`, 0, 0.82, 0x64748b));
    cooPads.add(
      buildMetricPad(
        "Cash Risk",
        asText(pulse?.risk?.cash).toUpperCase(),
        1.35,
        0.82,
        seatStateColor(
          pulse?.risk?.cash === "high"
            ? "blocked"
            : pulse?.risk?.cash === "medium"
              ? "warning"
              : "healthy",
        ),
      ),
    );
    root.add(cooPads);

    const departmentKeys = getRenderableDepartmentKeys(snapshot).filter(
      (key) => !["coo", "ceo", "aion", "openai"].includes(key),
    );

    departmentKeys.forEach((key) => {
      const zone = BOARDROOM_ZONES[key];
      const position = positions[key];
      const seatId = getDepartmentSeatId(key);

      const seat = getSeatById(snapshot, seatId);
      const floor = buildHexFloor(zone.label, zone.color, position[0], position[2], {
        scale: zone.scale,
        active: activeZone === key || selectedSeatId === seatId,
        stateText: seat?.state || "healthy",
        stateColorText:
          seat?.state === "blocked"
            ? "#ef4444"
            : seat?.state === "warning"
              ? "#f59e0b"
              : "#22c55e",
      });

      root.add(floor);
      registerInteractive(floor.children[1] || floor, {
        type: "seat",
        departmentKey: key,
        seatId,
      });

      renderDepartmentInterior(
        root,
        key,
        floors?.[key],
        position,
        selectedInspectorTarget,
        snapshot,
      );
    });

    return root;
  }

  function buildSceneShell(scene) {
    const THREE = ensureThree();

    scene.background = new THREE.Color("#eef3f9");
    scene.fog = new THREE.Fog("#eef3f9", 58, 180);

    const ambient = new THREE.AmbientLight(0xffffff, 1.12);
    scene.add(ambient);

    const key = new THREE.DirectionalLight(0xffffff, 1.15);
    key.position.set(8, 14, 10);
    scene.add(key);

    const fill = new THREE.DirectionalLight(0xffffff, 0.45);
    fill.position.set(-8, 8, -10);
    scene.add(fill);

    const grid = new THREE.GridHelper(
      180,
      140,
      new THREE.Color("#8fb8ea"),
      new THREE.Color("#c8ddf5"),
    );
    grid.position.set(0, -0.94, 0);
    grid.material.transparent = true;
    grid.material.opacity = 0.58;
    scene.add(grid);

    const plane = new THREE.Mesh(
      new THREE.PlaneGeometry(220, 220),
      new THREE.MeshStandardMaterial({
        color: 0xedf2f8,
        roughness: 0.98,
        metalness: 0.02,
      }),
    );
    plane.rotation.x = -Math.PI / 2;
    plane.position.set(0, -0.96, 0);
    scene.add(plane);
  }

  function applyCameraPose(camera, pose) {
    camera.position.set(
      pose.radius * Math.sin(pose.theta) * Math.cos(pose.phi),
      pose.y,
      pose.radius * Math.cos(pose.theta) * Math.cos(pose.phi),
    );
    camera.lookAt(pose.targetX, pose.targetY, pose.targetZ);
  }

  function setupSimpleOrbitControls(renderer, camera) {
    const state = {
      isDragging: false,
      lastX: 0,
      lastY: 0,
      theta: 0,
      phi: 0.42,
      radius: 32,
      y: 18,
      targetX: 0,
      targetY: 0,
      targetZ: -4,
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

      state.theta -= dx * 0.008;
      state.phi = clamp(state.phi - dy * 0.004, 0.12, 1.18);
      applyCameraPose(camera, state);
    }

    function onMouseUp() {
      state.isDragging = false;
    }

    function onWheel(event) {
      event.preventDefault();
      state.radius = clamp(state.radius + event.deltaY * 0.02, 12, 80);
      state.y = clamp(state.radius * 0.56, 7, 38);
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

      if (meta.type === "seat") {
        options.activeZone = meta.departmentKey;
        options.selectedSeatId = meta.seatId;
        options.selectedInspectorTarget = { kind: "seat", seatId: meta.seatId };

        if (typeof options.onActiveZoneChange === "function") {
          options.onActiveZoneChange(meta.departmentKey);
        }
        if (typeof options.onSeatSelect === "function") {
          options.onSeatSelect(meta.seatId, meta.departmentKey);
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

  function rebuildWorld(snapshot, options) {
    if (!current) return;

    clearInteractiveObjects();

    if (current.rootGroup) {
      current.scene.remove(current.rootGroup);
      disposeObject(current.rootGroup);
      current.rootGroup = null;
    }

    const rootGroup = buildBoardroomWorld(snapshot || {}, options || {});
    current.scene.add(rootGroup);
    current.rootGroup = rootGroup;
    current.options = {
      ...(current.options || {}),
      ...(options || {}),
      snapshot: snapshot || {},
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

    const camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 400);
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
    });

    renderer.setPixelRatio(Math.min(global.devicePixelRatio || 1, 2));
    renderer.setSize(width, height);
    renderer.outputColorSpace = THREE.SRGBColorSpace;

    container.innerHTML = "";
    container.appendChild(renderer.domElement);

    const controlsCleanup = setupSimpleOrbitControls(renderer, camera);
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
      interactives: [],
      options: {
        snapshot: opts.snapshot || {},
        viewMode: opts.viewMode || "spatial",
        activeZone: opts.activeZone || "coo",
        selectedSeatId: opts.selectedSeatId || null,
        selectedInspectorTarget: opts.selectedInspectorTarget || null,
        onActiveZoneChange: opts.onActiveZoneChange,
        onSeatSelect: opts.onSeatSelect,
        onInspectorTargetChange: opts.onInspectorTargetChange,
        requestRender: opts.requestRender,
      },
      rootGroup: null,
    };

    rebuildWorld(current.options.snapshot, current.options);

    const animate = function animate() {
      if (!current) return;
      current.renderer.render(current.scene, current.camera);
      current.rafId = global.requestAnimationFrame(animate);
    };

    animate();
    return current;
  }

  global.TessarisDesktopBoardroomRenderer = {
    mountBoardroom,
    updateBoardroom,
    disposeBoardroom: disposeCurrent,
  };
})(window);